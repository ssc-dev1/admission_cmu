{
    'name': 'OdooCMS Scholarship',
    'version': '12.0',
    'license': 'LGPL-3',
    'category': 'OdooCMS',
    'sequence': 4,
    'summary': 'Manage Scholarship',
    'description': """ Manage Scholarship""",
    'author': 'AARSOL',
    'website': 'http://www.aarsol.com/',
    'depends': ['odoocms_fee'],
    'data': [
        'security/ir.model.access.csv',
        'menu/scholarship_menu.xml',
        
        'views/scholarship_view.xml',
        'views/scholarship_type_view.xml',
        
        
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
