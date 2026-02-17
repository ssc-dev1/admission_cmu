{
    'name': ' Syncing Utility',
    'version': '1.0.4',
    'summary': "syncing utility to transer data inter modules",
    'description': 'syncing utility to transer data inter modules',
    'category': 'OdooCMS',
    'sequence': 1,
    'author': 'Abubakar',
    'company': 'UCP',
    'website': "https://ucp.edu.pk/",
    'depends': ['base','odoocms','web','odoocms_admission','odoocms_admission_ucp','odoocms_admission_cust_ext_a'],
    'data': [
        'security/ir.model.access.csv',
        'views/admission_sync_utility.xml',
        # 'views/syncing_conf.xml',
        'menu/menu.xml',
        'security/record_rule.xml',
        'views/custom_log_views.xml'

    ],
    'qweb': [],
    'assets': {
        'web.assets_frontend': [
            'syncing_utility/static/src/js/admission_sync.js'
        ],
    },
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,

}
