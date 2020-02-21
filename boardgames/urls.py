from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('update/<str:bgg_username>/', views.update, name='update'),
    path('update_bgstats', views.update_bgstats, name='update_bgstats'),
    path('games/<int:game_id>/', views.game_view, name='game'),
    path('games/', views.games_index, name='game_index'),
    path('categories/<int:category_id>/', views.category_view, name='category'),
    path('categories/', views.categories_index, name='categories_index'),
    path('mechanics/<int:mechanic_id>/', views.mechanic_view, name='mechanic'),
    path('mechanics/', views.mechanics_index, name='mechanics_index'),
    path('statistics', views.view_statistics, name='statistics'),
]
