# -*- coding: utf-8 -*-

{
    'name': "Mobile Device Sale",

    'summary': """
        Custom module to sell mobile devices in the eCommerce
        """,

    'description': """
        Custom module to sell mobile devices in the eCommerce
    """,

    'author': "Heyner Roque | Octupus Technologies SL",
    'website': "https://www.octupus.es",

    'category': 'productivity',
    'version': '0.1',

    'depends': ['base', 'sale', 'website_sale', 'product', 'stock', 'website_sale_stock'],

    'data': [
        'security/ir.model.access.csv',
        'views/res_config.xml',
        'views/product_specs.xml',
        'views/product_pricelist.xml',
        'views/sale_order.xml',
        'views/stock_picking.xml',
        'views/templates.xml',
        'views/sale_variants_template.xml',
    ],
    'installable': True,
    'application': False,
}
