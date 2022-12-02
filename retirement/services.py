import json
import pytz
from babel.dates import format_date
from decimal import Decimal
from django.conf import settings
from blitz_api.services import (
    send_mail as send_templated_email,
    send_email_from_template_id,
)
from django.utils import timezone
from retirement.models import WaitQueue
from store.models import Refund
from store.services import refund_amount

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

    context = {
        'USER_FIRST_NAME': user.first_name,
        'USER_LAST_NAME': user.last_name,
        'USER_EMAIL': user.email,
        'RETREAT_NAME': retreat.name,
        'WAIT_QUEUE_URL': wait_queue_url,
    }

    send_templated_email(
        [user.email],
        context,
        'WAIT_QUEUE_RESERVED_SEAT_CREATED'
    )


def send_retreat_confirmation_email(user, retreat):
    """
    This function sends an email to notify a user that his reservation to a
    specific retreat is confirmed.
    :param user: The user on the reservation
    :param retreat: The retreat that the user just bought
    :return:
    """
    if retreat.type.template_id_for_welcome_message:
        start_time = retreat.start_time
        start_time = start_time.astimezone(pytz.timezone('US/Eastern'))

        end_time = retreat.end_time
        end_time = end_time.astimezone(pytz.timezone('US/Eastern'))
        context = {
            'CUSTOM': json.loads(retreat.type.context_for_welcome_message),
            'USER_FIRST_NAME': user.first_name,
            'USER_LAST_NAME': user.last_name,
            'USER_EMAIL': user.email,
            'RETREAT_NAME': retreat.name_fr,
            'RETREAT_START_DATE': format_date(
                start_time,
                format='long',
                locale='fr'
            ),
            'RETREAT_START_TIME': start_time.strftime('%-Hh%M'),
            'RETREAT_END_DATE': format_date(
                end_time,
                format='long',
                locale='fr'
            ),
            'RETREAT_TYPE': retreat.type.name_fr,
            'RETREAT_END_TIME': end_time.strftime('%-Hh%M'),
            'RETREAT_START': start_time.strftime('%Y-%m-%d %H:%M'),
            'RETREAT_END': end_time.strftime('%Y-%m-%d %H:%M'),
            'RETREAT_VIDEOCONFERENCE_TOOL': retreat.videoconference_tool,
            'RETREAT_VIDEOCONFERENCE_LINK': retreat.videoconference_link,
            'RETREAT_NUMBER_OF_TOMATOES': retreat.get_number_of_tomatoes(),
            'LINK_TO_BE_PREPARED': settings.LOCAL_SETTINGS[
                'FRONTEND_INTEGRATION'][
                'LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT'],
            'LINK_TO_USER_PROFILE': settings.LOCAL_SETTINGS[
                'FRONTEND_INTEGRATION']['PROFILE_URL'],
        }
        if len(retreat.pictures.all()):
            context['RETREAT_PICTURE'] = "{0}{1}".format(
                settings.MEDIA_URL,
                retreat.pictures.first().picture.url
            )

        response_send_mail = send_email_from_template_id(
            [user],
            context,
            retreat.type.template_id_for_welcome_message
        )
        return response_send_mail
    else:
        return []


def send_retreat_reminder_email(user, retreat):
    """
    This function sends an email to notify a user that a retreat in which he
    has bought a seat is starting soon.
    :param user: The user on the reservation
    :param retreat: The retreat that will begin soon
    :return:
    """
    if retreat.type.name_fr == 'Virtuelle':
        return send_virtual_retreat_reminder_email(user, retreat)
    else:
        return send_physical_retreat_reminder_email(user, retreat)


def send_virtual_retreat_reminder_email(user, retreat):
    """
    This function sends an email to notify a user that a virtual retreat in
    which he has bought a seat is starting soon.
    """

    start_time = retreat.start_time
    start_time = start_time.astimezone(pytz.timezone('US/Eastern'))

    end_time = retreat.end_time
    end_time = end_time.astimezone(pytz.timezone('US/Eastern'))
    context = {
        'USER_FIRST_NAME': user.first_name,
        'USER_LAST_NAME': user.last_name,
        'USER_EMAIL': user.email,
        'RETREAT_NAME': retreat.name_fr,
        'RETREAT_START_DATE': format_date(
            start_time,
            format='long',
            locale='fr'
        ),
        'RETREAT_START_TIME': start_time.strftime('%-Hh%M'),
        'RETREAT_END_DATE': format_date(
            end_time,
            format='long',
            locale='fr'
        ),
        'RETREAT_END_TIME': end_time.strftime('%-Hh%M'),
        'RETREAT_NUMBER_OF_TOMATOES': retreat.get_number_of_tomatoes(),
        'LINK_TO_BE_PREPARED': settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION'][
            'LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT'],
        'LINK_TO_USER_PROFILE': settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION']['PROFILE_URL'],
    }

    response_send_mail = send_templated_email(
        [user],
        context,
        'REMINDER_VIRTUAL_RETREAT'
    )
    return response_send_mail


def send_physical_retreat_reminder_email(user, retreat):
    """
    This function sends an email to notify a user that a physical retreat in
    which he has bought a seat is starting soon.
    """

    start_time = retreat.start_time
    start_time = start_time.astimezone(pytz.timezone('US/Eastern'))

    end_time = retreat.end_time
    end_time = end_time.astimezone(pytz.timezone('US/Eastern'))
    context = {
        'USER_FIRST_NAME': user.first_name,
        'USER_LAST_NAME': user.last_name,
        'USER_EMAIL': user.email,
        'RETREAT_NAME': retreat.name_fr,
        'RETREAT_PLACE': retreat.place_name,
        'RETREAT_NUMBER_OF_TOMATOES': retreat.get_number_of_tomatoes(),
        'RETREAT_START_TIME': start_time.strftime('%Y-%m-%d %H:%M'),
        'RETREAT_END_TIME': end_time.strftime('%Y-%m-%d %H:%M'),
    }

    response_send_mail = send_templated_email(
        [user],
        context,
        'REMINDER_PHYSICAL_RETREAT'
    )

    return response_send_mail


def send_post_retreat_email(user, retreat):
    """
    This function sends an email to get back to a user after a retreat has
    ended.
    :param user: The user on the reservation
    :param retreat: The ended retreat
    :return:
    """
    if retreat.type.name_fr == 'Virtuelle':
        return send_post_virtual_retreat_email(user, retreat)
    else:
        return send_post_physical_retreat_email(user, retreat)


def send_post_physical_retreat_email(user, retreat):
    """
    This function sends an email to get back to a user after a
    physical retreat has ended.
    """

    start_time = retreat.start_time
    start_time = start_time.astimezone(pytz.timezone('US/Eastern'))

    end_time = retreat.end_time
    end_time = end_time.astimezone(pytz.timezone('US/Eastern'))
    context = {
        'USER_FIRST_NAME': user.first_name,
        'USER_LAST_NAME': user.last_name,
        'USER_EMAIL': user.email,
        'RETREAT_NAME': retreat.name_fr,
        'RETREAT_PLACE': retreat.place_name,
        'RETREAT_NUMBER_OF_TOMATOES': retreat.get_number_of_tomatoes(),
        'RETREAT_START_TIME': start_time.strftime('%Y-%m-%d %H:%M'),
        'RETREAT_END_TIME': end_time.strftime('%Y-%m-%d %H:%M'),
    }

    response_send_mail = send_templated_email(
        [user],
        context,
        'THROWBACK_PHYSICAL_RETREAT'
    )

    return response_send_mail


def send_post_virtual_retreat_email(user, retreat):
    """
    This function sends an email to get back to a user after a
    virtual retreat has ended.
    """

    start_time = retreat.start_time
    start_time = start_time.astimezone(pytz.timezone('US/Eastern'))

    end_time = retreat.end_time
    end_time = end_time.astimezone(pytz.timezone('US/Eastern'))
    context = {
        'USER_FIRST_NAME': user.first_name,
        'USER_LAST_NAME': user.last_name,
        'USER_EMAIL': user.email,
        'RETREAT_NAME': retreat.name_fr,
        'RETREAT_NUMBER_OF_TOMATOES': retreat.get_number_of_tomatoes(),
        'RETREAT_START_DATE': format_date(
            start_time,
            format='long',
            locale='fr'
        ),
        'RETREAT_START_TIME': start_time.strftime('%-Hh%M'),
        'RETREAT_END_DATE': format_date(
            end_time,
            format='long',
            locale='fr'
        ),
        'RETREAT_END_TIME': end_time.strftime('%-Hh%M'),
        'LINK_TO_REVIEW_FORM': retreat.review_url,
        'LINK_TO_BE_PREPARED': settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION'][
            'LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT'],
        'LINK_TO_USER_PROFILE': settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION']['PROFILE_URL'],
    }

    response_send_mail = send_templated_email(
        [user],
        context,
        'THROWBACK_VIRTUAL_RETREAT'
    )

    return response_send_mail


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


def send_automatic_email(user, retreat, email):
    """
    This function sends an automatic email to notify a user that has an
    active reservation on a retreat.
    """

    start_time = retreat.start_time
    start_time = start_time.astimezone(pytz.timezone('US/Eastern'))

    end_time = retreat.end_time
    end_time = end_time.astimezone(pytz.timezone('US/Eastern'))

    context = {
        'CUSTOM': json.loads(email.context),
        'USER_FIRST_NAME': user.first_name,
        'USER_LAST_NAME': user.last_name,
        'USER_EMAIL': user.email,
        'RETREAT_NAME': retreat.name_fr,
        'RETREAT_START_DATE': format_date(
            start_time,
            format='long',
            locale='fr'
        ),
        'RETREAT_START_TIME': start_time.strftime('%-Hh%M'),
        'RETREAT_END_DATE': format_date(
            end_time,
            format='long',
            locale='fr'
        ),
        'RETREAT_END_TIME': end_time.strftime('%-Hh%M'),
        'RETREAT_NUMBER_OF_TOMATOES': retreat.get_number_of_tomatoes(),
        'LINK_TO_BE_PREPARED': settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION'][
            'LINK_TO_BE_PREPARED_FOR_VIRTUAL_RETREAT'],
        'LINK_TO_USER_PROFILE': settings.LOCAL_SETTINGS[
            'FRONTEND_INTEGRATION']['PROFILE_URL'],
    }

    response_send_mail = send_email_from_template_id(
        [user],
        context,
        email.template_id
    )
    return response_send_mail


def send_updated_retreat_email(retreat, users_emails, reason, reason_message):
    """
    This function sends an automatic email to notify all registered users
    of a retreat that it has been updated. For example dates have changed or
    retreat is deleted
    """
    reason_template = {
        'deletion': 'RETREAT_DELETED',
        'update': 'RETREAT_UPDATED',
    }

    context = {
        'RETREAT_NAME': retreat.name_fr,
        'MESSAGE': reason_message,
    }

    response_send_mail = send_templated_email(
        users_emails,
        context,
        reason_template[reason]
    )
    return response_send_mail
