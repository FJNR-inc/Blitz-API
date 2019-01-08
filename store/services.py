import json
import random
import requests
import uuid

from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .exceptions import PaymentAPIError

PAYSAFE_EXCEPTION = {
    '3004': "{0}{1}".format(
        _("An error occured while adding the card: "),
        _("the zip/postal code must be provided for an AVS check request.")
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
        print(json.loads(err.response.content))
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

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
        print(json.loads(err.response.content))
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

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
        print(json.loads(err.response.content))
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

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
        print(json.loads(err.response.content))
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

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
        print(json.loads(err.response.content))
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

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
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

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
        print(json.loads(err.response.content))
        err_code = json.loads(err.response.content)['error']['code']
        if err_code in PAYSAFE_EXCEPTION:
            raise PaymentAPIError(PAYSAFE_EXCEPTION[err_code])
        raise PaymentAPIError(PAYSAFE_EXCEPTION['unknown'])

    return r
