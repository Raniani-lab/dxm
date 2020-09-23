# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = "stock.picking"

    quality_test_done = fields.Boolean(string='All Quality Test Done', compute='_check_quality_test_done')

    show_quality_test = fields.Boolean(compute="_show_quality_test")

    show_reception_adjustment = fields.Boolean(compute="_show_reception_adjustment")

    from_split = fields.Boolean(string="From Move Splitted")

    master_split = fields.Boolean(string="Is Master Split")

    def _show_reception_adjustment(self):
        get_param = self.env['ir.config_parameter'].sudo().get_param
        reception_op_id = int(get_param('mobile_device_reception.mobile_reception_op_type'))
        for picking in self:
            if picking.picking_type_id.id == reception_op_id and picking.state in ['draft', 'confirmed', 'waiting', 'assigned']:
                picking['show_reception_adjustment'] = True
            else:
                picking['show_reception_adjustment'] = False

    def _show_quality_test(self):
        q_test_id = self.env['ir.config_parameter'].sudo().get_param('mobile_device_reception.quality_test_op_type')
        for picking in self:
            if q_test_id:
                if int(q_test_id) == picking.picking_type_id.id:  # picking.company_id.functional_test_op_type
                    picking.show_quality_test = True
                else:
                    picking.show_quality_test = False
            else:
                picking.show_quality_test = False

    def _check_quality_test_done(self):
        for picking in self:
            test_done = True
            for move_line in picking.move_line_ids:
                if not move_line.quality_test_done:
                    test_done = False
            picking.quality_test_done = test_done

    def button_validate(self):
        q_test_id = int(self.env['ir.config_parameter'].sudo().get_param(
            'mobile_device_reception.quality_test_op_type'
        ))
        if self.picking_type_id.id == q_test_id:
            if not self.quality_test_done:
                raise ValidationError("You must run quality test in all lots to validate this picking.")
            else:
                # First check if there is move lines to SAT location.
                move_to_workshop = self._check_workshop_lines()
                if move_to_workshop:
                    workshop_move = self._create_workshop_move()
                    if workshop_move:
                        # Check if still qty to move
                        still_to_move = self.move_line_ids.filtered(
                            lambda move_line: move_line.lot_id.x_studio_resultado == 'Funcional'
                        )
                        if still_to_move:
                            return super(Picking, self).button_validate()
                        else:
                            return super(Picking, self).action_cancel()
                else:
                    return super(Picking, self).button_validate()
        else:
            return super(Picking, self).button_validate()
        # return super(Picking, self).button_validate()

    def _check_workshop_lines(self):
        workshop_lines = self.move_line_ids.filtered(
            lambda move_line: move_line.lot_id.x_studio_resultado == 'Con Avería'
        )
        if workshop_lines:
            return True
        else:
            return False

    def _create_workshop_move(self):
        workshop_op_type = int(self.env['ir.config_parameter'].sudo().get_param(
            'mobile_device_reception.workshop_op_type'
        ))
        op_type = self.env['stock.picking.type'].browse(workshop_op_type)
        workshop_picking = self.env['stock.picking']
        for picking in self:
            move_lines_to_workshop = picking.move_line_ids.filtered(
                lambda l: l.lot_id.x_studio_resultado == 'Con Avería'
            )
            # _logger.info("MOVE LINES TO WORKSHOP: %r", move_lines_to_workshop)
            if move_lines_to_workshop:
                ws_picking = picking.copy({
                    'name': '/',
                    'move_lines': [],
                    'move_line_ids': [],
                    'picking_type_id': workshop_op_type,
                    'location_dest_id': op_type.default_location_dest_id.id
                })
                move_map = {}
                for move_line in move_lines_to_workshop:
                    move_id = move_line.move_id.id
                    if move_id in move_map.keys():
                        map_ids = move_map.get(move_id)
                        map_ids.append(move_line.id)
                        move_map.update({move_id: map_ids})
                    else:
                        move_map[move_id] = [move_line.id]
                for move in move_map:
                    picking_move = picking.move_lines.filtered(lambda m: m.id == move)
                    split_qty = len(move_map.get(move))
                    picking_move.split_move_to_workshop(split_qty, ws_picking)
                ws_picking.action_assign()
                workshop_picking |= ws_picking
        return workshop_picking

    def run_quality_test(self):
        q_test_id = self.env['ir.config_parameter'].sudo().get_param('mobile_device_reception.quality_test_op_type')
        if int(q_test_id) == self.picking_type_id.id:
            return {
                'name': 'Run Quality Test',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'mobile.quality.test.wizard',
                'view_id': False,
                'target': 'new',
            }

    def action_reception_adjustment(self):
        return {
            'name': ' Add Reception ',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_type': 'form',
            'res_model': 'reception.adjustment.wizard',
            'view_id': False,
            'target': 'new',
            'context': {'default_picking_id': self.id}
        }

    def split_move_wizard(self):
        if len(self.move_line_ids.mapped('lot_id')) > 0:
            raise ValidationError("Lines with lots associates can't be unreserved")
        if self.from_split:
            raise ValidationError("This is an splitted move. Splitted move can't be splitted again")
        q_test_id = self.env['ir.config_parameter'].sudo().get_param('mobile_device_reception.quality_test_op_type')
        if int(q_test_id) == self.picking_type_id.id:
            return {
                'name': ' Split Stock Picking ',
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'split.stock.picking',
                'view_id': False,
                'target': 'new',
                'context': {'default_picking_id': self.id}
            }

    def _get_product_total_qty_splitted_move(self, picking, product):
        master_picking = None
        if picking.master_split:
            master_picking = picking
        elif picking.from_split:
            master_picking = self.env['stock.picking'].search([('name', '=', picking.origin)])
        children = self.env['stock.picking'].search([('origin', '=', master_picking.name)])
        product_total_qty = 0
        pickings = master_picking + children
        for pick in pickings:
            line = pick.move_lines.filtered(lambda m: m.product_id == product)
            line_qty = line.product_uom_qty
            product_total_qty += line_qty
        return product_total_qty
