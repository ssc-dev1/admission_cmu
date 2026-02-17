
{
    'name': 'OdooCMS Base',
    'version': '14.0.1.0.1',
    'summary': """Base Module for CMS""",
    'description': 'Base Module of Educational Institutes (University Level)',
    'category': 'OdooCMS',
    'sequence': 1,
    'author': 'AARSOL',
    'company': 'AARSOL',
    'website': "https://www.aarsol.com/",
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/odoocms_security.xml',
        'security/ir.model.access.csv',

        'data/data.xml',
        'menu/odoocms_menu.xml',
        
        'views/base_view.xml',
        'views/campus_view.xml',
        'views/institute_view.xml',
        'views/department_view.xml',
        'views/discipline_view.xml',
        'views/career_view.xml',

        'views/program_view.xml', # Specialization views in Program file
        'views/term_view.xml', # Session views in Term File

    ],
    'qweb': [
        # "static/src/xml/base.xml",
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,
}