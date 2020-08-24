from odoo import fields, models, api


class StockQuant (models.Model):
    _inherit = 'stock.quant'


    revision_grado = fields.Many2one(string="Grado",related="lot_id.x_studio_revision_grado")
    


