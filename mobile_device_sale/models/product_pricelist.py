# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from itertools import chain
import logging

_logger = logging.getLogger(__name__)


class ProductPricelist(models.Model):
    _inherit = 'product.pricelist'

    def _compute_price_rule_get_items(self, products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids):
        self.ensure_one()
        # _logger.info("INSIDE _compute_price_rule_get_items()")
        # Load all rules
        self.env['product.pricelist.item'].flush(['price', 'currency_id', 'company_id'])
        if len(products_qty_partner[0]) == 4:
            grade = products_qty_partner[0][-1] or 0
        else:
            grade = 0
        # _logger.info("GRADE PRICE LIST: %r", grade)
        # _logger.info("PRODUCT_TMPL_IDS: %r", prod_tmpl_ids)
        # _logger.info("PRODUCT_IDS: %r", prod_ids)
        # _logger.info("CATEG_IDS: %r", categ_ids)
        self.env.cr.execute(
            """
            SELECT
                item.id
            FROM
                product_pricelist_item AS item
            LEFT JOIN product_category AS categ ON item.categ_id = categ.id
            WHERE
                (item.product_tmpl_id IS NULL OR item.product_tmpl_id = any(%s))
                AND (item.product_id IS NULL OR item.product_id = any(%s))
                AND (item.categ_id IS NULL OR item.categ_id = any(%s))
                AND (item.pricelist_id = %s)
                AND (item.date_start IS NULL OR item.date_start<=%s)
                AND (item.date_end IS NULL OR item.date_end>=%s)
                AND (item.apply_grade_subgroup IS NULL OR item.apply_grade_subgroup = %s)
            ORDER BY
                item.applied_on, item.min_quantity desc, categ.complete_name desc, item.id desc
            """,
            (prod_tmpl_ids, prod_ids, categ_ids, self.id, date, date, grade))
        # NOTE: if you change `order by` on that query, make sure it matches
        # _order from model to avoid inconstencies and undeterministic issues.

        item_ids = [x[0] for x in self.env.cr.fetchall()]
        # _logger.info("END _compute_price_rule_get_items()")
        return self.env['product.pricelist.item'].browse(item_ids)

    def _compute_price_rule(self, products_qty_partner, date=False, uom_id=False):
        """ Low-level method - Mono pricelist, multi products
        Returns: dict{product_id: (price, suitable_rule) for the given pricelist}

        Date in context can be a date, datetime, ...

            :param products_qty_partner: list of typles products, quantity, partner, product grade
            :param datetime date: validity date
            :param ID uom_id: intermediate unit of measure
        """
        # _logger.info("INSIDE _compute_price_rule()")
        # _logger.info("PRODUCTS QTY PARTNER IN: %r", products_qty_partner)
        self.ensure_one()
        if not date:
            date = self._context.get('date') or fields.Date.today()
        date = fields.Date.to_date(date)  # boundary conditions differ if we have a datetime
        if not uom_id and self._context.get('uom'):
            uom_id = self._context['uom']
        if uom_id:
            # _logger.info("UOM PRESENT")
            # rebrowse with uom if given
            products = [item[0].with_context(uom=uom_id) for item in products_qty_partner]
            products_qty_partner = [(products[index], data_struct[1], data_struct[2], data_struct[3]) for index, data_struct in enumerate(products_qty_partner)]
        else:
            products = [item[0] for item in products_qty_partner]

        if not products:
            return {}

        categ_ids = {}
        for p in products:
            categ = p.categ_id
            while categ:
                categ_ids[categ.id] = True
                categ = categ.parent_id
        categ_ids = list(categ_ids)

        is_product_template = products[0]._name == "product.template"
        if is_product_template:
            prod_tmpl_ids = [tmpl.id for tmpl in products]
            # all variants of all products
            prod_ids = [p.id for p in
                        list(chain.from_iterable([t.product_variant_ids for t in products]))]
        else:
            prod_ids = [product.id for product in products]
            prod_tmpl_ids = [product.product_tmpl_id.id for product in products]

        # _logger.info("PRODUCTS QTY PARTNER: %r", products_qty_partner)

        items = self._compute_price_rule_get_items(products_qty_partner, date, uom_id, prod_tmpl_ids, prod_ids, categ_ids)
        # _logger.info("ITEMS: %r", items)
        results = {}
        if len(products_qty_partner[0]) == 3:
            products_qty_partner[0] += (0,)
        for product, qty, partner, grade in products_qty_partner:
            results[product.id] = 0.0
            suitable_rule = False

            # Final unit price is computed according to `qty` in the `qty_uom_id` UoM.
            # An intermediary unit price may be computed according to a different UoM, in
            # which case the price_uom_id contains that UoM.
            # The final price will be converted to match `qty_uom_id`.
            qty_uom_id = self._context.get('uom') or product.uom_id.id
            price_uom_id = product.uom_id.id
            qty_in_product_uom = qty
            if qty_uom_id != product.uom_id.id:
                try:
                    qty_in_product_uom = self.env['uom.uom'].browse([self._context['uom']])._compute_quantity(qty, product.uom_id)
                except UserError:
                    # Ignored - incompatible UoM in context, use default product UoM
                    pass

            # if Public user try to access standard price from website sale, need to call price_compute.
            # TDE SURPRISE: product can actually be a template
            price = product.price_compute('list_price')[product.id]

            price_uom = self.env['uom.uom'].browse([qty_uom_id])
            for rule in items:
                if rule.min_quantity and qty_in_product_uom < rule.min_quantity:
                    continue
                if is_product_template:
                    if rule.product_tmpl_id and product.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and not (product.product_variant_count == 1 and product.product_variant_id.id == rule.product_id.id):
                        # product rule acceptable on template if has only one variant
                        continue
                else:
                    if rule.product_tmpl_id and product.product_tmpl_id.id != rule.product_tmpl_id.id:
                        continue
                    if rule.product_id and product.id != rule.product_id.id:
                        continue

                if rule.categ_id:
                    cat = product.categ_id
                    while cat:
                        if cat.id == rule.categ_id.id:
                            break
                        cat = cat.parent_id
                    if not cat:
                        continue

                if rule.base == 'pricelist' and rule.base_pricelist_id:
                    price_tmp = rule.base_pricelist_id._compute_price_rule([(product, qty, partner)], date, uom_id)[product.id][0]  # TDE: 0 = price, 1 = rule
                    price = rule.base_pricelist_id.currency_id._convert(price_tmp, self.currency_id, self.env.company, date, round=False)
                else:
                    # if base option is public price take sale price else cost price of product
                    # price_compute returns the price in the context UoM, i.e. qty_uom_id
                    price = product.price_compute(rule.base)[product.id]

                convert_to_price_uom = (lambda price: product.uom_id._compute_price(price, price_uom))

                if price is not False:
                    if rule.compute_price == 'fixed':
                        price = convert_to_price_uom(rule.fixed_price)
                    elif rule.compute_price == 'percentage':
                        price = (price - (price * (rule.percent_price / 100))) or 0.0
                    else:
                        # complete formula
                        price_limit = price
                        price = (price - (price * (rule.price_discount / 100))) or 0.0
                        if rule.price_round:
                            price = tools.float_round(price, precision_rounding=rule.price_round)

                        if rule.price_surcharge:
                            price_surcharge = convert_to_price_uom(rule.price_surcharge)
                            price += price_surcharge

                        if rule.price_min_margin:
                            price_min_margin = convert_to_price_uom(rule.price_min_margin)
                            price = max(price, price_limit + price_min_margin)

                        if rule.price_max_margin:
                            price_max_margin = convert_to_price_uom(rule.price_max_margin)
                            price = min(price, price_limit + price_max_margin)
                    suitable_rule = rule
                break
            # Final price conversion into pricelist currency
            if suitable_rule and suitable_rule.compute_price != 'fixed' and suitable_rule.base != 'pricelist':
                if suitable_rule.base == 'standard_price':
                    cur = product.cost_currency_id
                else:
                    cur = product.currency_id
                price = cur._convert(price, self.currency_id, self.env.company, date, round=False)

            if not suitable_rule:
                cur = product.currency_id
                price = cur._convert(price, self.currency_id, self.env.company, date, round=False)

            results[product.id] = (price, suitable_rule and suitable_rule.id or False)
        # _logger.info("PRICE RESULTS: %r", results)
        # _logger.info("END _compute_price_rule()")
        return results

    def get_products_price(self, products, quantities, partners, grade=[], date=False, uom_id=False):
        """ For a given pricelist, return price for products
        Returns: dict{product_id: product price}, in the given pricelist """
        self.ensure_one()
        # _logger.info("ARGUMENTS ON _GET_PRODUCTS_PRICE(): %s, %s, %s, %s, %s, %s" % (products, quantities, partners, grade, date, uom_id))
        if len(grade) == 0:
            grade = [0 for x in range(len(products))]
        return {
            product_id: res_tuple[0]
            for product_id, res_tuple in self._compute_price_rule(
                list(zip(products, quantities, partners, grade)),
                date=date,
                uom_id=uom_id
            ).items()
        }

    def get_product_price(self, product, quantity, partner, grade=None, date=False, uom_id=False):
        """ For a given pricelist, return price for a given product """
        self.ensure_one()
        return self._compute_price_rule([(product, quantity, partner, grade)], date=date, uom_id=uom_id)[product.id][0]

    def get_product_price_rule(self, product, quantity, partner, grade=0, date=False, uom_id=False):
        """ For a given pricelist, return price and rule for a given product """
        # _logger.info("GET PRODUCT PRICE RULE")
        self.ensure_one()
        return self._compute_price_rule([(product, quantity, partner, grade)], date=date, uom_id=uom_id)[product.id]


class ProductPricelistItem(models.Model):
    _inherit = 'product.pricelist.item'

    apply_grade_subgroup = fields.Many2one(comodel_name='x_grado', string='Apply to Grade Subgroup')
