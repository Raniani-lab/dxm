# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class SplitStockPicking(models.TransientModel):
    _name = 'split.stock.picking'

    def _get_current_company(self):
        return self.env.company.id

    picking_id = fields.Many2one(comodel_name='stock.picking')
    move_line_ids = fields.One2many(comodel_name='split.stock.picking.line', inverse_name='stock_split_id',
                                    string='Split Quantity Lines By Product')
    responsible = fields.Many2one(comodel_name='res.users', string='Responsible', required=True)
    company_id = fields.Many2one(comodel_name='res.company', string="Company", default=_get_current_company)

    def split_stock_picking(self):
        _logger.info("PROCESSING PICKING.....")
        # context = self.env.context.copy() or {}
        # picking_id = context.get('active_id')
        # picking = self.env['stock.picking'].search([('id', '=', picking_id)])
        _logger.info("MOVE LINE IDS: %r", self.move_line_ids)
        _logger.info("PICKING ID: %r", self.picking_id)
        picking = self.picking_id
        if self.move_line_ids:
            new_picking = picking.copy({
                'name': '/',
                'move_lines': [],
                'move_line_ids': [],
                'origin': picking.name,
                'user_id': self.responsible.id
            })
            for line in self.move_line_ids:
                _logger.info("SPLITTING %s UNITS FOR PRODUCT %s" % (line.next_move_qty, line.product_id))
                # Process here data for each line and convert it in an stock.move
                move_line = picking.move_lines.filtered(lambda m: m.product_id.id == line.product_id.id)
                new_move_id = move_line._split(line.next_move_qty)
                new_move = self.env['stock.move'].browse(new_move_id)
                new_move.write({'picking_id': new_picking.id})
                # Write a note to the picking
                msg_body = "<p>Product %s moved %s units to process on order %s. Actual responsible: %s</p>" % \
                           (line.product_id.name,
                            line.next_move_qty,
                            new_picking.name,
                            self.responsible.name)
                msg_values = {'body': msg_body, 'model': picking._name, 'res_id': picking.id,
                              'message_type': 'comment', 'author_id': self.env.user.id}
                self.env['mail.message'].sudo().create(msg_values)

            picking.do_unreserve()
            picking.action_assign()
            new_picking.action_assign()
        else:
            raise ValidationError("You must provide at lest one line with a product and a quantity to split")
        return

    @api.onchange('move_line_ids')
    def onchange_lines(self):
        picking = self.picking_id
        if self.move_line_ids:
            for line in self.move_line_ids:
                if line.product_id and line.next_move_qty > 0:
                    move_line = picking.move_lines.filtered(lambda m: m.product_id.id == line.product_id.id)
                    if line.next_move_qty > move_line.product_uom_qty:
                        line.next_move_qty = 0
                        raise ValidationError("Quantity to split can't be grater or equal than "
                                              "total move quantity for this product")


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
