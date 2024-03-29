# Generated by Django 3.2.8 on 2021-11-16 15:06

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('tomato', '0004_attendance_updated_at'),
    ]

    operations = [
        migrations.CreateModel(
            name='Report',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created at')),
                ('reason', models.CharField(max_length=300, verbose_name='Reason')),
                ('message', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to='tomato.message', verbose_name='Message')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='reports', to=settings.AUTH_USER_MODEL, verbose_name='User')),
            ],
        ),
    ]
