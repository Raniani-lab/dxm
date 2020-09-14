from odoo import models, fields, api, exceptions
from datetime import date, datetime, timedelta
import logging

_logger = logging.getLogger(__name__)


class Wizard_Stock(models.TransientModel):
    _name = 'wizard.stock'

    producto = fields.Many2one('product.product', string="Producto")
    marca = fields.Many2one('product.brand', string="Marca")
    modelo = fields.Char("Escriba el Modelo")
    part_number = fields.Char("Escriba el Part Number")
    capacidad = fields.Many2one('x_capacidad', string="Capacidad de Almacenamiento")
    grado = fields.Many2one('x_grado', string="Grado")
    cant_a_mano = fields.Float("Cantidad a Mano")
    cant_prevista = fields.Float("Cantidad Prevista")
    tarifa_venta = fields.Float("Tarifa de Venta")
    color = fields.Many2one('x_color', string="Color")
    idioma = fields.Many2one('x_idioma_terminal', string="Idioma")
    cargador = fields.Many2one('x_cargador', string="Cargador")
    logo = fields.Many2one('x_logo', string="Logo")
    aplicaciones = fields.Many2one('x_terminal_aplicaciones', string="Aplicaciones")
    bloqueo = fields.Many2one('x_bloqueo', string="Bloqueo Operador")



    # @api.onchange('pickings_date_time')
    # def onchange_field_pickings_date_time(self):
    #     if self.pickings_date_time:
    #         date_init = self.pickings_date_time.strftime('%Y-%m-%d 00:00:00')
    #         date_end = self.pickings_date_time.strftime('%Y-%m-%d 23:59:59')
    #         mis_pedidos = self.env['stock.picking'].search([('date_done', '>', date_init), ('date_done', '<', date_end)]).ids
    #         self.write({'pedido': mis_pedidos})
    #
    #
    def print_stock_resumido(self):
        return self.env.ref('oct_reporte_lotes_filtrado.report_stock_resumido').report_action(self)

    def print_stock_ampliado(self):
        return self.env.ref('oct_reporte_lotes_filtrado.report_stock_ampliado').report_action(self)

