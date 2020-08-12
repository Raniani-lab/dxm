# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class Picking(models.Model):
    _inherit = "stock.picking"

    quality_test_done = fields.Boolean(string='All Quality Test Done', compute='_check_quality_test_done')

    show_quality_test = fields.Boolean(compute="_show_quality_test")

    show_inventory_adjustment = fields.Boolean(compute="_show_inventory_adjustment")

    inventory_adjusted = fields.Boolean(string="Inventory Adjustment")

    def _show_inventory_adjustment(self):
        q_test_id = self.env['ir.config_parameter'].sudo().get_param('mobile_device_reception.quality_test_op_type')
        for picking in self:
            show_adjustment = False
            for move in self.move_lines:
                if move.move_orig_ids:
                    if move.product_uom_qty != move.move_orig_ids[0].product_uom_qty and not picking.inventory_adjusted:
                        show_adjustment = True
                elif q_test_id == self.picking_type_id.id and not picking.inventory_adjusted:
                    show_adjustment = True
            picking['show_inventory_adjustment'] = show_adjustment

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
            _logger.info("MOVE LINES TO WORKSHOP: %r", move_lines_to_workshop)
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

    def run_inventory_adjustment(self):
        _logger.info("ADJUSTING INVENTORY")
        if not self.is_locked:
            self.action_toggle_is_locked()
        if self.state == 'draft':
            self.action_confirm()
        products_adjusted = 0
        for move in self.move_lines:
            if move.move_orig_ids:
                last_move_qty = move.move_orig_ids.product_uom_qty
                now_qty = move.product_uom_qty
                if last_move_qty != now_qty:
                    _logger.info("LINE %r CHANGED QTY", move.id)
                    if self.create_inventory_adjustment(move):
                        next_move = move.move_dest_ids[0]
                        if now_qty > 0:
                            next_move.write({'product_uom_qty': now_qty})
                            next_move.picking_id.action_assign()
                        else:
                            next_move._action_cancel()
                            # move._action_cancel()
                            # move.unlink()
                        products_adjusted += 1
            else:
                if self.create_inventory_adjustment(move):
                    products_adjusted += 1
                # new line added
                # next_pickings = self.move_lines.mapped('move_dest_ids').mapped('picking_id').sorted(key='id')
                # if len(next_pickings) > 1:
                #     for pick in next_pickings[1:]:
                #         _logger.info("CANCELING PICKING ID: %r", pick.id)
                #         pick.action_cancel()
                #         pick.unlink()
                # next_picking = next_pickings[0]
                # if self.create_inventory_adjustment(move):
                #     # create new move in next picking
                #     new_move = self.env['stock.move'].create({
                #         'name': move.product_id.display_name,
                #         'product_id': move.product_id.id,
                #         'product_uom_qty': move.product_uom_qty,
                #         'product_uom': move.product_uom.id,
                #         'description_picking': move.description_picking,
                #         'location_id': move.location_id.id,
                #         'location_dest_id': move.location_dest_id.id,
                #         'picking_id': next_picking.id,
                #         'picking_type_id': next_picking.picking_type_id.id,
                #         'restrict_partner_id': next_picking.owner_id.id,
                #         'company_id': next_picking.company_id.id,
                #         'warehouse_id': move.warehouse_id.id
                #     })
                #     move.write({'move_dest_ids': [new_move.id]})
                # next_picking.action_confirm()
        self.action_assign()
        self.write({'inventory_adjusted': True})
        message = self.env['message.popup']
        term = message.pluralize(products_adjusted, 'product', 'products')
        return message.popup(message="Inventory adjustment successfully for %s" % term)

    def create_inventory_adjustment(self, move):
        _logger.info("CREATING INVENTORY ADJUSTMENT")
        inventory_adjustment = self.env['stock.inventory'].create({
            'name': 'Automatic Adjustment For: ' + move.product_id.name,
            'company_id': move.company_id.id,
            'location_ids': [move.location_id.id],
            'product_ids': [move.product_id.id]
        })
        _logger.info("STOCK INVENTORY ID: %r", inventory_adjustment.id)
        inventory_adjustment._action_start()
        qty = move.product_uom_qty
        _logger.info("NOW QTY: %r", qty)
        if inventory_adjustment.line_ids:
            _logger.info("ADJUSTMENT WITH LINES")
            line_id = inventory_adjustment.line_ids.filtered(lambda l: not l.prod_lot_id)
            _logger.info("LINE ID: %r", line_id.id)
            if len(line_id) == 1:
                line_id.write({'product_qty': qty})
                _logger.info("ONE LINE")
            else:
                raise ValidationError(
                    "The product %s have many adjustments to do, please run the inventory adjustment manually" %
                    move.product_id.display_name)
        else:
            _logger.info("ADJUSTMENT WITH NO LINES, CREATING NEW LINE.....")
            self.env['stock.inventory.line'].create({
                'inventory_id': inventory_adjustment.id,
                'product_id': move.product_id.id,
                'product_uom_id': move.product_uom.id,
                'product_qty': qty,
                'location_id': move.location_id.id,
                'company_id': move.company_id.id
            })
        inventory_adjustment.action_validate()
        inventory_adjustment._action_done()
        return True

    def split_move_wizard(self):
        _logger.info("SPLITTING ORDER %r", self.id)
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
