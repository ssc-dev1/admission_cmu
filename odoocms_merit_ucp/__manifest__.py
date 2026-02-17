# -*- coding: utf-8 -*-
{
    'name': "OdooCMS Merit UCP",
    'version': '15.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 3,
    'summary': "Admission Module of Educational""",
    'author': 'Sulman &amp; Bilal',
    'company': 'AARSOL',
    'website': "http://www.aarsol.com/",
    'depends': ['mail', 'odoocms_admission', 'odoocms', 'odoocms_admission_ucp'],
    'data': [
        # 'security/odoocms_admission_security.xml',
        'security/ir.model.access.csv',
        'data/offer_letter.xml',
        'data/mail_template.xml',

        'views/odoocms_merit_registers_view.xml',
        'views/odoocms_merit_registers_line.xml',
        'views/application_transfer_register.xml',
        'views/odoocms_application.xml',
        'views/offer_letter_inherit.xml',
        # 'views/invoice_list.xml',

        'reports/merit_register_report.xml',
        
    ],
    'demo': [
        # 'demo/admission_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
