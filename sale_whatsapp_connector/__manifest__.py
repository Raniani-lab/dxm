# See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Odoo Whatsapp Integration',
    'summary': 'This module is used for send SO Details on Whatsapp',
    'version': '13.0.1.0.0',
    'license': 'LGPL-3',
    'author': 'Serpent Consulting Services Pvt. Ltd.',
    'maintainer': 'Serpent Consulting Services Pvt. Ltd.',
    'website': 'http://www.serpentcs.com',
    'sequence': 1,
    'category': 'Extra Tools',
    'depends': ['base_automation',
                'sale_management',
                'odoo_whatsapp_connector'
                ],
    'data': [
        'data/sale_data.xml',
    ],
    'images': ['static/description/sale-odoo-whatsapp.gif'],
    'external_dependencies': {'python': ['html2text']},
    'installable': True,
    'price': 31,
    'currency': 'EUR'
}
