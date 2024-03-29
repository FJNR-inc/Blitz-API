# Generated by Django 3.2.8 on 2022-12-14 21:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0046_auto_20221212_1710'),
    ]

    operations = [
        migrations.AddField(
            model_name='historicalorderline',
            name='total_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='Orderline total cost'),
        ),
        migrations.AddField(
            model_name='orderline',
            name='total_cost',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=6, verbose_name='Orderline total cost'),
        ),
    ]
