# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class InventoryAdjustment(models.TransientModel):
    _name = 'inventory.adjustment.wizard'

    picking_id = fields.Many2one(comodel_name='stock.picking')
    company_id = fields.Many2one(comodel_name='res.company')
    change_line_ids = fields.One2many(comodel_name='inventory.adjustment.wizard.line', inverse_name='adjustment_id')

    def run_inventory_adjustment(self):
        # _logger.info("ADJUSTING INVENTORY FOR PICKING: %r", self.picking_id.name)
        # Unreserve the picking.....
        # _logger.info("STATES BEFORE: %r", self.picking_id.move_lines.mapped('state'))
        self.picking_id.do_unreserve()
        # _logger.info("STATES AFTER: %r", self.picking_id.move_lines.mapped('state'))
        # Unlock the picking.....
        # _logger.info(self.picking_id.is_locked)
        if self.picking_id.is_locked:
            # _logger.info("LOCKED..... UNLOCKING.....")
            self.picking_id.action_toggle_is_locked()
        for line in self.change_line_ids:
            # _logger.info("PROCESSING LINE ID: %r", line.id)
            line.process_inventory_adjustment()
        # Lock the picking.....
        # _logger.info("FINISHED ALL INVENTORY LINES")
        if not self.picking_id.is_locked:
            # _logger.info("UNLOCKED..... LOCKING.....")
            self.picking_id.action_toggle_is_locked()
        # Reserve
        # self.picking_id.do_unreserve()
        # _logger.info("STATES FINISHING: %r", self.picking_id.move_lines.mapped('state'))
        for line in self.picking_id.move_lines:
            _logger.info(line.product_id.name + " " + line.state)
        self.picking_id.action_assign()
        _logger.info("END!!!!!!!!!!!!!!!!!!!!!")
        return True


class InventoryAdjustmentLine(models.TransientModel):
    _name = 'inventory.adjustment.wizard.line'

    def _get_product_domain(self):
        _logger.info("GETTING PRODUCT DOMAIN")
        _logger.info("CONTEXT: %r", self.env.context)
        picking_id = self.env.context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        product_ids = picking.move_lines.mapped('product_id').ids
        _logger.info("PRODUCT IDS: %r", product_ids)
        return [('id', 'in', product_ids)]

    def _get_move(self):
        # _logger.info("CONTEXT: %r", self.env.context)
        if self.adjustment_id.picking_id:
            picking = self.adjustment_id.picking_id
        else:
            picking_id = self.env.context.get('active_id')
            picking = self.env['stock.picking'].browse(picking_id)
        move_id = picking.move_lines.filtered(lambda m: m.product_id.id == self.source_product.id)[0]
        # _logger.info("MOVE ID: %r", move_id)
        return move_id

    adjustment_id = fields.Many2one(comodel_name='inventory.adjustment.wizard')
    source_product = fields.Many2one(comodel_name='product.product', string="Product", required=True,
                                     domain=lambda self: self._get_product_domain())
    result_product = fields.Many2one(comodel_name='product.product', string="Changed By", required=True)
    quantity = fields.Integer(string="Quantity", required=True)

    @api.onchange('quantity')
    def onchange_quantity(self):
        # _logger.info("QUANTITY CHANGED")
        if self.source_product:
            move = self._get_move()
            if move:
                move_quantity = move.product_uom_qty
                if self.quantity > move_quantity:
                    self.quantity = 0
                    raise ValidationError(_("Quantity can't be greater than demanded quantity in move"))
            else:
                raise ValidationError(_("Can't find a move for this product"))

    def process_inventory_adjustment(self):
        if self.quantity > 0 and self.source_product and self.result_product:
            move = self._get_move()
            inventory_processed = False

            # Inventory adjustment object
            inventory_adjustment = self.env['stock.inventory'].with_context({'model': 'stock.inventory'}).create({
                'name': move.picking_id.name + ' - Adjustment For: ' + move.product_id.name,
                'company_id': move.company_id.id,
                'location_ids': [move.location_id.id],
                'product_ids': [self.source_product.id, self.result_product.id]
            })
            # Start inventory
            inventory_adjustment._action_start()
            # At least must find a line with the existing quantities of the source product
            if inventory_adjustment.line_ids:
                _logger.info("LINES IN INVENTORY ADJUSTMENT.....")
                # find the line for the source product
                source_adjust = inventory_adjustment.\
                    line_ids.filtered(lambda l: l.product_id.id == self.source_product.id and not l.prod_lot_id)
                if source_adjust and len(source_adjust) == 1:
                    _logger.info("SOURCE QTY: %r", source_adjust.product_qty)
                    _logger.info("ADJUSTED TO: %r", source_adjust.product_qty - self.quantity)

                    source_adjust.write({'product_qty': source_adjust.product_qty - self.quantity})
                else:
                    raise ValidationError(_("Can't process more than one line of inventory adjustment by product."))

                # find the line for the result product
                result_adjust = inventory_adjustment. \
                    line_ids.filtered(lambda l: l.product_id.id == self.result_product.id and not l.prod_lot_id)
                # Adjust the line
                if result_adjust and len(result_adjust) == 1:
                    _logger.info("RESULT QTY: %r", result_adjust.product_qty)
                    _logger.info("RESULT ADJUST TO: %r", result_adjust.product_qty + self.quantity)
                    result_adjust.write({'product_qty': result_adjust.product_qty + self.quantity})
                # Create if not exist.
                else:
                    _logger.info("NEW INVENTORY LINE FOR PRODUCT RESULT")
                    self.env['stock.inventory.line'].create({
                        'inventory_id': inventory_adjustment.id,
                        'product_id': self.result_product.id,
                        'product_uom_id': move.product_uom.id,
                        'product_qty': self.quantity,
                        'location_id': move.location_id.id,
                        'company_id': move.company_id.id
                    })

                inventory_adjustment.action_validate()
                inventory_adjustment._action_done()
                inventory_processed = True
                _logger.info("INVENTORY VALIDATED")

            # Finish Inventory Adjustment operation

            if inventory_processed:
                # Stock Move Adjust Operations
                # Find existing move for result product.
                existing_move = move.picking_id.move_lines.filtered(lambda m: m.product_id.id == self.result_product.id)
                if existing_move:
                    _logger.info("EXISTING MOVE")
                    existing_move.write(
                        {'product_uom_qty': existing_move.product_uom_qty + self.quantity}
                    )
                    existing_move.move_dest_ids.write(
                        {'product_uom_qty': existing_move.move_dest_ids.product_uom_qty + self.quantity}
                    )

                else:
                    _logger.info("CREATING NEW MOVE.....")
                    new_move = self.env['stock.move'].create({
                        'name': self.result_product.display_name,
                        'product_id': self.result_product.id,
                        'product_uom_qty': self.quantity,
                        'product_uom': move.product_uom.id,
                        'description_picking': move.description_picking,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'picking_id': move.picking_id.id,
                        'picking_type_id': move.picking_type_id.id,
                        'restrict_partner_id': move.restrict_partner_id.id,
                        'company_id': move.company_id.id,
                        'warehouse_id': move.warehouse_id.id,
                        'move_line_ids': [],
                        'move_orig_ids': [move.move_orig_ids[0].id],
                        'state': 'confirmed',
                        'origin': move.origin
                    })

                    _logger.info("CREATING NEXT MOVE")
                    next_new_move = self.env['stock.move'].create({
                        'name': self.result_product.display_name,
                        'product_id': self.result_product.id,
                        'product_uom_qty': self.quantity,
                        'product_uom': move.product_uom.id,
                        'description_picking': move.description_picking,
                        'location_id': move.move_dest_ids.location_id.id,
                        'location_dest_id': move.move_dest_ids.location_dest_id.id,
                        'picking_id': move.move_dest_ids.picking_id.id,
                        'picking_type_id': move.move_dest_ids.picking_type_id.id,
                        'restrict_partner_id': move.move_dest_ids.restrict_partner_id.id,
                        'company_id': move.company_id.id,
                        'warehouse_id': move.move_dest_ids.warehouse_id.id,
                        'move_line_ids': [],
                        'move_orig_ids': [new_move.id],
                        'state': 'waiting',
                        'origin': move.move_dest_ids.origin
                    })

                # Edited move adjust if not change all quantities
                if self.quantity != move.product_uom_qty:
                    move.write({'product_uom_qty': move.product_uom_qty - self.quantity})
                    move.move_dest_ids.write({'product_uom_qty': move.move_dest_ids.product_uom_qty - self.quantity})

                # Edited move adjust if change all quantities
                elif self.quantity == move.product_uom_qty:
                    move._action_cancel()
                    move.move_dest_ids._action_cancel()

            return True
