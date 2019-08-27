from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from retirement.models import WaitQueue
from store.models import Refund
from store.services import (PAYSAFE_EXCEPTION,
                            refund_amount, )

TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


def notify_reserved_retreat_seat(user, retreat):
    """
    This function sends an email to notify a user that he has a reserved seat
    to a retreat for 24h hours.
    """

    wait_queue: WaitQueue = WaitQueue.objects.get(user=user, retreat=retreat)

    # Setup the url for the activation button in the email
    wait_queue_url = settings.LOCAL_SETTINGS[
        'FRONTEND_INTEGRATION'][
        'RETREAT_UNSUBSCRIBE_URL'] \
        .replace(
        "{{wait_queue_id}}",
        str(wait_queue.id)
    )

    merge_data = {'RETREAT_NAME': retreat.name,
                  'WAIT_QUEUE_URL': wait_queue_url}

    plain_msg = render_to_string("reserved_place.txt", merge_data)
    msg_html = render_to_string("reserved_place.html", merge_data)

    return send_mail(
        "Place exclusive pour 24h",
        plain_msg,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=msg_html,
    )


def send_retreat_7_days_email(user, retreat):
    """
    This function sends an email to notify a user that a retreat in which he
    has bought a seat is starting in 7 days.
    """

    merge_data = {'RETREAT': retreat}

    plain_msg = render_to_string("reminder.txt", merge_data)
    msg_html = render_to_string("reminder.html", merge_data)

    return send_mail(
        "Rappel retraite",
        plain_msg,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=msg_html,
    )


def send_post_retreat_email(user, retreat):
    """
    This function sends an email to get back to a user after a retreat has
    ended.
    """

    merge_data = {
        'RETREAT': retreat,
        'USER': user,
    }

    plain_msg = render_to_string("throwback.txt", merge_data)
    msg_html = render_to_string("throwback.html", merge_data)

    return send_mail(
        "Merci pour votre participation",
        plain_msg,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=msg_html,
    )


def refund_retreat(reservation, refund_rate, refund_reason):
    """
    reservation: Reservation model instance
    refund_rate: integer from 0 to 100 defining percentage of amount refunded
    refund_reason: string for additonnal details

    This function finds the order associated to the reservation and does a
    complete refund. It also creates the Refund object to keep track of the
    transaction.
    """
    orderline = reservation.order_line
    user = orderline.order.user
    retreat = reservation.retreat
    previous_refunds = orderline.refunds
    refunded_amount = Decimal(0)

    if previous_refunds:
        refunded_amount = sum(
            previous_refunds.all().values_list('amount', flat=True)
        )

    amount_to_refund = (retreat.price - refunded_amount) * refund_rate

    tax = round(amount_to_refund * Decimal(TAX_RATE), 2)
    amount_to_refund *= Decimal(TAX_RATE + 1)

    refund_response = refund_amount(
        orderline.order.settlement_id,
        int(amount_to_refund)
    )
    refund_res_content = refund_response.json()

    refund_instance = Refund.objects.create(
        orderline=orderline,
        refund_date=timezone.now(),
        amount=amount_to_refund / 100,
        details=refund_reason,
        refund_id=refund_res_content['id'],
    )

    return refund_instance
