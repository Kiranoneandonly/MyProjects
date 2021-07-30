python manage.py dumpdata shared --indent=2 > fixtures\shared.json
python manage.py dumpdata accounts --indent=2 > fixtures\accounts.json
python manage.py dumpdata services --indent=2 > fixtures\services.json
python manage.py dumpdata people --indent=2 > fixtures\people.json
python manage.py dumpdata clients --indent=2 > fixtures\clients.json
python manage.py dumpdata vendors --indent=2 > fixtures\vendors.json
python manage.py dumpdata prices --indent=2 > fixtures\prices.json
python manage.py dumpdata localization_kits --indent=2 > fixtures\localization_kits.json
python manage.py dumpdata projects --indent=2 > fixtures\projects.json
python manage.py dumpdata tasks --indent=2 > fixtures\tasks.json
python manage.py dumpdata preferred_vendors --indent=2 > fixtures\preferred_vendors.json
python manage.py dumpdata finance --indent=2 > fixtures\finance.json
python manage.py dumpdata invoices --indent=2 > fixtures\invoices.json

