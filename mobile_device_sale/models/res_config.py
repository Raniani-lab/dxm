from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    name = 'res.config.settings'
    _inherit = 'res.config.settings'

    delivery_op_type = fields.Many2one(comodel_name='stock.picking.type',
                                       string='Delivery Operation Type',
                                       help='Picking type for delivery operations')

    website_for_sell = fields.Many2one(comodel_name='website',
                                       string='Website For Sell',
                                       help='Website for sell mobile devices')

    mobile_stock_location = fields.Many2one(comodel_name='stock.location',
                                            string='Default Sale Location',
                                            help='Default website location for sale')

    payment_method_to_negotiate_price = fields.Many2one(comodel_name='payment.acquirer',
                                                        string='Payment Method to Negotiate Price')

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        get_param = self.env['ir.config_parameter'].sudo().get_param
        res.update(
            delivery_op_type=int(get_param('mobile_device_sale.delivery_op_type')),
            website_for_sell=int(get_param('mobile_device_sale.website_for_sell')),
            payment_method_to_negotiate_price=int(get_param('mobile_device_sale.payment_method_to_negotiate_price')),
            mobile_stock_location=int(get_param('mobile_device_sale.mobile_stock_location'))
        )
        return res

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        set_param = self.env['ir.config_parameter'].sudo().set_param

        delivery_op_type = self.delivery_op_type and self.delivery_op_type.id or False
        website_for_sell = self.website_for_sell and self.website_for_sell.id or False
        mobile_stock_location = self.mobile_stock_location and self.mobile_stock_location.id or False
        payment_method_to_negotiate_price = self.payment_method_to_negotiate_price and self.payment_method_to_negotiate_price.id or False

        set_param('mobile_device_sale.delivery_op_type', delivery_op_type)
        set_param('mobile_device_sale.website_for_sell', website_for_sell)
        set_param('mobile_device_sale.mobile_stock_location', mobile_stock_location)
        set_param('mobile_device_sale.payment_method_to_negotiate_price', payment_method_to_negotiate_price)
