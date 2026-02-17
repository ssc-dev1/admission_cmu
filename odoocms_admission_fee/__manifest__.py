# -*- coding: utf-8 -*-
{
    'name': "OdooCMS Admission Fee",
    'version': '15.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 3,
    'summary': "Admission Fee Module of Education""",
    'author': 'AARSOL',
    'company': 'AARSOL',
    'website': "http://www.aarsol.com/",
    'depends': ['odoocms_base',
                'mail',
                'odoocms',
                'odoocms_admission',
                'odoocms_fee', 'odoocms_merit_ucp'
                ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        'menus/menu.xml',

        'views/odoocms_fee_admission_receipt.xml',
        'views/odoocms_application_view.xml',
        'views/invoice_list.xml',
        'views/generate_invoice.xml',
        'views/receipt.xml',

        'wizards/allocate_slot.xml',
        'wizards/selected_candidate_challan_rep_wiz.xml',

        'reports/selected_candidate_challan_report.xml',
        'views/odoocms_application_single_challan_view.xml',
        'reports/report.xml',

    ],
    'demo': [
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
