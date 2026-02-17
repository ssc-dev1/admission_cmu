# -*- coding: utf-8 -*-
{
    'name': "portal_assets",
    'summary': """
        Common Web Portal Assets""",
    'description': """
        Common Web Portal Assets
    """,
    'author': "Sulman Shaukat &amp; Assad Ullah Baig ",
    'website': "",
    'category': 'Uncategorized',
    'version': '1.0',
    'depends': ['website'],

'assets': {
        'portal_assets.assets_dashboard': [
            'https://fonts.googleapis.com/icon?family=Material+Icons',
            'portal_assets/app-assets/vendors/vendors.min.css',
            'portal_assets/app-assets/vendors/materialize-stepper/materialize-stepper.css',
            'portal_assets/app-assets/css/themes/vertical-modern-menu-template/materialize.css',
            'portal_assets/app-assets/css/pages/form-wizard.css',
            'portal_assets/app-assets/css/pages/dashboard.css',
            'portal_assets/app-assets/css/custom/custom.css',
            'portal_assets/app-assets/js/vendors.js',
            'portal_assets/app-assets/vendors/materialize-stepper/materialize-stepper.js',
            'portal_assets/app-assets/js/custom/custom-script.js',
            'portal_assets/app-assets/js/scripts/form-wizard.js',
            'portal_assets/app-assets/js/scripts/advance-ui-modals.js',
            'portal_assets/app-assets/js/scripts/form-elements.js',


        ],

    },
'data': [
        'views/assets.xml',
        #'views/errorpage.xml',
    ],
}