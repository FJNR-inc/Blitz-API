from datetime import datetime

from django.contrib.contenttypes.models import ContentType

import pytz
from django.conf import settings
from rest_framework.test import APITestCase

from blitz_api.factories import (
    UserFactory,
    OrderFactory,
    ReservationFactory,
    OptionProductFactory,
    OrderLineFactory,
    OrderLineBaseProductFactory
)

from retirement.models import (
    Retreat,
    RetreatDate,
    RetreatType,
)
from store.models import (
    OptionProduct
)

LOCAL_TIMEZONE = pytz.timezone(settings.TIME_ZONE)


class RetreatTests(APITestCase):

    def setUp(self):
        self.retreat_type = ContentType.objects.get_for_model(Retreat)
        self.retreatType = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat,
        )
        self.retreat.activate()

        self.shared_room_option = OptionProductFactory(
            is_room_option=True,
            type=OptionProduct.METADATA_SHARED_ROOM

        )
        self.shared_room_option.available_on_products.add(self.retreat)
        self.shared_room_option.save()

        self.single_room_option = OptionProductFactory(
            is_room_option=True,
            type=OptionProduct.METADATA_NONE
        )
        self.single_room_option.available_on_products.add(self.retreat)
        self.single_room_option.save()

    def test_create(self):
        """
        Ensure that we can create a retreat.
        """
        self.retreatType2 = RetreatType.objects.create(
            name="Type 1",
            minutes_before_display_link=10,
            number_of_tomatoes=4,
        )
        self.retreat2 = Retreat.objects.create(
            name="mega_retreat",
            details="This is a description of the mega retreat.",
            seats=400,
            address_line1="123 random street",
            postal_code="123 456",
            state_province="Random state",
            country="Random country",
            price=199,
            min_day_refund=7,
            min_day_exchange=7,
            refund_rate=50,
            accessibility=True,
            form_url="example.com",
            carpool_url='example2.com',
            review_url='example3.com',
            has_shared_rooms=True,
            toilet_gendered=False,
            room_type=Retreat.SINGLE_OCCUPATION,
            display_start_time=LOCAL_TIMEZONE.localize(
                datetime(2130, 1, 15, 8)
            ),
            type=self.retreatType2,
        )
        RetreatDate.objects.create(
            start_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 15, 8)),
            end_time=LOCAL_TIMEZONE.localize(datetime(2130, 1, 17, 12)),
            retreat=self.retreat2,
        )
        self.retreat2.activate()

        self.assertEqual(self.retreat2.__str__(), "mega_retreat")

    def test_get_retreat_room_distribution(self):
        """
        Test the room distribution for a retreat
        """
        user_1 = UserFactory(email='1@test.ca')
        user_2 = UserFactory(email='2@test.ca')
        user_3 = UserFactory(email='3@test.ca')
        user_4 = UserFactory(email='4@test.ca')
        user_5 = UserFactory(email='5@test.ca')
        user_6 = UserFactory(email='6@test.ca')
        user_7 = UserFactory(email='7@test.ca')
        user_8 = UserFactory(email='8@test.ca')
        user_9 = UserFactory(email='9@test.ca')
        user_10 = UserFactory(email='10@test.ca')
        user_11 = UserFactory(email='11@test.ca')
        user_12 = UserFactory(email='12@test.ca')  # will be non-active
        user_13 = UserFactory(email='13@test.ca')
        user_14 = UserFactory(email='14@test.ca')
        user_15 = UserFactory(email='15@test.ca')
        user_16 = UserFactory(email='16@test.ca')
        user_17 = UserFactory(email='17@test.ca')

        order_1 = OrderFactory(user=user_1)
        order_2 = OrderFactory(user=user_2)
        order_3 = OrderFactory(user=user_3)
        order_4 = OrderFactory(user=user_4)
        order_5 = OrderFactory(user=user_5)
        order_6 = OrderFactory(user=user_6)
        order_7 = OrderFactory(user=user_7)
        order_8 = OrderFactory(user=user_8)
        order_9 = OrderFactory(user=user_9)
        order_10 = OrderFactory(user=user_10)
        order_11 = OrderFactory(user=user_11)
        order_12 = OrderFactory(user=user_12)
        order_13 = OrderFactory(user=user_13)
        order_14 = OrderFactory(user=user_14)
        order_15 = OrderFactory(user=user_15)
        order_16 = OrderFactory(user=user_16)
        order_17 = OrderFactory(user=user_17)

        order_line_1 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_1)
        order_line_2 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_2)
        order_line_3 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_3)
        order_line_4 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_4)
        order_line_5 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_5)
        order_line_6 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_6)
        order_line_7 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_7)
        order_line_8 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_8)
        order_line_9 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_9)
        order_line_10 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_10)
        order_line_11 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_11)
        order_line_12 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_12)
        order_line_13 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_13)
        order_line_14 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_14)
        order_line_15 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_15)
        order_line_16 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_16)
        order_line_17 = OrderLineFactory(content_type=self.retreat_type, object_id=self.retreat.id, order=order_17)

        reservation_1 = ReservationFactory(user=user_1, retreat=self.retreat, order_line=order_line_1)
        reservation_2 = ReservationFactory(user=user_2, retreat=self.retreat, order_line=order_line_2)
        reservation_3 = ReservationFactory(user=user_3, retreat=self.retreat, order_line=order_line_3)
        reservation_4 = ReservationFactory(user=user_4, retreat=self.retreat, order_line=order_line_4)
        reservation_5 = ReservationFactory(user=user_5, retreat=self.retreat, order_line=order_line_5)
        reservation_6 = ReservationFactory(user=user_6, retreat=self.retreat, order_line=order_line_6)
        reservation_7 = ReservationFactory(user=user_7, retreat=self.retreat, order_line=order_line_7)
        reservation_8 = ReservationFactory(user=user_8, retreat=self.retreat, order_line=order_line_8)
        reservation_9 = ReservationFactory(user=user_9, retreat=self.retreat, order_line=order_line_9)
        reservation_10 = ReservationFactory(user=user_10, retreat=self.retreat, order_line=order_line_10)
        reservation_11 = ReservationFactory(user=user_11, retreat=self.retreat, order_line=order_line_11)
        reservation_12 = ReservationFactory(
            user=user_12, retreat=self.retreat, order_line=order_line_12, is_active=False)
        reservation_13 = ReservationFactory(user=user_13, retreat=self.retreat, order_line=order_line_13)
        reservation_14 = ReservationFactory(user=user_14, retreat=self.retreat, order_line=order_line_14)
        reservation_15 = ReservationFactory(user=user_15, retreat=self.retreat, order_line=order_line_15)
        reservation_16 = ReservationFactory(user=user_16, retreat=self.retreat, order_line=order_line_16)
        reservation_17 = ReservationFactory(user=user_17, retreat=self.retreat, order_line=order_line_17)

        metadata_1 = {"share_with_member": "14@test.ca", "share_with_preferred_gender": "mixte"}
        metadata_2 = {"share_with_member": "11@test.ca", "share_with_preferred_gender": "man"}
        metadata_3 = {"share_with_member": "", "share_with_preferred_gender": "woman"}
        metadata_4 = {"share_with_member": "", "share_with_preferred_gender": "non-binary"}
        metadata_5 = {"share_with_member": "", "share_with_preferred_gender": "non-binary"}
        metadata_6 = {"share_with_member": "", "share_with_preferred_gender": "woman"}
        metadata_7 = {"share_with_member": "", "share_with_preferred_gender": "non-binary"}
        metadata_8 = {"share_with_member": "", "share_with_preferred_gender": "man"}
        metadata_9 = {"share_with_member": "", "share_with_preferred_gender": "man"}
        metadata_10 = {"share_with_member": "", "share_with_preferred_gender": "man"}
        metadata_11 = {"share_with_member": "2@test.ca", "share_with_preferred_gender": "woman"}
        metadata_12 = {"share_with_member": "", "share_with_preferred_gender": "woman"}
        metadata_13 = {"share_with_member": "", "share_with_preferred_gender": "woman"}
        metadata_14 = {"share_with_member": "1@test.ca", "share_with_preferred_gender": "woman"}
        metadata_15 = {"share_with_member": "not@found.ca", "share_with_preferred_gender": "mixte"}

        option_1 = OrderLineBaseProductFactory(
                    order_line=order_line_1, option=self.shared_room_option, metadata=metadata_1)
        option_2 = OrderLineBaseProductFactory(
                    order_line=order_line_2, option=self.shared_room_option, metadata=metadata_2)
        option_3 = OrderLineBaseProductFactory(
                    order_line=order_line_3, option=self.shared_room_option, metadata=metadata_3)
        option_4 = OrderLineBaseProductFactory(
                    order_line=order_line_4, option=self.shared_room_option, metadata=metadata_4)
        option_5 = OrderLineBaseProductFactory(
                    order_line=order_line_5, option=self.shared_room_option, metadata=metadata_5)
        option_6 = OrderLineBaseProductFactory(
                    order_line=order_line_6, option=self.shared_room_option, metadata=metadata_6)
        option_7 = OrderLineBaseProductFactory(
                    order_line=order_line_7, option=self.shared_room_option, metadata=metadata_7)
        option_8 = OrderLineBaseProductFactory(
                    order_line=order_line_8, option=self.shared_room_option, metadata=metadata_8)
        option_9 = OrderLineBaseProductFactory(
                    order_line=order_line_9, option=self.shared_room_option, metadata=metadata_9)
        option_10 = OrderLineBaseProductFactory(
                    order_line=order_line_10, option=self.shared_room_option, metadata=metadata_10)
        option_11 = OrderLineBaseProductFactory(
                    order_line=order_line_11, option=self.shared_room_option, metadata=metadata_11)
        option_12 = OrderLineBaseProductFactory(
                    order_line=order_line_12, option=self.shared_room_option, metadata=metadata_12)
        option_13 = OrderLineBaseProductFactory(
                    order_line=order_line_13, option=self.shared_room_option, metadata=metadata_13)
        option_14 = OrderLineBaseProductFactory(
                    order_line=order_line_14, option=self.shared_room_option, metadata=metadata_14)
        option_15 = OrderLineBaseProductFactory(
                    order_line=order_line_15, option=self.shared_room_option, metadata=metadata_15)
        option_16 = OrderLineBaseProductFactory(
                    order_line=order_line_16, option=self.single_room_option)
        option_17 = OrderLineBaseProductFactory(
                    order_line=order_line_17, option=self.single_room_option)

        distribution = self.retreat.get_retreat_room_distribution()
        self.assertEqual(len(distribution), 16)
        room_set = set()
        for user in distribution:
            room_set.add(user['room_number'])
        self.assertEqual(len(room_set), 9)
        # Single room
        self.assertEqual(distribution[0]['email'], user_16.email)
        self.assertEqual(distribution[1]['email'], user_17.email)
        # Friend room
        self.assertEqual(distribution[2]['email'], distribution[3]['share_with'])
        self.assertEqual(distribution[3]['email'], distribution[2]['share_with'])
        self.assertEqual(distribution[2]['room_number'], distribution[3]['room_number'])

        self.assertEqual(distribution[4]['email'], distribution[5]['share_with'])
        self.assertEqual(distribution[5]['email'], distribution[4]['share_with'])
        self.assertEqual(distribution[4]['room_number'], distribution[5]['room_number'])

        # Match room
        self.assertEqual(distribution[6]['gender_preference'], distribution[7]['gender_preference'])
        self.assertEqual(distribution[6]['room_number'], distribution[7]['room_number'])

        self.assertEqual(distribution[8]['gender_preference'], distribution[9]['gender_preference'])
        self.assertEqual(distribution[8]['room_number'], distribution[9]['room_number'])

        self.assertEqual(distribution[10]['gender_preference'], distribution[11]['gender_preference'])
        self.assertEqual(distribution[10]['room_number'], distribution[11]['room_number'])

        # Match as possible
        self.assertEqual(distribution[12]['gender_preference'], metadata_15['share_with_preferred_gender'])
        self.assertEqual(distribution[12]['share_with'], metadata_15['share_with_member'])
        self.assertEqual(distribution[12]['room_number'], distribution[13]['room_number'])

        self.assertEqual(distribution[14]['room_number'], distribution[15]['room_number'])
