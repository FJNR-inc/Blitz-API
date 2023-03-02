import calendar

from rest_framework import status
from rest_framework.test import (
    APIClient,
)
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model

from blitz_api.testing_tools import CustomAPITestCase
from blitz_api.factories import (
    UserFactory,
    AdminFactory,
)
from tomato.factories import TomatoFactory
from tomato.models import Tomato

User = get_user_model()


class TomatoTests(CustomAPITestCase):

    ATTRIBUTES = [
        'id',
        'url',
        'user',
        'number_of_tomato',
        'source',
        'acquisition_date',
        'created_at',
        'updated_at',
    ]

    @classmethod
    def setUpClass(cls):
        super(TomatoTests, cls).setUpClass()

        cls.client = APIClient()
        cls.user = UserFactory()
        cls.admin = AdminFactory()

    def test_create_as_user(self):
        """
        Ensure we can log some tomatoes as a simple user.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'number_of_tomato': 12.5,
            'source': Tomato.TOMATO_SOURCE_MANUAL
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.json(),
        )

        self.check_attributes(response.json())

    def test_create_as_admin(self):
        """
        Ensure we can log some tomatoes as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        data = {
            'number_of_tomato': 12.5,
            'source': Tomato.TOMATO_SOURCE_MANUAL
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.json(),
        )

        self.check_attributes(response.json())

    def test_create_as_unauthenticated(self):
        """
        Ensure we can't log some tomatoes when unauthenticated.
        """

        data = {
            'number_of_tomato': 12.5,
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

        self.assertEqual(
            response.json(),
            {
                "detail": "Authentication credentials were not provided."
            }
        )

    def test_create_in_future(self):
        """
        Ensure we can't log some tomatoes in the future.
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'number_of_tomato': 12.5,
            'acquisition_date': timezone.now() + timedelta(days=30),
            'source': Tomato.TOMATO_SOURCE_MANUAL
        }

        response = self.client.post(
            reverse('tomato-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertEqual(
            response.json(),
            {'acquisition_date': [
                'The date of acquisition of the tomatoes cannot be set '
                'in the future.']}
        )

    def test_list_as_user(self):
        """
        Ensure we can list tomatoes as a simple user.
        """
        for item in range(1, 10):
            TomatoFactory(user=self.user)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            9
        )

        for item in result['results']:
            self.check_attributes(item)

    def test_list_as_unauthenticated(self):
        """
        Ensure we can't list tomatoes as an unauthenticated user.
        """
        for item in range(1, 10):
            TomatoFactory(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_filter_by_user_as_user(self):
        """
        Ensure we can list tomatoes as a simple user filtered by user.
        """
        for item in range(1, 10):
            TomatoFactory(user=self.user)

        user2 = UserFactory()
        for item in range(1, 10):
            TomatoFactory(user=user2)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'user': self.user.id
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            9
        )

        for item in result['results']:
            self.check_attributes(item)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'user': user2.id
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            0
        )

    def test_filter_by_user_as_admin(self):
        """
        Ensure we can list tomatoes as an admin filtered by user.
        """
        for item in range(1, 10):
            TomatoFactory(user=self.user)

        user2 = UserFactory()
        for item in range(1, 10):
            TomatoFactory(user=user2)

        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'user': self.user.id
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            9
        )

        for item in result['results']:
            self.check_attributes(item)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'user': user2.id
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            9
        )

    def test_filter_by_source_as_user(self):
        """
        Ensure we can list tomatoes as a simple user filtered by source.
        """
        for item in range(1, 8):
            TomatoFactory(user=self.user, source=Tomato.TOMATO_SOURCE_RETREAT)

        for item in range(1, 3):
            TomatoFactory(user=self.user, source=Tomato.TOMATO_SOURCE_CHRONO)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'source': Tomato.TOMATO_SOURCE_RETREAT
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            7
        )

        for item in result['results']:
            self.check_attributes(item)

    def test_filter_by_source_as_admin(self):
        """
        Ensure we can list tomatoes as an admin filtered by source.
        """
        for item in range(1, 8):
            TomatoFactory(user=self.user, source=Tomato.TOMATO_SOURCE_RETREAT)

        for item in range(1, 3):
            TomatoFactory(user=self.user, source=Tomato.TOMATO_SOURCE_CHRONO)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'source': Tomato.TOMATO_SOURCE_RETREAT
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            7
        )

        for item in result['results']:
            self.check_attributes(item)

    def test_filter_acquisition_date_as_user(self):
        """
        Ensure we can filter by created_at as user
        """
        today = timezone.now()
        first_day = today.replace(
            day=1, hour=0, minute=0, microsecond=0
        )
        day = calendar.monthrange(today.year, today.month)[1]
        last_day = today.replace(
            day=day, hour=23, minute=59, microsecond=999999
        )
        next_month = today + timedelta(days=31)
        last_month = today - timedelta(days=31)
        # Override created_at only possible through update
        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.all().update(acquisition_date=next_month)

        x = Tomato.objects.create(user=self.user, number_of_tomato=5)
        y = Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.filter(pk__in=[x.id, y.id]).update(
            acquisition_date=last_month)

        for item in range(1, 8):
            Tomato.objects.create(
                user=self.user, acquisition_date=today, number_of_tomato=5)

        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse('tomato-list'),
            {
                'acquisition_date__lte': last_day.strftime(
                    '%Y-%m-%d %H:%M:%S'),
                'acquisition_date__gte': first_day.strftime(
                    '%Y-%m-%d %H:%M:%S'),
            },
            format='json',
        )

        result = response.json()

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            result['count'],
            7
        )

        for item in result['results']:
            self.check_attributes(item)

    def test_community_tomatoes(self):
        """
        Test we can get community tomatoes of current month without being
        authenticated
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('tomato-community-tomatoes'),
            format='json',
        )
        result = response.json()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            result['community_tomato'],
            0
        )
        today = timezone.now()
        # Out of month tomatoes
        last_month = today - timedelta(days=31)
        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.create(user=self.admin, number_of_tomato=4)
        Tomato.objects.create(user=self.user, number_of_tomato=7)
        Tomato.objects.all().update(acquisition_date=last_month)

        t1 = Tomato.objects.create(user=self.user, number_of_tomato=15)
        t2 = Tomato.objects.create(user=self.admin, number_of_tomato=23)
        t3 = Tomato.objects.create(user=self.user, number_of_tomato=45)
        current_entries = [
            t1.number_of_tomato, t2.number_of_tomato, t3.number_of_tomato]

        response = self.client.get(
            reverse('tomato-community-tomatoes'),
            format='json',
        )
        result = response.json()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(
            result['community_tomato'],
            sum(current_entries)
        )

    def test_statistics_tomatoes_invalid_start(self):
        """
        Test we cant get tomatoes statistics with invalid start
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'start_date': 'invalid start',
                'end_date': '2010-01-01T00:00:00Z'
            },
            content_type='application/json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

    def test_statistics_tomatoes_invalid_end(self):
        """
        Test we cant get tomatoes statistics with invalid end
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'end_date': 'invalid start',
                'start_date': '2010-01-01T00:00:00Z'
            },
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

    def test_statistics_tomatoes_invalid_dates(self):
        """
        Test we cant get tomatoes statistics with invalid dates
        """
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'start_date': '2012-01-01T00:00:00Z',
                'end_date': '2010-01-01T00:00:00Z'
            },
            format='json',
        )
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
            response.content
        )

    def test_statistics_tomatoes_empty_data(self):
        """
        Test we can get tomatoes statistics
        even if there is no data at all
        """
        today = timezone.datetime(2023, 2, 26, 0, 0, 0)
        last_year = today - timedelta(days=366)
        limit_last_year = last_year + timedelta(days=1)

        end = today.strftime('%Y-%m-%dT%H:%M:%SZ')
        start = limit_last_year.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'start_date': start,
                'end_date': end
            },
            content_type='application/json',
        )
        result = response.json()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(result['totals']['global'], 0)
        self.assertEqual(result['totals']['user'], 0)
        self.assertEqual(
            result['graph']['labels'],
            [
                '2022-02-01T00:00:00-0500',
                '2022-03-01T00:00:00-0500',
                '2022-04-01T00:00:00-0500',
                '2022-05-01T00:00:00-0500',
                '2022-06-01T00:00:00-0500',
                '2022-07-01T00:00:00-0500',
                '2022-08-01T00:00:00-0500',
                '2022-09-01T00:00:00-0500',
                '2022-10-01T00:00:00-0500',
                '2022-11-01T00:00:00-0500',
                '2022-12-01T00:00:00-0500',
                '2023-01-01T00:00:00-0500',
                '2023-02-01T00:00:00-0500',
            ],
        )
        self.assertEqual(
            result['graph']['datasets'],
            [
                {
                    'label': 'number_of_tomato',
                    'data': [
                        {'x': '2022-02-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-03-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-04-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-05-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-06-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-07-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-08-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-09-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-10-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-11-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-12-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-01T00:00:00-0500', 'y': 0.0},
                    ]
                }
            ],
        )

    def test_statistics_tomatoes_year(self):
        """
        Test we can get tomatoes statistics of current year
        """
        today = timezone.datetime(2023, 2, 26, 0, 0, 0)
        last_year = today - timedelta(days=366)
        limit_last_year = last_year + timedelta(days=1)

        end = today.strftime('%Y-%m-%dT%H:%M:%SZ')
        start = limit_last_year.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.client.force_authenticate(user=self.user)

        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.create(user=self.admin, number_of_tomato=4)
        Tomato.objects.create(user=self.user, number_of_tomato=7)
        Tomato.objects.all().update(acquisition_date=last_year)

        t1 = Tomato.objects.create(
            user=self.user,
            number_of_tomato=15,
            acquisition_date=today - timedelta(days=1),
        )
        t2 = Tomato.objects.create(
            user=self.admin,
            number_of_tomato=23,
            acquisition_date=today - timedelta(days=2),
        )
        t3 = Tomato.objects.create(
            user=self.user,
            number_of_tomato=45,
            acquisition_date=today - timedelta(days=3),
        )
        current_entries = [
            t1.number_of_tomato,
            t2.number_of_tomato,
            t3.number_of_tomato,
        ]
        user_entries = [
            t1.number_of_tomato,
            t3.number_of_tomato,
        ]

        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'start_date': start,
                'end_date': end
            },
            content_type='application/json',
        )
        result = response.json()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(result['totals']['global'], sum(current_entries))
        self.assertEqual(result['totals']['user'], sum(user_entries))
        self.assertEqual(
            result['graph']['labels'],
            [
                '2022-02-01T00:00:00-0500',
                '2022-03-01T00:00:00-0500',
                '2022-04-01T00:00:00-0500',
                '2022-05-01T00:00:00-0500',
                '2022-06-01T00:00:00-0500',
                '2022-07-01T00:00:00-0500',
                '2022-08-01T00:00:00-0500',
                '2022-09-01T00:00:00-0500',
                '2022-10-01T00:00:00-0500',
                '2022-11-01T00:00:00-0500',
                '2022-12-01T00:00:00-0500',
                '2023-01-01T00:00:00-0500',
                '2023-02-01T00:00:00-0500',
            ],
        )
        self.assertEqual(
            result['graph']['datasets'],
            [
                {
                    'label': 'number_of_tomato',
                    'data': [
                        {'x': '2022-02-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-03-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-04-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-05-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-06-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-07-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-08-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-09-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-10-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-11-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2022-12-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-01T00:00:00-0500', 'y': 0.0},
                        {
                            'x': '2023-02-01T00:00:00-0500',
                            'y': 60.0
                        },
                    ]
                }
            ],
        )

    def test_statistics_tomatoes_month(self):
        """
        Test we can get tomatoes statistics of current month
        """
        today = timezone.datetime(2023, 2, 26, 0, 0, 0)
        last_month = today - timedelta(days=32)
        limit_last_month = last_month + timedelta(days=1)

        end = today.strftime('%Y-%m-%dT%H:%M:%SZ')
        start = limit_last_month.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.client.force_authenticate(user=self.user)

        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.create(user=self.admin, number_of_tomato=4)
        Tomato.objects.create(user=self.user, number_of_tomato=7)
        Tomato.objects.all().update(acquisition_date=last_month)

        t1 = Tomato.objects.create(
            user=self.user,
            number_of_tomato=15,
            acquisition_date=today - timedelta(days=1),
        )
        t2 = Tomato.objects.create(
            user=self.admin,
            number_of_tomato=23,
            acquisition_date=today - timedelta(days=2),
        )
        t3 = Tomato.objects.create(
            user=self.user,
            number_of_tomato=45,
            acquisition_date=today - timedelta(days=3),
        )
        current_entries = [
            t1.number_of_tomato,
            t2.number_of_tomato,
            t3.number_of_tomato,
        ]
        user_entries = [
            t1.number_of_tomato,
            t3.number_of_tomato,
        ]

        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'start_date': start,
                'end_date': end
            },
            content_type='application/json',
        )
        result = response.json()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(result['totals']['global'], sum(current_entries))
        self.assertEqual(result['totals']['user'], sum(user_entries))
        self.assertEqual(
            result['graph']['labels'],
            [
                '2023-01-25T00:00:00-0500',
                '2023-01-26T00:00:00-0500',
                '2023-01-27T00:00:00-0500',
                '2023-01-28T00:00:00-0500',
                '2023-01-29T00:00:00-0500',
                '2023-01-30T00:00:00-0500',
                '2023-01-31T00:00:00-0500',
                '2023-02-01T00:00:00-0500',
                '2023-02-02T00:00:00-0500',
                '2023-02-03T00:00:00-0500',
                '2023-02-04T00:00:00-0500',
                '2023-02-05T00:00:00-0500',
                '2023-02-06T00:00:00-0500',
                '2023-02-07T00:00:00-0500',
                '2023-02-08T00:00:00-0500',
                '2023-02-09T00:00:00-0500',
                '2023-02-10T00:00:00-0500',
                '2023-02-11T00:00:00-0500',
                '2023-02-12T00:00:00-0500',
                '2023-02-13T00:00:00-0500',
                '2023-02-14T00:00:00-0500',
                '2023-02-15T00:00:00-0500',
                '2023-02-16T00:00:00-0500',
                '2023-02-17T00:00:00-0500',
                '2023-02-18T00:00:00-0500',
                '2023-02-19T00:00:00-0500',
                '2023-02-20T00:00:00-0500',
                '2023-02-21T00:00:00-0500',
                '2023-02-22T00:00:00-0500',
                '2023-02-23T00:00:00-0500',
                '2023-02-24T00:00:00-0500',
                '2023-02-25T00:00:00-0500',
            ],
        )
        self.assertEqual(
            result['graph']['datasets'],
            [
                {
                    'label': 'number_of_tomato',
                    'data': [
                        {'x': '2023-01-25T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-26T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-27T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-28T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-29T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-30T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-01-31T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-01T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-02T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-03T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-04T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-05T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-06T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-07T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-08T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-09T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-10T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-11T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-12T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-13T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-14T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-15T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-16T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-17T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-18T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-19T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-20T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-21T00:00:00-0500', 'y': 0.0},
                        {'x': '2023-02-22T00:00:00-0500', 'y': 0.0},
                        {
                            'x': '2023-02-23T00:00:00-0500',
                            'y': 45.0
                        },
                        {'x': '2023-02-24T00:00:00-0500', 'y': 0.0},
                        {
                            'x': '2023-02-25T00:00:00-0500',
                            'y': 15.0
                        }
                    ]
                }
            ],
        )

    def test_statistics_tomatoes_week(self):
        """
        Test we can get tomatoes statistics of current week
        """
        today = timezone.datetime(2023, 2, 26, 0, 0, 0)
        last_week = today - timedelta(days=7)
        limit_last_week = last_week + timedelta(days=1)

        end = today.strftime('%Y-%m-%dT%H:%M:%SZ')
        start = limit_last_week.strftime('%Y-%m-%dT%H:%M:%SZ')
        self.client.force_authenticate(user=self.user)

        Tomato.objects.create(user=self.user, number_of_tomato=5)
        Tomato.objects.create(user=self.admin, number_of_tomato=4)
        Tomato.objects.create(user=self.user, number_of_tomato=7)
        Tomato.objects.all().update(acquisition_date=last_week)

        t1 = Tomato.objects.create(
            user=self.user,
            number_of_tomato=15,
            acquisition_date=today - timedelta(days=1),
        )
        t2 = Tomato.objects.create(
            user=self.admin,
            number_of_tomato=23,
            acquisition_date=today - timedelta(days=2),
        )
        t3 = Tomato.objects.create(
            user=self.user,
            number_of_tomato=45,
            acquisition_date=today - timedelta(days=3),
        )
        current_entries = [
            t1.number_of_tomato,
            t2.number_of_tomato,
            t3.number_of_tomato,
        ]
        user_entries = [
            t1.number_of_tomato,
            t3.number_of_tomato,
        ]

        response = self.client.get(
            reverse('tomato-statistics'),
            data={
                'start_date': start,
                'end_date': end
            },
            content_type='application/json',
        )
        result = response.json()
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        self.assertEqual(result['totals']['global'], sum(current_entries))
        self.assertEqual(result['totals']['user'], sum(user_entries))
        self.assertEqual(
            result['graph']['labels'],
            [
                '2023-02-19T00:00:00-0500',
                '2023-02-20T00:00:00-0500',
                '2023-02-21T00:00:00-0500',
                '2023-02-22T00:00:00-0500',
                '2023-02-23T00:00:00-0500',
                '2023-02-24T00:00:00-0500',
                '2023-02-25T00:00:00-0500',
            ],
        )
        self.assertEqual(
            result['graph']['datasets'],
            [
                {
                    'label': 'number_of_tomato',
                    'data': [
                        {
                            'x': '2023-02-19T00:00:00-0500',
                            'y': 0.0,
                        },
                        {
                            'x': '2023-02-20T00:00:00-0500',
                            'y': 0.0,
                        },
                        {
                            'x': '2023-02-21T00:00:00-0500',
                            'y': 0.0,
                        },
                        {
                            'x': '2023-02-22T00:00:00-0500',
                            'y': 0.0,
                        },
                        {
                            'x': '2023-02-23T00:00:00-0500',
                            'y': 45.0
                        },
                        {
                            'x': '2023-02-24T00:00:00-0500',
                            'y': 0.0
                        },
                        {
                            'x': '2023-02-25T00:00:00-0500',
                            'y': 15.0
                        }
                    ]
                },
            ],
        )
