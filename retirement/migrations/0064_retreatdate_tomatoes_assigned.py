# Generated by Django 3.2.8 on 2023-01-09 20:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('retirement', '0063_auto_20221121_1234'),
    ]

    operations = [
        migrations.AddField(
            model_name='retreatdate',
            name='tomatoes_assigned',
            field=models.BooleanField(default=False, verbose_name='Tomatoes assigned'),
        ),
    ]