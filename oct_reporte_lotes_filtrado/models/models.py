# -*- coding: utf-8 -*-

# from odoo import models, fields, api
# import logging
#
# _logger = logging.getLogger(__name__)
#
#
# class etiquetas_prod(models.Model):
#     _inherit = 'stock.picking'
#     _name = 'etiquetas.productos'

#     def action_wizard(self):
#         form_id = self.env.ref('oct_wizard_etiquetas_prod.wizard_popup_model_view_etiqueta').id
#         ctx = self._context.copy() or {}
# #         wizard_ticket = self.env['wizard.ticket'].create({'pos_order_id': self.id})
# #         _logger.info(wizard_ticket)

#         return {
#             'type': 'ir.actions.act_window',
#             'view_type': 'form',
#             'view_mode': 'form',
#             'res_model': 'wizard.etiqueta',
#             'views': [(form_id, 'form')],
#             'view_id': form_id,
#             'target': 'new',
#             'context': {'context_data': ctx},
#         }

#     name = fields.Char()
#     value = fields.Integer()
#     value2 = fields.Float(compute="_value_pc", store=True)
#     description = fields.Text()
#
#     @api.depends('value')
#     def _value_pc(self):
#         self.value2 = float(self.value) / 100