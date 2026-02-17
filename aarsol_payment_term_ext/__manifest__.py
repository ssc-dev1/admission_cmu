{
    "name": "Payment Term Extension",
    "version": "15.0.1.0.1",
    "category": "Accounting & Finance",
    "summary": "Adds rounding, months, weeks and multiple payment days properties on payment term lines",
    "author": "AARSOL",
    "website": "https://www.aarsol.com",
    "license": "AGPL-3",
    "depends": ["account", "purchase"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_payment_term.xml"
    ],
    # "demo": ["demo/account_demo.xml"],
    "installable": True,
}

# https://github.com/OCA/account-payment
