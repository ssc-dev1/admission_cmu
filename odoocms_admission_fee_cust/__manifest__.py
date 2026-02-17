{
    'name': 'CUST Admission Fee Extension',
    'version': '0.1',
    'category': 'Extra Tools',
    'sequence': 11,
    'license': 'AGPL-3',
    'author': 'AARSOL Pvt. Ltd.',
    'website': 'http://www.aarsol.com',
    'summary': """ CUST Admission Fee Extension""",
    'description': """This Module Adds Additional Features in Fee""",
    'demo_xml': [],
    'update_xml': [],
    'depends': ['base',
                'mail',
                'odoocms_base',
                'odoocms_fee',
                'odoocms_fee_ext',
                'odoocms_admission',
                'odoocms_admission_ucp',
                'odoocms_admission_fee_ucp',
                ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'menus/menu.xml',
        'data/data.xml',
        'data/sequence.xml',

        # Views

        # ***** Reports *****#
        # 'reports/cust_admission_invoice_report.xml',
    ],
    'images': ['static/description/main.gif'],
    'js': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
