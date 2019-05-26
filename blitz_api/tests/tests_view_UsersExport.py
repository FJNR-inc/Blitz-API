import json

from rest_framework import status
from rest_framework.response import Response
from rest_framework.test import APIClient, APITestCase

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.conf import settings

from xlrd import open_workbook
from xlrd.sheet import Sheet

from ..factories import UserFactory, AdminFactory

User = get_user_model()


class UsersTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(UsersTests, cls).setUpClass()
        cls.client = APIClient()
        cls.client_authenticate = APIClient()
        cls.export_url = reverse('user-export')

    def setUp(self):
        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.save()

        self.admin = AdminFactory()
        self.admin.set_password('Test123!')
        self.admin.save()

        self.client_authenticate.force_authenticate(user=self.admin)

        self.nb_setup_user = 2

    def test_export_content(self):
        response: Response = self.client_authenticate.get(
            self.export_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.content
        )

        export_response = json.loads(response.content)

        self.assertEqual(
            export_response['count'],
            self.nb_setup_user,
            "Count value of export is different than expected"
        )

        self.assertEqual(
            export_response['limit'],
            1000,
        )

        """
        response_export_file: Response = self.client.get(
            export_response['file_url']
        )

        self.assertNotEqual(
            response_export_file.status_code,
            status.HTTP_404_NOT_FOUND,
            export_response['file_url']
        )

        self.assertEqual(
            response_export_file.status_code,
            status.HTTP_200_OK,
            response_export_file.content
        )

        wb = open_workbook(file_contents=response.content)

        first_sheet: Sheet = wb.sheets[0]

        col_infos = []

        for col_number in range(first_sheet.ncols):
            try:
                col_infos.append({
                    'col_number': col_number,
                    'col_name': first_sheet.cell(1, col_number).value
                })

            except:
                pass

        users = []

        for row in range(first_sheet.nrows):
            user_data = dict()
            try:
                for col_info in col_infos:

                    user_info = first_sheet.cell(
                        row,
                        col_info['col_number']).value
                    user_data[col_info['col_name']] = user_info

            except:
                pass

            users.append(user_data)

        user_0_id = users[0]['id']

        user_0 = User.objects.get(id=user_0_id)

        self.assertEqual(
            users[0]['first_name'],
            user_0.first_name,
            users[0]
        )"""
