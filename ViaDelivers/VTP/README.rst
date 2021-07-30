
* install python 2.7
* install postgresql and postgresql-dev packages (postgresq 9.1)
* install libevent-dev for gevent
* install all PIP requirements.txt

| load backup of existing DB into postgresql

* createdb circus
* createuser
* > username is django_login
* > make superuser
* > set django_login password to 'django'

| **db setup**
* psql circus < circus.dump.unix

*Make sure the Site is setup to appropriate domain URL.*

* Production: translation.viadelivers.com
* Test: translation-dev.viadelivers.com
* Dev: localhost:8000


**environment variables:**

* VTP_SETTINGS_ENV=local
* BASE_URL="http://localhost:8000"
* DEBUG_VTP=true

**Steps**

* run migrations
* run server
* run celery worker

| **Default logins:**

* via_portal: admin / admin or admin@viadelivers.com / admin
* client_portal: client@test.com / test
* vendor_portal: vendor@test.com / test

**Reset south migrations on Dev:**

* python manage.py sqlclear south | psql -d circus -U django_login
* python manage.py sqlall south | psql -d circus -U django_login
* python manage.py migrate --fake

**to test migrations run:**

* python manage.py test accounts


| RESETTING SOUTH ON HEROKU 
| - Make sure db connections string is valid.
| - DO NOT RUN UNLESS ABSOLUTELY SURE 
| - IGNORE TRANSACTION ERRORS

*vtp-dev*

* heroku run python src/circus/manage.py sqlclear south --app circus-dev | psql -h ec2-107-21-106-181.compute-1.amazonaws.com -d de1b3f8i4dbea3 -U owgnqihhyxrbyn -p 5432
* heroku run python src/circus/manage.py sqlall south --app circus-dev | psql -h ec2-107-21-106-181.compute-1.amazonaws.com -d de1b3f8i4dbea3 -U owgnqihhyxrbyn -p 5432
* heroku run python src/circus/manage.py migrate --fake --app circus-dev

*vtp-prod*

* heroku run python src/circus/manage.py sqlclear south --app via-translation-portal | psql -h ec2-75-101-166-204.compute-1.amazonaws.com -d deuubb9kpeca72 -U ua0bon38e3s8v8 -p 5752
* heroku run python src/circus/manage.py sqlall south --app via-translation-portal | psql -h ec2-75-101-166-204.compute-1.amazonaws.com -d deuubb9kpeca72 -U ua0bon38e3s8v8 -p 5752
* heroku run python src/circus/manage.py migrate --fake --app via-translation-portal


TEAMserver Paths (Logs and Configs)
===================================

Hostname: via-teamserver

IIS logs: C:\inetpub\logs\LogFiles\W3SVC1\
 (combined dev & production)

ATRIL TEAMserver logs:
C:\ProgramData\ATRIL\TEAMServer\TcpService.log
C:\ProgramData\ATRIL\Déjà Vu X2\Atril.DejaVuX2.Base.Engine.log


Dev:
----

project files in C:\circus_dev\media\projects\$VTP_PROJECT_ID\
    (includes analysis)

dvxanalyzer config: C:\DVXAnalyzer_TEAMServer_dev\Web.config


production:
-----------

project files in C:\vtp_prod\media\projects\$VTP_PROJECT_ID\
