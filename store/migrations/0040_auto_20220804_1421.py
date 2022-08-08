# Generated by Django 3.2.8 on 2022-08-04 18:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0039_auto_20220802_1433'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicaloptionproduct',
            name='has_stock',
            field=models.BooleanField(default=False, help_text='True if option has stock, False if stock is infinite or NA', verbose_name='Has stock'),
        ),
        migrations.AlterField(
            model_name='optionproduct',
            name='has_stock',
            field=models.BooleanField(default=False, help_text='True if option has stock, False if stock is infinite or NA', verbose_name='Has stock'),
        ),
    ]