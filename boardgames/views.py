from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from django.urls import reverse
import requests
import xmltodict
from .models import BoardGame, BoardGameCategory, BoardGameMechanic, BoardGameExpansion, Player, Play, PlayerScore
from collections import OrderedDict
from time import sleep
from functools import partial
from django.db.models.query import QuerySet
import json

base_game_only_func = partial(BoardGame.objects.all().filter, boardgameexpansion__isnull=True)

def index(request):
    return HttpResponse("Nothing at the base here right now")

def update_game_model_from_bgstats(game_data, game):

	game.bgstats_id = game_data['id']
	if game_data.get('bggName', None) is not None:
		game.name = game_data['bggName']
	else:
		game.name = game_data['name']
	game.no_points = game_data.get('noPoints', None)
	game.highest_wins = game_data.get('highestWins', None)
	game.cooperative = game_data.get('cooperative', None)
	game.uses_teams = game_data.get('usesTeams', None)

	return True

def create_or_update_player_model(player_data, player):

	player.player_name = player_data.get('name', None)
	player.bgg_username = player_data.get('bggUsername', None)
	player.bgstats_uuid = player_data.get('uuid', None)

	return True

def create_or_update_play_model(play_data, play):

	play.game = BoardGame.objects.get(bgstats_id=play_data['gameRefId'])
	print(play.game)
	play.play_date = play_data.get('playDate', None)
	play.ignore = play_data.get('ignored', None)

	return True

def str_repr_int(str_to_test):

	return len(str_to_test) > 0 and (all(str_to_test[i] in "0123456789" for i in range(len(str_to_test))) or (str_to_test[0] in "+-" and all(str_to_test[i] in "0123456789" for i in range(1,len(str_to_test)))))

def create_or_update_player_score_model(player_score_data, player_score):

	score = player_score_data.get('score', '')
	player_score.score = score if str_repr_int(score) else None
	player_score.role = player_score_data.get('role', None)
	player_score.start_player = player_score_data.get('startPlayer', False)
	player_score.seat_order = player_score_data.get('seatOrder', 0)
	player_score.new_player = player_score_data.get('newPlayer', False)
	team = player_score_data.get('team', '')
	player_score.team = team if str_repr_int(team) else None
	# This field is required
	player_score.winner = player_score_data.get('winner')

	return True


def update_bgstats(players_data):

	f = open('BGStatsExport.json', 'r')
	plays_data = json.load(f)

	for game_data in plays_data['games']:
		game, _ = BoardGame.objects.get_or_create(bgg_id=game_data['bggId'])
		update_game_model_from_bgstats(game_data, game)
		game.save()

	for player_data in plays_data['players']:
		player, _ = Player.objects.get_or_create(bgstats_id=player_data['id'])
		create_or_update_player_model(player_data, player)
		player.save()

	for play_data in plays_data['plays']:
		play, _ = Play.objects.get_or_create(play_uuid=play_data['uuid'])
		create_or_update_play_model(play_data, play)
		print(play.game)
		print(play.game.name)
		play.save()

		for player_score_data in play_data['playerScores']:
			player_score, _ = play.player_scores.get_or_create(player=Player.objects.get(bgstats_id=player_score_data['playerRefId']))
			create_or_update_player_score_model(player_score_data, player_score)
			player_score.play = play
			player_score.save()

	return HttpResponseRedirect(reverse('game_index'))

def create_or_update_board_game_model(boardgame_model, game_dict_contents):

    name = game_dict_contents['name']
    if type(name) is list:
        for name in game_dict_contents['name']:
            if name['@type'] == 'primary':
                boardgame_model.name = name['@value']
    else:
        boardgame_model.name = name['@value']

    print(boardgame_model.name)

    boardgame_model.min_players = game_dict_contents['minplayers']['@value']
    boardgame_model.max_players = game_dict_contents['maxplayers']['@value']

    best_player_count = 0
    for item in game_dict_contents['poll']:
        if item['@name'] == 'suggested_numplayers':
            best = 0
            for row in item['results']:
                if int(row['result'][0]['@numvotes']) > best:
                    best_player_count = int(row['@numplayers'])
                    best = int(row['result'][0]['@numvotes'])

    boardgame_model.best_with = best_player_count

    boardgame_model.len_m = game_dict_contents['playingtime']['@value']
    boardgame_model.min_len_m = game_dict_contents['minplaytime']['@value']
    boardgame_model.max_len_m = game_dict_contents['maxplaytime']['@value']

    ratings_dict = game_dict_contents['statistics']['ratings']

    boardgame_model.average = ratings_dict['average']['@value']
    boardgame_model.bayes_average = ratings_dict['bayesaverage']['@value']

    boardgame_model.weight = ratings_dict['averageweight']['@value']

    categories = []
    mechanics = []
    for link in game_dict_contents['link']:
        if link['@type'] == 'boardgamecategory':
            category, created = BoardGameCategory.objects.get_or_create(category_name=link['@value'])
            if created:
                category.save()
            boardgame_model.categories.add(category)
        elif link['@type'] == 'boardgamemechanic':
            mechanic, created = BoardGameMechanic.objects.get_or_create(mechanic_name=link['@value'])
            if created:
                mechanic.save()
            boardgame_model.mechanics.add(mechanic)
        elif link['@type'] == 'boardgameexpansion' and link.get('@inbound', None) is not None:
            base_game, created = BoardGame.objects.get_or_create(bgg_id=link['@id'])
            if created:
                base_game.save()
            boardgame_model.base_game = base_game

    return True

def update(request, bgg_username):
    # Only gets board games (no expansions), needs to be a second call per BGG API documentation
    url = f"https://www.boardgamegeek.com/xmlapi2/collections?username={bgg_username}&own=1&excludesubtype=boardgameexpansion"

    r = requests.get(url)
    while r.status_code == 202:
        r = requests.get(url)

    collection_dict = xmltodict.parse(r.text)['items']['item']

    for game in collection_dict:
        sleep_len_s = 2
        game_url = f"https://www.boardgamegeek.com/xmlapi2/thing?id={game['@objectid']}&stats=1"

        sleep(sleep_len_s)
        gr = requests.get(game_url)

        # HTTP Too Many Requests code
        while gr.status_code == 429:
            sleep_len_s *= 2
            print(f"Sleeping {sleep_len_s}")
            sleep(sleep_len_s)
            gr = requests.get(game_url)
        if gr.status_code == 200:
            game_response = gr.text
            game_data = xmltodict.parse(game_response)
            obj, created = BoardGame.objects.get_or_create(bgg_id=game['@objectid'])
            create_or_update_board_game_model(obj, game_data['items']['item'])
            obj.owners.add(Player.objects.get_or_create(bgg_username=bgg_username)[0])
            obj.save()

    owned_expansion_url = f"https://www.boardgamegeek.com/xmlapi2/collections?username={bgg_username}&own=1&subtype=boardgameexpansion"

    oer = requests.get(owned_expansion_url)
    while oer.status_code == 202:
        oer = requests.get(url)

    exp_collection_dict = xmltodict.parse(oer.text)['items']['item']

    for expansion in exp_collection_dict:
        sleep_len_s = 2
        expansion_url = f"https://www.boardgamegeek.com/xmlapi2/thing?id={expansion['@objectid']}&stats=1"

        sleep(sleep_len_s)
        er = requests.get(expansion_url)

        # HTTP Too Many Requests code
        while er.status_code == 429:
            sleep_len_s *= 2
            sleep(sleep_len_s)
            print(f"Sleeping {sleep_len_s}")
            er = requests.get(expansion_url)

        if er.status_code == 200:
            expansion_response = er.text
            expansion_data = xmltodict.parse(expansion_response)
            exp, created = BoardGameExpansion.objects.get_or_create(bgg_id=expansion['@objectid'])
            create_or_update_board_game_model(exp, expansion_data['items']['item'])
            exp.owners.add(Player.objects.get_or_create(bgg_username=bgg_username)[0])
            exp.save()

    return HttpResponseRedirect(reverse('game_index'))

def games_index(request):
    boardgames_list = base_game_only_func().order_by('name')
    expansions_list = BoardGameExpansion.objects.all().order_by("name")
    template = loader.get_template('boardgames/game_index.html')
    context = {
        'boardgames_list': boardgames_list,
        'expansions_list': expansions_list,
    }
    return HttpResponse(template.render(context, request))

def game_view(request, game_id):
    boardgame = BoardGame.objects.get(id=game_id)
    expansions = None
    try:
        boardgame = BoardGameExpansion.objects.get(id=game_id)
    except:
        pass

    try:
        expansions = BoardGame.objects.get(id=game_id).expansions.all()
    except:
        pass
    template = loader.get_template('boardgames/game.html')
    context = {
        'boardgame': boardgame,
        'expansions': expansions
    }
    return HttpResponse(template.render(context, request))

def categories_index(request):
    categories_list = BoardGameCategory.objects.all().order_by('category_name')
    template = loader.get_template('boardgames/category_index.html')
    context = {
        'categories_list': categories_list,
    }
    return HttpResponse(template.render(context, request))

def category_view(request, category_id):
    category = BoardGameCategory.objects.get(id=category_id)
    template = loader.get_template('boardgames/category.html')
    context = {
        'category': category,
    }
    return HttpResponse(template.render(context, request))

def mechanics_index(request):
    mechanics_list = BoardGameMechanic.objects.all().order_by('mechanic_name')
    template = loader.get_template('boardgames/mechanic_index.html')
    context = {
        'mechanics_list': mechanics_list,
    }
    return HttpResponse(template.render(context, request))

def mechanic_view(request, mechanic_id):
    mechanic = BoardGameMechanic.objects.get(id=mechanic_id)
    template = loader.get_template('boardgames/mechanic.html')
    context = {
        'mechanic': mechanic,
    }
    return HttpResponse(template.render(context, request))

def view_statistics(request):
    boardgames_list = BoardGame.objects.all()
    results = {}
    average_average = 0
    average_weight = 0
    for boardgame in boardgames_list:
        average_average += boardgame.average
        average_weight += boardgame.weight
        
    all_categories = BoardGameCategory.objects.all().order_by('category_name')
    all_mechanics = BoardGameMechanic.objects.all().order_by('mechanic_name')
        
        
    results['average'] = average_average/len(boardgames_list)
    results['weight'] = average_weight/len(boardgames_list)
    results['categories'] = all_categories
    results['len_categories'] = len(all_categories)
    results['mechanics'] = all_mechanics
    results['len_mechanics'] = len(all_mechanics)
    
    template = loader.get_template('boardgames/statistics.html')
    context = {
        'statistics': results,
    }
    return HttpResponse(template.render(context, request))


    
