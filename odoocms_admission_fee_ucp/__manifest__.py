{
    'name': 'UCP Admission Fee Extension',
    'version': '0.1',
    'category': 'Extra Tools',
    'sequence': 10,
    'license': 'AGPL-3',
    'author': 'AARSOL Pvt. Ltd.',
    'website': 'http://www.aarsol.com',
    'summary': """ UCP Admission Fee Extension""",
    'description': """This Module Adds Additional Features in Fee""",
    'demo_xml': [],
    'update_xml': [],
    'depends': ['base',
                'mail',
                'hr',
                'odoocms_base',
                'odoocms_fee',
                'odoocms_fee_ext',
                'odoocms_admission',
                'odoocms_admission_ucp'
                ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'menus/menu.xml',
        'data/data.xml',
        'data/sequence.xml',

        # Views
        'views/ucp_odoocms_fee_receipt_view.xml',
        'views/odoocms_show_challan_on_portal_view.xml',
        'views/odoocms_fee_payment_register_view.xml',
        'views/odoocms_student_view.xml',
        'views/odoocms_program_batch_fee_view.xml',
        'views/odoocms_unconfirmed_paid_bank_challan_view.xml',
        'views/odoocms_application_view.xml',
        'views/res_users_view.xml',

        # Wizards
        'wizards/prospectus_challan_rep_wizard.xml',

        # ***** Reports *****#
        # 'reports/cust_admission_invoice_report.xml',
        'reports/prospectus_challan_report.xml',
        'reports/report.xml',
    ],
    'images': ['static/description/main.gif'],
    'js': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}
