from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone

from store.exceptions import PaymentAPIError
from store.models import Refund
from store.services import (PAYSAFE_EXCEPTION,
                            refund_amount, )


TAX_RATE = settings.LOCAL_SETTINGS['SELLING_TAX']


def notify_reserved_retirement_seat(user, retirement):
    """
    This function sends an email to notify a user that he has a reserved seat
    to a retirement for 24h hours.
    """

    merge_data = {'RETIREMENT_NAME': retirement.name}

    plain_msg = render_to_string("reserved_place.txt", merge_data)
    msg_html = render_to_string("reserved_place.html", merge_data)

    return send_mail(
        "Place exclusive pour 24h",
        plain_msg,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=msg_html,
    )


def send_retirement_7_days_email(user, retirement):
    """
    This function sends an email to notify a user that a retirement in which he
    has bought a seat is starting in 7 days.
    """

    merge_data = {'RETIREMENT': retirement}

    plain_msg = render_to_string("reminder.txt", merge_data)
    msg_html = render_to_string("reminder.html", merge_data)

    return send_mail(
        "Rappel retraite",
        plain_msg,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=msg_html,
    )


def send_post_retirement_email(user, retirement):
    """
    This function sends an email to get back to a user after a retirement has
    ended.
    """

    merge_data = {'RETIREMENT': retirement}

    plain_msg = render_to_string("throwback.txt", merge_data)
    msg_html = render_to_string("throwback.html", merge_data)

    return send_mail(
        "Merci pour votre participation",
        plain_msg,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=msg_html,
    )


def refund_retirement(reservation, refund_rate, refund_reason):
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
    retirement = reservation.retirement
    previous_refunds = orderline.refunds
    refunded_amount = Decimal(0)

    if previous_refunds:
        refunded_amount = sum(
            previous_refunds.all().values_list('amount', flat=True)
        )

    amount_to_refund = (retirement.price - refunded_amount) * refund_rate

    tax = round(amount_to_refund * Decimal(TAX_RATE), 2)
    amount_to_refund *= Decimal(TAX_RATE + 1)

    refund_response = refund_amount(
        orderline.order.settlement_id,
        int(amount_to_refund)
    )

    refund_instance = Refund.objects.create(
        orderline=orderline,
        refund_date=timezone.now(),
        amount=amount_to_refund/100,
        details=refund_reason,
    )

    return refund_instance
