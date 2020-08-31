# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    digital_canon_id = fields.Many2one(comodel_name="sale.digital.canon", string="Digital Canon")
