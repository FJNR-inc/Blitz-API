# Generated by Django 2.2.12 on 2020-08-13 19:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retirement', '0043_auto_20200813_1451'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalretreattype',
            name='short_description',
            field=models.TextField(default='placeholder', verbose_name='Short description'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='retreattype',
            name='short_description',
            field=models.TextField(default='placeholder', verbose_name='Short description'),
            preserve_default=False,
        ),
    ]
