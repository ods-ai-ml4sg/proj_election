# Generated by Django 2.2.5 on 2020-09-23 09:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ORM', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='election',
            name='mandates',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]