# Generated by Django 3.2.8 on 2022-11-21 17:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retirement', '0062_auto_20220821_1243'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalretreat',
            name='community_description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='historicalretreat',
            name='community_name',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
        migrations.AddField(
            model_name='historicalretreat',
            name='is_specific_to_community',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='retreat',
            name='community_description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='retreat',
            name='community_name',
            field=models.CharField(blank=True, max_length=300, null=True),
        ),
        migrations.AddField(
            model_name='retreat',
            name='is_specific_to_community',
            field=models.BooleanField(default=False),
        ),
    ]