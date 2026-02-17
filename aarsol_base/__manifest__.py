{
    'name': 'AARSOL Base',
    'summary': 'AARSOL Base',
    'description': """ AARSOL Base """,
    'version': '15',
    'category': 'Productivity',
    'sequence': 1,
    'website': 'http://www.aarsol.com',
    'author': 'Farooq Arif',
    'maintainer': 'Farooq Arif, Huzaifa Farooq',
    'license': 'AGPL-3',
    'depends': ['base'],
    'data': [
        # 'data/activity_data.xml',
        'views/users_view.xml',
        'views/company_view.xml',

    ],
    'application': False,
    # 'pre_init_hook': '_pre_init_aarsol_signin',
    'installable': True,
    'auto_install': False,
}
