# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    apply_digital_canon = fields.Boolean(string="Apply Digital Canon")
