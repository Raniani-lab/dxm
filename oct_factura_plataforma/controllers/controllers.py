# -*- coding: utf-8 -*-
from odoo import http

# class OctMakeModules(http.Controller):
#     @http.route('/oct_factura_plataforma/oct_factura_plataforma/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/oct_factura_plataforma/oct_factura_plataforma/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('oct_make_modules.listing', {
#             'root': '/oct_factura_plataforma/oct_factura_plataforma',
#             'objects': http.request.env['oct_factura_plataforma.oct_factura_plataforma'].search([]),
#         })

#     @http.route('/oct_factura_plataforma/oct_factura_plataforma/objects/<model("oct_factura_plataforma.oct_factura_plataforma"):obj>/,auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('oct_make_modules.object', {
#             'object': obj
#         })