# -*- coding: utf-8 -*-
{
    'name': "oct_product_new_field",

    'summary': """
        Product new field,

    'description': 
    "Add product.product model new field"        
    """,

    'author': "Pastor Enrique Sanchez | Octupus",
    'website': "http://www.octupus.es",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/11.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','product','website_sale_stock'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}