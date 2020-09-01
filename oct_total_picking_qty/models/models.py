# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PickingCost(models.Model):
    _inherit = "stock.picking"

    computed_total_demand = fields.Float(string='Total demandado', compute='_calculate_move_qty')
    computed_total_qty_done = fields.Float(string='Total hecho', compute='_calculate_move_qty')


    def _calculate_move_qty(self):
        for picking in self:
            total_demand = 0
            total_done = 0
            for move in picking.move_ids_without_package:
                total_demand += move.product_uom_qty
                total_done += move.quantity_done
            picking.computed_total_demand = total_demand
            picking.computed_total_qty_done = total_done