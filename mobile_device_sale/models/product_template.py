# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    stock_qty = fields.Float(string="Real Quantity in Stock", compute="_get_product_stock")

    def _get_product_stock(self):
        default_location_id = self.env['ir.config_parameter'].sudo().get_param(
            'mobile_device_sale.mobile_stock_location')
        stock_location = self.env['stock.location'].sudo().browse(int(default_location_id))

        for template in self:
            template_quants = self.env['stock.quant'].sudo()._gather(template.product_variant_id, stock_location)
            lot_filter = 'q.reserved_quantity == 0 and q.quantity > 0'
            quants_filtered = template_quants.filtered(lambda q: eval(lot_filter))
            template.stock_qty = len(quants_filtered)
