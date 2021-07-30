git push vtp-prod master
heroku run python src/circus/manage.py syncdb --app via-translation-portal
heroku run python src/circus/manage.py migrate --app via-translation-portal
