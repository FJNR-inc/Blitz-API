from decimal import Decimal
import json
import random
import requests
import uuid

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from log_management.models import Log
from .exceptions import PaymentAPIError
from .models import CouponUser


###############################################################################
#                         PAYSAFE RELATED SERVICES                            #
###############################################################################


PAYSAFE_EXCEPTION = {
    '3004': "{0}{1}".format(
        _("An error occured while adding the card: "),
        _("the zip/postal code must be provided for an AVS check request.")
    ),
    '3006': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("You submitted an expired credit card number with your request.")
    ),
    '3008': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("card type not supported.")
    ),
    '3009': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("the request has been declined by the issuing bank.")
    ),
    '3022': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("the card has been declined due to insufficient funds.")
    ),
    '3029': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("The external processing gateway has rejected the transaction.")
    ),
    '3404': "{0}{1}".format(
        _("An error occured while processing the refund: "),
        _("The settlement has already been fully refunded.")
    ),
    '3406': "{0}{1}".format(
        _("An error occured while processing the refund: "),
        _("The settlement you are attempting to refund has not been batched "
          "yet. There are no settled funds available to refund.")
    ),
    '5031': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("the transaction has already been processed.")
    ),
    '5068': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("invalid payment or single-use token.")
    ),
    '5269': _("Not found."),
    '5270': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("permission denied.")
    ),
    '5500': "{0}{1}".format(
        _("An error occured while processing the payment: "),
        _("invalid payment token or payment profile/card inactive.")
    ),
    '7503': "{0}{1}".format(
        _("An error occured while adding the card: "),
        _("a card with that number already exists.")
    ),
    '7505': "{0}{1}".format(
        _("An error occured while adding the card: "),
        _("the payment profile for this user already exists.")
    ),
    'unknown': _("The request could not be processed.")
}

PAYSAFE_CARD_TYPE = {
    'AM': "American Express",
    'DC': "Discover",
    'JC': "JCB",
    'MC': "Mastercard",
    'MD': "Maestro",
    'SO': "Solo",
    'VI': "Visa",
    'VD': "Visa Debit",
    'VE': "Visa Electron",
    'NONE': None,
}


def manage_paysafe_error(err, additional_data):
    try:
        err_code = json.loads(err.response.content)['error']['code']

        Log.error(
            source='PAYSAFE',
            error_code=err_code,
            message=err,
            additional_data=json.dumps(additional_data)
        )

        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
    except json.decoder.JSONDecodeError as err:
        print(err.response)

    Log.error(
        source='PAYSAFE',
        error_code='unknown',
        message=err,
        additional_data=json.dumps(additional_data)
    )
    raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])


def charge_payment(amount, payment_token, reference_number):
    """
    This method is used to charge an amount to a card represented by the
    payment token.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    order:              Django Order model instance
    payment_profile:    Django PaymentProfile model instance
    """
    auth_url = '{0}{1}{2}{3}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['CARD_URL'],
        "accounts/" + settings.PAYSAFE['ACCOUNT_NUMBER'],
        "/auths/",
    )

    data = {
        "merchantRefNum": "charge-" + str(uuid.uuid4()),
        "amount": amount,
        "settleWithAuth": True,
        "card": {
            "paymentToken": payment_token,
        }
    }

    try:
        r = requests.post(
            auth_url,
            auth=(
                settings.PAYSAFE['USER'],
                settings.PAYSAFE['PASSWORD'],
            ),
            json=data,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
                    'amount': amount,
                    'payment_token': payment_token,
                    'reference_number': reference_number
                })
    return r


def refund_amount(settlement_id, amount):
    """
    This method is used to refund an amount to the same card that was used for
    buying the products contained in the order.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    settlement_id: ID for the Paysafe settlement
    amount:        Positive number representing the amount to be refunded back
    """
    refund_url = '{0}{1}{2}{3}{4}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['CARD_URL'],
        "accounts/" + settings.PAYSAFE['ACCOUNT_NUMBER'],
        "/settlements/" + settlement_id,
        "/refunds"
    )

    data = {
        "merchantRefNum": "refund-" + str(uuid.uuid4()),
        "amount": amount,
    }

    try:
        r = requests.post(
            refund_url,
            auth=(
                settings.PAYSAFE['USER'],
                settings.PAYSAFE['PASSWORD'],
            ),
            json=data,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
            'settlement_id': settlement_id,
            'amount': amount,
        })

    return r


def create_external_payment_profile(user):
    """
    This method is used to create a payment profile in external payment API.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    user:           Django User model instance
    """
    create_profile_url = '{0}{1}{2}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['VAULT_URL'],
        "profiles/",
    )

    data = {
        "merchantCustomerId": str(uuid.uuid4()),
        "locale": "en_US",
        "firstName": user.first_name,
        "lastName": user.last_name,
        "email": user.email,
        "phone": user.phone,
    }

    try:
        r = requests.post(
            create_profile_url,
            auth=(
                settings.PAYSAFE['USER'],
                settings.PAYSAFE['PASSWORD']
            ),
            json=data,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
            'data': data,
        })

    return r


def get_external_payment_profile(profile_id):
    """
    This method is used to get a payment profile from an external payment API.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    profile_id:   External profile ID
    """
    get_profile_url = '{0}{1}{2}{3}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['VAULT_URL'],
        "profiles/" + profile_id,
        "?fields=cards",
    )

    try:
        r = requests.get(
            get_profile_url,
            auth=(settings.PAYSAFE['USER'], settings.PAYSAFE['PASSWORD']),
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
            'profile_id': profile_id,
        })

    return r


def update_external_card(profile_id, card_id, single_use_token):
    """
    This method is used to update cards.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    profile_id:         External profile ID
    card_id:            External card ID
    single_use_token:   Single use token representing the card instance
    """
    put_cards_url = '{0}{1}{2}{3}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['VAULT_URL'],
        "profiles/" + profile_id,
        "/cards/" + card_id,
    )

    data = {
        "singleUseToken": single_use_token
    }

    try:
        r = requests.put(
            put_cards_url,
            auth=(settings.PAYSAFE['USER'], settings.PAYSAFE['PASSWORD']),
            json=data,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
            'profile_id': profile_id,
            'card_id': card_id,
            'single_use_token': single_use_token,
        })

    return r


def create_external_card(profile_id, single_use_token):
    """
    This method is used to add cards to a profile.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    profile_id:         External profile ID
    single_use_token:   Single use token representing the card instance
    """
    post_cards_url = '{0}{1}{2}{3}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['VAULT_URL'],
        "profiles/" + profile_id,
        "/cards/",
    )

    data = {
        "singleUseToken": single_use_token
    }

    try:
        r = requests.post(
            post_cards_url,
            auth=(settings.PAYSAFE['USER'], settings.PAYSAFE['PASSWORD']),
            json=data,
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        err = json.loads(err.response.content)
        err_code = err['error']['code']
        if err_code == "7503":
            try:
                r = get_external_card(
                    err['links'][0]['href'].split("/")[-1]
                )
                card_data = json.loads(r.content)
                delete_external_card(profile_id, card_data['id'])
                r = requests.post(
                    post_cards_url,
                    auth=(
                        settings.PAYSAFE['USER'],
                        settings.PAYSAFE['PASSWORD']
                    ),
                    json=data,
                )
                r.raise_for_status()
                return r
            except requests.exceptions.HTTPError as err:
                if err_code in PAYSAFE_EXCEPTION:
                    raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
                raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

    return r


def get_external_cards(profile_id):
    """
    This method is used to get cards of a payment profile from an external
    payment API.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    profile_id:   External profile ID
    """
    profile = get_external_payment_profile(profile_id).json()

    cards = list()

    for idx, card in enumerate(profile['cards']):
        cards.insert(idx, dict())
        cards[idx]['id'] = card.get('id')
        cards[idx]['card_bin'] = card.get('cardBin')
        cards[idx]['card_expiry'] = card.get('cardExpiry')
        cards[idx]['card_type'] = card.get('cardType')
        cards[idx]['holder_name'] = card.get('holderName')
        cards[idx]['last_digits'] = card.get('lastDigits')
        cards[idx]['payment_token'] = card.get('paymentToken')
        cards[idx]['status'] = card.get('status')

    return cards


def get_external_card(card_id):
    """
    This method is used to get an existing card of a payment profile from an
    external payment API.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    card_id:   External card ID
    """
    get_card_url = '{0}{1}{2}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['VAULT_URL'],
        "cards/" + card_id,
    )

    try:
        r = requests.get(
            get_card_url,
            auth=(settings.PAYSAFE['USER'], settings.PAYSAFE['PASSWORD']),
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
            'card_id': card_id
        })

    return r


def delete_external_card(profile_id, card_id):
    """
    This method is used to delete an existing card of a payment profile from an
    external payment API.
    This is tigthly coupled with Paysafe for now, but this should be made
    generic in the future to ease migrations to another payment patform.

    card_id:   External card ID
    """
    delete_card_url = '{0}{1}{2}{3}'.format(
        settings.PAYSAFE['BASE_URL'],
        settings.PAYSAFE['VAULT_URL'],
        "profiles/" + profile_id,
        "/cards/" + card_id,
    )

    try:
        r = requests.delete(
            delete_card_url,
            auth=(settings.PAYSAFE['USER'], settings.PAYSAFE['PASSWORD']),
        )
        r.raise_for_status()
    except requests.exceptions.HTTPError as err:
        manage_paysafe_error(err, {
            'profile_id': profile_id,
            'card_id': card_id
        })

    return r


###############################################################################
#                               OTHER SERVICES                                #
###############################################################################


def validate_coupon_for_order(coupon, order):
    """
    coupon: Coupon model instance
    order: Order model instance

    THIS DOES NOT RECORD COUPON USE. Linked CouponUser instance needs to be
    updated outside of this function!

    Returns a dict containing informations concerning the coupon use.
    """
    now = timezone.now()
    user = order.user
    coupon_info = {
        'valid_use': False,
        'error': None,
        'value': None,
        'orderline': None,
    }

    # Check if the ocupon is active
    if (coupon.start_time > now or coupon.end_time < now):
        coupon_info['error'] = {
            'non_field_errors': [_(
                "This coupon is only valid between {0} and {1}."
                .format(
                    coupon.start_time.date(),
                    coupon.end_time.date()
                )
            )]
        }
        return coupon_info

    # Check if the user's profile is complete
    if not (user.academic_program_code and
            user.faculty and user.student_number):
        coupon_info['error'] = {
            'non_field_errors': [_(
                "Incomplete user profile. 'academic_program_code',"
                " 'faculty' and 'student_number' fields must be "
                "filled in the user profile to use a coupon."
            )]
        }
        return coupon_info

    # Check if the maximum number of use for this coupon is exceeded
    coupon_user, created = CouponUser.objects.get_or_create(
        coupon=coupon,
        user=user,
        defaults={'uses': 0},
    )
    total_coupon_uses = CouponUser.objects.filter(coupon=coupon)
    total_coupon_uses = sum(
        total_coupon_uses.values_list('uses', flat=True)
    )
    valid_use = coupon_user.uses < coupon.max_use_per_user
    valid_use = valid_use or not coupon.max_use_per_user
    valid_use = valid_use and (total_coupon_uses < coupon.max_use
                               or not coupon.max_use)
    if not valid_use:
        coupon_info['error'] = {
            'non_field_errors': [_(
                "Maximum number of uses exceeded for this coupon."
            )]
        }
        return coupon_info

    # Check if the coupon can be applied to a product in the order
    applicable_orderlines = order.order_lines.filter(
        Q(content_type__in=coupon.applicable_product_types.all())
        | Q(content_type__model='package',
            object_id__in=coupon.applicable_packages.all().
            values_list('id', flat=True))
        | Q(content_type__model='timeslot',
            object_id__in=coupon.applicable_timeslots.all().
            values_list('id', flat=True))
        | Q(content_type__model='membership',
            object_id__in=coupon.applicable_memberships.all().
            values_list('id', flat=True))
        | Q(content_type__model='retreat',
            object_id__in=coupon.applicable_retreats.all().
            values_list('id', flat=True))
    )
    if not applicable_orderlines:
        coupon_info['error'] = {
            'non_field_errors': [_(
                "This coupon does not apply to any product."
            )]
        }
        return coupon_info

    # The coupon is valid and can be used.
    # We find the product to which it applies.
    # We calculate the official amount to be discounted.
    coupon_info['valid_use'] = True
    most_exp_product = applicable_orderlines[0].content_object
    coupon_info['orderline'] = applicable_orderlines[0]
    for orderline in applicable_orderlines:
        product = orderline.content_object
        if product.price > most_exp_product.price:
            most_exp_product = product
            coupon_info['orderline'] = orderline
    if not coupon.value:
        percent_off = Decimal(coupon.percent_off) / 100
        discount_amount = most_exp_product.price * percent_off
    else:
        discount_amount = min(
            coupon.value,
            most_exp_product.price
        )
    coupon_info['value'] = discount_amount

    return coupon_info


def notify_for_coupon(email, coupon):
    """
    This function sends an email to notify a user that he has access to a
    coupon code for his next purchase.
    """

    merge_data = {'COUPON': coupon}

    plain_msg = render_to_string("coupon_code.txt", merge_data)
    msg_html = render_to_string("coupon_code.html", merge_data)

    try:
        return send_mail(
            "Coupon rabais",
            plain_msg,
            settings.DEFAULT_FROM_EMAIL,
            [email],
            html_message=msg_html,
        )
    except Exception as err:
        additional_data = {
            'title': "Coupon rabais",
            'default_from': settings.DEFAULT_FROM_EMAIL,
            'user_email': email,
            'merge_data': merge_data,
            'template': 'coupon_code'
        }
        Log.error(
            source='SENDING_BLUE_TEMPLATE',
            message=err,
            additional_data=json.dumps(additional_data)
        )
        raise
