import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "elections_db.settings")
django.setup()

from ORM.models import Election

if __name__=="__main__":
    data = Election.objects.all()
    data