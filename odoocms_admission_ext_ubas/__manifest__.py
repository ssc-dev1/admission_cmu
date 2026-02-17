# -*- encoding: utf-8 -*-
{
    'name': 'OdooCMS admission Extension UBAS',
    'version': '1.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 3,
    'summary': 'Admission Management Extension for UBAS ',
    'author': 'AARSOL',
    'company': 'AARSOL',
    'website': 'http://www.aarsol.com/',
    'depends': ['base' ,'odoocms_base', 'odoocms_admission','odoocms_admission_ucp' ,'odoocms_merit_ucp'],
    'data': [
        'views/backend/odoocms_application_ext.xml',
        'data/company_rules.xml',

        'views/portal/account_registration_ubas.xml',
        'views/portal/account_registration_maju.xml',
        'views/portal/account_registration_cust.xml',
        'views/portal/thankyou.xml',
        'views/portal/dashboard_ucp.xml',

    ],
    'application': True,
}
