import json

from datetime import datetime, timedelta, date

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core import mail
from django.test import modify_settings, override_settings
from django.utils import timezone
from django.urls import reverse

import pytz
import responses
from unittest import mock

from blitz_api.factories import UserFactory, AdminFactory

from workplace.models import TimeSlot, Period, Workplace
from retirement.models import Retreat, RetreatInvitation

from .paysafe_sample_responses import (
    SAMPLE_PROFILE_RESPONSE,
    SAMPLE_PAYMENT_RESPONSE,
    SAMPLE_CARD_RESPONSE,
    SAMPLE_INVALID_PAYMENT_TOKEN,
    SAMPLE_INVALID_SINGLE_USE_TOKEN,
    SAMPLE_CARD_ALREADY_EXISTS,
    SAMPLE_CARD_REFUSED,
)

from ..models import (
    Package, Order, OrderLine, Membership, PaymentProfile,
    Coupon, CouponUser, MembershipCoupon, OptionProduct
)

User = get_user_model()

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


@override_settings(
    PAYSAFE={
        'ACCOUNT_NUMBER': "0123456789",
        'USER': "user",
        'PASSWORD': "password",
        'BASE_URL': "http://example.com/",
        'VAULT_URL': "customervault/v1/",
        'CARD_URL': "cardpayments/v1/"
    },
    LOCAL_SETTINGS={
        "EMAIL_SERVICE": True,
        "FRONTEND_INTEGRATION": {
            "POLICY_URL": "fake_url",
            "LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT": "fake_url",
            "PROFILE_URL": "fake_url"
        }
    }
)
class OrderTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user: User = UserFactory()
        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()
        self.admin = AdminFactory()
        self.admin.city = "Current city"
        self.admin.phone = "123-456-7890"
        self.admin.faculty = "Random faculty"
        self.admin.student_number = "Random code"
        self.admin.academic_program_code = "Random code"
        self.admin.save()
        self.membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        self.package_type = ContentType.objects.get_for_model(Package)
        self.package = Package.objects.create(
            name="extreme_package",
            details="100 reservations package",
            available=True,
            price=40,
            reservations=100,
        )
        self.package2 = Package.objects.create(
            name="extreme_package2",
            details="1000 reservations package",
            available=True,
            price=4000,
            reservations=1000,
        )
        self.order = Order.objects.create(
            user=self.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
            reference_number=751,
        )
        self.order_admin = Order.objects.create(
            user=self.admin,
            transaction_date=timezone.now(),
            authorization_id=2,
            settlement_id=2,
            reference_number=751,
        )
        self.order_line = OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.package_type,
            object_id=self.package.id,
            cost=self.package.price,
        )
        self.payment_profile = PaymentProfile.objects.create(
            name="payment_api_name",
            owner=self.admin,
            external_api_id="123",
            external_api_url="https://example.com/customervault/v1/profiles"
        )
        self.workplace = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=40,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        self.workplace_no_seats = Workplace.objects.create(
            name="random_workplace",
            details="This is a description of the workplace.",
            seats=0,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
        )
        self.period = Period.objects.create(
            name="random_period_active",
            workplace=self.workplace,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        self.period_no_seats = Period.objects.create(
            name="random_period_active",
            workplace=self.workplace_no_seats,
            start_date=timezone.now(),
            end_date=timezone.now() + timedelta(weeks=4),
            price=3,
            is_active=True,
        )
        self.time_slot = TimeSlot.objects.create(
            name="morning_time_slot",
            period=self.period,
            price=1,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        self.time_slot_no_seats = TimeSlot.objects.create(
            name="no_place_left_timeslot",
            period=self.period_no_seats,
            price=3,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
        )
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            seats=400,
            details="This is a description of the mega retreat.",
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            activity_language='FR',
            accessibility=True,
            has_shared_rooms=True,
        )
        self.retreat.add_wait_queue_place(self.user, generate_cron=False)
        self.retreat_no_seats = Retreat.objects.create(
            name="no_place_left_retreat",
            seats=0,
            details="This is a description of the full retreat.",
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            activity_language='FR',
            accessibility=True,
            has_shared_rooms=True,
        )
        self.virtualRetreat = Retreat.objects.create(
            name="virtual retreat",
            seats=400,
            details="This is a description of the virtual retreat.",
            price=200,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            activity_language='FR',
            videoconference_tool='Jitsi',
            type=Retreat.TYPE_VIRTUAL,
        )
        self.virtualRetreat2 = Retreat.objects.create(
            name="virtual retreat 2",
            seats=400,
            details="This is a description of the virtual retreat 2.",
            price=100,
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 12)),
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            is_active=True,
            activity_language='FR',
            videoconference_tool='Jitsi',
            type=Retreat.TYPE_VIRTUAL,
        )
        self.coupon = Coupon.objects.create(
            code="ABCD1234",
            start_time=LOCAL_TIMEZONE.localize(datetime(2000, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            value=10,
            max_use_per_user=0,
            max_use=0,
            owner=self.admin,
        )
        self.coupon.applicable_product_types.set([self.package_type])
        self.coupon_user = CouponUser.objects.create(
            user=self.admin,
            uses=5,
            coupon=self.coupon,
        )

        self.invitation = RetreatInvitation.objects.create(
            retreat=self.retreat,
            nb_places=5,
            reserve_seat=True
        )

        self.maxDiff = None

        self.options: OptionProduct = OptionProduct.objects.create(
            name="Vegan",
            details="Vegan details",
            available=True,
            price=50,
            max_quantity=10
        )

    @responses.activate
    def test_create_with_payment_token(self):
        """
        Ensure we can create an order when provided with a payment_token.
        (Token representing an existing payment card.)
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }, {
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
                'metadata':
                    json.dumps({'invitation_id': self.invitation.id}),
                'options': [{
                    'id': self.options.id,
                    'quantity': 1
                }]
            }],
            'coupon': "ABCD1234",
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        new_order_id = response_data['id']

        del response_data['url']
        del response_data['id']

        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']

        del response_data['order_lines'][2]['order']
        del response_data['order_lines'][2]['url']
        del response_data['order_lines'][2]['id']

        del response_data['order_lines'][3]['order']
        del response_data['order_lines'][3]['url']
        del response_data['order_lines'][3]['id']

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        content = {
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 50.0,
                'metadata': None,
                'options': []
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
                'coupon': "ABCD1234",
                'coupon_real_value': 10.0,
                'cost': 2 * self.package.price - 10,
                'metadata': None,
                'options': []
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 0.0,
                'metadata': None,
                'options': []
            }, {
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'metadata':
                    json.dumps({'invitation_id': self.invitation.id}),
                'cost': 199.0 + self.options.price,
                'options': [{
                    'id': self.options.id,
                    'quantity': 1
                }]
            }],
            'user': f'http://testserver/users/{self.admin.id}',
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertCountEqual(response_data['order_lines'],
                              content['order_lines'])
        del response_data['order_lines']
        del content['order_lines']

        self.assertEqual(response_data, content)

        old_uses = self.coupon_user.uses
        self.coupon_user.refresh_from_db()
        self.assertEqual(self.coupon_user.uses, old_uses + 1)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, self.package.reservations * 2)
        self.assertEqual(admin.membership, self.membership)
        self.assertEqual(
            admin.membership_end,
            FIXED_TIME.date() + self.membership.duration
        )
        admin.tickets = 1
        admin.membership = None
        admin.save()

        # 1 email for the order details
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 2)

        # validate that the invitation are linked to the
        # reservation of the retreat
        self.assertEqual(
            self.invitation.retreat_reservations.all()[0].user,
            self.admin)

        new_order: Order = Order.objects.get(id=new_order_id)
        total_price = \
            self.membership.price * 1 + \
            self.package.price * 2 + \
            self.retreat.price * 1 + \
            self.options.price - \
            self.coupon.value

        self.assertEqual(new_order.total_cost, total_price)

    @responses.activate
    def test_order_retreat_invitation_reserved_seats(self):
        """
        Ensure we can create an order when provided with a payment_token.
        (Token representing an existing payment card.)
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        self.retreat.seats = self.invitation.nb_places_free()
        self.retreat.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
                'options': [{
                    'id': self.options.id,
                    'quantity': 1
                }]
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content,
        )

        response_data = json.loads(response.content)
        data = {
            "non_field_errors": [
                "There are no places left in the requested retreat."]
        }

        self.assertEqual(
            response_data,
            data,
            response_data,
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
                'metadata':
                    json.dumps({'invitation_id': self.invitation.id}),
                'options': [{
                    'id': self.options.id,
                    'quantity': 1
                }]
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

    @responses.activate
    def test_buy_renew_membership(self):
        """
        Ensure we can renew a membership
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        end_time_membership = date(2018, 1, 15)
        end_time_membership_updated = \
            end_time_membership + self.membership.duration

        self.user.membership = self.membership
        self.user.membership_end = end_time_membership

        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.membership_end,
                         end_time_membership_updated)

    @responses.activate
    def test_buy_renew_membership_with_old_membership(self):
        """
        Ensure we can renew a membership
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        end_time_membership = date(2017, 1, 15)
        end_time_membership_updated = \
            FIXED_TIME.date() + self.membership.duration

        self.user.membership = self.membership
        self.user.membership_end = end_time_membership
        self.user.save()

        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        self.user.refresh_from_db()
        self.assertEqual(self.user.membership_end,
                         end_time_membership_updated)

    @responses.activate
    def test_create_reservation_only(self):
        """
        Ensure we can create an order for a reservation only.
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'order_lines': [{
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        content = {
            'order_lines': [{
                'content_type': 'timeslot',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 0.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.admin.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '0',
            'settlement_id': '0',
            'reference_number': '0',
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 0)
        admin.tickets = 1
        admin.membership = None
        admin.save()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_reservation_only_from_admin(self):
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'order_lines': [{
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }],
            'target_user': 'http://testserver/users/' + str(self.user.id),
            'bypass_payment': False,
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['transaction_date']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        content = {
            'order_lines': [{
                'content_type': 'timeslot',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 0.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.user.id),
            'authorization_id': '0',
            'settlement_id': '0',
            'reference_number': '0',
        }

        self.assertEqual(response_data, content)

        user = self.user
        user.refresh_from_db()

        self.assertEqual(user.tickets, 0)

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_reservation_only_from_admin_without_payment(self):
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'order_lines': [{
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }],
            'target_user': 'http://testserver/users/' + str(self.user.id),
            'bypass_payment': True,
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         response.content)

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['transaction_date']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        content = {
            'order_lines': [{
                'content_type': 'timeslot',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 0.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.user.id),
            'authorization_id': '0',
            'settlement_id': '0',
            'reference_number': '0',
        }

        self.assertEqual(response_data, content)

        user = self.user
        user.refresh_from_db()

        self.assertEqual(user.tickets, 1)

    @responses.activate
    def test_create_reservation_only_from_not_admin(self):
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'order_lines': [{
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }],
            'target_user': 'http://testserver/users/' + str(self.user.id),
            'bypass_payment': False,
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors':
                [
                    'You don\'t have the permission to create '
                    'an order for another user.'
                ]
        }

        self.assertEqual(response_data, content)

    @responses.activate
    def test_create_reservation_twice(self):
        """
        Ensure we can't create an order for the same reservation twice.
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'order_lines': [{
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        content = {
            'order_lines': [{
                'content_type': 'timeslot',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 0.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.admin.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '0',
            'settlement_id': '0',
            'reference_number': '0',
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 0)
        admin.tickets = 1
        admin.membership = None
        admin.save()

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "You already are registered to this timeslot: "
                "2130-01-15 13:00:00+00:00 - 2130-01-15 17:00:00+00:00."
            ]
        }

        self.assertEqual(response_data, content)

    @responses.activate
    def test_create_user_has_membership(self):
        """
        Ensure we can't create an order containing a membership if the user
        already has a membership.
        """
        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "You already have an active membership."
            ]
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        admin.tickets = 1
        admin.membership = None
        admin.save()

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_create_no_place_left(self):
        """
        Ensure we can't create an order with reservations if the requested
        timeslot has no place left.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "There are no places left in the requested timeslot."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_coupon_invalid(self):
        """
        Ensure we can't create an order with invalid coupon.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "INVALID",
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'coupon': ['Object with code=INVALID does not exist.']
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_coupon_max_use_exceeded(self):
        """
        Ensure we can't create an order with a coupon already used maximum
        times.
        """
        self.client.force_authenticate(user=self.admin)

        self.coupon.max_use = 1
        self.coupon.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'Maximum number of uses exceeded for this coupon.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.coupon.max_use = 0
        self.coupon.save()

        old_uses = self.coupon_user.uses

        self.coupon_user.refresh_from_db()

        self.assertEqual(self.coupon_user.uses, old_uses)
        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_coupon_max_user_use_exceeded(self):
        """
        Ensure we can't create an order with a coupon already used maximum
        times by a specific user.
        """
        self.client.force_authenticate(user=self.admin)

        self.coupon.max_use_per_user = 1
        self.coupon.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'Maximum number of uses exceeded for this coupon.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.coupon.max_use_per_user = 0
        self.coupon.save()

        old_uses = self.coupon_user.uses

        self.coupon_user.refresh_from_db()

        self.assertEqual(self.coupon_user.uses, old_uses)
        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_coupon_incomplete_user_profile(self):
        """
        Ensure we can't create an order with a coupon when the user doesn't
        have a complete profile.
        """
        self.client.force_authenticate(user=self.admin)

        self.admin.faculty = None
        self.admin.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Incomplete user profile. 'academic_program_code',"
                " 'faculty' and 'student_number' fields must be "
                "filled in the user profile to use a coupon."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.admin.faculty = "Random faculty"
        self.admin.save()

        admin = self.admin
        admin.refresh_from_db()

        self.coupon.max_use = 0
        self.coupon.save()

        old_uses = self.coupon_user.uses

        self.coupon_user.refresh_from_db()

        self.assertEqual(self.coupon_user.uses, old_uses)
        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_coupon_not_active(self):
        """
        Ensure we can't create an order with a coupon that is not active.
        """
        FIXED_TIME = datetime(1999, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-list'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'This coupon is only valid between 2000-01-15 and 2130-01-15.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.coupon.max_use = 0
        self.coupon.save()

        old_uses = self.coupon_user.uses

        self.coupon_user.refresh_from_db()

        self.assertEqual(self.coupon_user.uses, old_uses)
        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_coupon_not_applicable(self):
        """
        Ensure we can't create an order with a coupon that is not applicable.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'This coupon does not apply to any product.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.coupon.max_use = 0
        self.coupon.save()

        old_uses = self.coupon_user.uses

        self.coupon_user.refresh_from_db()

        self.assertEqual(self.coupon_user.uses, old_uses)
        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_no_place_left_retreat(self):
        """
        Ensure we can't create an order with reservations if the requested
        retreat has no place left.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'retreat',
                'object_id': self.retreat_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "There are no places left in the requested retreat."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_reserved_retreat_not_authorized(self):
        """
        Ensure we can't create an order with reservations if the requested
        retreat has only reserved seats and the user has not been notified
        (not on the mailing list).
        """
        self.client.force_authenticate(user=self.user)

        self.retreat_no_seats.wait_queue_places.all().delete()
        self.retreat_no_seats.add_wait_queue_place(self.user,
                                                   generate_cron=False)
        self.retreat_no_seats.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'retreat',
                'object_id': self.retreat_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "There are no places left in the requested retreat."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_create_reserved_retreat(self):
        """
        Ensure we can create an order with reservations if the requested
        retreat has reserved seats and the user has been notified
        (on the mailing list).
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        self.retreat_no_seats.wait_queue_places.all().delete()
        new_wait_queue_place = \
            self.retreat_no_seats.add_wait_queue_place(self.user)
        self.retreat_no_seats.add_user_to_wait_queue(self.user)
        new_wait_queue_place.notify()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'retreat',
                'object_id': self.retreat_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        content = {
            'order_lines': [{
                'content_type': 'retreat',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 199.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the notification
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 3)

    @responses.activate
    def test_fail_order_retreat_that_need_a_membership(self):
        """
        Ensure we can't create an order with a physical retreat that need a
        membership of we do not have a membership in profile or in cart
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()

        self.assertEqual(
            self.user.get_active_membership(),
            None
        )

        self.retreat.exclusive_memberships.add(self.membership)
        self.retreat.save()

        self.assertTrue(
            self.retreat.exclusive_memberships.all().exists()
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'object_id': self.retreat.id,
                    'quantity': 1,
                },
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)
        content = {
            "order_lines": [
                {
                    "object_id": [
                        "User does not have the required membership to "
                        "order this package."
                    ]
                }
            ]
        }
        self.assertEqual(
            response_data,
            content
        )

    @responses.activate
    def test_create_retreat(self):
        """
        Ensure we can create an order with a physical retreat and a
        membership and that we pay for all
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'object_id': self.retreat.id,
                    'quantity': 1,
                },
                {
                    'content_type': 'membership',
                    'object_id': self.membership.id,
                    'quantity': 1,
                }
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']
        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['object_id']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']
        content = {
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 199.0,
                    'metadata': None,
                    'options': []
                },
                {
                    'content_type': 'membership',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 50.0,
                    'metadata': None,
                    'options': []
                }
            ],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 2)

    @responses.activate
    @override_settings(
        LIMIT_DATE_FOR_FREE_VIRTUAL_RETREAT_ON_MEMBERSHIP='5000-01-01'
    )
    def test_create_virtual_retreat_with_membership(self):
        """
        Ensure we can create an order with a virtual retreat and a
        membership and that the virtual retreat is free
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()

        number_of_free_virtual_retreat_in_bank = \
            self.user.number_of_free_virtual_retreat

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'object_id': self.virtualRetreat.id,
                    'quantity': 1,
                },
                {
                    'content_type': 'membership',
                    'object_id': self.membership.id,
                    'quantity': 1,
                }
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']
        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['object_id']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']
        content = {
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 0.0,
                    'metadata': None,
                    'options': []
                },
                {
                    'content_type': 'membership',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 50.0,
                    'metadata': None,
                    'options': []
                }
            ],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        refreshed_user = User.objects.get(id=self.user.id)

        self.assertEqual(
            number_of_free_virtual_retreat_in_bank,
            refreshed_user.number_of_free_virtual_retreat
        )

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 2)

    @responses.activate
    @override_settings(
        LIMIT_DATE_FOR_FREE_VIRTUAL_RETREAT_ON_MEMBERSHIP='5000-01-01'
    )
    def test_create_membership_before_end_of_limit_free_virtual_retreat(self):
        """
        Ensure we can create an order with a membership and get
        a free virtual retreat in bank
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()

        number_of_free_virtual_retreat_in_bank =\
            self.user.number_of_free_virtual_retreat

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'membership',
                    'object_id': self.membership.id,
                    'quantity': 1,
                }
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']
        content = {
            'order_lines': [
                {
                    'content_type': 'membership',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 50.0,
                    'metadata': None,
                    'options': []
                }
            ],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        refreshed_user = User.objects.get(id=self.user.id)

        self.assertEqual(
            number_of_free_virtual_retreat_in_bank + 1,
            refreshed_user.number_of_free_virtual_retreat
        )

        self.assertEqual(response_data, content)

        # 1 email for the order details
        self.assertEqual(len(mail.outbox), 1)

    @responses.activate
    def test_create_virtual_retreat_with_membership_after_limit(self):
        """
        Ensure we can create an order with a virtual retreat and a
        membership and that the virtual retreat is not free since the limit
        is passed
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'object_id': self.virtualRetreat.id,
                    'quantity': 1,
                },
                {
                    'content_type': 'membership',
                    'object_id': self.membership.id,
                    'quantity': 1,
                }
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']
        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['object_id']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']
        content = {
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 200.0,
                    'metadata': None,
                    'options': []
                },
                {
                    'content_type': 'membership',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 50.0,
                    'metadata': None,
                    'options': []
                }
            ],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 2)

    @responses.activate
    def test_create_virtual_retreat_with_free_retreat_in_profile(self):
        """
        Ensure we can create an order with a virtual retreat and a
        free virtual retreat in banks and that the virtual retreat is free
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.number_of_free_virtual_retreat = 1
        self.user.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'object_id': self.virtualRetreat.id,
                    'quantity': 1,
                }
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['reference_number']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']
        content = {
            'order_lines': [
                {
                    'object_id': self.virtualRetreat.id,
                    'content_type': 'retreat',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 0.0,
                    'metadata': None,
                    'options': []
                }
            ],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': 0,
            'settlement_id': 0,
        }

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 2)

    @responses.activate
    def test_create_two_virtual_retreat_with_free_retreat_in_profile(self):
        """
        Ensure we can create an order with two virtual retreat and that the
        first virtual retreat is free
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.number_of_free_virtual_retreat = 1
        self.user.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [
                {
                    'content_type': 'retreat',
                    'object_id': self.virtualRetreat.id,
                    'quantity': 1,
                },
                {
                    'content_type': 'retreat',
                    'object_id': self.virtualRetreat2.id,
                    'quantity': 1,
                }
            ],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['reference_number']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']
        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']
        content = {
            'order_lines': [
                {
                    'object_id': self.virtualRetreat.id,
                    'content_type': 'retreat',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 0.0,
                    'metadata': None,
                    'options': []
                },
                {
                    'object_id': self.virtualRetreat2.id,
                    'content_type': 'retreat',
                    'quantity': 1,
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': 100.0,
                    'metadata': None,
                    'options': []
                }
            ],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
        }

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the free retreat informations
        # 1 email for the payed retreat informations
        self.assertEqual(len(mail.outbox), 3)

    @responses.activate
    def test_create_retreat_twice(self):
        """
        Ensure we can't create an order with a reservation for a retreat
        to which the user is already registered.
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = "Current city"
        self.user.phone = "123-456-7890"
        self.user.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']
        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        content = {
            'order_lines': [{
                'content_type': 'retreat',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 199.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        # 1 email for the order details
        # 1 email for the retreat informations
        self.assertEqual(len(mail.outbox), 2)

        # Duplicate order
        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "You already are registered to this retreat: {0}.".format(
                    str(self.retreat)
                )
            ]
        }

        self.assertEqual(response_data, content)

    @responses.activate
    def test_create_retreat_missing_user_info(self):
        """
        Ensure we can't create an order with reservations if the requesting
        user has an incomplete profile.
        """
        self.client.force_authenticate(user=self.user)

        self.user.city = None
        self.user.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'retreat',
                'object_id': self.retreat_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Incomplete user profile. 'phone' and 'city' field must "
                "be filled in the user profile to book a retreat."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_create_not_enough_tickets(self):
        """
        Ensure we can't create an order with reservations if the requesting
        user doesn't have enough tickets.
        """
        self.client.force_authenticate(user=self.admin)

        self.admin.tickets = 0
        self.admin.save()

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot_no_seats.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "You don't have enough tickets to make this reservation."
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 0)
        self.assertEqual(admin.membership, None)

        self.admin.tickets = 1
        self.admin.save()

    @responses.activate
    def test_create_with_invalid_payment_token(self):
        """
        Ensure we can't create an order when provided with a bad payment_token.
        (Token representing an non-existing payment card.)
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_INVALID_PAYMENT_TOKEN,
            status=400
        )

        data = {
            'payment_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "An error occured while processing the payment: "
                "invalid payment token or payment profile/card "
                "inactive."
            ]
        }

        self.assertEqual(
            json.loads(response.content).get('non_field_errors'),
            content.get('non_field_errors'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_with_single_use_token_no_profile(self):
        """
        Ensure we can create an order when provided with a single_use_token.
        (Token representing a new payment card.)
        The PaymentProfile will be created if none exists.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'single_use_token': "SChsxyprFn176yhD",
            'order_lines': [{
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['object_id']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']

        content = {
            'order_lines': [{
                'content_type': 'package',
                'quantity': 2,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 2 * self.package.price,
                'metadata': None,
                'options': []
            }, {
                'content_type': 'timeslot',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 0.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        user = self.user
        user.refresh_from_db()
        self.assertEqual(user.tickets, self.package.reservations * 2)
        user.tickets = 1
        user.save()

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    @responses.activate
    def test_create_with_single_use_token_existing_profile(self):
        """
        Ensure we can create an order when provided with a single_use_token.
        The existing PaymentProfile will be used. A new card will be added.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        data = {
            'single_use_token': "SChsxyprFn176yhD",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['object_id']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']

        content = {
            'order_lines': [{
                'content_type': 'membership',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 50.0,
                'metadata': None,
                'options': []
            }, {
                'content_type': 'package',
                'quantity': 2,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 2 * self.package.price,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.admin.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, self.package.reservations * 2 + 1)
        self.assertEqual(admin.membership, self.membership)
        admin.tickets = 1
        admin.membership = None
        admin.save()

    @responses.activate
    def test_create_with_invalid_single_use_token(self):
        """
        Ensure we can't create an order when provided with a bad
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_INVALID_SINGLE_USE_TOKEN,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = content = {
            'non_field_errors': [
                "An error occured while processing the payment: "
                "invalid payment or single-use token."
            ]
        }

        self.assertEqual(
            json.loads(response.content).get('non_field_errors'),
            content.get('non_field_errors'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    @responses.activate
    def test_create_with_invalid_single_use_token_no_profile(self):
        """
        Ensure we can't create an order when provided with a bad
        single_use_token.
        (Token representing a new payment card.)
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_INVALID_SINGLE_USE_TOKEN,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                "An error occured while processing the payment: "
                "invalid payment or single-use token."
            ]
        }

        self.assertEqual(
            json.loads(response.content).get('non_field_errors'),
            content.get('non_field_errors'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = self.user
        user.refresh_from_db()

        self.assertEqual(user.tickets, 1)
        self.assertEqual(user.membership, None)

    @responses.activate
    def test_create_payment_issue(self):
        """
        Ensure we can't create an order when the payment proccessing fails.
        """
        self.client.force_authenticate(user=self.user)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/",
            json=SAMPLE_PROFILE_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_CARD_REFUSED,
            status=400
        )

        data = {
            'single_use_token': "invalid",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = content = {
            'non_field_errors': [
                "An error occured while processing the payment: "
                "the request has been declined by the issuing bank."
            ]
        }

        self.assertEqual(
            json.loads(response.content).get('non_field_errors'),
            content.get('non_field_errors'))

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        user = self.user
        user.refresh_from_db()

        self.assertEqual(user.tickets, 1)
        self.assertEqual(user.membership, None)

    @responses.activate
    def test_create_with_single_use_token_existing_card(self):
        """
        Ensure we can create an order when provided with a single_use_token
        representing a card that is already stored in the user's profile.
        """
        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_ALREADY_EXISTS,
            status=400
        )

        responses.add(
            responses.POST,
            "http://example.com/customervault/v1/profiles/123/cards/",
            json=SAMPLE_CARD_RESPONSE,
            status=201
        )

        responses.add(
            responses.GET,
            "http://example.com/customervault/v1/cards/456",
            json=SAMPLE_CARD_RESPONSE,
            status=200
        )

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        responses.add(
            responses.DELETE,
            "http://example.com/customervault/v1/profiles/123/cards/"
            "424d2472-4afd-44a3-a678-8f4611e864a5",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'user': reverse('user-detail', args=[self.admin.id]),
            'single_use_token': "invalid",
            'transaction_date': timezone.now(),
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        del response_data['order_lines'][0]['order']
        del response_data['order_lines'][0]['object_id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['id']

        del response_data['order_lines'][1]['order']
        del response_data['order_lines'][1]['object_id']
        del response_data['order_lines'][1]['url']
        del response_data['order_lines'][1]['id']

        content = {
            'authorization_id': '1',
            'order_lines': [{
                'content_type': 'membership',
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 50.0,
                'metadata': None,
                'options': []
            }, {
                'content_type': 'package',
                'quantity': 2,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 2 * self.package.price,
                'metadata': None,
                'options': []
            }],
            'settlement_id': '1',
            'reference_number': '751',
            'transaction_date': response_data['transaction_date'],
            'user': 'http://testserver/users/' + str(self.admin.id),
        }

        self.assertEqual(response_data, content)

        self.admin.refresh_from_db()

        self.assertEqual(self.admin.tickets, self.package.reservations * 2 + 1)
        self.assertEqual(self.admin.membership, self.membership)

    def test_create_missing_payment_details(self):
        """
        Ensure we can't create an order if no payment details are provided.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'user': reverse('user-detail', args=[self.user.id]),
            'transaction_date': timezone.now(),
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'order': 'http://testserver/orders/' + str(self.order.id),
                'quantity': 1,
                'url': 'http://testserver/order_lines/' +
                       str(self.order_line.id)
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'order': 'http://testserver/orders/' + str(self.order.id),
                'quantity': 2,
                'url': 'http://testserver/order_lines/' +
                       str(self.order_line.id)
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'non_field_errors': [
                'A payment_token or single_use_token is required to '
                'create an order.'
            ]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        admin = self.admin
        admin.refresh_from_db()

        self.assertEqual(admin.tickets, 1)
        self.assertEqual(admin.membership, None)

    def test_create_missing_field(self):
        """
        Ensure we can't create an order when required field are missing.
        """
        self.client.force_authenticate(user=self.admin)

        data = {}

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'order_lines': ['This field is required.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_null_field(self):
        """
        Ensure we can't create an order when required field are null.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'order_lines': None,
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'order_lines': ['This field may not be null.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_invalid_field(self):
        """
        Ensure we can't create an order when required field are invalid.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'order_lines': (1,),
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        content = {
            'order_lines': [{
                'non_field_errors': [
                    'Invalid data. Expected a dictionary, but got int.'
                ]
            }]
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @responses.activate
    def test_create_with_membership_coupon(self):
        """
        Ensure we can order a membership that includes a membership coupon
        """
        self.client.force_authenticate(user=self.admin)

        nb_coupon_start = self.admin.coupons.all().count()

        membership_coupon = MembershipCoupon.objects.create(
            value=100,
            percent_off=0,
            max_use=4,
            max_use_per_user=4,
            details="",
            membership=self.membership,
        )

        membership_coupon.applicable_product_types.set(
            [ContentType.objects.get_for_model(Membership)]
        )

        membership_coupon.save()

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        del response_data['order_lines'][0]['id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['order']

        content = {
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 50.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.admin.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        self.assertEqual(self.admin.coupons.all().count(), 1 + nb_coupon_start)

        # Get the last coupon generate, it should be the new one associate
        # with the membership
        new_coupon = self.admin.coupons.all().order_by('-id')[0]

        self.assertEqual(new_coupon.value, membership_coupon.value)
        self.assertEqual(new_coupon.percent_off, 0)
        self.assertEqual(new_coupon.max_use, 4)
        self.assertEqual(new_coupon.max_use_per_user, 4)
        self.assertEqual(new_coupon.details, "")

        self.assertTrue(
            timezone.now() - timedelta(minutes=1) <
            new_coupon.start_time <
            timezone.now()
        )

        self.assertTrue(
            timezone.now() + self.membership.duration - timedelta(minutes=1) <
            new_coupon.end_time <
            timezone.now() + self.membership.duration
        )

    @responses.activate
    def test_create_with_membership_coupon_after_limit(self):
        """
        Ensure we can order a membership that includes a membership coupon
        """
        self.client.force_authenticate(user=self.admin)

        nb_coupon_start = self.admin.coupons.all().count()

        membership_coupon = MembershipCoupon.objects.create(
            value=100,
            percent_off=0,
            max_use=4,
            max_use_per_user=4,
            details="",
            membership=self.membership,
            limit_date=timezone.now()
        )

        membership_coupon.applicable_product_types.set(
            [ContentType.objects.get_for_model(Membership)]
        )

        membership_coupon.save()

        FIXED_TIME = datetime(2018, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        responses.add(
            responses.POST,
            "http://example.com/cardpayments/v1/accounts/0123456789/auths/",
            json=SAMPLE_PAYMENT_RESPONSE,
            status=200
        )

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content,
        )

        response_data = json.loads(response.content)
        del response_data['url']
        del response_data['id']

        del response_data['order_lines'][0]['id']
        del response_data['order_lines'][0]['url']
        del response_data['order_lines'][0]['order']

        content = {
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': 50.0,
                'metadata': None,
                'options': []
            }],
            'user': 'http://testserver/users/' + str(self.admin.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
        }

        self.assertEqual(response_data, content)

        # The number of coupon does not change since the limit_date is expired
        self.assertEqual(self.admin.coupons.all().count(), nb_coupon_start)

    def test_update(self):
        """
        Ensure we can update an order.
        An empty 'order_lines' list will be ignored.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'order_lines': [{
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 99,
            }],
        }

        response = self.client.put(
            reverse(
                'order-detail',
                kwargs={'pk': self.order.id},
            ),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'id': self.order.id,
            'url': 'http://testserver/orders/' + str(self.order.id),
            'user': 'http://testserver/users/' + str(self.user.id),
            'transaction_date': response_data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
            'order_lines': [{
                'url': f'http://testserver/order_lines/{self.order_line.id}',
                'id': self.order_line.id,
                'content_type': 'package',
                'coupon_real_value': 0.0,
                'cost': 99.0 * self.package.price,
                'coupon': None,
                'object_id': self.package.id,
                'quantity': 99,
                'order': 'http://testserver/orders/' + str(self.order.id),
                'metadata': None,
                'options': [],
            }],
        }

        self.assertCountEqual(response_data['order_lines'],
                              content['order_lines'])
        del response_data['order_lines']
        del content['order_lines']

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_delete(self):
        """
        Ensure we can delete an order.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'order-detail',
                kwargs={'pk': self.order.id},
            ),
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_list(self):
        """
        Ensure we can't list orders as an unauthenticated user.
        """
        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_owner(self):
        """
        Ensure we can list owned orders as an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 1,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.order.id,
                'transaction_date': data['results'][0]['transaction_date'],
                'authorization_id': '1',
                'settlement_id': '1',
                'reference_number': '751',
                'order_lines': [{
                    'content_type': 'package',
                    'id': self.order_line.id,
                    'object_id': self.package.id,
                    'order': 'http://testserver/orders/' + str(self.order.id),
                    'quantity': 1,
                    'url': 'http://testserver/order_lines/' +
                           str(self.order_line.id),
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': self.package.price,
                    'metadata': None,
                    'options': []
                }],
                'url': 'http://testserver/orders/' + str(self.order.id),
                'user': 'http://testserver/users/' + str(self.user.id),
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_admin(self):
        """
        Ensure we can list all orders as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('order-list'),
            format='json',
        )

        data = json.loads(response.content)

        content = {
            'count': 2,
            'next': None,
            'previous': None,
            'results': [{
                'id': self.order.id,
                'transaction_date': data['results'][0]['transaction_date'],
                'authorization_id': '1',
                'settlement_id': '1',
                'reference_number': '751',
                'order_lines': [{
                    'content_type': 'package',
                    'id': self.order_line.id,
                    'object_id': self.package.id,
                    'order': 'http://testserver/orders/' + str(self.order.id),
                    'quantity': 1,
                    'url': 'http://testserver/order_lines/' +
                           str(self.order_line.id),
                    'coupon': None,
                    'coupon_real_value': 0.0,
                    'cost': self.package.price,
                    'metadata': None,
                    'options': []
                }],
                'url': 'http://testserver/orders/' + str(self.order.id),
                'user': 'http://testserver/users/' + str(self.user.id),
            }, {
                'id': self.order_admin.id,
                'transaction_date': data['results'][1]['transaction_date'],
                'authorization_id': '2',
                'settlement_id': '2',
                'reference_number': '751',
                'order_lines': [],
                'url': 'http://testserver/orders/' + str(self.order_admin.id),
                'user': 'http://testserver/users/' + str(self.admin.id),
            }]
        }

        self.assertEqual(data, content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read(self):
        """
        Ensure we can't read an order as an unauthenticated user.
        """

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': self.order.id},
            ),
        )

        content = {'detail': 'Authentication credentials were not provided.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_read_owner(self):
        """
        Ensure we can read an order owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': self.order.id},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': self.order.id,
            'transaction_date': data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
            'order_lines': [{
                'content_type': 'package',
                'id': self.order_line.id,
                'object_id': self.package.id,
                'order': 'http://testserver/orders/' + str(self.order.id),
                'quantity': 1,
                'url': 'http://testserver/order_lines/' +
                       str(self.order_line.id),
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': self.package.price,
                'metadata': None,
                'options': []
            }],
            'url': 'http://testserver/orders/' + str(self.order.id),
            'user': 'http://testserver/users/' + str(self.user.id),
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_owner_not_owned(self):
        """
        Ensure we can't read an order not owned by an authenticated user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 2},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_read_admin(self):
        """
        Ensure we can read any order as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': self.order.id},
            ),
        )

        data = json.loads(response.content)

        content = {
            'id': self.order.id,
            'transaction_date': data['transaction_date'],
            'authorization_id': '1',
            'settlement_id': '1',
            'reference_number': '751',
            'order_lines': [{
                'content_type': 'package',
                'id': self.order_line.id,
                'object_id': self.package.id,
                'order': 'http://testserver/orders/' + str(self.order.id),
                'quantity': 1,
                'url': 'http://testserver/order_lines/' +
                       str(self.order_line.id),
                'coupon': None,
                'coupon_real_value': 0.0,
                'cost': self.package.price,
                'metadata': None,
                'options': []
            }],
            'url': 'http://testserver/orders/' + str(self.order.id),
            'user': 'http://testserver/users/' + str(self.user.id),
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_read_non_existent(self):
        """
        Ensure we get not found when asking for an order that doesn't
        exist.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'order-detail',
                kwargs={'pk': 999},
            ),
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_validate_coupon(self):
        """
        Ensure that we can validate a coupon before creating an order.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }, {
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        content = {
            'orderline': {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
                'metadata': None,
                'options': []
            },
            'value': 10.0
        }

        self.assertEqual(response_data, content)

    def test_validate_coupon_full_discount(self):
        """
        Ensure that we can validate a coupon with 100% discount.
        """
        self.client.force_authenticate(user=self.admin)

        self.coupon.value = 0
        self.coupon.percent_off = 100
        self.coupon.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package.id,
                'quantity': 2,
            }, {
                'content_type': 'timeslot',
                'object_id': self.time_slot.id,
                'quantity': 1,
            }, {
                'content_type': 'retreat',
                'object_id': self.retreat.id,
                'quantity': 1,
            }, {
                'content_type': 'package',
                'object_id': self.package2.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content,
        )

        content = {
            'orderline': {
                'content_type': 'package',
                'object_id': self.package2.id,
                'quantity': 1,
                'metadata': None,
                'options': []
            },
            'value': 4000.0
        }

        self.assertEqual(response_data, content)

        self.coupon.value = 10.0
        self.coupon.save()

    def test_validate_coupon_invalid(self):
        """
        Ensure we can't validate a coupon with an invalid coupon.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "INVALID",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'coupon': ['Object with code=INVALID does not exist.']
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_coupon_missing(self):
        """
        Ensure we can't validate a coupon with a missing coupon.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'coupon': ['This field is required.']
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_coupon_max_use_exceeded(self):
        """
        Ensure we can't validate a coupon with a coupon already used maximum
        times.
        """
        self.client.force_authenticate(user=self.admin)

        self.coupon.max_use = 1
        self.coupon.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'Maximum number of uses exceeded for this coupon.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.coupon.max_use = 0
        self.coupon.save()

    def test_validate_coupon_max_user_use_exceeded(self):
        """
        Ensure we can't validate a coupon with a coupon already used maximum
        times by a specific user.
        """
        self.client.force_authenticate(user=self.admin)

        self.coupon.max_use_per_user = 1
        self.coupon.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'Maximum number of uses exceeded for this coupon.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.coupon.max_use_per_user = 0
        self.coupon.save()

    def test_validate_coupon_incomplete_user_profile(self):
        """
        Ensure we can't validate a coupon with a coupon when the user doesn't
        have a complete profile.
        """
        self.client.force_authenticate(user=self.admin)

        self.admin.faculty = None
        self.admin.save()

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                "Incomplete user profile. 'academic_program_code',"
                " 'faculty' and 'student_number' fields must be "
                "filled in the user profile to use a coupon."
            ]
        }

        self.admin.faculty = "Random faculty"
        self.admin.save()

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_coupon_not_active(self):
        """
        Ensure we can't validate a coupon with a coupon that is not active.
        """
        FIXED_TIME = datetime(1999, 1, 1, tzinfo=LOCAL_TIMEZONE)

        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        with mock.patch(
                'store.serializers.timezone.now', return_value=FIXED_TIME):
            response = self.client.post(
                reverse('order-validate-coupon'),
                data,
                format='json',
            )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'This coupon is only valid between 2000-01-15 and 2130-01-15.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_validate_coupon_not_applicable(self):
        """
        Ensure we can't validate a coupon with a coupon that is not applicable.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'payment_token': "CZgD1NlBzPuSefg",
            'order_lines': [{
                'content_type': 'membership',
                'object_id': self.membership.id,
                'quantity': 1,
            }],
            'coupon': "ABCD1234",
        }

        response = self.client.post(
            reverse('order-validate-coupon'),
            data,
            format='json',
        )

        response_data = json.loads(response.content)

        content = {
            'non_field_errors': [
                'This coupon does not apply to any product.'
            ]
        }

        self.assertEqual(response_data, content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
