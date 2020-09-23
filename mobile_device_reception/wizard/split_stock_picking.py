# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import numpy as np
import logging

_logger = logging.getLogger(__name__)


class SplitStockPicking(models.TransientModel):
    _name = 'split.stock.picking'

    def _get_current_company(self):
        return self.env.company.id

    picking_id = fields.Many2one(comodel_name='stock.picking')
    move_line_ids = fields.One2many(comodel_name='split.stock.picking.line', inverse_name='stock_split_id',
                                    string='Split Quantity Lines By Product')
    section_line_ids = fields.One2many(comodel_name='split.stock.picking.section', inverse_name='stock_split_id',
                                    string='Split Quantity Lines By Product')
    split_mode = fields.Selection(selection=[('simple', 'Simple '), ('section', 'By Section')],
                                  string="Split Mode", default="section")
    keep_target_operation = fields.Boolean(string="Keep Target Operation")
    responsible = fields.Many2one(comodel_name='res.users', string='Responsible', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string="Company", default=_get_current_company)

    def split_stock_picking(self):
        _logger.info("PROCESSING PICKING.....")
        # context = self.env.context.copy() or {}
        # picking_id = context.get('active_id')
        # picking = self.env['stock.picking'].search([('id', '=', picking_id)])
        _logger.info("PICKING ID: %r", self.picking_id)
        picking = self.picking_id
        if self.split_mode == 'simple':
            if self.move_line_ids:
                for line in self.move_line_ids:
                    _logger.info("SPLITTING %s UNITS FOR PRODUCT %s" % (line.next_move_qty, line.product_id))
                    # Process here data for each line and convert it in an stock.move
                    move_line = picking.move_lines.filtered(lambda m: m.product_id.id == line.product_id.id)
                    self._split_move(move_line, line.next_move_qty, responsible_id=self.responsible.id)

                    # If not keep target operation generate new one
                    if not self.keep_target_operation:
                        next_op_move = move_line.move_dest_ids
                        if next_op_move:
                            self._split_move(next_op_move, line.next_move_qty)
            else:
                raise ValidationError("You must provide at lest one line with a product and a quantity to split")
            return
        elif self.split_mode == 'section':
            if self.section_line_ids:
                for line in self.section_line_ids:
                    move_line = picking.move_lines.filtered(lambda m: m.product_id.id == line.product_id.id)
                    move_qty = move_line.product_uom_qty
                    qty_array = np.arange(move_qty)
                    qty_list = [len(x) for x in np.array_split(qty_array, line.section_qty)][1:]
                    for qty in qty_list:
                        _logger.info("SPLITTING %s UNITS FOR PRODUCT %s" % (qty, line.product_id.name))
                        splitted_move = self._split_move(move_line, qty, responsible_id=self.responsible.id,
                                                         keep_target=True if self.keep_target_operation else False)
                        if not self.keep_target_operation:
                            next_op_move = move_line.move_dest_ids
                            if next_op_move:
                                next_splitted = self._split_move(next_op_move, qty, state='waiting')
                                splitted_move.write({'move_dest_ids': [next_splitted.id]})
            else:
                raise ValidationError("You must provide at lest one line with a product and a section quantity.")
            return

    def _split_move(self, move, qty, responsible_id=False, keep_target=False, state='confirmed'):
        _logger.info("SPLITTING MOVE %r", move.id)
        _logger.info("KEEP TARGET: %r", keep_target)
        picking = move.picking_id
        _logger.info("PICKING PARTNER: %r", picking.partner_id)
        new_picking = picking.copy({
            'name': '/',
            'move_lines': [],
            'move_line_ids': [],
            'origin': picking.name,
            'partner_id': picking.partner_id.id,
            'user_id': responsible_id,
            'from_split': True,
            'state': state
        })
        if keep_target:
            new_move_id = move._split(qty)
            new_move = self.env['stock.move'].browse(new_move_id)
        else:
            new_move = move.copy({
                'product_uom_qty': qty,
                'picking_id': new_picking.id,
                'move_line_ids': [],
                'move_dest_ids': [],
                'state': state
            })

        picking.do_unreserve()
        if picking.is_locked:
            picking.action_toggle_is_locked()
        move.write({'product_uom_qty': (move.product_uom_qty - qty)})
        picking.write({'master_split': True})
        if not picking.is_locked:
            picking.action_toggle_is_locked()
        picking.action_assign()

        # Write a note to the picking
        msg_body = "<p>Product %s moved %s units to process on order %s. Actual responsible: %s</p>" % \
                   (move.product_id.name,
                    qty,
                    new_picking.name,
                    self.responsible.name)
        picking.message_post(body=msg_body)
        new_picking.action_assign()

        return new_move

    @api.onchange('move_line_ids')
    def onchange_lines(self):
        picking = self.picking_id
        if self.move_line_ids:
            for line in self.move_line_ids:
                if line.product_id and line.next_move_qty > 0:
                    move_line = picking.move_lines.filtered(lambda m: m.product_id.id == line.product_id.id)
                    if line.next_move_qty > move_line.product_uom_qty:
                        line.next_move_qty = 0
                        raise ValidationError("Quantity to split can't be greater or equal than "
                                              "total move quantity for this product")


class SplitStockPickingSection(models.TransientModel):
    _name = 'split.stock.picking.section'

    def _get_picking_products(self):
        context = self.env.context.copy() or {}
        picking_id = context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        product_ids = picking.move_lines.mapped('product_id')
        return [('id', 'in', product_ids.ids)]

    stock_split_id = fields.Many2one(comodel_name='split.stock.picking', string='Split Move')
    picking_id = fields.Many2one(comodel_name='stock.picking', related='stock_split_id.picking_id')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=_get_picking_products)
    section_qty = fields.Integer(string='Sections')


class SplitStockPickingLine(models.TransientModel):
    _name = 'split.stock.picking.line'

    def _get_picking_products(self):
        context = self.env.context.copy() or {}
        picking_id = context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        product_ids = picking.move_lines.mapped('product_id')
        return [('id', 'in', product_ids.ids)]

    stock_split_id = fields.Many2one(comodel_name='split.stock.picking', string='Split Move')
    picking_id = fields.Many2one(comodel_name='stock.picking', related='stock_split_id.picking_id')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=_get_picking_products)
    next_move_qty = fields.Integer(string='Qty To Next Move')
