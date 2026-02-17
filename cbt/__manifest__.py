# -*- coding: utf-8 -*-
{
    'name': "CBET",
    'summary': 'University Online Entry Test Application',
    'category': 'OdooCMS',
    'sequence': 4,
    'author': "NUST & AARSOL",
    'website': "https://www.aarsol.com",
    'version': '15.1',
    'depends': [
        'base',
        'website_partner',
        'website_mail',
        # 'website_form',
        'website',
        'base_setup',
        'auth_signup', 'hr'
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',

        # 'wizard/export_data_wizard.xml',

        # 'views/assests.xml',
        'views/views.xml',
        'views/templates.xml',
        'views/faculty_roles.xml',
        'views/ip_address.xml',
        'views/paper_criteria.xml',
        'views/paper_criteria_rules.xml',
        'views/paper_generation.xml',
        'views/papers.xml',
        'views/paper_conduct.xml',
        'views/review_questions.xml',
        'views/test_schedule.xml',
        'views/student_setup.xml',
        'views/student_paper.xml',
        # 'views/instructions.xml',
        'views/res_config_setting_inherit.xml',
        # 'wizard/cbt_api_wizard_views.xml',
        # 'wizard/import_data_wizard.xml',
        'report/paper.xml',
        'report/report.xml',
        # 'views/cbt_export.xml',
        # 'wizard/subject_result.xml',
    ],
'assets': {
'web.assets_qweb': [
        'cbt/static/src/xml/button.xml',
    ],

        'web.assets_backend': [
            'cbt/static/src/js/fetch_participant.js',

        ],


    },


    'application': True,


}
