from mailchimp3 import MailChimp
from mailchimp3.mailchimpclient import MailChimpError

from blitz_api import settings

LIST_ID = settings.MAILCHIMP_SUBSCRIBE_LIST_ID


def get_mail_chimp_client() -> MailChimp:
    return MailChimp(
        mc_api=settings.MAILCHIMP_API_KEY,
        enabled=settings.MAILCHIMP_ENABLED)


def add_to_list(
        email: str,
        first_name: str,
        last_name: str):
    client: MailChimp = get_mail_chimp_client()
    return client.lists.members.create(
        LIST_ID,
        {
            'email_address': email,
            'status': 'subscribed',
            'merge_fields': {
                'FNAME': first_name,
                'LNAME': last_name,
            }
        }
    )


def get_member(
    email: str
):
    client: MailChimp = get_mail_chimp_client()
    return client.lists.members.get(
            list_id=LIST_ID,
            subscriber_hash=email,
        )


def is_email_on_list(
    email: str
) -> bool:

    try:
        member = get_member(email)
    except MailChimpError:
        return False
    return True if member else False
