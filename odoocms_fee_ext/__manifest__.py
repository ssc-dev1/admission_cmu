{
    "name": "OdooCMS Fee Extension",
    'version': '14.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 3,
    'summary': "Fee Management Module Extension of OdooCMS""",
    'author': 'AARSOL',
    'company': 'AARSOL',
    'website': "http://www.aarsol.com/",
    'depends': ['odoocms_fee'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'menus/menu.xml',
        'reports/report.xml',

        # Views
        'views/actions_inherits.xml',
        'views/odoocms_program_batch_view.xml',
        'views/odoocms_student_faculty_wise_challan_view.xml',
        'views/odoocms_fee_waiver_ext.xml',
        'views/odoocms_program_term_scholarship_view.xml',

        # SARFRAZ@02032023
        # 'views/odoocms_application_view.xml',

        'views/odoocms_student_view.xml',
        'views/odoocms_student_scholarship_eligibility_view.xml',
        'views/odoocms_student_applied_scholarships_view.xml',
        'views/odoocms_scholarship_continue_policy_view.xml',
        'views/odoocms_scholarship_continue_policy_detail_view.xml',
        'views/odoocms_scholarship_block_view.xml',
        'views/odoocms_student_special_scholarship_view.xml',
        'views/odoocms_fee_defaulter_student_view.xml',
        'views/odoocms_challan_fine_policy_view.xml',
        'views/odoocms_fee_payment_register_view.xml',

        'views/inputs/odoocms_fee_additional_charges_view.xml',
        'views/inputs/odoocms_input_other_fine_view.xml',
        'views/inputs/attendance_fine_view.xml',
        'views/inputs/odoocms_overdraft_view.xml',
        'views/inputs/student_fine_discount_view.xml',
        'views/odoocms_student_finance_clearance_view.xml',
        'views/odoocms_adddrop_policy_view.xml',
        'views/odoocms_show_challan_on_portal_view.xml',

        # Wizards
        'wizards/odoocms_program_term_scholarship_copy_view.xml',
        'wizards/odoocms_scholarship_policy_copy_wiz_view.xml',
        'wizards/student_scholarship_eligibility_add_remove_wiz_view.xml',
        'wizards/fee_data_import_view.xml',


        # New Wiz
        'wizards/new_wiz/fee_challan_print_wiz_view.xml',
        'wizards/new_wiz/show_student_fee_challans_wiz_view.xml',
        'wizards/new_wiz/fee_challan_merge_wiz_view.xml',
        'wizards/new_wiz/fee_scholarship_adjustment_wiz_view.xml',

        # input Wiz
        'wizards/input_wiz/bulk_student_additional_charges_wizard.xml',
        'wizards/input_wiz/other_fine_import_wizard_view.xml',
        'wizards/input_wiz/ad_hoc_charges_import_wizard_view.xml',

        'views/odoocms_fee_receipt_view.xml',

        # Reports
        'reports/report_challan.xml',
        'reports/misc_challan_report.xml',
        'reports/admission_invoice_report.xml',
        'reports/odoocms_fee_defaulter_student_report.xml',

    ],
    'application': True,
}
