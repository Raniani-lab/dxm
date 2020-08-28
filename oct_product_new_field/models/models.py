# -*- coding: utf-8 -*-


from odoo import models, fields, api

"""class AddProductField(models.Model):
    _inherit = "product.product"

    cantidad_a_mano = fields.Float('Cantidad a Mano', related='qty_available', store=True)
    cantidad_prevista = fields.Float('Cantidad Prevista', related='virtual_available', store=True)"""


class AddProductTemplateField(models.Model):
    _inherit = "product.template"

    descripcion_website = fields.Text('Descripción para Website', store=True)

#     descripcion_website = fields.Text('Descripción para Website',compute="_des")

#     def _des(self):
#         for object in self:
#             object.descripcion_website = object.description_sale
