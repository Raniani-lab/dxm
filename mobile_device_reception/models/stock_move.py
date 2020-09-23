# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = 'stock.move'

    def split_move_to_workshop(self, qty, dest_picking):
        if self.product_uom_qty >= qty:
            move_obj = self.env['stock.move'].browse(self.id)
            move_lines = move_obj.move_line_ids.filtered(
                lambda l: l.lot_id.x_studio_resultado == 'Con Avería'
            )
            new_move = self.env['stock.move'].create({
                'name': self.product_id.display_name,
                'product_id': self.product_id.id,
                'product_uom_qty': qty,
                'product_uom': self.product_uom.id,
                'description_picking': self.description_picking,
                'location_id': dest_picking.location_id.id,
                'location_dest_id': dest_picking.location_dest_id.id,
                'picking_id': dest_picking.id,
                'picking_type_id': dest_picking.picking_type_id.id,
                'restrict_partner_id': dest_picking.owner_id.id,
                'company_id': dest_picking.company_id.id,
                'warehouse_id': self.warehouse_id.id,
                'move_line_ids': [(4, m.id) for m in move_lines]
            })
            for line in move_lines:
                line.write({
                    # 'move_id': new_move.id,
                    'picking_id': dest_picking.id,
                    'location_dest_id': dest_picking.location_dest_id.id,
                    'state': 'assigned'
                })
            _logger.info("NEXT MOVE: %r", self.move_dest_ids)
            next_move = self.move_dest_ids[0]
            expected_qty = next_move.product_uom_qty
            next_move.write({'product_uom_qty': expected_qty - qty})
            self['product_uom_qty'] = self.product_uom_qty - qty
            return new_move
