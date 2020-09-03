# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class DigitalCanon(models.Model):
    _name = 'sale.digital.canon'
    _description = 'Sale Digital Canon'

    name = fields.Char(string="Canon Name")
    description = fields.Text(string="Description")
    amount = fields.Monetary(string="Amount", currency_field='currency_id')
    category_ids = fields.One2many(comodel_name="product.category", inverse_name="digital_canon_id")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company.id)
    currency_id = fields.Many2one(string='Currency', related='company_id.currency_id', readonly=True,
                                  relation="res.currency")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
