import json

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import (
    APIRequestFactory,
    APITestCase
)
from blitz_api.factories import (
    UserFactory,
    AdminFactory,
    MagicLinkFactory
)
from blitz_api.models import MagicLink


class TestMagicLink(APITestCase):
    def setUp(self):
        self.user = UserFactory()
        self.user.set_password('Test1234!')
        self.user.save()

        self.admin = AdminFactory()
        self.admin.set_password('Test123!')
        self.admin.save()

        self.magiclink = MagicLinkFactory()

        factory = APIRequestFactory()
        self.request = factory.get('/')

    def test_create_magiclink_as_user(self):
        """
        Test that a user can't create a MagicLink
        """
        self.client.force_authenticate(user=self.user)

        data = {
            'full_link': 'My user full link',
            'description': 'My magiclink description',
        }

        response = self.client.post(
            reverse('magiclink-list'),
            data,
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
            response.content
        )
        content = json.loads(response.content)
        self.assertEqual(
            content,
            {
                "detail":
                    "You do not have permission to perform this action."
            }
        )


def test_retrieve_magiclink_as_unauthenticated(self):
    """
    Test that an unauthenticated user can retrieve a MagicLink
    """
    response = self.client.get(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
        ),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
        response.content
    )
    content = json.loads(response.content)
    self.assertEqual(
        content['full_link'],
        self.magiclink.full_link
    )
    magic_link = MagicLink.objects.get(id=self.magiclink.id)
    self.assertEqual(magic_link.nb_uses, 1)


def test_retrieve_magiclink_as_user(self):
    """
    Test that a user can retrieve a MagicLink
    """
    self.client.force_authenticate(user=self.user)

    response = self.client.get(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
        ),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
        response.content
    )
    content = json.loads(response.content)
    self.assertEqual(
        content['full_link'],
        self.magiclink.full_link
    )
    magic_link = MagicLink.objects.get(id=self.magiclink.id)
    self.assertEqual(magic_link.nb_uses, 1)


def test_retrieve_magiclink_as_user_uses(self):
    """
    Test that retrieving a magic link increments its uses
    """
    self.client.force_authenticate(user=self.user)

    response = self.client.get(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
        ),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
    )
    response = self.client.get(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
        ),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
    )
    magic_link = MagicLink.objects.get(id=self.magiclink.id)
    self.assertEqual(magic_link.nb_uses, 2)


def test_update_magiclink_as_user(self):
    """
    Test that a user can't update the magiclink
    """
    data = {
        'full_link': 'My user full link',
        'description': 'Long Text Updated',
    }

    self.client.force_authenticate(user=self.user)

    response = self.client.patch(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
            request=self.request
        ),
        data,
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_403_FORBIDDEN,
        response.content
    )

    content = json.loads(response.content)
    self.assertEqual(
        content,
        {
            "detail":
                "You do not have permission to perform this action."
        }
    )


def test_destroy_magiclink_as_user(self):
    """
    Test that a user can't destroy the magiclink
    """

    self.client.force_authenticate(user=self.user)

    response = self.client.delete(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
            request=self.request
        ),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_403_FORBIDDEN,
        response.content
    )

    content = json.loads(response.content)
    self.assertEqual(
        content,
        {
            "detail":
                "You do not have permission to perform this action."
        }
    )


def test_create_magiclink_as_admin(self):
    """
    Test that a staff member can create a MagicLink
    """
    self.client.force_authenticate(user=self.admin)

    data = {
        'full_link': 'My user full link',
        'description': 'Long Text',
    }

    response = self.client.post(
        reverse('magiclink-list'),
        data,
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_201_CREATED,
        response.content
    )


def test_list_all_magiclinks_as_admin(self):
    """
    Test that a staff member can list the magiclinks
    """
    self.magiclink_2 = MagicLinkFactory()
    self.magiclink_3 = MagicLinkFactory()

    self.client.force_authenticate(user=self.admin)
    response = self.client.get(
        reverse('magiclink-list'),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
        response.content
    )
    content = json.loads(response.content)
    self.assertEqual(
        (content['count']),
        3
    )


def test_search_magiclink_type(self):
    """
    Ensure an admin can filter magiclinks by type
    """
    self.magiclink_2 = MagicLinkFactory()

    self.client.force_authenticate(user=self.admin)
    response = self.client.get(
        reverse('magiclink-list') + '?search=DOWNLOAD',
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
        response.content
    )
    content = json.loads(response.content)
    self.assertEqual(
        (content['count']),
        2
    )


def test_update_magiclink_as_admin(self):
    """
    Test that a staff member can update a magiclink
    """
    self.client.force_authenticate(user=self.admin)

    data = {
        'description': 'New Long Text updated',
    }

    response = self.client.patch(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
            request=self.request
        ),
        data,
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_200_OK,
        response.content
    )
    content = json.loads(response.content)

    self.assertEqual(
        content['description'],
        'New Long Text updated'
    )

    self.assertEqual(
        MagicLink.objects.get(id=self.magiclink.id).description,
        'New Long Text updated'
    )


def test_destroy_magiclink_as_admin(self):
    """
    Test that a staff member can destroy a magiclink
    """
    self.client.force_authenticate(user=self.admin)

    response = self.client.delete(
        reverse(
            'magiclink-detail',
            kwargs={'pk': self.magiclink.id},
            request=self.request
        ),
        format='json',
    )

    self.assertEqual(
        response.status_code,
        status.HTTP_204_NO_CONTENT,
        response.content
    )
