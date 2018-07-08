import json

from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from django.urls import reverse

from .. import models
from ..factories import UserFactory, AdminFactory


class UsersIdTests(APITestCase):

    @classmethod
    def setUpClass(cls):
        super(UsersIdTests, cls).setUpClass()
        org = models.Organization.objects.create(name="random_university")
        models.Domain.objects.create(
            name="mailinator.com",
            organization_id=org.id
        )
        models.AcademicField.objects.create(name="random_field")
        models.AcademicLevel.objects.create(name="random_level")
        cls.user_attrs = [
            'id',
            'url',
            'email',
            'first_name',
            'last_name',
            'is_active',
            'phone',
            'other_phone',
            'is_superuser',
            'is_staff',
            'university',
            'last_login',
            'date_joined',
            'academic_level',
            'academic_field',
            'gender',
            'birthdate',
            'groups',
            'user_permissions',
            'tickets',
            'membership',
            'membership_end',
        ]

    def setUp(self):
        self.client = APIClient()

        self.user = UserFactory()
        self.user.set_password('Test123!')
        self.user.save()

        self.admin = AdminFactory()
        self.admin.set_password('Test123!')
        self.admin.save()

    def test_retrieve_user_id_not_exist(self):
        """
        Ensure we can't retrieve a user that doesn't exist.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            reverse(
                'user-detail',
                kwargs={'pk': 999},
            )
        )

        content = {"detail": "Not found."}
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_retrieve_user_id_not_exist_without_permission(self):
        """
        Ensure we can't know a user doesn't exist without permission
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'user-detail',
                kwargs={'pk': 999},
            )
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_retrieve_user(self):
        """
        Ensure we can retrieve a user.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            )
        )

        content = json.loads(response.content)

        # Check id of the user
        self.assertEqual(content['id'], 1)

        # Check the system doesn't return attributes not expected
        attributes = self.user_attrs.copy()
        for key in content.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_retrieve_user_profile(self):
        """
        Ensure we can retrieve our details through /profile.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse(
                'profile',
            )
        )

        content = json.loads(response.content)

        # Check id of the user
        self.assertEqual(content['id'], 1)

        # Check the system doesn't return attributes not expected
        attributes = self.user_attrs.copy()
        for key in content.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_user_with_permission(self):
        """
        Ensure we can update a specific user if caller has permission.
        """

        data = {
            "phone": "1234567890",
        }

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = json.loads(response.content)

        # Check if update was successful
        self.assertEqual(content['phone'], data['phone'])

        # Check id of the user
        self.assertEqual(content['id'], 1)

        # Check the system doesn't return attributes not expected
        attributes = self.user_attrs.copy()
        for key in content.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_partial_update_user_with_permission_change_password(self):
        """
        Ensure we can change password if current password is provided and the
        new password is validated.
        """

        data = {
            "password": "Test123!",
            "new_password": "!321tseT"
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = json.loads(response.content)

        # Check id of the user
        self.assertEqual(content['id'], 1)

        # Check the system doesn't return attributes not expected
        attributes = self.user_attrs.copy()
        for key in content.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        self.user.refresh_from_db()

        # Ensure that the password has been changed successfully
        self.assertTrue(self.user.check_password("!321tseT"))

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user_with_permission(self):
        """
        Ensure we can update a specific user if caller has permission.
        Put requires a full update, including password.
        """
        data = {
            'password': 'Test123!',
            'new_password': '!321tset',
            'phone': '1234567890',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                'name': "random_university"
            },
            'academic_field': {'name': "random_field"},
            'academic_level': {'name': "random_level"},
            'gender': "M",
            'birthdate': "1999-11-11",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.put(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = json.loads(response.content)

        self.user.refresh_from_db()

        # Check if update was successful
        self.assertEqual(content['phone'], data['phone'])
        self.assertTrue(self.user.check_password("!321tset"))

        # Check id of the user
        self.assertEqual(content['id'], 1)

        # Check the system doesn't return attributes not expected
        attributes = self.user_attrs.copy()
        for key in content.keys():
            self.assertTrue(
                key in attributes,
                'Attribute "{0}" is not expected but is '
                'returned by the system.'.format(key)
            )
            attributes.remove(key)

        # Ensure the system returns all expected attributes
        self.assertTrue(
            len(attributes) == 0,
            'The system failed to return some '
            'attributes : {0}'.format(attributes)
        )

        # Check the status code
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user_without_permission(self):
        """
        Ensure we can't update a specific user doesn't have permission.
        """

        data = {
            "phone": "1234567890",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.admin.id},
            ),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_non_existent_user(self):
        """
        Ensure we get permission denied when trying to update an invalid user.
        """

        data = {
            "phone": "1234567890",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': 9999},
            ),
            data,
            format='json',
        )

        content = {
            'detail': 'You do not have permission to perform this action.'
        }
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_non_existent_user_as_admin(self):
        """
        Ensure we get not found when trying to update an invalid user as
        an admin.
        """

        data = {
            "phone": "1234567890",
        }

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': 9999},
            ),
            data,
            format='json',
        )

        content = {'detail': 'Not found.'}

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_weak_new_password(self):
        """
        Ensure we can't update our password if it is not validated.
        """

        data = {
            "phone": "1234567890",
            "password": "Test123!",
            "new_password": "1234567890",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = {'new_password': ['This password is entirely numeric.']}
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_missing_old_password(self):
        """
        Ensure we can't update our password if the current one is not provided.
        """

        data = {
            "phone": "1234567890",
            "new_password": "1234567890",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = {'password': 'This field is required.'}
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_wrong_old_password(self):
        """
        Ensure we can't update our password if the current one is wrong.
        """

        data = {
            "phone": "1234567890",
            "password": "invalid",
            "new_password": "new_pass123",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = {'password': 'Bad password'}
        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_invalid_fields(self):
        """
        Ensure we can't update fields with invalid values.
        Some fields like university are ignored and left in data on
        purpose.
        """

        data = {
            'email': 'John@invalid.com',
            'password': '1927nce-736',
            'first_name': 'Chuck',
            'last_name': 'Norris',
            'university': {
                "name": "invalid_university"
            },
            'academic_field': {'name': "invalid_field"},
            'academic_level': {'name': "invalid_level"},
            'gender': "invalid_gender",
            'birthdate': "invalid_date",
        }

        self.client.force_authenticate(user=self.user)

        response = self.client.patch(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
            data,
            format='json',
        )

        content = {
            'academic_field': ['This academic field does not exist.'],
            'birthdate': [
                'Date has wrong format. Use one of these formats instead: '
                'YYYY[-MM[-DD]].'
            ],
            'gender': ['"invalid_gender" is not a valid choice.']
        }

        self.assertEqual(json.loads(response.content), content)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_user_as_admin(self):
        """
        Ensure we can deactivate a user as an admin.
        """
        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
        )
        self.user.refresh_from_db()

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )
        self.assertFalse(self.user.is_active)

        self.user.is_active = True
        self.user.refresh_from_db()

    def test_delete_user(self):
        """
        Ensure that a user can deactivate its own account.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'user-detail',
                kwargs={'pk': self.user.id},
            ),
        )
        self.user.refresh_from_db()

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )
        self.assertFalse(self.user.is_active)

        self.user.is_active = True
        self.user.refresh_from_db()

    def test_delete_inexistent_user(self):
        """
        Ensure that deleting a non-existent user does nothing.
        """
        self.client.force_authenticate(user=self.user)

        response = self.client.delete(
            reverse(
                'user-detail',
                kwargs={'pk': 999},
            ),
        )

        self.assertEqual(
            response.status_code, status.HTTP_204_NO_CONTENT
        )
