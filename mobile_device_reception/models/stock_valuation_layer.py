# -*- coding: utf-8 -*-

from odoo import models, fields, tools, api, _
import logging

_logger = logging.getLogger(__name__)


class StockValuationLayer(models.Model):
    _inherit = 'stock.valuation.layer'

    def _set_active(self):
        for vl in self:
            if vl.product_id:
                vl.active = vl.product_id.active
            elif vl.lot_id:
                vl.active = True
            else:
                vl.active = False

    active = fields.Boolean(related=False, compute='_set_active', store=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True, check_company=True, required=False)
    lot_id = fields.Many2one(comodel_name='stock.production.lot', string="Lot")
    uom_id = fields.Many2one(related='product_id.uom_id', readonly=True, required=False)

    def init(self):
        tools.create_index(
            self._cr, 'stock_valuation_layer_index',
            self._table, ['product_id', 'lot_id', 'remaining_qty', 'stock_move_id', 'company_id', 'create_date']
        )


