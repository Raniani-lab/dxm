# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.depends_context('pricelist', 'partner', 'quantity', 'uom', 'date', 'no_variant_attributes_price_extra', 'grade')
    def _compute_product_price(self):
        # _logger.info("!!COMPUTING PRODUCT PRICE.....")
        prices = {}
        pricelist_id_or_name = self._context.get('pricelist')
        if pricelist_id_or_name:
            pricelist = None
            partner = self.env.context.get('partner', False)
            quantity = self.env.context.get('quantity', 1.0)
            grade = self.env.context.get('grade', 0)
            # _logger.info("GRADE ENV CONTEXT: %r", grade)
            # _logger.info("CONTEXT ON SELF: %r", self._context)
            # _logger.info("CONTEXT ON ENV: %r", self.env.context)

            # Support context pricelists specified as list, display_name or ID for compatibility
            if isinstance(pricelist_id_or_name, list):
                pricelist_id_or_name = pricelist_id_or_name[0]
            if isinstance(pricelist_id_or_name, str):
                pricelist_name_search = self.env['product.pricelist'].name_search(pricelist_id_or_name, operator='=',
                                                                                  limit=1)
                if pricelist_name_search:
                    pricelist = self.env['product.pricelist'].browse([pricelist_name_search[0][0]])
            elif isinstance(pricelist_id_or_name, int):
                pricelist = self.env['product.pricelist'].browse(pricelist_id_or_name)

            if pricelist:
                quantities = [quantity] * len(self)
                partners = [partner] * len(self)
                grades = [grade] * len(self)
                prices = pricelist.get_products_price(self, quantities, partners, grades)

        for product in self:
            product.price = prices.get(product.id, 0.0)
