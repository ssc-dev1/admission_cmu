{
    'name': "Send SMS",
    'version': '0.1',
    'author': "Debasish Dash",
    'category': 'Tools',
    'summary': 'You can use multiple gateway for multiple sms template to send SMS.',
    'description': 'Allows you to send SMS to the mobile no.',
    'website': "http://www.fdshive.com",
    'depends': ['base', 'web', 'hr', 'odoocms_base', 'odoocms'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'menus/menu.xml',
        'data/sequence.xml',

        'view/send_sms_view.xml',
        'view/ir_actions_server_views.xml',
        'view/sms_track_view.xml',
        'view/sms_cron_view.xml',
        'view/gateway_setup_view.xml',

        'view/send_sms_employee_view.xml',
        'view/send_sms_student_view.xml',
        'view/send_sms_list_view.xml',

        'wizard/sms_compose_view.xml',

    ],
    'images': ['static/description/banner.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}

# UCP
# http://173.45.125.162:8888/push-url/?user=tower&pwd=tower@pc_987&to=3000777655&from=UCP&text=Test Message from Odoo
