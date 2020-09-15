# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.model
    def create(self, vals):
        res = super(SaleOrder, self).create(vals)
        res.order_process_canon()
        return res

    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        self.order_process_canon()
        return res

    def onchange_order_line(self):
        _logger.info("ORDER LINES CHANGED.....")
        self.order_process_canon()

    def order_process_canon(self):
        order_canon_ids = self.order_line.mapped('product_id.categ_id.digital_canon_id')
        _logger.info("CANONs IN THIS ORDER: %r", order_canon_ids)
        apply_for_canon = self.partner_id.property_account_position_id.apply_digital_canon
        if order_canon_ids and apply_for_canon:
            for canon in order_canon_ids:
                canon_order_lines = self.order_line.filtered(lambda l: l.product_id.categ_id.digital_canon_id.id == canon.id)
                _logger.info("THIS CANON LINES: %r", canon_order_lines)
                # canon_product_qty = sum(canon_order_lines.mapped('product_uom_qty'))
                canon_product_qty = 0
                for canon_line in canon_order_lines:
                    _logger.info("CANON LINE: %s, QTY: %s" % (canon_line.id, canon_line.product_uom_qty))
                    canon_product_qty += canon_line.product_uom_qty
                _logger.info("CANON PRODUCT QTY: %r", canon_product_qty)
                # find an existing line for this canon
                canon_line = self.order_line.filtered(lambda l: l.is_digital_canon and l.digital_canon_id.id == canon.id)
                if canon_line and canon_product_qty > 0:
                    _logger.info("UPDATING CANON LINE --> %r", canon_line.id)
                    # Update canon line
                    canon_line.write({'product_uom_qty': canon_product_qty})
                elif canon_line and canon_product_qty == 0:
                    _logger.info("CANON QTY = 0")
                    canon_line.sudo().unlink()
                else:
                    _logger.info("CREATING CANON LINE")
                    # Create canon line
                    vals = {
                        'order_id': self.id,
                        'name': canon.product_id.name,
                        'product_id': canon.product_id.id,
                        'product_uom_qty': canon_product_qty,
                        'price_unit': canon.amount,
                        'is_digital_canon': True,
                        'digital_canon_id': canon.id
                    }
                    canon_line = self.env['sale.order.line'].create(vals)
                    if canon_line:
                        for line in canon_order_lines:
                            line.write({'digital_canon_line_id': canon_line.id})
        else:
            if self.order_line:
                for line in self.order_line:
                    if line.is_digital_canon:
                        _logger.info("LINE %s IS CANON MUST BE DELETED." % line.id)
                        line.unlink()

    def get_canon_info(self):
        canon_info = {}
        for line in self.order_line:
            if line.is_digital_canon:
                canon_info.update({line.digital_canon_id.id: line.product_uom_qty})
        return canon_info


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    is_digital_canon = fields.Boolean(string="Is Digital Canon")
    digital_canon_line_id = fields.Many2one(comodel_name="sale.order.line", string="Related Digital Canon Line")
    digital_canon_id = fields.Many2one(comodel_name="sale.digital.canon")
