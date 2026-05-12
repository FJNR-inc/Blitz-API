import requests

from celery import shared_task
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from django.db.models import Sum, Q, F, Value
from django.db.models.functions import Coalesce

from retirement.models import WaitQueuePlace
from store.models import Refund, RefundTransaction

@shared_task
def process_refund():
    # Get refunds where the total successful transaction amount is less than the refund amount
    refunds = Refund.objects.annotate(
        successful_amount=Coalesce(
            Sum(
                'transactions__amount',
                filter=Q(transactions__is_successful=True)
            ),
            Value(0)
        )
    ).filter(
        successful_amount__lt=F('amount')
    )
    
    for refund in refunds:
        if refund.transactions.all().exists():
            # We already tried to process this refund, so we skip it to avoid duplicates
            # This logic could be enhance in the future to handle retries and failures
            continue
        
        # Call the external API to process the refund
        refund.process_automatic_refund()