# -*- encoding: utf-8 -*-
{
    'name': 'Application Portal',
    'summary': 'OdooCms Application Portal For Admission.',
    'category': 'OdooCMS',
    'version': '15.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 4,
    'author': 'AARSOL',
    'company': 'AARSOL',
    'website': 'http://www.aarsol.com/',
    'depends': ['odoocms_admission', 'website', 'odoocms_fee_ext'],
    'data': [
        'security/company_rules.xml',
        'security/ir.model.access.csv',

        'data/sequence.xml',
        'views//backend/res_config_settings_views.xml',
        'views/backend/odoocms_application_main_step_view.xml',
        # 'views/backend/web_widget_colorpicker_view.xml',

        'views/portal/component/header.xml',
        'views/portal/component/carousel.xml',
        'views/portal/component/progress.xml',
        'views/backend/odoocms_application_view.xml',
        'views/portal/submission_message.xml',
        'views/portal/admission_application.xml',
        'views/portal/steps/personal_details.xml',
        'views/portal/steps/preferences.xml',
        'views/portal/steps/final_confirmation.xml',
        'views/portal/steps/testing_center.xml',
        'views/portal/steps/fee_voucher.xml',
        'views/portal/steps/fee_voucher_ucp.xml',
        'views/portal/steps/documents_upload.xml',
        'views/portal/steps/contact_details.xml',
        'views/portal/steps/guardian_details.xml',
        'views/portal/steps/scholarship.xml',
        'views/portal/steps/merit.xml',
        'views/portal/steps/program_transfer.xml',
        'views/portal/steps/education_details.xml',
        'views/portal/account_registration.xml',
        'views/portal/account_registration_ucp.xml',
        'views/portal/all_merit.xml',
        'views/portal/dashboard.xml',
        'views/portal/dashboard_ucp.xml',
        'views/portal/thankyou.xml',
        'views/backend/test_center.xml',
        'views/backend/odoocms_program_register.xml',
        
        # 'reports/report_admission_invoice.xml',
        'reports/admit_card.xml',

    ],
    'assets': {

        'web.assets_qweb': [
            'odoocms_admission_portal/static/xml/widget.xml',

        ],
        'web.assets_backend': [
            'odoocms_admission_portal/static/css/widget.css',
            'odoocms_admission_portal/static/bootstrap/css/bootstrap-colorpicker.min.css',
            'odoocms_admission_portal/static/js/widget.js',
            'odoocms_admission_portal/static/bootstrap/js/bootstrap-colorpicker.min.js',
        ],



    },



    'installable': True,
    'auto_install': False,
    'application': True,
}
