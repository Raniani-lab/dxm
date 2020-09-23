# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class ReceptionAdjustment(models.TransientModel):
    _name = 'reception.adjustment.wizard'

    picking_id = fields.Many2one(comodel_name='stock.picking')
    company_id = fields.Many2one(comodel_name='res.company')
    change_line_ids = fields.One2many(comodel_name='reception.adjustment.wizard.line', inverse_name='adjustment_id')

    def run_reception_adjustment(self):
        self.picking_id.do_unreserve()
        if self.picking_id.is_locked:
            self.picking_id.action_toggle_is_locked()
        for line in self.change_line_ids:
            line.process_adjustment()
        if not self.picking_id.is_locked:
            self.picking_id.action_toggle_is_locked()
        self.picking_id.action_assign()
        return True

    # @api.onchange('change_line_ids')
    # def onchange_change_lines(self):
    #     _logger.info("CHANGE LINE ON WIZARD.....")
    #     for line in self.change_line_ids:
    #         if line.source_product_id and line.adjustment_id.picking_id.purchase_id:
    #             order_line = line.adjustment_id.picking_id.purchase_id.order_line.filtered(
    #                 lambda l: l.product_id.id == line.source_product_id.id)
    #             _logger.info("ORDER LINE: %r", order_line.price_unit)
    #             line['price'] = order_line.price_unit
    #         else:
    #             line['price'] = 0.0


class ReceptionAdjustmentLine(models.TransientModel):
    _name = 'reception.adjustment.wizard.line'

    def _get_product_domain(self):
        _logger.info("GETTING PRODUCT DOMAIN")
        _logger.info("CONTEXT: %r", self.env.context)
        picking_id = self.env.context.get('active_id')
        picking = self.env['stock.picking'].browse(picking_id)
        product_ids = picking.move_lines.mapped('product_id').ids
        _logger.info("PRODUCT IDS: %r", product_ids)
        return [('id', 'in', product_ids)]

    adjustment_id = fields.Many2one(comodel_name='reception.adjustment.wizard')
    source_product_id = fields.Many2one(comodel_name='product.product', string="Source Product",
                                        domain=lambda self: self._get_product_domain())
    product_id = fields.Many2one(comodel_name='product.product', string="Product", required=True)
    grade_id = fields.Many2one(comodel_name='x_grado', string="Grade", required=True)
    quantity = fields.Integer(string="Quantity", required=True)
    price = fields.Monetary(string="Price", currency_field='currency_id', default=0.0)
    currency_id = fields.Many2one('res.currency', related='adjustment_id.company_id.currency_id', readonly=True)

    @api.onchange('source_product_id')
    def onchange_source_product(self):
        _logger.info("CHANGE PRODUCT ON WIZARD.....")
        if self.source_product_id and self.adjustment_id.picking_id.purchase_id:
            order_line = self.adjustment_id.picking_id.purchase_id.order_line.filtered(
                lambda l: l.product_id.id == self.source_product_id.id)
            _logger.info("ORDER LINE: %r", order_line.price_unit)
            self['price'] = order_line.price_unit
        else:
            self['price'] = 0.0

    def process_adjustment(self):
        _logger.info("ADDING RECEPTION.....")
        _logger.info("PRODUCT: %s, QUANTITY: %s, PRICE: %s" % (self.product_id.name, self.quantity, self.price))
        po = self.adjustment_id.picking_id.purchase_id
        # Create new move
        # new_move = self.env['stock.move'].create({
        #     'name': self.product_id.display_name,
        #     'product_id': self.product_id.id,
        #     'product_uom_qty': self.quantity,
        #     'product_uom': self.product_id.uom_id.id,
        #     'description_picking': self.product_id.display_name,
        #     'location_id': self.adjustment_id.picking_id.location_id.id,
        #     'location_dest_id': self.adjustment_id.picking_id.location_dest_id.id,
        #     'picking_id': self.adjustment_id.picking_id.id,
        #     'picking_type_id': self.adjustment_id.picking_id.picking_type_id.id,
        #     'company_id': self.adjustment_id.picking_id.company_id.id,
        #     'warehouse_id': self.adjustment_id.picking_id.move_lines.mapped('warehouse_id').id,
        #     'move_line_ids': [],
        #     'state': 'confirmed',
        #     'origin': self.adjustment_id.picking_id.origin,
        #     'x_studio_grado_preliminar': self.grade_id.id
        # })
        # if new_move and self.source_product_id:
        #     move = self.adjustment_id.picking_id.move_lines.filtered(lambda m: m.product_id.id ==
        #     self.source_product_id.id)
        #     if move:
        #         if move.product_uom_qty > self.quantity:
        #             self.change_move_quantity_recursively(move, self.quantity)
        #         elif move.product_uom_qty == self.quantity:
        #             move._action_cancel()
        #         else:
        #             raise ValidationError(_("On
        #             substitution, quantity can't be greater than source product quantity"))

        # Create the PO line.
        if po:
            source_line = False
            if self.source_product_id:
                source_line = po.order_line.filtered(lambda l: l.product_id.id == self.source_product_id.id)
            po_line = self.env['purchase.order.line'].create(
                {
                    'product_id': self.product_id.id,
                    'name': self.product_id.name,
                    'price_unit': self.price,
                    'product_qty': self.quantity,
                    'product_uom_qty': self.quantity,
                    'product_uom': self.product_id.uom_id.id,
                    'product_uom_category_id': self.product_id.uom_id.category_id.id,
                    'x_studio_grado_preliminar': self.grade_id.id,
                    'order_id': po.id,
                    'partner_id': po.partner_id.id,
                    # 'move_ids': [new_move.id],
                    # 'account_analytic_id': po.order_line.mapped('account_analytic_id').id,
                    # 'analytic_tag_ids': ,
                    'company_id': self.env.company.id,
                    'date_planned': po.date_planned or po.order_line.mapped('date_planned')[0],
                    'taxes_id': self.product_id.supplier_taxes_id.ids
                }
            )
            _logger.info("NEW PURCHASE ORDER LINE CREATED WITH ID: %r", po_line.id)
            if source_line:
                new_qty = source_line.product_uom_qty - self.quantity
                if new_qty < 0:
                    new_qty = 0
                source_line.write({'product_qty': new_qty, 'product_uom_qty': new_qty})
            if self.source_product_id:
                move = self.adjustment_id.picking_id.move_lines.filtered(lambda m: m.product_id.id == self.source_product_id.id)
                if move:
                    if move.product_uom_qty > self.quantity:
                        self.change_move_quantity_recursively(move, self.quantity)
                    elif move.product_uom_qty == self.quantity:
                        move._action_cancel()
                    else:
                        raise ValidationError(_("On substitution, quantity can't be greater than source product quantity"))
        else:
            raise ValidationError(_("No Purchase order associated to this move. "
                                    "You don't need this, just create the entry manually"))

    def change_move_quantity_recursively(self, move, qty):
        while move:
            move.picking_id.do_unreserve()
            if move.picking_id.is_locked:
                move.picking_id.action_toggle_is_locked()

            move.write({'product_uom_qty': move.product_uom_qty - qty})

            if not move.picking_id.is_locked:
                move.picking_id.action_toggle_is_locked()
            move.picking_id.action_assign()

            move = move.move_dest_ids
        return
