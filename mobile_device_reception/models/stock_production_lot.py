# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = "stock.production.lot"

    esthetic_test_id = fields.Many2one(comodel_name="esthetic.quality.test")
    functional_test_id = fields.Many2one(comodel_name="functional.quality.test")

    lot_value_svl = fields.Float(compute='_compute_lot_value_svl')
    lot_quantity_svl = fields.Float(compute='_compute_lot_value_svl')
    stock_valuation_layer_ids = fields.One2many(comodel_name='stock.valuation.layer', inverse_name='lot_id')

    @api.depends('stock_valuation_layer_ids')
    def _compute_lot_value_svl(self):
        # _logger.info("COMPUTING LOT SVL.....")
        # _logger.info("SELF HERE: %r", self)
        company_id = self.env.context.get('force_company', self.env.company.id)

        for lot in self:

            domain = [
                ('lot_id', '=', lot.id),
                ('company_id', '=', company_id),
            ]
            groups = self.env['stock.valuation.layer'].read_group(domain, ['value:sum', 'quantity:sum'], ['lot_id'])
            # _logger.info("GROUPS: %r", groups)
            if len(groups):
                for group in groups:
                    _logger.info("LOT: %r", lot.name)
                    _logger.info("LOT VALUE: %r", group['value'])
                    _logger.info("LOT QTY: %r", group['quantity'])
                    lot.lot_value_svl = self.env.company.currency_id.round(group['value']) or 0.0
                    lot.lot_quantity_svl = group['quantity'] or 0.0
            else:
                lot.lot_value_svl = 0
                lot.lot_quantity_svl = 0

    @api.depends('name')
    def _compute_purchase_order_ids(self):
        _logger.info("COMPUTING PURCHASE ON LOTS")
        for lot in self:
            stock_moves = self.env['stock.move.line'].search([
                ('lot_id', '=', lot.id),
                ('state', '=', 'done')
            ]).mapped('move_id')
            stock_moves_origin = stock_moves.mapped('move_orig_ids')
            stock_moves = stock_moves.search([('id', 'in', stock_moves.ids)]).filtered(
                lambda move: move.picking_id.location_id.usage == 'supplier' and move.state == 'done')
            if not stock_moves:
                stock_moves = stock_moves_origin.filtered(
                    lambda move: move.picking_id.location_id.usage == 'supplier' and move.state == 'done')
            if not stock_moves.mapped('purchase_line_id.order_id'):
                stock_moves = stock_moves_origin.mapped('move_orig_ids').search([('id', 'in', stock_moves.ids)]).filtered(
                    lambda move: move.picking_id.location_id.usage == 'supplier' and move.state == 'done')
            lot.purchase_order_ids = stock_moves.mapped('purchase_line_id.order_id')
            lot.purchase_order_count = len(lot.purchase_order_ids)
