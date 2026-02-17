{
    'name': 'UCP Fee Extension',
    'version': '0.1',
    'category': 'Extra Tools',
    'sequence': 10,
    'license': 'OPL-1',
    'author': 'AARSOL Pvt. Ltd.',
    'website': 'http://www.aarsol.com',
    'summary': """ UCP Fee Extension Including Connection with SQL""",
    'description': """This Module Allows You To Sync Insert And Update Fee Data With SQL.""",
    'demo_xml': [],
    'update_xml': [],
    'depends': ['base',
                'mail',
                'odoocms_base',
                'odoocms_fee',
                'odoocms_fee_ext',
                'odoocms_attendance',
                ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'menus/menu.xml',
        'data/data.xml',
        'data/sequence.xml',

        # Views
        'views/fee_odoo_sql_connector.xml',
        'views/department_view.xml',
        'views/program_view.xml',
        'views/institute_view.xml',
        'views/term_view.xml',
        'views/res_partner_bank_view.xml',
        'views/odoocms_fee_sync_pool.xml',
        'views/ucp_odoocms_fee_receipt_view.xml',

        'views/odoocms_fee_payment_register_view.xml',
        'views/odoocms_student_view.xml',

        'views/odoocms_program_batch_fee_view.xml',

        'views/odoocms_sync_challan_summary_view.xml',
        'views/odoocms_fee_unpaid_student_withdraw_view.xml',
        'views/odoocms_withdraw_student_unpaid_challans_view.xml',

        'wizards/generate_bulk_misc_challan_wiz_view.xml',
        'wizards/ucp_course_drop_wiz_view.xml',
        'wizards/fee_defaulter_rep_wiz_view.xml',
        # 'wizards/attendance_fine_wiz_view.xml',
        'wizards/odoocms_advance_to_main_registration_wiz_view.xml',
        'wizards/fee_data_import_view.xml',

        # Report Wizards
        'wizards/report_wiz/program_wise_fin_summary_wiz_view.xml',
        'wizards/report_wiz/receipt_received_summary_wiz_view.xml',
        'wizards/report_wiz/receipt_received_detail_wiz_view.xml',
        'wizards/report_wiz/student_fine_history_rep_wiz_view.xml',

        'reports/report.xml',

        'reports/fee_defaulter_report.xml',
        'reports/program_wise_fin_summary_report.xml',
        'reports/receipt_received_summary_report.xml',
        'reports/receipt_received_detail_report.xml',
        'reports/student_fine_history_report.xml',
        'reports/odoocms_fee_credit_hours_report.xml',
        'reports/odoocms_fee_discount_report.xml',
        'reports/odoocms_registration_status_report.xml',
        'reports/odoocms_bank_wise_payment_report.xml',
        'reports/odoocms_challan_status_report.xml',
        # 'reports/student_fee_letter_report.xml',

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
