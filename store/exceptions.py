class PaymentAPIError(Exception):
    """
    Raised when a payment related action fails.
    """
    def __init__(self, error, detail):

        super(PaymentAPIError, self).__init__(error)
        self.detail = detail
