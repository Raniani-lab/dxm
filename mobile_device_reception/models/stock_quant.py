from odoo import fields, models, api


class StockQuant (models.Model):
    _inherit = 'stock.quant'


    revision_grado = fields.Many2one(string="Grado",related="lot_id.x_studio_revision_grado")
    color = fields.Many2one(string="Color",related="lot_id.x_studio_color")
    red = fields.Many2one(string="Red",related="lot_id.x_studio_red")
    logo = fields.Many2one(string="Logo",related="lot_id.x_studio_logo")
    idioma = fields.Many2one(string="Idioma",related="lot_id.x_studio_idioma")
    cargador = fields.Many2one(string="Cargador",related="lot_id.x_studio_cargador")
    aplicaciones = fields.Many2one(string="Aplicaciones",related="lot_id.x_studio_aplicaciones")



