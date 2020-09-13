# -*- coding: utf-8 -*-
from odoo import http

# class WcWizardGiftReceipt(http.Controller):
#     @http.route('/wc_wizard_gift_receipt/wc_wizard_gift_receipt/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/wc_wizard_gift_receipt/wc_wizard_gift_receipt/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('wc_wizard_gift_receipt.listing', {
#             'root': '/wc_wizard_gift_receipt/wc_wizard_gift_receipt',
#             'objects': http.request.env['wc_wizard_gift_receipt.wc_wizard_gift_receipt'].search([]),
#         })

#     @http.route('/wc_wizard_gift_receipt/wc_wizard_gift_receipt/objects/<model("wc_wizard_gift_receipt.wc_wizard_gift_receipt"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('wc_wizard_gift_receipt.object', {
#             'object': obj
#         })