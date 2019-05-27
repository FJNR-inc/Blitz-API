# Generated by Django 2.0.8 on 2019-05-17 19:23

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('workplace', '0023_auto_20190517_1435'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('retirement', '0011_auto_20190517_1435'),
        ('store', '0024_auto_20190517_1435'),
    ]

    operations = [
        migrations.CreateModel(
            name='HistoricalMembershipCoupon',
            fields=[
                ('id', models.IntegerField(auto_created=True, blank=True, db_index=True, verbose_name='ID')),
                ('deleted', models.DateTimeField(editable=False, null=True)),
                ('value', models.DecimalField(decimal_places=2, max_digits=6, null=True, verbose_name='Value')),
                ('percent_off', models.PositiveIntegerField(null=True, verbose_name='Percentage off')),
                ('max_use', models.PositiveIntegerField()),
                ('max_use_per_user', models.PositiveIntegerField()),
                ('details', models.TextField(blank=True, max_length=1000, null=True, verbose_name='Details')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL)),
                ('membership', models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='store.Membership')),
            ],
            options={
                'verbose_name': 'historical membership coupon',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='MembershipCoupon',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('deleted', models.DateTimeField(editable=False, null=True)),
                ('value', models.DecimalField(decimal_places=2, max_digits=6, null=True, verbose_name='Value')),
                ('percent_off', models.PositiveIntegerField(null=True, verbose_name='Percentage off')),
                ('max_use', models.PositiveIntegerField()),
                ('max_use_per_user', models.PositiveIntegerField()),
                ('details', models.TextField(blank=True, max_length=1000, null=True, verbose_name='Details')),
                ('applicable_memberships', models.ManyToManyField(blank=True, related_name='applicable_membershipcoupons', to='store.Membership', verbose_name='Applicable memberships')),
                ('applicable_packages', models.ManyToManyField(blank=True, related_name='applicable_membershipcoupons', to='store.Package', verbose_name='Applicable packages')),
                ('applicable_product_types', models.ManyToManyField(blank=True, to='contenttypes.ContentType')),
                ('applicable_retirements', models.ManyToManyField(blank=True, related_name='applicable_membershipcoupons', to='retirement.Retirement', verbose_name='Applicable retirements')),
                ('applicable_timeslots', models.ManyToManyField(blank=True, related_name='applicable_membershipcoupons', to='workplace.TimeSlot', verbose_name='Applicable timeslots')),
                ('membership', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='store.Membership')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
