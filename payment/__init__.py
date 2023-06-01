'''

OiOiOi, (LEVI)

in this app, we specifically checking for payment status/validating/creating/initiating payment

Mostly services will have 2 todo's from merchant's server side (our backend side)
    - Initiate the payment constraints => txnId
    o User on the frontend does payment
    - Validate the payment (different approaches)

Currently, we are supporting 3 payment methods
1. Gpay REF-(https://developers.google.com/pay/api/web/overview)
2. Paytm [check if user/ip from india] REF-(https://business.paytm.com/docs/jscheckout-integration-overview?ref=jsCheckoutdoc)
3. Paypal REF-(https://developer.paypal.com/docs/checkout/standard/integrate/)

Mostly we'll have 6 core low-level views
    3 for initiating payment (1 for each)
    3 for validating the payment (1 for each)

However there are also top-level views:
    - CONSTRAINT_CHECK (not implemented yet!)

NOTE: We are suppose to generate unique TransactionReferenceId for each transaction.

Paypal:
    ✅settings.PAYPAL_CONFIG
    o Realatively easy to setup REF-(https://developer.paypal.com/docs/checkout/standard/integrate/) just convert from .JS
    - auth token lasts for about (~8.5 hours)
    - CLIENT_ID: ASlAoLEU-UqcfUceKTXaJoSN7RNr3uQEEXbUl-EveheEAsfsZvuS9cYZw969PzgM9jgT1U9G9SxRyFns
    - SEC_KI: EGRFIICOA9cmV8F2yzIVsXtCLMVLGUPZlGi1uPgQqMTPewWfdcLHlIWi-WVAuWfeCaSph60Xu4BLG6yD

Gpay/Paytm (Only for indian request/ips):
    - REF-(https://developers.google.com/pay/india/api/web/create-payment-method)
    https://developers.google.com/pay/india/api/web/pay-ui
    For a response without a signature, we recommend that you treat this as a payment failure. Response without a signature might happen. One of the possible reasons is when user doesn't have the internet connectivity while making payment for the selected goods.

'''