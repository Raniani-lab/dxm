from odoo import fields, models, api
from odoo.tools.float_utils import float_is_zero
import logging

_logger = logging.getLogger(__name__)


class StockQuant (models.Model):
    _inherit = 'stock.quant'

    revision_grado = fields.Many2one(string="Grado",related="lot_id.x_studio_revision_grado")
    color = fields.Many2one(string="Color",related="lot_id.x_studio_color")
    red = fields.Many2one(string="Red",related="lot_id.x_studio_red")
    logo = fields.Many2one(string="Logo",related="lot_id.x_studio_logo")
    idioma = fields.Many2one(string="Idioma",related="lot_id.x_studio_idioma")
    cargador = fields.Many2one(string="Cargador",related="lot_id.x_studio_cargador")
    aplicaciones = fields.Many2one(string="Aplicaciones",related="lot_id.x_studio_aplicaciones")

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ For standard and AVCO valuation, compute the current accounting
        valuation of the quants by multiplying the quantity by
        the standard price. Instead for FIFO, use the quantity times the
        average cost (valuation layers are not manage by location so the
        average cost is the same for all location and the valuation field is
        a estimation more than a real value).
        """
        _logger.info("COMPUTING LOT SVL.....")
        self.currency_id = self.env.company.currency_id
        for quant in self:
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.location_id:
                quant.value = 0
                return

            if not quant.location_id._should_be_valued() or \
                    (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                continue
            if quant.product_id.cost_method == 'fifo':
                if quant.lot_id and quant.lot_id.lot_quantity_svl > 0:
                    quantity = quant.lot_id.lot_quantity_svl
                else:
                    quantity = quant.product_id.quantity_svl
                if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                    quant.value = 0.0
                    continue
                if quant.lot_id and quant.lot_id.lot_value_svl > 0:
                    average_cost = quant.lot_id.lot_value_svl / quantity
                    quant.value = quant.quantity * average_cost
                else:
                    average_cost = quant.product_id.value_svl / quantity
                    quant.value = quant.quantity * average_cost
            else:
                if quant.lot_id and quant.lot_id.lot_value_svl > 0:
                    quant.value = quant.quantity * quant.lot_id.lot_value_svl
                else:
                    quant.value = quant.quantity * quant.product_id.standard_price



