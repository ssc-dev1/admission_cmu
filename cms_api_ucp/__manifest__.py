# -*- coding: utf-8 -*-
{
    'name': "CMS API",
    'version': '1.0',
    'category': 'Odoo CMS',
    'summary': "APIs for Integration",
    'description': "APIs for Integration",
    'author': "AARSOL",
    'website': "http://aarsol.com",

    'depends': ['base',
                'odoocms',
                'base_rest',
                'base_rest_auth_api_key'
                ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        'views/account_ext.xml',
        'views/log.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
