# Generated by Django 3.2.8 on 2022-11-03 19:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blitz_api', '0028_alter_exportmedia_type'),
        ('store', '0044_auto_20221031_1457'),
    ]

    operations = [
        migrations.AddField(
            model_name='coupon',
            name='organization',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='coupons', to='blitz_api.organization', verbose_name='Organization'),
        ),
        migrations.AddField(
            model_name='historicalcoupon',
            name='organization',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='blitz_api.organization', verbose_name='Organization'),
        ),
    ]
