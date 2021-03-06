# Generated by Django 2.0.2 on 2018-04-30 00:03

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blitz_api', '0004_actiontoken'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='academic_field',
            field=models.CharField(blank=True, choices=[('SCI', 'Science'), ('SOC', 'Social')], max_length=100, null=True, verbose_name='Academic field'),
        ),
        migrations.AddField(
            model_name='user',
            name='academic_level',
            field=models.CharField(blank=True, choices=[('SEC', 'Secondary'), ('COL', 'College'), ('UNI', 'University')], max_length=100, null=True, verbose_name='Academic level'),
        ),
        migrations.AddField(
            model_name='user',
            name='birthdate',
            field=models.DateField(blank=True, max_length=100, null=True, verbose_name='Birthdate'),
        ),
        migrations.AddField(
            model_name='user',
            name='gender',
            field=models.CharField(blank=True, choices=[('M', 'Male'), ('F', 'Female'), ('T', 'Trans'), ('A', 'Do not wish to identify myself')], max_length=100, null=True, verbose_name='Gender'),
        ),
        migrations.AddField(
            model_name='user',
            name='other_phone',
            field=models.CharField(blank=True, max_length=17, null=True, verbose_name='Other number'),
        ),
        migrations.AddField(
            model_name='user',
            name='phone',
            field=models.CharField(blank=True, max_length=17, null=True, verbose_name='Phone number'),
        ),
        migrations.AddField(
            model_name='user',
            name='university',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='blitz_api.Organization'),
        ),
        migrations.AddField(
            model_name='actiontoken',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='activation_token', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
    ]
