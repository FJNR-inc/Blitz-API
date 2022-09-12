from unittest import mock
from django.test import TestCase
from datetime import datetime
from dateutil.relativedelta import relativedelta


from log_management.tasks import export_anonymous_chrono_data
from log_management.factories import (
    ActionLogFactory
)
from log_management.models import ActionLog
from blitz_api.models import ExportMedia
from blitz_api.factories import AdminFactory


class TestExportAnonymousChronoDataTask(TestCase):

    def setUp(self):
        self.admin = AdminFactory()
        ActionLogFactory()
        ActionLogFactory()
        ActionLogFactory()
        ActionLogFactory()

        self.assertEqual(
            ActionLog.objects.all().count(),
            4)

    @mock.patch('blitz_api.models.ExportMedia.send_confirmation_email')
    def test_export_anonymous_chrono_data(self, mock_method):
        """
        """
        mock_method.return_value = None
        end_date = datetime.now()
        start_date = end_date - relativedelta(months=1)
        start_date = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date = end_date.strftime('%Y-%m-%d %H:%M:%S')
        export_anonymous_chrono_data(self.admin.id, start_date, end_date)
        self.assertEqual(
            ExportMedia.objects.all().count(),
            1)
        export = ExportMedia.objects.all().first()
        self.assertEqual(
            export.type,
            ExportMedia.EXPORT_ANONYMOUS_CHRONO_DATA)
