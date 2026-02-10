{
    'name': ' Transfer_Images',
    'version': '13.0.1.0.1',
    'summary': """Core Module for UMS""",
    'description': 'Core Module of Educational Institutes (University Level)',
    'category': 'OdooCMS',
    'sequence': 1,
    'author': 'AARSOL',
    'company': 'AARSOL',
    'website': "https://www.aarsol.com/",
    'depends': ['odoocms'],
    'data': [
        'security/ir.model.access.csv',

        'menu/menu.xml',
        'views/transfer_images.xml',

    ],
    'qweb': [
        # "static/src/xml/base.xml",
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': True,

}
