git push circus-dev master
heroku run python src/circus/manage.py syncdb --app circus-dev
heroku run python src/circus/manage.py migrate --app circus-dev
