# Generated by Django 3.0.3 on 2020-02-20 20:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('boardgames', '0009_auto_20200220_1911'),
    ]

    operations = [
        migrations.AlterField(
            model_name='boardgame',
            name='bgstats_id',
            field=models.IntegerField(null=True, unique=True),
        ),
    ]
