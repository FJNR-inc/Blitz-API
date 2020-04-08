

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse


class MailChimpTests(APITestCase):

    def setUp(self):
        self.client = APIClient()

    def test_create(self):

        data = {
            'email': 'jeffyer38130@gmail.com',
            'first_name': 'Chuck',
            'last_name': 'Norris',
        }

        response = self.client.post(
            reverse('mail_chimp'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.content
        )
