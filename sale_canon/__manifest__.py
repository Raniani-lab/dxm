# -*- coding: utf-8 -*-

{
    'name': "Sale Digital Canon",

    'summary': """
        Sale Digital Canon
        """,

    'description': """
        Sale Digital Canon
    """,

    'author': "Heyner Roque | Octupus Technologies SL",
    'website': "https://www.octupus.es",

    'category': 'productivity',
    'version': '0.1',

    'depends': ['base', 'sale', 'website_sale', 'product'],

    'data': [
        'security/ir.model.access.csv',
        'views/digital_canon_views.xml',
        'views/product_category_views.xml',
        'views/sale_order_views.xml',
        'views/account_fiscal_position.xml',
        'data/digital_canon_data.xml'
    ],
    'installable': True,
    'application': False,
}
