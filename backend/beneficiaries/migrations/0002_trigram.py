from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations


class Migration(migrations.Migration):
    """Active pg_trgm pour la recherche approximative sur les noms."""

    dependencies = [("beneficiaries", "0001_initial")]

    operations = [TrigramExtension()]