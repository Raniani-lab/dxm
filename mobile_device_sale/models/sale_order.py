# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.http import request
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
import ast
import logging

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # order_line_copy = fields.Many2one(comodel_name="sale.order.line", related="order_line")
    specs_ids = fields.One2many('product.line.specs', 'order_id',
                                      string='SPECS Lines', compute="_get_specs_lines")

    def _get_specs_lines(self):
        for order in self:
            order.specs_ids = [(6, 0, order.order_line.mapped('line_specs_ids').ids)]

    def _cart_find_product_line(self, product_id=None, line_id=None, grade=0):
        """Find the cart line matching the given parameters.

        If a product_id is given, the line will match the product only if the
        line also has the same special attributes: `no_variant` attributes and
        `is_custom` values.

        Add filter order lines by product grade
        """
        _logger.info("FINDING LINE IF EXIST")
        _logger.info("PRODUCT ID: %r", product_id)
        _logger.info("LINE ID: %r", line_id)
        _logger.info("GRADE FINDING LINE: %r", grade)
        line = super(SaleOrder, self)._cart_find_product_line(product_id, line_id)
        _logger.info("LINE RESULT BEFORE FILTER: %r", line)
        _logger.info("LINE ORDERS IDS: %r", line.mapped('order_id').ids)
        # grade filtering
        if grade:
            line = line.filtered(lambda l: l.product_grade.id == int(grade))
        _logger.info("LINE RESULT: %r", line)
        _logger.info("END LINE FINDING")
        return line

    def _website_product_id_change(self, order_id, product_id, qty=0, grade=0):
        _logger.info("AT _WEBSITE_PRODUCT_ID_CHANGE()")
        order = self.sudo().browse(order_id)
        product_context = dict(self.env.context)
        product_context.setdefault('lang', order.partner_id.lang)
        product_context.update({
            'partner': order.partner_id,
            'quantity': qty,
            'date': order.date_order,
            'pricelist': order.pricelist_id.id,
            'force_company': order.company_id.id,
        })
        _logger.info("GRADE HERE.... %r", grade)
        if grade:
            product_context.update({'grade': grade})
        _logger.info("PRODUCT CONTEXT: %r", product_context)
        product = self.env['product.product'].with_context(product_context).browse(product_id)
        discount = 0

        if order.pricelist_id.discount_policy == 'without_discount':
            # This part is pretty much a copy-paste of the method '_onchange_discount' of
            # 'sale.order.line'.
            _logger.info("PRICE LIST DISCOUNT POLICY: without_discount ")
            price, rule_id = order.pricelist_id.with_context(product_context).get_product_price_rule(product, qty or 1.0, order.partner_id, grade or 0)
            pu, currency = request.env['sale.order.line'].with_context(product_context)._get_real_price_currency(product, rule_id, qty, product.uom_id, order.pricelist_id.id)
            if pu != 0:
                if order.pricelist_id.currency_id != currency:
                    # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                    date = order.date_order or fields.Date.today()
                    pu = currency._convert(pu, order.pricelist_id.currency_id, order.company_id, date)
                discount = (pu - price) / pu * 100
                if discount < 0:
                    # In case the discount is negative, we don't want to show it to the customer,
                    # but we still want to use the price defined on the pricelist
                    discount = 0
                    pu = price
        else:
            _logger.info("GET PRODUCT.PRICE")
            pu = product.with_context(grade=grade).price
            if order.pricelist_id and order.partner_id:
                _logger.info("FINFING LINE IN PRODUCT CHANGE.....")
                order_line = order._cart_find_product_line(product.id, grade=grade)
                if order_line:
                    pu = self.env['account.tax']._fix_tax_included_price_company(pu, product.taxes_id, order_line[0].tax_id, self.company_id)
        values = {
            'product_id': product_id,
            'product_uom_qty': qty,
            'order_id': order_id,
            'product_uom': product.uom_id.id,
            'price_unit': pu,
            'discount': discount,
        }

        _logger.info("VALUES: %r", values)
        _logger.info("END _WEBSITE_PRODUCT_ID_CHANGE()")

        return values

    def _cart_update(self, product_id=None, line_id=None, add_qty=0, set_qty=0, **kwargs):
        """ Add or set product quantity, add_qty can be negative """
        _logger.info("CART UPDATE KWARG: %r", kwargs)
        _logger.info("CART UPDATE ADD QTY: %r", add_qty)
        _logger.info("CART UPDATE SET QTY: %r", set_qty)
        self.ensure_one()
        product_context = dict(self.env.context)
        _logger.info("PRODUCT CONTEXT AT FIRST: %r", product_context)
        product_context.setdefault('lang', self.sudo().partner_id.lang)
        grade = 0
        if 'grade' in kwargs.keys():
            if kwargs.get('grade') != 0:
                _logger.info("SETTING GRADE ON CONTEXT.....")
                product_context.update({'grade': kwargs.get('grade')})
                grade = kwargs.get('grade')
        SaleOrderLineSudo = self.env['sale.order.line'].sudo().with_context(product_context)
        # change lang to get correct name of attributes/values
        product_with_context = self.env['product.product'].with_context(product_context)
        product = product_with_context.browse(int(product_id))
        _logger.info("PRODUCT CONTEXT AT LAST: %r", product_context)
        process_qty = add_qty
        try:
            if add_qty:
                add_qty = float(add_qty)
        except ValueError:
            add_qty = 1
        try:
            if set_qty:
                set_qty = float(set_qty)
        except ValueError:
            set_qty = 0
        quantity = 0
        order_line = False
        if self.state != 'draft':
            request.session['sale_order_id'] = None
            raise UserError(_('It is forbidden to modify a sales order which is not in draft status.'))
        if line_id is not False:
            _logger.info("LINE ID NOT FALSE. LINE ID: %r", line_id)
            order_line = self._cart_find_product_line(product_id, line_id, grade=grade)[:1]

        # Create line if no line with product_id can be located
        if not order_line:
            _logger.info("NOT ORDER LINE. CREATING A NEW ONE.....")
            if not product:
                raise UserError(_("The given product does not exist therefore it cannot be added to cart."))

            no_variant_attribute_values = kwargs.get('no_variant_attribute_values') or []
            received_no_variant_values = product.env['product.template.attribute.value'].browse(
                [int(ptav['value']) for ptav in no_variant_attribute_values])
            received_combination = product.product_template_attribute_value_ids | received_no_variant_values
            product_template = product.product_tmpl_id

            # handle all cases where incorrect or incomplete data are received
            combination = product_template._get_closest_possible_combination(received_combination)

            # get or create (if dynamic) the correct variant
            product = product_template._create_product_variant(combination)

            if not product:
                raise UserError(_("The given combination does not exist therefore it cannot be added to cart."))

            product_id = product.id

            values = self._website_product_id_change(self.id, product_id, qty=1, grade=grade)
            # Add grade to the line
            if grade:
                values.update({'product_grade': int(grade)})

            # add no_variant attributes that were not received
            for ptav in combination.filtered(lambda
                                                     ptav: ptav.attribute_id.create_variant == 'no_variant' and ptav not in received_no_variant_values):
                no_variant_attribute_values.append({
                    'value': ptav.id,
                })

            # save no_variant attributes values
            if no_variant_attribute_values:
                values['product_no_variant_attribute_value_ids'] = [
                    (6, 0, [int(attribute['value']) for attribute in no_variant_attribute_values])
                ]

            # add is_custom attribute values that were not received
            custom_values = kwargs.get('product_custom_attribute_values') or []
            received_custom_values = product.env['product.template.attribute.value'].browse(
                [int(ptav['custom_product_template_attribute_value_id']) for ptav in custom_values])

            for ptav in combination.filtered(lambda ptav: ptav.is_custom and ptav not in received_custom_values):
                custom_values.append({
                    'custom_product_template_attribute_value_id': ptav.id,
                    'custom_value': '',
                })

            # save is_custom attributes values
            if custom_values:
                values['product_custom_attribute_value_ids'] = [(0, 0, {
                    'custom_product_template_attribute_value_id': custom_value[
                        'custom_product_template_attribute_value_id'],
                    'custom_value': custom_value['custom_value']
                }) for custom_value in custom_values]

            # create the line
            order_line = SaleOrderLineSudo.create(values)
            order_line.order_id.onchange_order_line()  # Call here to calculate canon

            try:
                order_line._compute_tax_id()
            except ValidationError as e:
                # The validation may occur in backend (eg: taxcloud) but should fail silently in frontend
                _logger.debug("ValidationError occurs during tax compute. %s" % (e))
            if add_qty:
                add_qty -= 1

        # compute new quantity
        if set_qty:
            quantity = set_qty
        elif add_qty is not None:
            quantity = order_line.product_uom_qty + (add_qty or 0)

        # Remove zero of negative lines
        if quantity <= 0:
            linked_line = order_line.linked_line_id
            order_line.unlink()
            if linked_line:
                # update description of the parent
                linked_product = product_with_context.browse(linked_line.product_id.id)
                linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
        else:
            # update line
            no_variant_attributes_price_extra = [ptav.price_extra for ptav in
                                                 order_line.product_no_variant_attribute_value_ids]
            values = self.with_context(
                no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra))._website_product_id_change(
                self.id, product_id, qty=quantity, grade=int(grade))
            if self.pricelist_id.discount_policy == 'with_discount' and not self.env.context.get('fixed_price'):
                order = self.sudo().browse(self.id)
                product_context.update({
                    'partner': order.partner_id,
                    'quantity': quantity,
                    'date': order.date_order,
                    'pricelist': order.pricelist_id.id,
                    'force_company': order.company_id.id,
                })
                _logger.info("ORDER PRICELIST NAME: %r", order.pricelist_id.name)
                if grade:
                    product_context.update({'grade': int(grade)})
                product_with_context = self.env['product.product'].with_context(product_context)
                product = product_with_context.browse(product_id)
                _logger.info("GETTING PRICE UNIT ON _CART_UPDATE()")
                values['price_unit'] = self.env['account.tax']._fix_tax_included_price_company(
                    order_line._get_display_price(product),
                    order_line.product_id.taxes_id,
                    order_line.tax_id,
                    self.company_id
                )
                _logger.info("PRICE UNIT ON _CART_UPDATE(): %r", values['price_unit'])

            order_line.write(values)

            # link a product to the sales order
            if kwargs.get('linked_line_id'):
                linked_line = SaleOrderLineSudo.browse(kwargs['linked_line_id'])
                order_line.write({
                    'linked_line_id': linked_line.id,
                })
                linked_product = product_with_context.browse(linked_line.product_id.id)
                linked_line.name = linked_line.get_sale_order_line_multiline_description_sale(linked_product)
            # Generate the description with everything. This is done after
            # creating because the following related fields have to be set:
            # - product_no_variant_attribute_value_ids
            # - product_custom_attribute_value_ids
            # - linked_line_id
            order_line.name = order_line.get_sale_order_line_multiline_description_sale(product)

        option_lines = self.order_line.filtered(lambda l: l.linked_line_id.id == order_line.id)
        # Specs handler
        if len(kwargs) > 1:
            color = network = lang = charger = logo = lock_status = apps = 0
            existing_specs = order_line.line_specs_ids
            if 'specs' in kwargs.keys():
                _logger.info("SPECS DICT: %r", kwargs.get('specs'))
                specs = ast.literal_eval(kwargs.get('specs'))
                for key in specs:
                    if key == 'device_color':
                        color = int(specs[key]) if specs[key] != '0' else 0
                    if key == 'device_network_type':
                        network = int(specs[key]) if specs[key] != '0' else 0
                    if key == 'device_lang':
                        lang = int(specs[key]) if specs[key] != '0' else 0
                    if key == 'device_charger':
                        charger = int(specs[key]) if specs[key] != '0' else 0
                    if key == 'device_logo':
                        logo = int(specs[key]) if specs[key] != '0' else 0
                    if key == 'device_lock_status':
                        lock_status = int(specs[key]) if specs[key] != '0' else 0
                    if key == 'device_applications':
                        apps = int(specs[key]) if specs[key] != '0' else 0
            if 'color' in kwargs.keys():
                color = int(kwargs.get('color'))

            specs_values = {
                'sale_order_line_id': order_line.id,
                'quantity': process_qty,
                'color': color,
                'lock_status': lock_status,
                'logo': logo,
                'charger': charger,
                'network_type': network,
                'lang': lang,
                'applications': apps
            }
            if not existing_specs:
                _logger.info("NOT EXISTING SPECS. CREATING NEW ONE")
                new_specs = self.env['product.line.specs'].create(specs_values)
                _logger.info("NEW SPECS: %r", new_specs)
            elif existing_specs:
                _logger.info("EXISTING SPECS")
                match_specs = order_line.match_product_specs(**kwargs)
                _logger.info("MATCH SPECS OBJECTS: %r", match_specs)
                if match_specs:
                    # Update qty
                    match_specs.write({'quantity': match_specs.quantity + process_qty})
                else:
                    self.env['product.line.specs'].create(specs_values)

        return {'line_id': order_line.id, 'quantity': quantity, 'option_ids': list(set(option_lines.ids))}


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_grade = fields.Many2one(comodel_name='x_grado', string='Grade')
    line_specs_ids = fields.One2many(comodel_name='product.line.specs', inverse_name='sale_order_line_id')
    price_offered = fields.Monetary(string="Price Offered")
    color_relation = fields.Char(string="Colors", compute="_get_specs_colors")

    def _get_specs_colors(self):
        for line in self:
            colors = line.line_specs_ids.mapped('color.x_name')
            if len(colors) > 1:
                line.color_relation = "%s Colores" % len(colors)
            elif len(colors) == 1:
                line.color_relation = colors[0]
            else:
                line.color_relation = ""

    def match_product_specs(self, **kwargs):
        _logger.info("MATCH SPECS KW ARGS: %r", kwargs)

        if 'specs' in kwargs.keys():
            specs_dict = ast.literal_eval(kwargs['specs'])
            # kwargs['color'] = specs_dict['device_color']
            kwargs['lock_status'] = specs_dict['device_lock_status']
            kwargs['logo'] = specs_dict['device_logo']
            kwargs['charger'] = specs_dict['device_charger']
            # kwargs['network_type'] = specs_dict['device_network_type']
            # kwargs['lang'] = specs_dict['device_lang']
            kwargs['applications'] = specs_dict['device_applications']

        domain = [('sale_order_line_id', '=', self.id)]

        if 'grade' in kwargs.keys():
            domain += [('grade', '=', int(kwargs.get('grade')) or False)]

        if 'color' in kwargs.keys():
            domain += [('color', '=', int(kwargs.get('color')) or False)]
        else:
            domain += [('color', '=', False)]

        if 'lock_status' in kwargs.keys():
            domain += [('lock_status', '=', int(kwargs.get('lock_status')) or False)]
        else:
            domain += [('lock_status', '=', False)]

        if 'logo' in kwargs.keys():
            domain += [('logo', '=', int(kwargs.get('logo')) or False)]
        else:
            domain += [('logo', '=', False)]

        if 'charger' in kwargs.keys():
            domain += [('charger', '=', int(kwargs.get('charger')) or False)]
        else:
            domain += [('charger', '=', False)]

        if 'network_type' in kwargs.keys():
            domain += [('network_type', '=', int(kwargs.get('network_type')) or False)]
        else:
            domain += [('network_type', '=', False)]

        if 'lang' in kwargs.keys():
            domain += [('lang', '=', int(kwargs.get('lang')) or False)]
        else:
            domain += [('lang', '=', False)]

        if 'applications' in kwargs.keys():
            domain += [('applications', '=', int(kwargs.get('applications')) or False)]
        else:
            domain += [('applications', '=', False)]
        return self.env['product.line.specs'].search(domain)

    def match_product_any_specs(self, **kwargs):
        _logger.info("MATCH ANY SPECS KW ARGS: %r", kwargs)

        if 'specs' in kwargs.keys():
            specs_dict = ast.literal_eval(kwargs['specs'])
            kwargs['color'] = specs_dict['device_color']
            kwargs['lock_status'] = specs_dict['device_lock_status']
            kwargs['logo'] = specs_dict['device_logo']
            kwargs['charger'] = specs_dict['device_charger']
            # kwargs['network_type'] = specs_dict['device_network_type']
            # kwargs['lang'] = specs_dict['device_lang']
            kwargs['applications'] = specs_dict['device_applications']

        domain = [('sale_order_line_id', '=', self.id)]

        if 'grade' in kwargs.keys() and int(kwargs.get('grade')) != 0:
            domain += [('grade', '=', int(kwargs.get('grade')))]

        if 'color' in kwargs.keys() and int(kwargs.get('color')) != 0:
            domain += [('color', '=', int(kwargs.get('color')))]

        if 'lock_status' in kwargs.keys() and int(kwargs.get('lock_status')) != 0:
            domain += [('lock_status', '=', int(kwargs.get('lock_status')))]

        if 'logo' in kwargs.keys() and int(kwargs.get('logo')) != 0:
            domain += [('logo', '=', int(kwargs.get('logo')))]

        if 'charger' in kwargs.keys() and int(kwargs.get('charger')):
            domain += [('charger', '=', int(kwargs.get('charger')))]

        if 'network_type' in kwargs.keys() and int(kwargs.get('network_type')) != 0:
            domain += [('network_type', '=', int(kwargs.get('network_type')))]

        if 'lang' in kwargs.keys() and int(kwargs.get('lang')) != 0:
            domain += [('lang', '=', int(kwargs.get('lang')))]

        if 'applications' in kwargs.keys() and int(kwargs.get('applications')) != 0:
            domain += [('applications', '=', int(kwargs.get('applications')))]

        return self.env['product.line.specs'].search(domain)

    def match_product_partial_specs(self, **kwargs):
        _logger.info("MATCH PARTIAL SPECS KW ARGS: %r", kwargs)

        if 'specs' in kwargs.keys():
            specs_dict = ast.literal_eval(kwargs['specs'])
            kwargs['color'] = specs_dict['device_color']
            kwargs['lock_status'] = specs_dict['device_lock_status']
            kwargs['logo'] = specs_dict['device_logo']
            kwargs['charger'] = specs_dict['device_charger']
            # kwargs['network_type'] = specs_dict['device_network_type']
            # kwargs['lang'] = specs_dict['device_lang']
            kwargs['applications'] = specs_dict['device_applications']

        domain = [('sale_order_line_id', '=', self.id)]

        if 'grade' in kwargs.keys() and int(kwargs.get('grade')) != 0:
            domain += [('grade', '=', int(kwargs.get('grade')))]

        if 'color' in kwargs.keys() and int(kwargs.get('color')) != 0:
            domain += [('color', 'in', [int(kwargs.get('color')), False])]

        if 'lock_status' in kwargs.keys() and int(kwargs.get('lock_status')) != 0:
            domain += [('lock_status', 'in', [int(kwargs.get('lock_status')), False])]

        if 'logo' in kwargs.keys() and int(kwargs.get('logo')) != 0:
            domain += [('logo', 'in', [int(kwargs.get('logo')), False])]

        if 'charger' in kwargs.keys() and int(kwargs.get('charger')):
            domain += [('charger', 'in', [int(kwargs.get('charger')), False])]

        if 'network_type' in kwargs.keys() and int(kwargs.get('network_type')) != 0:
            domain += [('network_type', 'in', [int(kwargs.get('network_type')), False])]

        if 'lang' in kwargs.keys() and int(kwargs.get('lang')) != 0:
            domain += [('lang', 'in', [int(kwargs.get('lang')), False])]

        if 'applications' in kwargs.keys() and int(kwargs.get('applications')) != 0:
            domain += [('applications', 'in', [int(kwargs.get('applications')), False])]

        return self.env['product.line.specs'].search(domain)

    def _get_display_price(self, product):
        _logger.info("_GET_DISPLAY_PRICE")
        no_variant_attributes_price_extra = [
            ptav.price_extra for ptav in self.product_no_variant_attribute_value_ids.filtered(
                lambda ptav:
                    ptav.price_extra and
                    ptav not in product.product_template_attribute_value_ids
            )
        ]
        if no_variant_attributes_price_extra:
            product = product.with_context(
                no_variant_attributes_price_extra=tuple(no_variant_attributes_price_extra)
            )

        if self.order_id.pricelist_id.discount_policy == 'with_discount':
            _logger.info("PRICE LIST WITH DISCOUNT")
            _logger.info("CONTEXT: %r", self.env.context)
            _logger.info("GRADE IN LINE: %r", self.product_grade.id)
            price = product.with_context(pricelist=self.order_id.pricelist_id.id,
                                         grade=self.product_grade.id or 0).price
            _logger.info("PRICE: %r", price)
            return price
        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order,
                               uom=self.product_uom.id, grade=self.product_grade.id or 0)

        product_grade = self.product_grade.id or 0

        final_price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id, product_grade)
        base_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id, self.product_uom_qty, self.product_uom, self.order_id.pricelist_id.id)
        if currency != self.order_id.pricelist_id.currency_id:
            base_price = currency._convert(
                base_price, self.order_id.pricelist_id.currency_id,
                self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
        # negative discounts (= surcharge) are included in the display price
        _logger.info("GETTING MAX VALUE")
        return max(base_price, final_price)

    @api.onchange('line_specs_ids')
    def on_change_specs(self):
        if self.line_specs_ids:
            line_qty = self.product_uom_qty
            specs_qty = 0
            for specs in self.line_specs_ids:
                specs_qty += specs.quantity
            if specs_qty > line_qty:
                raise ValidationError("Specification Quantities can't be grate than sale line quantity")

    @api.onchange('product_uom', 'product_uom_qty')
    def product_uom_change(self):
        _logger.info("ON CHANGE PRODUCT_UOM_QTY.....")
        if not self.product_uom or not self.product_id:
            self.price_unit = 0.0
            return
        if self.order_id.pricelist_id and self.order_id.partner_id:
            product = self.product_id.with_context(
                lang=self.order_id.partner_id.lang,
                partner=self.order_id.partner_id,
                quantity=self.product_uom_qty,
                date=self.order_id.date_order,
                pricelist=self.order_id.pricelist_id.id,
                uom=self.product_uom.id,
                fiscal_position=self.env.context.get('fiscal_position'),
                grade=self.product_grade.id
            )
            price_unit = self.env['account.tax']._fix_tax_included_price_company(self._get_display_price(product),
                                                                                      product.taxes_id, self.tax_id,
                                                                                      self.company_id)
            _logger.info("PRICE UNIT=%r", price_unit)
            self.price_unit = price_unit

    @api.onchange('product_id', 'price_unit', 'product_uom', 'product_uom_qty', 'tax_id')
    def _onchange_discount(self):
        if not (self.product_id and self.product_uom and
                self.order_id.partner_id and self.order_id.pricelist_id and
                self.order_id.pricelist_id.discount_policy == 'without_discount' and
                self.env.user.has_group('product.group_discount_per_so_line')):
            return

        self.discount = 0.0
        product = self.product_id.with_context(
            lang=self.order_id.partner_id.lang,
            partner=self.order_id.partner_id,
            quantity=self.product_uom_qty,
            date=self.order_id.date_order,
            pricelist=self.order_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        product_context = dict(self.env.context, partner_id=self.order_id.partner_id.id, date=self.order_id.date_order,
                               uom=self.product_uom.id)
        grade = self.product_grade
        price, rule_id = self.order_id.pricelist_id.with_context(product_context).get_product_price_rule(
            self.product_id, self.product_uom_qty or 1.0, self.order_id.partner_id, grade)
        new_list_price, currency = self.with_context(product_context)._get_real_price_currency(product, rule_id,
                                                                                               self.product_uom_qty,
                                                                                               self.product_uom,
                                                                                               self.order_id.pricelist_id.id)

        if new_list_price != 0:
            if self.order_id.pricelist_id.currency_id != currency:
                # we need new_list_price in the same currency as price, which is in the SO's pricelist's currency
                new_list_price = currency._convert(
                    new_list_price, self.order_id.pricelist_id.currency_id,
                    self.order_id.company_id or self.env.company, self.order_id.date_order or fields.Date.today())
            discount = (new_list_price - price) / new_list_price * 100
            if (discount > 0 and new_list_price > 0) or (discount < 0 and new_list_price < 0):
                self.discount = discount

    @api.depends('product_id')
    @api.onchange('product_grade')
    def onchange_grade(self):
        if self.product_id:
            grade_id = self.product_grade.id or 0
            pricelist_obj = self.order_id.pricelist_id
            product_obj = self.product_id.product_tmpl_id
            partner_id = self.order_id.partner_id
            product_price = pricelist_obj.get_product_price(product_obj, 1, partner_id, grade=grade_id)
            self.price_unit = product_price

    def action_show_line_specs(self):
        view = self.env.ref('mobile_device_sale.sale_order_line_specs_form')

        return {
            'name': _('Product Line Specifications'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'sale.order.line',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id
        }

    # @api.model
    # def create(self, vals):
    #     res = super(SaleOrderLine, self).create(vals)
    #     _logger.info("LINE CREATE")
    #     if self.line_specs_ids.ids:
    #         for specs_id in self.line_specs_ids.ids:
    #             specs = self.env['product.line.specs'].search([('id', '=', specs_id)])
    #             specs_filter = specs.create_specs_filter_values()
    #             product_id = self.product_id
    #             company_id = self.env.user.company_id
    #             warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id.id)])
    #             stock_location = warehouse_id.lot_stock_id
    #             all_product_quants = self.env['stock.quant']._gather(product_id, stock_location)
    #             # todo: verify reserved quants
    #             quants = all_product_quants.filtered(lambda q: eval(specs_filter))
    #             specs.write({'available_qty': len(quants)})
    #     return res

    # def write(self, vals):
    #     res = super(SaleOrderLine, self).write(vals)
    #     _logger.info("LINE WRITE")
    #     if self.line_specs_ids.ids:
    #         for specs_id in self.line_specs_ids.ids:
    #             specs = self.env['product.line.specs'].search([('id', '=', specs_id)])
    #             specs_filter = specs.create_specs_filter_values()
    #             product_id = self.product_id
    #             company_id = self.env.user.company_id
    #             warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', company_id.id)])
    #             stock_location = warehouse_id.lot_stock_id
    #             all_product_quants = self.env['stock.quant']._gather(product_id, stock_location)
    #             # todo: verify reserved quants
    #             quants = all_product_quants.filtered(lambda q: eval(specs_filter[1]))
    #             specs.write({'available_qty': len(quants)})
    #     return res

