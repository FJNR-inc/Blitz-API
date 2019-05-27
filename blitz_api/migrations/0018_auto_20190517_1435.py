# Generated by Django 2.0.8 on 2019-05-17 18:35

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('blitz_api', '0017_actiontoken_data_change_email'),
    ]

    operations = [
        migrations.AlterField(
            model_name='historicalactiontoken',
            name='user',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AlterField(
            model_name='historicaltemporarytoken',
            name='token_ptr',
            field=models.ForeignKey(auto_created=True, blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, parent_link=True, related_name='+', to='authtoken.Token'),
        ),
        migrations.AlterField(
            model_name='historicaltemporarytoken',
            name='user',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='User'),
        ),
        migrations.AlterField(
            model_name='historicaluser',
            name='academic_field',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='blitz_api.AcademicField', verbose_name='Academic field'),
        ),
        migrations.AlterField(
            model_name='historicaluser',
            name='academic_level',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='blitz_api.AcademicLevel', verbose_name='Academic level'),
        ),
        migrations.AlterField(
            model_name='historicaluser',
            name='membership',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='store.Membership', verbose_name='Membership'),
        ),
    ]
