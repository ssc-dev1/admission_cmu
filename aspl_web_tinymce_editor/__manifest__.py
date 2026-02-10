# -*- coding: utf-8 -*-
#################################################################################
# Author      : Acespritech Solutions Pvt. Ltd. (<www.acespritech.com>)
# Copyright(c): 2012-Present Acespritech Solutions Pvt. Ltd.
# All Rights Reserved.
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#################################################################################

{
    'name': 'TinyMCE Widget (Community)',
    'summary': 'Provides a widget for editing HTML fields using tinymce',
    'version': '1.0',
    'description': """Provides a widget for editing HTML fields using tinymce.""",
    'author': 'Acespritech Solutions Pvt. Ltd.',
    'category': 'Tools',
    'website': "http://www.acespritech.com",
    'price': 20.00,
    'currency': 'EUR',
    'depends': ['base', 'base_setup', 'web',],
    'data': [
        'security/ir.model.access.csv',
        # 'views/template.xml',
        'views/res_config_view.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'web.assets_backend': [
            'aspl_web_tinymce_editor/static/lib/tinymce/tinymce.min.js',
            'aspl_web_tinymce_editor/static/lib/tinymce/themes/modern/theme.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/advlist/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/anchor/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/autolink/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/autoresize/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/charmap/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/code/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/colorpicker/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/emoticons/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/autosave/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/save/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/fullpage/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/fullscreen/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/hr/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/image/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/imagetools/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/insertdatetime/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/link/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/lists/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/media/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/nonbreaking/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/pagebreak/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/paste/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/preview/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/print/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/searchreplace/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/spellchecker/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/tabfocus/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/table/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/textcolor/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/textpattern/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/plugins/wordcount/plugin.min.js',
        'aspl_web_tinymce_editor/static/lib/tinymce/skins/lightgray/content.min.css',
        'aspl_web_tinymce_editor/static/lib/tinymce/skins/lightgray/skin.min.css',
        'aspl_web_tinymce_editor/static/src/js/web_tinymce.js',

        ],
    'installable': True,
    'auto_install': False,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
