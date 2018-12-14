from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string


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
