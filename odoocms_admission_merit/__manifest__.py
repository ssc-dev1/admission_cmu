# -*- coding: utf-8 -*-
{
    'name': "OdooCMS Admission Merit",
    'version': '15.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 3,
    'summary': "Admission Module of Educational""",
    'author': 'Sulman Shaukat',
    'company': 'AARSOL',
    'website': "http://www.aarsol.com/",
    'depends': ['odoocms_admission'],
    'data': [
        # 'security/odoocms_admission_security.xml',
        'security/company_rules.xml',
        'security/ir.model.access.csv',

        'views/odoocms_merit_registers_view.xml',
        'views/odoocms_merit_registers_line.xml',
        'views/invoice_list.xml',
        'views/offer_letter.xml',
        'reports/offer_letter.xml',

        'wizard/generate_invoice.xml',
    ],
    'demo': [
        # 'demo/admission_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
