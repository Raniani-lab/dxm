from odoo.http import request
from odoo import fields, http, SUPERUSER_ID, tools, _
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.main import Website
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv import expression
from odoo.addons.website_sale.controllers.main import WebsiteSale
from werkzeug.exceptions import Forbidden, NotFound
import datetime
import ast
import time
import logging

_logger = logging.getLogger(__name__)


class TableCompute(object):

    def __init__(self):
        self.table = {}

    def _check_place(self, posx, posy, sizex, sizey, ppr):
        res = True
        for y in range(sizey):
            for x in range(sizex):
                if posx + x >= ppr:
                    res = False
                    break
                row = self.table.setdefault(posy + y, {})
                if row.setdefault(posx + x) is not None:
                    res = False
                    break
            for x in range(ppr):
                self.table[posy + y].setdefault(x, None)
        return res

    def process(self, products, ppg=20, ppr=4):
        # Compute products positions on the grid
        minpos = 0
        index = 0
        maxy = 0
        x = 0
        for p in products:
            x = min(max(p.website_size_x, 1), ppr)
            y = min(max(p.website_size_y, 1), ppr)
            if index >= ppg:
                x = y = 1

            pos = minpos
            while not self._check_place(pos % ppr, pos // ppr, x, y, ppr):
                pos += 1
            # if 21st products (index 20) and the last line is full (ppr products in it), break
            # (pos + 1.0) / ppr is the line where the product would be inserted
            # maxy is the number of existing lines
            # + 1.0 is because pos begins at 0, thus pos 20 is actually the 21st block
            # and to force python to not round the division operation
            if index >= ppg and ((pos + 1.0) // ppr) > maxy:
                break

            if x == 1 and y == 1:  # simple heuristic for CPU optimization
                minpos = pos // ppr

            for y2 in range(y):
                for x2 in range(x):
                    self.table[(pos // ppr) + y2][(pos % ppr) + x2] = False
            self.table[pos // ppr][pos % ppr] = {
                'product': p, 'x': x, 'y': y,
                'class': " ".join(x.html_class for x in p.website_style_ids if x.html_class)
            }
            if index <= ppg:
                maxy = max(maxy, y + (pos // ppr))
            index += 1

        # Format table according to HTML needs
        rows = sorted(self.table.items())
        rows = [r[1] for r in rows]
        for col in range(len(rows)):
            cols = sorted(rows[col].items())
            x += len(cols)
            rows[col] = [r[1] for r in cols if r[1]]

        return rows


class WebsiteSale(WebsiteSale):

    def sitemap_shop(env, rule, qs):
        if not qs or qs.lower() in '/shop':
            yield {'loc': '/shop'}

        Category = env['product.public.category']
        dom = sitemap_qs2dom(qs, '/shop/category', Category._rec_name)
        dom += env['website'].get_current_website().website_domain()
        for cat in Category.search(dom):
            loc = '/shop/category/%s' % slug(cat)
            if not qs or qs.lower() in loc:
                yield {'loc': loc}

    def get_product_brands(self, products):
        return products.sudo().mapped('product_brand_id')

    def generate_lot_filter(self, **kwargs):
        operand = ' and '
        specs_filter = ''
        if kwargs['device_grade'] != '0':
            specs_filter = 'l.x_studio_revision_grado.id == %s' % int(kwargs['device_grade'])
        # if kwargs['device_color'] != '0':
        #     if len(specs_filter) > 0:
        #         specs_filter += operand + 'l.x_studio_color.id == %s' % int(kwargs['device_color'])
        #     else:
        #         specs_filter += 'l.x_studio_color.id == %s' % int(kwargs['device_color'])
        # if kwargs['device_network_type'] != '0':
        #     if len(specs_filter) > 0:
        #         specs_filter += operand + 'l.x_studio_red.id == %s' % int(kwargs['device_network_type'])
        #     else:
        #         specs_filter += 'l.x_studio_red.id == %s' % int(kwargs['device_network_type'])
        # if kwargs['device_lang'] != '0':
        #     if len(specs_filter) > 0:
        #         specs_filter += operand + 'l.x_studio_idioma.id == %s' % int(kwargs['device_lang'])
        #     else:
        #         specs_filter += 'l.x_studio_idioma.id == %s' % int(kwargs['device_lang'])
        if kwargs['device_charger'] != '0':
            if len(specs_filter) > 0:
                specs_filter += operand + 'l.x_studio_cargador.id == %s' % int(kwargs['device_charger'])
            else:
                specs_filter += 'l.x_studio_cargador.id == %s' % int(kwargs['device_charger'])
        if kwargs['device_logo'] != '0':
            if len(specs_filter) > 0:
                specs_filter += operand + 'l.x_studio_logo.id == %s' % int(kwargs['device_logo'])
            else:
                specs_filter += 'l.x_studio_logo.id == %s' % int(kwargs['device_logo'])
        if kwargs['device_lock_status'] != '0':
            if len(specs_filter) > 0:
                specs_filter += operand + 'l.x_studio_bloqueo.id == %s' % int(kwargs['device_lock_status'])
            else:
                specs_filter += 'l.x_studio_bloqueo.id == %s' % int(kwargs['device_lock_status'])
        if kwargs['device_applications'] != '0':
            if len(specs_filter) > 0:
                specs_filter += operand + 'l.x_studio_aplicaciones.id == %s' % int(kwargs['device_applications'])
            else:
                specs_filter += 'l.x_studio_aplicaciones.id == %s' % int(kwargs['device_applications'])
        return specs_filter

    def filter_product_by_specs(self, products, **kwargs):
        product_variants = products.mapped('product_variant_id')
        lots = request.env['stock.production.lot'].sudo().search([('product_id', 'in', product_variants.ids)])
        lots = lots.filtered(lambda l: l.product_qty > 0)
        _logger.info("ALL LOTS: %r", lots)
        lot_filter = self.generate_lot_filter(**kwargs)
        _logger.info("SPEC FILTER: %r", lot_filter)
        if len(lot_filter) > 0:
            _logger.info("FILTERING PRODUCTS BY SPECS.....")
            lots_filtered = lots.filtered(lambda l: eval(lot_filter))
            _logger.info("LOTS FILTERED: %r", lots_filtered)
            product_ids = lots_filtered.mapped('product_id').mapped('product_tmpl_id').ids
            _logger.info("PRODUCTS IDS: %r", product_ids)
            return products.filtered(lambda p: p.id in product_ids)
        else:
            return products

    def check_products_stock(self, products):
        products_recordset = products
        for product in products:
            product_qty = self.get_product_quants(product.product_variant_id)
            if product_qty <= 0:
                if product.inventory_availability in ['always', 'threshold']:
                    products_recordset -= product

        return products_recordset

    @http.route([
        '''/shop''',
        '''/shop/page/<int:page>''',
        '''/shop/category/<model("product.public.category"):category>''',
        '''/shop/category/<model("product.public.category"):category>/page/<int:page>'''
    ], type='http', auth="public", website=True, sitemap=sitemap_shop)
    def shop(self, page=0, category=None, search='', ppg=False, **post):
        _logger.info("ON SHOP INHERITED CONTROLLER")
        _logger.info("POST ARGS: %r", post)
        active_filter = False
        website_for_sell = request.env['ir.config_parameter'].sudo().get_param('mobile_device_sale.website_for_sell')
        current_website = request.env['website'].get_current_website().id
        _logger.info("CURRENT WEBSITE: %r", current_website)
        if request.env.user.id == 4 and int(website_for_sell) == current_website:
            _logger.info("REDIRECT TO LOGIN PAGE")
            return request.redirect('/web/login?redirect=/shop')
        if int(website_for_sell) == current_website:
            mobile_sale = True
            default_specs = {
                # 'device_network_type': '0',
                # 'device_lang': '0',
                'device_charger': '0',
                'device_logo': '0',
                'device_lock_status': '0',
                'device_applications': '0',
                'device_model': '0',
                'device_grade': '0',
                'device_color': '0',
                'device_capacity': '0'
            }
            active_specs = False
            if len(post):
                specs_post = post
                if 'fw' in post.keys() and len(post) == 1:
                    specs_post.update(default_specs)
                for key in post:
                    if post[key] != '0' and key not in ['fw']:
                        active_filter = True
                        if key in [
                            # 'device_network_type',
                            # 'device_lang',
                            'device_charger',
                            'device_logo',
                            'device_lock_status',
                            'device_applications',
                            'device_grade',
                            'device_color'
                        ]:
                            active_specs = True
            else:
                specs_post = default_specs
            brand_list = request.httprequest.args.getlist('brand')
            if brand_list:
                brand_set = [int(x) for x in brand_list]
            else:
                brand_set = []
            add_qty = int(post.get('add_qty', 1))
            Category = request.env['product.public.category']
            if category:
                category = Category.search([('id', '=', int(category))], limit=1)
                if not category or not category.can_access_from_current_website():
                    raise NotFound()
            else:
                category = Category

            if ppg:
                try:
                    ppg = int(ppg)
                    post['ppg'] = ppg
                except ValueError:
                    ppg = False
            if not ppg:
                ppg = request.env['website'].get_current_website().shop_ppg or 20

            # ppr = request.env['website'].get_current_website().shop_ppr or 4
            ppr = 2
            _logger.info("CURRENT WEBSITE %r", request.env['website'].get_current_website())
            attrib_list = request.httprequest.args.getlist('attrib')
            _logger.info("ATTRIB LIST: %r", attrib_list)
            attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
            attributes_ids = {v[0] for v in attrib_values}
            attrib_set = {v[1] for v in attrib_values}

            domain = self._get_search_domain(search, category, attrib_values)
            product_models = []

            domain += [('stock_qty', '>', 0)]

            if brand_list:
                domain += [('product_brand_id', 'in', brand_set)]
                product_models = request.env['product.template'].search([
                    ('product_brand_id', 'in', brand_set),
                    ('stock_qty', '!=', 0)]).mapped('x_studio_modelo')

            if specs_post['device_model'] != '0':
                domain += [('x_studio_modelo', '=', specs_post['device_model'])]

            if specs_post['device_capacity'] != '0':
                domain += [('x_studio_capacidad_de_almacenamiento', '=', int(specs_post['device_capacity']))]

            _logger.info("DOMAIN: %r", domain)

            keep = QueryURL('/shop', category=category and int(category), search=search, attrib=attrib_list,
                            order=post.get('order'))

            pricelist_context, pricelist = self._get_pricelist_context()

            request.context = dict(request.context, pricelist=pricelist.id, partner=request.env.user.partner_id)

            url = "/shop"
            if search:
                post["search"] = search
            if attrib_list:
                post['attrib'] = attrib_list

            Product = request.env['product.template'].with_context(bin_size=True)

            all_products_with_stock = Product.search([('website_published', '=', True),
                                                      ('website_id', '=', int(website_for_sell)),
                                                      ('stock_qty', '>', 0)])  # before virtual_available
            all_products_with_stock = self.check_products_stock(all_products_with_stock)
            product_brands = self.get_product_brands(all_products_with_stock)
            search_product = Product.search(domain)
            website_domain = request.website.website_domain()
            categs_domain = [('parent_id', '=', False)] + website_domain
            if search:
                search_categories = Category.search(
                    [('product_tmpl_ids', 'in', search_product.ids)] + website_domain).parents_and_self
                categs_domain.append(('id', 'in', search_categories.ids))
            else:
                search_categories = Category
            categs = Category.search(categs_domain)

            if category:
                url = "/shop/category/%s" % slug(category)

            product_count = len(search_product)
            pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)
            products = Product.search(domain, limit=ppg, offset=pager['offset'], order=self._get_search_order(post))

            ProductAttribute = request.env['product.attribute']
            if products:
                # get all products without limit
                _logger.info("GETTING ATTRIBUTES WITH PRODUCT LIST: %r", search_product.ids)
                attributes = ProductAttribute.search([('product_tmpl_ids', 'in', search_product.ids)])
            else:
                attributes = ProductAttribute.browse(attributes_ids)

            layout_mode = request.session.get('website_sale_shop_layout_mode')
            if not layout_mode:
                if request.website.viewref('website_sale.products_list_view').active:
                    layout_mode = 'list'
                else:
                    layout_mode = 'grid'

            grades = request.env['x_grado'].sudo().search([('x_studio_website_published', '=', True)])
            device_colors = request.env['x_color'].sudo().search([])
            device_lock_status = request.env['x_bloqueo'].sudo().search([])
            device_logo = request.env['x_logo'].sudo().search([])
            device_charger = request.env['x_cargador'].sudo().search([])
            # device_network_type = request.env['x_red'].sudo().search([])
            # device_lang = request.env['x_idioma_terminal'].sudo().search([])
            device_applications = request.env['x_terminal_aplicaciones'].sudo().search([])

            products = self.check_products_stock(products)
            device_capacity = products.sudo().mapped('x_studio_capacidad_de_almacenamiento')
            _logger.info("CAPACITIES: %r", device_capacity)
            if not brand_list:
                product_models = products.mapped('x_studio_modelo')
            products = self.filter_product_by_specs(products, **specs_post)

            # update product_count
            product_count = len(products)
            # update pager
            pager = request.website.pager(url=url, total=product_count, page=page, step=ppg, scope=7, url_args=post)

            values = {
                'search': search,
                'category': category,
                'attrib_values': attrib_values,
                'attrib_set': attrib_set,
                'pager': pager,
                'pricelist': pricelist,
                'add_qty': add_qty,
                'products': products,
                'search_count': product_count,  # common for all searchbox
                'bins': TableCompute().process(products, ppg, ppr),
                'ppg': ppg,
                'ppr': ppr,
                'categories': categs,
                'attributes': attributes,
                'keep': keep,
                'search_categories_ids': search_categories.ids,
                'layout_mode': layout_mode,
                'grades': grades,
                'device_colors': device_colors,
                'website_for_sell': int(website_for_sell),
                'device_lock_status': device_lock_status,
                'device_logo': device_logo,
                'device_charger': device_charger,
                # 'device_network_type': device_network_type,
                # 'device_lang': device_lang,
                'device_applications': device_applications,
                'specs_post': specs_post,
                'product_models': product_models,
                'mobile_sale': mobile_sale,
                'product_brands': product_brands,
                'device_capacity': device_capacity,
                'brand_set': brand_set,
                'active_filter': active_filter,
                'active_specs': active_specs
            }
            if category:
                values['main_object'] = category
            return request.render("website_sale.products", values)
        else:
            return super(WebsiteSale, self).shop(page=page, category=category, search=search, ppg=ppg, **post)

    @http.route(['''/shop/get_product_info'''], type='json', auth="public", website=True)
    def get_product_info(self, product_id=None, grade=0, color=0, lock_status=0, logo=0, charger=0,
                         network_type=0, lang=0, applications=0):
        _logger.info("GET INFO PRODUCT ID: %r", product_id)
        product_obj = request.env['product.product'].browse(int(product_id))
        pricelist = self._get_pricelist_context()[1].id
        pricelist_obj = request.env['product.pricelist'].browse(int(pricelist))
        partner_id = request.env.user.partner_id
        partner_price_list = partner_id.property_product_pricelist
        if partner_price_list:
            pricelist_obj = partner_price_list
        today = datetime.date.today()

        product_quants = self.get_product_quants(product_obj.product_variant_id,
                                                 grade=int(grade),
                                                 color=int(color),
                                                 lock_status=int(lock_status),
                                                 logo=int(logo),
                                                 charger=int(charger),
                                                 network_type=int(network_type),
                                                 lang=int(lang),
                                                 applications=int(applications))

        sale_order = request.website.sale_get_order()
        cart_qty = 0
        if sale_order:
            _logger.info("SALE ORDER IN GET PRODUCT INFO: %r", sale_order)
            cart_qty = self.get_quant_in_cart(sale_order, product_obj, grade=grade, color=color,
                                              lock_status=lock_status, logo=logo, charger=charger,
                                              applications=applications)
                                                # network_type=network_type, lang=0

        quant_colors = self.get_quant_colors(product_obj.product_variant_id, grade=grade)
        result = {}
        color_data = []
        for color_id in quant_colors:
            color_quantity = self.get_product_quants(product_obj.product_variant_id,
                                                     grade=int(grade),
                                                     color=color_id.id,
                                                     lock_status=int(lock_status),
                                                     logo=int(logo),
                                                     charger=int(charger),
                                                     applications=int(applications))
            color_data.append((color_id.id, color_id.x_color_index, color_id.x_name, color_quantity))
        result.update({'color_data': color_data})

        if product_quants < cart_qty:
            cart_qty = product_quants

        return {'product_id': product_id, 'product_quants': product_quants, 'cart_qty': cart_qty, 'color': result}

    def normalize_filter_specs_names(self, **kwargs):

        _logger.info("KWARGS: %r", kwargs)
        if 'fw' in kwargs.keys():
            kwargs.pop('fw')
        if 'device_model' in kwargs.keys():
            kwargs.pop('device_model')
        if 'device_capacity' in kwargs.keys():
            kwargs.pop('device_capacity')
        if 'brand' in kwargs.keys():
            kwargs.pop('brand')
        if 'search' in kwargs.keys():
            kwargs.pop('search')
        normalized_specs_filter = {x.split('_')[1] if len(x.split('_')) == 2 else '_'.join([x.split('_')[1], x.split('_')[2]]): int(kwargs[x]) for x in kwargs}
        _logger.info("NORMALIZED SPECS FILTER: %r", normalized_specs_filter)
        return normalized_specs_filter

    @http.route(['''/shop/get_product_info/detail'''], type='json', auth="public", website=True)
    def get_product_info_detail(self, product_id, grade=None, specs=None):
        _logger.info("GET DETAIL PRODUCT ID: %r", product_id)
        if specs:
            specs_dict = ast.literal_eval(specs)
        else:
            specs_dict = {}
        specs_filter = self.normalize_filter_specs_names(**specs_dict)

        product_obj = request.env['product.product'].browse(int(product_id))
        pricelist = self._get_pricelist_context()[1].id
        pricelist_obj = request.env['product.pricelist'].browse(int(pricelist))
        partner_id = request.env.user.partner_id
        partner_price_list = partner_id.property_product_pricelist
        if partner_price_list:
            pricelist_obj = partner_price_list
        today = datetime.date.today()

        result = {}

        if not grade:
            specs_quant = self.get_product_quants(product_obj.product_variant_id, **specs_filter)
            grades = request.env['x_grado'].sudo().search([('x_studio_website_published', '=', True)])  # ('x_studio_is_grade_test', '=', True)
            for grade in grades:
                product_price = pricelist_obj.get_product_price(product_obj, 1, partner_id, grade=grade.id, date=today)
                product_quants = self.get_product_quants(product_obj.product_variant_id, grade=grade.id, **specs_filter)

                _logger.info("PRODUCT QUANTS: %r", product_quants)
                result.update({grade.id: [product_price, product_quants]})

            return {'product_id': product_id, 'specs_quant': specs_quant, 'product_data': result}

        else:
            # Check if there are quantities in cart
            sale_order = request.website.sale_get_order()
            specs_filter.update({'grade': int(grade)})
            if sale_order:
                _logger.info("SALE ORDER IN GET PRODUCT INFO: %r", sale_order)
                cart_qty = self.get_quant_in_cart(sale_order, product_obj, **specs_filter)
            specs_filter.pop('grade')
            result.update({'product_id': product_obj.product_variant_id.id})
            quant_colors = self.get_quant_colors(product_obj.product_variant_id, grade=grade)
            grade_quant = self.get_product_quants(product_obj.product_variant_id, grade=grade, **specs_filter)
            color_data = []
            for color in quant_colors:
                color_quantity = self.get_product_quants(product_obj.product_variant_id,
                                                         grade=int(grade),
                                                         color=color.id)
                color_data.append((color.id, color.x_color_index, color.x_name, color_quantity))
            result.update({'color_data': color_data})
            if grade_quant < cart_qty:
                cart_qty = grade_quant
            return {'product_id': product_id, 'grade_quant': grade_quant, 'cart_qty': cart_qty, 'color': result}

    @http.route(['''/shop/get_product_info/grid'''], type='json', auth="public", website=True)
    def get_product_info_grid(self, product_id=None, grade=None, specs=None):
        _logger.info("GET INFO PRODUCT ID: %r", product_id)
        _logger.info("SPECS FILTER VALUES: %r", specs)
        if specs:
            specs_dict = ast.literal_eval(specs)
        else:
            specs_dict = {}
        specs_filter = self.normalize_filter_specs_names(**specs_dict)

        product_obj = request.env['product.product'].browse(int(product_id))
        pricelist = self._get_pricelist_context()[1].id
        pricelist_obj = request.env['product.pricelist'].browse(int(pricelist))
        partner_id = request.env.user.partner_id
        partner_price_list = partner_id.property_product_pricelist
        if partner_price_list:
            pricelist_obj = partner_price_list
        today = datetime.date.today()

        result = {}
        cart_qty = 0

        # get product price and quants by grade in the grid.
        if not grade:

            specs_quant = self.get_product_quants(product_obj.product_variant_id, **specs_filter)
            specs_filter.pop('grade')
            grades = request.env['x_grado'].sudo().search([('x_studio_website_published', '=', True)])  # ('x_studio_is_grade_test', '=', True)
            for grade in grades:
                product_price = pricelist_obj.get_product_price(product_obj, 1, partner_id, grade=grade.id, date=today)
                product_quants = self.get_product_quants(product_obj.product_variant_id, grade=grade.id, **specs_filter)

                _logger.info("PRODUCT QUANTS: %r", product_quants)
                result.update({grade.id: [product_price, product_quants]})

            return {'product_id': product_id, 'specs_quant': specs_quant, 'product_data': result}
        else:
            # Check if there are quantities in cart
            sale_order = request.website.sale_get_order()
            specs_filter.update({'grade': int(grade)})
            if sale_order:
                _logger.info("SALE ORDER IN GET PRODUCT INFO: %r", sale_order)
                cart_qty = self.get_quant_in_cart(sale_order, product_obj, **specs_filter)
            specs_filter.pop('grade')
            result.update({'product_id': product_obj.product_variant_id.id})
            quant_colors = self.get_quant_colors(product_obj.product_variant_id, grade=grade)
            grade_quant = self.get_product_quants(product_obj.product_variant_id, grade=grade, **specs_filter)
            color_data = []
            if 'color' in specs_filter.keys():
                specs_filter.pop('color')
            for color in quant_colors:
                color_quantity = self.get_product_quants(product_obj.product_variant_id,
                                                         grade=int(grade),
                                                         color=color.id, **specs_filter)
                color_data.append((color.id, color.x_color_index, color.x_name, color_quantity))
            result.update({'color_data': color_data})
            if grade_quant < cart_qty:
                cart_qty = grade_quant
            return {'product_id': product_id, 'grade_quant': grade_quant, 'cart_qty': cart_qty, 'color': result}

    def get_quant_in_cart(self, order, product, **kwargs):
        _logger.info("ANALYZING CART QTY.....")
        _logger.info("KWARGS: %r", kwargs)
        cart_qty = 0
        available_for_sale = 0
        for line in order.order_line:
            if line.product_id.id == product.id and line.product_grade.id == int(kwargs.get('grade')):
                _logger.info("FINDING PRODUCT SPECS IN LINE: %s, PRODUCT: %s" % (line.id, line.product_id.id))
                # Find if there is a line with no more specs than grade
                line_grade = line.match_product_specs(grade=int(kwargs.get('grade')))
                # get total grade quants
                grade_quants = self.get_product_quants(product, grade=int(kwargs.get('grade')))
                _logger.info("GRADE QUANTS: %r", grade_quants)
                _logger.info("LINE GRADE MATCH: %r", line_grade)
                line_match = line.match_product_partial_specs(**kwargs)  # grade=int(kwargs.get('grade'))
                if line_grade:
                    line_match = line_match - line_grade
                if line_match:
                    _logger.info("LINE MATCH EXIST: %r", line_match)
                    if line_grade:
                        cart_qty = sum(line_match.mapped('quantity')) + sum(line_grade.mapped('quantity'))
                    else:
                        cart_qty = sum(line_match.mapped('quantity'))
                else:
                    available_for_sale = self.get_product_quants(product, **kwargs)
                    _logger.info("AVAILABLE FOR SALE: %r", available_for_sale)
                if line_grade and not line_match:
                    total_grade_in_cart = sum(line_grade.mapped('quantity'))
                    _logger.info("TOTAL GRADE IN CART: %r", total_grade_in_cart)
                    if total_grade_in_cart == grade_quants:
                        _logger.info("TOTAL GRADE IN CART == GRADE QUANTS")
                        cart_qty = grade_quants
                    elif total_grade_in_cart < grade_quants:
                        cart_qty = available_for_sale - (available_for_sale - total_grade_in_cart)
                    else:
                        _logger.info("TOTAL GRADE IN CART != GRADE QUANTS")
                        cart_qty = available_for_sale - (grade_quants - total_grade_in_cart)
                        _logger.info("CART_QTY AFTER REST: %r", cart_qty)
                    if cart_qty < 0:
                        _logger.info("CART QTY < 0")
                        cart_qty = 0
        _logger.info("CART QUANTS: %r", cart_qty)

        return cart_qty

    def get_quant_colors(self, product_id, grade):
        default_location_id = request.env['ir.config_parameter'].sudo().get_param(
            'mobile_device_sale.mobile_stock_location')
        stock_location = request.env['stock.location'].browse(int(default_location_id))
        all_product_quants = request.env['stock.quant'].sudo()._gather(product_id, stock_location)
        lot_filter = 'q.lot_id.x_studio_revision_grado.id == %s' % grade
        quants_filtered = all_product_quants.filtered(lambda q: eval(lot_filter))

        return quants_filtered.mapped('lot_id').mapped('x_studio_color')

    def get_product_quants(self, product_id, **kwargs):
        default_location_id = request.env['ir.config_parameter'].sudo().get_param(
            'mobile_device_sale.mobile_stock_location')
        stock_location = request.env['stock.location'].sudo().browse(int(default_location_id))
        _logger.info("PRODUCT_ID: %s, LOCATION: %s" % (product_id, stock_location))
        all_product_quants = request.env['stock.quant'].sudo()._gather(product_id, stock_location)
        _logger.info("ALL QUANTS: %r", all_product_quants)
        # reserved_filter = 'q.reserved_quantity == 1'
        lot_filter = 'q.reserved_quantity == 0 and q.quantity > 0'
        operand = " and "
        # grade
        if 'grade' in kwargs.keys():
            if kwargs.get('grade') != 0:
                lot_filter += operand + 'q.lot_id.x_studio_revision_grado.id == %s' % kwargs.get('grade')
        # Color
        if 'color' in kwargs.keys():
            if kwargs.get('color') != 0:
                lot_filter += operand + "q.lot_id.x_studio_color.id == %s" % kwargs.get('color')
        # # Lock Status
        if 'lock_status' in kwargs.keys():
            if len(lot_filter) > 0 and kwargs.get('lock_status') != 0:
                lot_filter += operand + "q.lot_id.x_studio_bloqueo.id == %s" % kwargs.get('lock_status')
            elif kwargs.get('lock_status') != 0:
                lot_filter = "q.lot_id.x_studio_bloqueo.id == %s" % kwargs.get('lock_status')

        # # Logo
        if 'logo' in kwargs.keys():
            if len(lot_filter) > 0 and kwargs.get('logo') != 0:
                lot_filter += operand + "q.lot_id.x_studio_logo.id == %s" % kwargs.get('logo')
            elif kwargs.get('logo') != 0:
                lot_filter = "q.lot_id.x_studio_logo.id == %s" % kwargs.get('logo')

        # # Charger
        if 'charger' in kwargs.keys():
            if len(lot_filter) > 0 and kwargs.get('charger') != 0:
                lot_filter += operand + "q.lot_id.x_studio_cargador.id == %s" % kwargs.get('charger')
            elif kwargs.get('charger') != 0:
                lot_filter = "q.lot_id.x_studio_cargador.id == %s" % kwargs.get('charger')

        # # Network Type
        if 'network_type' in kwargs.keys():
            if len(lot_filter) > 0 and kwargs.get('network_type') != 0:
                lot_filter += operand + "q.lot_id.x_studio_red.id == %s" % kwargs.get('network_type')
            elif kwargs.get('network_type') != 0:
                lot_filter = "q.lot_id.x_studio_red.id == %s" % kwargs.get('network_type')

        # # Lang
        if 'lang' in kwargs.keys():
            if len(lot_filter) > 0 and kwargs.get('lang') != 0:
                lot_filter += operand + "q.lot_id.x_studio_idioma.id == %s" % kwargs.get('lang')
            elif kwargs.get('lang') != 0:
                lot_filter = "q.lot_id.x_studio_idioma.id == %s" % kwargs.get('lang')

        # # Applications
        if 'applications' in kwargs.keys():
            if len(lot_filter) > 0 and kwargs.get('applications') != 0:
                lot_filter += operand + "q.lot_id.x_studio_aplicaciones.id == %s" % kwargs.get('applications')
            elif kwargs.get('applications') != 0:
                lot_filter = "q.lot_id.x_studio_aplicaciones.id == %s" % kwargs.get('applications')

        _logger.info("LOT FILTER: %r", lot_filter)
        reserved_quants = 0
        if len(lot_filter) > 0:
            # reserved_quants = len(all_product_quants.filtered(lambda  q: eval(reserved_filter)))
            quants_filtered = all_product_quants.filtered(lambda q: eval(lot_filter))
            _logger.info("QUANTS FILTERED: %r", quants_filtered)
        else:
            quants_filtered = all_product_quants

        return len(quants_filtered)

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True, **kwargs):
        """This route is called when changing quantity from the cart or adding
        a product from the wishlist."""
        _logger.info("PRODUCT ID ON CART UPDATE JSON: %r", product_id)
        order = request.website.sale_get_order(force_create=1, **kwargs)
        if order.state != 'draft':
            request.website.sale_reset()
            return {}

        # website_for_sell = request.env['ir.config_parameter'].sudo().get_param('mobile_device_sale.website_for_sell')
        # current_website = request.env['website'].get_current_website().id
        # if int(website_for_sell) != current_website:
        #     product = request.env['product.product'].browse(product_id)
        #     product_qty = product.qty_available
        #     cart_qty = order.cart_quantity
        #     if product_qty <= cart_qty or set_qty > (product_qty - cart_qty):
        #         raise ValidationError("No more products in stock")

        value = order._cart_update(product_id=product_id, line_id=line_id, add_qty=add_qty, set_qty=set_qty, **kwargs)


        if not order.cart_quantity:
            request.website.sale_reset()
            return value

        order = request.website.sale_get_order(**kwargs)
        value['cart_quantity'] = order.cart_quantity

        if not display:
            return value

        value['website_sale.cart_lines'] = request.env['ir.ui.view'].render_template("website_sale.cart_lines", {
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': order._cart_accessories()
        })
        value['website_sale.short_cart_summary'] = request.env['ir.ui.view'].render_template(
            "website_sale.short_cart_summary", {
                'website_sale_order': order,
            })
        _logger.info("VALUE AT _CART_UPDATE_JSON: %r", value)
        order.onchange_order_line()
        return value

    def _prepare_product_values(self, product, category, search, **kwargs):
        website_for_sell = request.env['ir.config_parameter'].sudo().get_param('mobile_device_sale.website_for_sell')
        current_website = request.env['website'].get_current_website().id
        if int(website_for_sell) == current_website:
            mobile_sale = True
        else:
            mobile_sale = False

        add_qty = int(kwargs.get('add_qty', 1))

        product_context = dict(request.env.context, quantity=add_qty,
                               active_id=product.id,
                               partner=request.env.user.partner_id)
        ProductCategory = request.env['product.public.category']

        if category:
            category = ProductCategory.browse(int(category)).exists()

        attrib_list = request.httprequest.args.getlist('attrib')
        attrib_values = [[int(x) for x in v.split("-")] for v in attrib_list if v]
        attrib_set = {v[1] for v in attrib_values}

        keep = QueryURL('/shop', category=category and category.id, search=search, attrib=attrib_list)

        categs = ProductCategory.search([('parent_id', '=', False)])

        pricelist = request.website.get_current_pricelist()

        if not product_context.get('pricelist'):
            product_context['pricelist'] = pricelist.id
            product = product.with_context(product_context)

        # Needed to trigger the recently viewed product rpc
        view_track = request.website.viewref("website_sale.product").track

        # get quants to filter available specs
        default_location_id = request.env['ir.config_parameter'].sudo().get_param('mobile_device_sale.mobile_stock_location')
        stock_location = request.env['stock.location'].sudo().browse(int(default_location_id))
        all_product_quants = request.env['stock.quant'].sudo()._gather(product.product_variant_id, stock_location)
        all_product_quants = all_product_quants.filtered(lambda q: q.reserved_quantity == 0 and q.quantity > 0)
        product_lots = all_product_quants.mapped('lot_id')
        if int(website_for_sell) == current_website:
            grades = request.env['x_grado'].search([('x_studio_website_published', '=', True)])
            # device_colors = request.env['x_color'].search([])
            device_colors = product_lots.mapped('x_studio_color')
            # device_lock_status = request.env['x_bloqueo'].search([])
            device_lock_status = product_lots.mapped('x_studio_bloqueo')
            # device_logo = request.env['x_logo'].search([])
            device_logo = product_lots.mapped('x_studio_logo')
            # device_charger = request.env['x_cargador'].search([])
            device_charger = product_lots.mapped('x_studio_cargador')
            # device_network_type = request.env['x_red'].search([])
            device_network_type = product_lots.mapped('x_studio_red')
            # device_lang = request.env['x_idioma_terminal'].search([])
            device_lang = product_lots.mapped('x_studio_idioma')
            # device_applications = request.env['x_terminal_aplicaciones'].search([])
            device_applications = product_lots.mapped('x_studio_aplicaciones')
        else:
            grades, device_colors, device_lock_status, device_lock_status, device_logo, \
            device_charger, device_network_type, device_lang, device_applications = [False for i in range(9)]


        _logger.info("LOCK STATUS ELEMENTS: %r", device_lock_status)
        return {
            'search': search,
            'category': category,
            'pricelist': pricelist,
            'attrib_values': attrib_values,
            'attrib_set': attrib_set,
            'keep': keep,
            'categories': categs,
            'main_object': product,
            'product': product,
            'add_qty': add_qty,
            'view_track': view_track,
            'grades': grades,
            'device_colors': device_colors,
            'device_lock_status': device_lock_status,
            'device_logo': device_logo,
            'device_charger': device_charger,
            'device_network_type': device_network_type,
            'device_lang': device_lang,
            'device_applications': device_applications,
            'mobile_sale': mobile_sale
        }

    @http.route(['/shop/cart/delete_specs'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_specs(self, specs_id, **kwargs):
        """This route is called when delete sale order line specifications."""
        _logger.info("!!!!!DELETING SPECS ID: %r", specs_id)
        specs_obj = request.env['product.line.specs'].sudo().search([('id', '=', int(specs_id))])
        remain_order_lines = 0
        canon_info = {}
        if specs_obj:
            line_obj = specs_obj.sale_order_line_id
            sale_obj = line_obj.order_id
            new_line_qty = line_obj.product_uom_qty - specs_obj.quantity
            specs_obj.unlink()
            if new_line_qty > 0:
                line_obj.write({'product_uom_qty': new_line_qty})
            else:
                line_obj.unlink()
            remain_order_lines = len(sale_obj.order_line.filtered(lambda l: not l.is_digital_canon))
            sale_obj.onchange_order_line()
            canon_info = sale_obj.get_canon_info()
        result = {
            'remain_lines': remain_order_lines,
            'success': 'true',
            'canon_info': canon_info
        }
        return result

    @http.route(['''/shop/cart/update_price_offered'''], type='json', auth="public", website=True)
    def set_order_line_price_offered(self, line_id=None, offer=None):
        _logger.info("SET PRICE OFFERED FOR LINE ID: %r", line_id)
        result = 'done'
        partner_id = request.env.user.partner_id
        order_line = request.env['sale.order.line'].sudo().search([('id', '=', int(line_id))])
        order = order_line.order_id
        # set partner as follower in this order if not following
        if partner_id.id not in order.message_follower_ids.mapped('partner_id').ids:
            order.message_subscribe(partner_ids=partner_id.ids)
        try:
            if offer:
                order_line.write({'price_offered': float(offer)})
            elif order_line.price_offered:
                order_line.write({'price_offered': 0.0})
            msg_body = "<p>New price offer from %s for product %s grade %s.<br/> Price offered: %s</p>" % (
                partner_id.name,
                order_line.product_id.name,
                order_line.product_grade.x_name,
                float(offer))
            msg_values = {'body': msg_body, 'model': order._name, 'res_id': order.id,
                          'message_type': 'comment', 'author_id': 2}
            request.env['mail.message'].sudo().create(msg_values)

        except Exception as e:
            _logger.info("ERROR PROCESSING OFFER. ERROR: %r", e)
            result = 'error'
        return {'response': result}

    @http.route(['''/shop/get_mobile_device_sell_website'''], type='json', auth="public", website=True)
    def get_sell_website_id(self):
        website_for_sell = request.env['ir.config_parameter'].sudo().get_param('mobile_device_sale.website_for_sell')
        return {'website_mobile_sell': int(website_for_sell)}

    @http.route(['/shop/cart'], type='http', auth="public", website=True, sitemap=False)
    def cart(self, access_token=None, revive='', **post):
        website_for_sell = request.env['ir.config_parameter'].sudo().get_param('mobile_device_sale.website_for_sell')
        current_website = request.env['website'].get_current_website().id
        if int(website_for_sell) == current_website:
            mobile_sale = True
        else:
            mobile_sale = False
        order = request.website.sale_get_order()
        _logger.info("ORDER FOR THIS CART: %r", order)
        if order and order.state != 'draft':
            request.session['sale_order_id'] = None
            order = request.website.sale_get_order()
        values = {}
        if access_token:
            abandoned_order = request.env['sale.order'].sudo().search([('access_token', '=', access_token)], limit=1)
            if not abandoned_order:  # wrong token (or SO has been deleted)
                raise NotFound()
            if abandoned_order.state != 'draft':  # abandoned cart already finished
                values.update({'abandoned_proceed': True})
            elif revive == 'squash' or (revive == 'merge' and not request.session.get(
                    'sale_order_id')):  # restore old cart or merge with unexistant
                request.session['sale_order_id'] = abandoned_order.id
                return request.redirect('/shop/cart')
            elif revive == 'merge':
                abandoned_order.order_line.write({'order_id': request.session['sale_order_id']})
                abandoned_order.action_cancel()
            elif abandoned_order.id != request.session.get(
                    'sale_order_id'):  # abandoned cart found, user have to choose what to do
                values.update({'access_token': abandoned_order.access_token})

        values.update({
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': [],
            'mobile_sale': mobile_sale
        })
        if order:
            order.order_line.filtered(lambda l: not l.product_id.active).unlink()
            _order = order
            if not request.env.context.get('pricelist'):
                _order = order.with_context(pricelist=order.pricelist_id.id)
            values['suggested_products'] = _order._cart_accessories()

        if post.get('type') == 'popover':
            # force no-cache so IE11 doesn't cache this XHR
            return request.render("website_sale.cart_popover", values, headers={'Cache-Control': 'no-cache'})

        return request.render("website_sale.cart", values)

    @http.route(['/shop/payment'], type='http', auth="public", website=True, sitemap=False)
    def payment(self, **post):
        """ Payment step. This page proposes several payment means based on available
        payment.acquirer. State at this point :

         - a draft sales order with lines; otherwise, clean context / session and
           back to the shop
         - no transaction in context / session, or only a draft one, if the customer
           did go to a payment.acquirer website but closed the tab without
           paying / canceling
        """
        order = request.website.sale_get_order()
        redirection = self.checkout_redirection(order)
        if redirection:
            return redirection

        render_values = self._get_shop_payment_values(order, **post)
        render_values['only_services'] = order and order.only_services or False
        # Negotiation Process Check.
        order_to_negotiate_price = sum(order.order_line.mapped('price_offered'))
        _logger.info("TO NEGOTIATE: %r", order_to_negotiate_price)
        get_param = request.env['ir.config_parameter'].sudo().get_param
        payment_method_id = get_param('mobile_device_sale.payment_method_to_negotiate_price')
        payment_method = request.env['payment.acquirer'].browse(int(payment_method_id))
        if payment_method and order_to_negotiate_price > 0:
            render_values['acquirers'] = payment_method
        elif payment_method:
            render_values['acquirers'] = [x for x in render_values['acquirers'] if x != payment_method]

        if render_values['errors']:
            render_values.pop('acquirers', '')
            render_values.pop('tokens', '')

        _logger.info("RENDER VALUES: %r", render_values)
        return request.render("website_sale.payment", render_values)

    @http.route('/shop/payment/validate', type='http', auth="public", website=True, sitemap=False)
    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """

        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)
            assert tx in order.transaction_ids()
        elif order:
            tx = order.get_portal_last_transaction()
        else:
            tx = None

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')
        if order and not order.amount_total and not tx:
            order.with_context(send_email=True).action_confirm()
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx and tx.state == 'draft':
            return request.redirect('/shop')
        # Confirm order if not negotiate price and is transaction
        get_param = request.env['ir.config_parameter'].sudo().get_param
        negotiation_acquirer_id = int(get_param('mobile_device_sale.payment_method_to_negotiate_price'))
        if tx.acquirer_id.provider == 'transfer' and tx.acquirer_id.id != negotiation_acquirer_id:
            order.with_context(send_email=True).action_confirm()

        PaymentProcessing.remove_payment_transaction(tx)

        return request.redirect('/shop/confirmation')

    @http.route(['''/shop/get_product_variant_quant_info'''], type='json', auth="public", website=True)
    def get_product_variant_quant_info(self, product_template_id=None):
        get_param = request.env['ir.config_parameter'].sudo().get_param
        location_id = int(get_param('mobile_device_sale.standard_stock_location'))
        location = request.env['stock.location'].sudo().browse(location_id)
        product_obj = request.env['product.template'].sudo().browse(int(product_template_id))
        return self.get_attribute_quants(product_obj, location)

    def get_attribute_quants(self, product_template_obj, location):
        att_qty_resume = {}  # {id: qty, id: qty}
        for att_value in product_template_obj.valid_product_template_attribute_line_ids.product_template_value_ids:
            pq = 0
            for i in att_value.ptav_product_variant_ids:
                pq += sum(request.env['stock.quant'].sudo()._gather(i, location).mapped('quantity'))
            att_qty_resume.update({att_value.id: pq})
        return att_qty_resume
