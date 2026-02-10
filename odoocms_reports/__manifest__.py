{
    'name': 'odoocms_reports',
    'version': '1.1.5',
    'summary': 'odoocms reports',
    'description': 'this directory will contains the code for CMS reports',
    'category': '',
    'author': 'Abubakar',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['base','web','website','odoocms_base', 'odoocms','send_sms'],
    'data': [
        'security/report_users.xml',
        'views/sms_report_menu.xml'

    ],
    'assets': {
        'web.assets_frontend': [
            '/odoocms_reports/static/src/js/sms_report.js',
            '/odoocms_reports/static/src/js/social_media_tracking.js',
            '/odoocms_reports/static/src/css/social_media_tracking.css',
            '/odoocms_reports/static/src/js/admission_comparison_report.js'
            ],
        'web.assets_backend': [
            '/odoocms_reports/static/src/js/sms_report.js',
            '/odoocms_reports/static/src/js/social_media_tracking.js',
            '/odoocms_reports/static/src/js/admission_comparison_report.js',
             '/odoocms_reports/static/src/css/social_media_tracking.css'
        ],
        'web.assets_qweb': [
            '/odoocms_reports/static/xml/sms_report_templates.xml',
            '/odoocms_reports/static/xml/social_media_tracking.xml',
            '/odoocms_reports/static/xml/admission_comparison_report.xml',
             '/odoocms_reports/static/src/css/social_media_tracking.css'
        ]
    },
    'demo': [],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    },
    'installable': True,
    'auto_install': False,
    'application': True
}