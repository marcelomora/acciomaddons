# -*- coding: utf-8 -*-
{
    'name': "Cookie Notice",

    'summary': """
        Website cookie notice """,

    'description': """
        GDPR compliant cookie notice. 
    """,

    'author': "Accioma",
    'website': "http://www.accioma.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Website',
    'version': '10.0.1',

    # any module necessary for this one to work correctly
    'depends': ['website'],

    # always loaded
    'data': [
        'views/templates.xml',
        'views/cookie_notice_templates.xml',
    ],
}