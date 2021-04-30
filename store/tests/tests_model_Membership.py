from datetime import timedelta

from django.test import override_settings
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType

from rest_framework.test import APITestCase

from blitz_api.factories import UserFactory
from blitz_api.models import AcademicLevel

from ..models import Membership, Order, OrderLine


@override_settings(
    LOCAL_SETTINGS={
        "EMAIL_SERVICE": True,
    }
)
class MembershipTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(MembershipTests, cls).setUpClass()
        cls.membership_type = ContentType.objects.get_for_model(Membership)
        cls.user = UserFactory()
        cls.academic_level = AcademicLevel.objects.create(
            name="University"
        )
        cls.order = Order.objects.create(
            user=cls.user,
            transaction_date=timezone.now(),
            authorization_id=1,
            settlement_id=1,
        )

    def test_create(self):
        """
        Ensure that we can create a membership.
        """
        membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )

        membership.academic_levels.set([self.academic_level])

        self.assertEqual(membership.__str__(), "basic_membership")

    def test_membership_order_lines(self):
        """
        Ensure that we can get order lines for a specific membership.
        """
        membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )
        membership.academic_levels.set([self.academic_level])
        OrderLine.objects.create(
            order=self.order,
            quantity=1,
            content_type=self.membership_type,
            object_id=membership.id,
        )

        self.assertEqual(
            str(membership.order_lines.all()[0]),
            "basic_membership, qt:1"
        )

    def test_membership_welcome_email_no_specified(self):
        """
        Ensure that we does not fail if the membership have no welcome email
        """
        membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
        )

        user = UserFactory()
        user.membership = membership
        user.membership_end = timezone.now() + membership.duration
        user.save()

        self.assertEqual(
            membership.send_welcome_email(user),
            [],
        )

    def test_membership_welcome_email(self):
        """
        Ensure that we can send a welcome email
        """
        membership = Membership.objects.create(
            name="basic_membership",
            details="1-Year student membership",
            available=True,
            price=50,
            duration=timedelta(days=365),
            welcome_email_template_id=1,
        )

        user = UserFactory()
        user.membership = membership
        user.membership_end = timezone.now() + membership.duration
        user.save()

        self.assertEqual(
            membership.send_welcome_email(user),
            [],
        )
