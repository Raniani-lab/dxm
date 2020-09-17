# -*- coding: utf-8 -*-

{
    'name': "Mobile Device Reception",

    'summary': """
        This is module to load lot information and make a quality test for mobile devices in the reception process. 
        """,

    'description': """
        This is module to load lot information and make a quality test for mobile devices in the reception process.
    """,

    'author': "Heyner Roque | Octupus Technologies SL",
    'website': "https://www.octupus.es",

    'category': 'productivity',
    'version': '0.1',

    'depends': ['base', 'stock', 'stock_account', 'purchase', 'purchase_stock'],

    'data': [
        'security/ir.model.access.csv',
        'data/group_data.xml',
        'data/report_paper_format.xml',
        'views/backend_assets.xml',
        'views/stock_picking_view.xml',
        'views/stock_production_lot.xml',
        'views/product_template.xml',
        'views/purchase_order.xml',
        'views/res_config.xml',
        'views/functional_quality_test_view.xml',
        'views/esthetic_quality_test_view.xml',
        'wizard/quality_test_view.xml',
        'wizard/graduation_wizard_view.xml',
        'wizard/split_stock_picking.xml',
        'wizard/inventory_adjustment_wizard_view.xml',
        'report/product_label_template.xml',
        'report/product_label.xml',
        'views/stock_quant.xml'
    ],
    'installable': True,
    'application': False,
}
