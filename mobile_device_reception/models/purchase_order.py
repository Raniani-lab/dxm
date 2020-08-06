# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

PAYMENT_SATE = [
        ('paid', _('Paid')),
        ('not_paid', _('Not Paid')),
        ('partially_paid', _('Partially Paid')),
        ('partially_billed', _('Partially Billed')),
        ('not_billed', _('Not Billed'))]


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    payment_state = fields.Selection(selection=PAYMENT_SATE, string="Payment State", compute="_compute_payment_state")

    def _compute_payment_state(self):
        for record in self:
            payment_state = 'not_billed'
            purchase_amount = record.amount_total
            if record.invoice_ids:
                total_amount = sum(record.invoice_ids.mapped('amount_total'))
                residual = sum(record.invoice_ids.mapped('amount_residual'))
                if purchase_amount != total_amount:
                    payment_state = 'partially_billed'
                else:
                    if residual > 0 and residual == total_amount:
                        payment_state = 'not_paid'
                    elif residual > 0 and residual != total_amount:
                        payment_state = 'partially_paid'
                    elif residual == 0:
                        payment_state = 'paid'
            record.payment_state = payment_state

    @api.onchange('order_line')
    def _onchange_order_line_content(self):
        """
        Set the reception operation type according to the category of the product.
        """
        get_param = self.env['ir.config_parameter'].sudo().get_param
        root_cat = get_param('mobile_device_reception.mobile_root_category')
        mobile_op_type = get_param('mobile_device_reception.mobile_reception_op_type')
        standard_op_type = get_param('mobile_device_reception.standard_op_type')
        categories = self.order_line.mapped('product_id').mapped('categ_id')
        mobile_categories = self.env['product.category'].search([('parent_id', 'child_of', int(root_cat))])
        mobile_flag = False
        for cat in categories:
            if cat.id in mobile_categories.ids:
                mobile_flag = True
                break
        if mobile_flag:
            self.picking_type_id = int(mobile_op_type)
        else:
            self.picking_type_id = int(standard_op_type)
