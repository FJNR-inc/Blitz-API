# Generated by Django 2.2.7 on 2019-12-22 08:47

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('retirement', '0022_auto_20191112_1128'),
    ]

    operations = [
        migrations.CreateModel(
            name='WaitQueuePlace',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create', models.DateTimeField(auto_now_add=True, verbose_name='Create')),
                ('available', models.BooleanField(default=True, verbose_name='Available')),
                ('cancel_by', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wait_queue_places', to=settings.AUTH_USER_MODEL, verbose_name='Cancel by')),
            ],
        ),
        migrations.CreateModel(
            name='WaitQueuePlaceReserved',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('create', models.DateTimeField(auto_now_add=True, verbose_name='Create')),
                ('notified', models.BooleanField(default=False, verbose_name='Notified')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wait_queue_places_reserved', to=settings.AUTH_USER_MODEL, verbose_name='User')),
                ('wait_queue_place', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wait_queue_places_reserved', to='retirement.WaitQueuePlace', verbose_name='Wait Queue Place')),
            ],
        ),
        migrations.RemoveField(
            model_name='waitqueuenotification',
            name='retreat',
        ),
        migrations.RemoveField(
            model_name='waitqueuenotification',
            name='user',
        ),
        migrations.RemoveField(
            model_name='historicalretreat',
            name='next_user_notified',
        ),
        migrations.RemoveField(
            model_name='historicalretreat',
            name='reserved_seats',
        ),
        migrations.RemoveField(
            model_name='retreat',
            name='next_user_notified',
        ),
        migrations.RemoveField(
            model_name='retreat',
            name='reserved_seats',
        ),
        migrations.DeleteModel(
            name='HistoricalWaitQueueNotification',
        ),
        migrations.DeleteModel(
            name='WaitQueueNotification',
        ),
        migrations.AddField(
            model_name='waitqueueplace',
            name='retreat',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wait_queue_places', to='retirement.Retreat', verbose_name='Retreat'),
        ),
    ]
