# -*- coding: utf-8 -*-


from odoo import models, fields, api


class AddProductField(models.Model):
    _inherit = "product.product"

    cantidad_a_mano = fields.Float('Cantidad a Mano', related='qty_available', store=True)
    cantidad_prevista = fields.Float('Cantidad Prevista', related='virtual_available', store=True)
