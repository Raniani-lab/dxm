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

    from_split = fields.Boolean(string="From Move Splitted")

    master_split = fields.Boolean(string="Is Master Split")

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
            picking['show_inventory_adjustment'] = True  # show_adjustment

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
        _logger.info("ADJUSTING INVENTORY FOR %r", self.name)
        if not self.is_locked:
            self.action_toggle_is_locked()
        if self.state == 'draft':
            self.action_confirm()
        products_adjusted = 0
        message = self.env['message.popup']

        for move in self.move_lines:
            if move.move_orig_ids:
                _logger.info("LINE WITH ORIGIN")
                last_move_qty = move.move_orig_ids.product_uom_qty
                now_qty = move.product_uom_qty
                if last_move_qty != now_qty or move.picking_id.master_split or move.picking_id.from_split:
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
        self.action_assign()
        if products_adjusted > 0:
            self.write({'inventory_adjusted': True})
            term = message.pluralize(products_adjusted, 'product', 'products')
            msg = "Inventory adjustment successfully for %s" % term
        else:
            msg = "No operations lines modified to adjust"
        return message.popup(message=msg)

    def create_inventory_adjustment(self, move):
        _logger.info("CREATING INVENTORY ADJUSTMENT")

        qty = 0
        if move.picking_id.master_split or move.picking_id.from_split:
            _logger.info("ADJUSTING SPLITTED PICKING")
            total_product_qty = self._get_product_total_qty_splitted_move(move.picking_id, move.product_id)
            _logger.info("TOTAL PRODUCT QTY ON ALL SPLITTED PICKINGS: %r", total_product_qty)
            if move.move_orig_ids:
                if total_product_qty == move.move_orig_ids[0].product_uom_qty:
                    return False
                qty = move.move_orig_ids[0].product_uom_qty - total_product_qty
            else:
                qty = -(move.product_uom_qty)
        else:
            if move.move_orig_ids:
                qty = move.move_orig_ids[0].product_uom_qty - move.product_uom_qty
            else:
                qty = -move.product_uom_qty

        inventory_adjustment = self.env['stock.inventory'].create({
            'name': 'Automatic Adjustment For: ' + move.product_id.name,
            'company_id': move.company_id.id,
            'location_ids': [move.location_id.id],
            'product_ids': [move.product_id.id]
        })
        _logger.info("STOCK INVENTORY ID: %r", inventory_adjustment.id)
        inventory_adjustment._action_start()

        _logger.info("QTY: %r", qty)

        if inventory_adjustment.line_ids:
            _logger.info("ADJUSTMENT WITH LINES")
            line_id = inventory_adjustment.line_ids.filtered(lambda l: not l.prod_lot_id)
            _logger.info("LINE IDs: %r", line_id.ids)
            if len(line_id) == 1:
                _logger.info("ONE LINE")
                _logger.info("LINE QTY: %r", line_id.product_qty)
                line_id.write({'product_qty': line_id.product_qty - qty})

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
                'product_qty': -(qty) if qty < 0 else qty,
                'location_id': move.location_id.id,
                'company_id': move.company_id.id
            })
        inventory_adjustment.action_validate()
        inventory_adjustment._action_done()
        return True

    def split_move_wizard(self):
        _logger.info("SPLITTING PICKING %r", self.id)
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
