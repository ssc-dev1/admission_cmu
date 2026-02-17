{
    'name': 'Odoocms Admission CUST Ext A',
    'version': '1.0.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'author': 'Abubakar',
    'website': '',
    'depends': ['odoocms_base', 'mail', 'odoocms', 'odoocms_assets', 'odoocms_admission','odoocms_merit_ucp'],
    'data': [
        'data/email_template.xml',
        'reports/merit_list_register_report.xml',
        'views/meritlist.xml',
        'views/pre_test.xml',
        'views/admission_register.xml',
        'data/view_template_inherits.xml',
        'views/views_inherit.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    },

    'application': False
}
