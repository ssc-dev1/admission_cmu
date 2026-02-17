{
    'name': 'Fee Integration SQL Extension',
    'version': '0.1',
    'category': 'Extra Tools',
    'sequence': 10,
    'license': 'AGPL-3',
    'author': 'AARSOL Pvt. Ltd.',
    'website': 'http://www.aarsol.com',
    'summary': """ Fee Extension Including Connection with SQL""",
    'description': """This Module Allows You To Sync Insert And Update Fee Data With SQL.""",
    'demo_xml': [],
    'update_xml': [],
    'depends': ['base',
                'mail',
                'odoocms',
                'odoocms_base',
                'odoocms_academic',
                'odoocms_fee',
                'odoocms_fee_ext',
                ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'menus/menu.xml',
        'data/data.xml',
        'data/sequence.xml',

        # Views
        'views/department_view.xml',
        'views/institute_view.xml',
        'views/program_view.xml',
        'views/res_partner_bank_view.xml',
        'views/term_view.xml',
        'views/fee_odoo_sql_connector.xml',
        'views/odoocms_fee_sync_pool.xml',
        'views/odoocms_sync_challan_summary_view.xml',

        'reports/report.xml',
    ],
    'images': ['static/description/main.gif'],
    'js': [],
    'application': True,
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
# https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver15#ubuntu17
# https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server?view=sql-server-ver15
# apt-get update
# apt-get install unixodbc-dev
# pip install pyodbc
