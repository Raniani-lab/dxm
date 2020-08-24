# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def get_similar_barcode(self):
        picking = self
        lots = []
        products_quantity = {}
        default_location_id = self.env['ir.config_parameter'].sudo().get_param(
            'mobile_device_sale.mobile_stock_location')
        stock_location = self.env['stock.location'].browse(int(default_location_id))
        _logger.info("PICKING: %r", picking)
        for line in picking.move_lines:
            if line.product_id.id in products_quantity.keys():
                quantity = products_quantity.get(line.product_id.id)['quantity']
                products_quantity.update({line.product_id.id: {
                    'quantity': quantity + line.product_uom_qty, 'scanned_qty': 0}})
            else:
                products_quantity.update({line.product_id.id: {
                                              'quantity': line.product_uom_qty, 'scanned_qty': 0}})
            product_quants = self.env['stock.quant'].sudo()._gather(line.product_id, stock_location)
            for specs in line.mapped('move_line_specs_ids'):
                specs_filter = specs.create_specs_filter_values()[1]
                _logger.info("SPECS FILTER: %r", specs_filter)
                quant_filtered = product_quants.filtered(lambda q: eval(specs_filter))
                lots_in_quants = quant_filtered.mapped('lot_id').ids
                lots += lots_in_quants

        return {'lots': lots, 'products_quants': products_quantity}
