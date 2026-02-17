{
    'name': 'odoo admission ext a',
    'version': '1.0.0',
    'summary': 'MIS Enhancements',
    'description': 'this directory will contains the code for MIS enhancements',
    'category': '',
    'author': 'MIS',
    'website': '',
    'license': 'LGPL-3',
    'depends': ['odoocms_base',
                'mail',
                'odoocms',
                'odoocms_admission',
                'odoocms_assets',
                'odoocms_admission_ucp',
                'odoocms_admission_fee',
                'odoocms_merit_ucp']
    ,
    'data': [
        'views/applicant_doc.xml',
        'views/allocate_scholarship.xml',
        'views/meritlist.xml',
        'views/single_challan.xml',
        'views/pre_test.xml',
        'views/pwwf_scholarship.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'external_dependencies': {
        'python': [],
    },
    'application': True
}
