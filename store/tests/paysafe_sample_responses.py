"""
This file contains samples of the Paysafe API response.

August 21th 2018
"""


SAMPLE_PROFILE_RESPONSE = {
    "id": "123",
    "status": "ACTIVE",
    "merchantCustomerId": "mycustomer1",
    "locale": "en_US",
    "firstName": "John",
    "middleName": "James",
    "lastName": "Smith",
    "dateOfBirth": {
        "year": 1981,
        "month": 10,
        "day": 24
    },
    "ip": "192.0.126.111",
    "gender": "M",
    "nationality": "Canadian",
    "paymentToken": "P63dhGFvywNxhWd",
    "phone": "777-444-8888",
    "cellPhone": "777-555-8888",
    "email": "john.smith@email.com",
    "cards": [
        {
            "status": "ACTIVE",
            "id": "456",
            "cardBin": "453091",
            "lastDigits": "2345",
            "cardExpiry": {
                "year": 2019,
                "month": 12
            },
            "holderName": "John Smith",
            "nickName": "Personal Visa",
            "cardType": "VI",
            "paymentToken": "CIgbMO3P1j7HUiy",
            "defaultCardIndicator": True
        }
    ]
}

SAMPLE_PAYMENT_RESPONSE = {
    'links': [{
        'rel': 'settlement',
        'href': 'https://example.com/cardpayments/v1/accounts'
                '/0123456789/settlements/1'
    }, {
        'rel': 'self',
        'href': 'https://example.com/cardpayments/v1/accounts'
                '/0123456789/auths/1'
    }],
    'id': '1',
    'merchantRefNum': '751',
    'txnTime': '2018-08-20T14:50:11Z',
    'status': 'COMPLETED',
    'amount': 85000,
    'settleWithAuth': True,
    'preAuth': False,
    'availableToSettle': 0,
    'card': {
        'type': 'VI',
        'lastDigits': '1111',
        'cardExpiry': {
            'month': 2,
            'year': 2041
        }
    },
    'authCode': '338602',
    'profile': {
        'firstName': 'Heather',
        'lastName': 'Brewer',
        'email': 'john8@blitz.com'
    },
    'merchantDescriptor': {
        'dynamicDescriptor': 'NBX*DD Line 1',
        'phone': '000-111000099'
    },
    'visaAdditionalAuthData': {},
    'currencyCode': 'CAD',
    'avsResponse': 'NOT_PROCESSED',
    'cvvVerification': 'NOT_PROCESSED',
    'settlements': [{
        'links': [{
            'rel': 'self',
            'href': 'https://example.com/cardpayments/v1/'
                    'accounts/0123456789/settlements/1'
        }],
        'id': '1',
        'merchantRefNum': '751', 'txnTime': '2018-08-20T14:50:11Z',
        'status': 'PENDING',
        'amount': 85000,
        'availableToRefund': 85000
    }]
}

SAMPLE_CARD_RESPONSE = {
    "status": "ACTIVE",
    "id": "424d2472-4afd-44a3-a678-8f4611e864a5",
    "cardBin": "453091",
    "lastDigits": "2345",
    "cardExpiry": {
        "year": 2019,
        "month": 2
    },
    "cardType": "VI",
    "paymentToken": "CYQ3O0svO35unUI",
    "storedCredentialTokenStatus": "UNVERIFIED"
}

SAMPLE_INVALID_PAYMENT_TOKEN = {
    "id": "179c4cd9-65de-477b-aec9-00e6ef7da0b8",
    "error": {
        "code": "5500",
        "message": "Either the payment token is invalid or the corresponding "
                   "profile or credit card is not active."
    }
}

SAMPLE_INVALID_SINGLE_USE_TOKEN = {
    "error": {
        "code": "5068",
        "message": "Either you submitted a request that is missing a "
                   "mandatory field or the value of a field does not match "
                   "the format expected.",
        "fieldErrors": [
            {
                "field": "singleUseToken",
                "error": "The specified value does not exist in the system."
            }
        ]
    }
}

SAMPLE_CARD_ALREADY_EXISTS = {
    "error": {
        "code": "7503",
        "message": "Card number already in use - 456",
    },
    'links': [{
        'rel': 'existing_entity',
        'href': 'https://api.test.paysafe.com/customervault/v1/cards/456'
    }],
}

SAMPLE_CARD_REFUSED = {
    "error": {
        "code": "3009",
        "message": "Your request has been declined by the issuing bank.",
    },
}

UNKNOWN_EXCEPTION = {
    "error": {
        "code": "9999",
        "message": "Other unhandled exceptions.",
    },
}
