# Django server

This is a basic Django server that will be connected to all applications I write. Uses Python 3.7.4 and django 3.0.2.

# Install

Clone this repo with the following command to whatever local location you desire using:

`git clone https://github.com/SnarkAttack/server.git`

Install pipenv using `pip3 install pipenv`.

Navigate into the server folder and run `pipenv install`, which will install all required packages.

Run the server using the standard `python3 manage.py runserver`

If you for some reason intend to use this in production, please for the love of all that is good any holy change the SECRET_KEY in settings/settings.py. A new one can be generated with:

`python3 manage.py shell -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"`
