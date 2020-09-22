from odoo import models, fields, api
import logging
import base64
import tempfile
from odoo.osv import expression

_logger = logging.getLogger(__name__)

try:
    import xlsxwriter
except ImportError:
    _logger.warning("Cannot import xlsxwriter")
    xlsxwriter = False


class Wizard_Stock(models.TransientModel):
    _name = 'wizard.stock'

    producto = fields.Many2one('product.product', string="Producto")
    marca = fields.Many2one('product.brand', string="Marca")
    modelo = fields.Char("Escriba el Modelo")
    part_number = fields.Char("Escriba el Part Number")
    capacidad = fields.Many2one('x_capacidad', string="Capacidad de Almacenamiento")
    grado = fields.Many2one('x_grado', string="Grado")
    cant_prevista = fields.Float("Cantidad Prevista")
    tarifa_venta = fields.Float("Tarifa de Venta")
    color = fields.Many2one('x_color', string="Color")
    idioma = fields.Many2one('x_idioma_terminal', string="Idioma")
    cargador = fields.Many2one('x_cargador', string="Cargador")
    logo = fields.Many2one('x_logo', string="Logo")
    aplicaciones = fields.Many2one('x_terminal_aplicaciones', string="Aplicaciones")
    bloqueo = fields.Many2one('x_bloqueo', string="Bloqueo Operador")
    location_id = fields.Many2one('stock.location', string="Ubicacion", domain=[('usage', '=', 'internal')])

    def action_export_excel_stock_resumido(self):
        if not xlsxwriter:
            raise UserError(_("The Python library xlsxwriter is installed. Contact your system administrator"))

        file_path = tempfile.mktemp(suffix='.xlsx')
        workbook = xlsxwriter.Workbook(file_path)
        styles = {
            'main_header_style': workbook.add_format({
                'bold': True,
                'font_size': 11,
                'border': 1,
            }),
            'main_data_style': workbook.add_format({
                'font_size': 11,
                'border': 1,
            }),
        }
        worksheet = workbook.add_worksheet(u"Reporte de Stock Resumido.xlsx")
        cur_column = 1
        for column in [("Producto"), ("Marca"), ("Modelo"), ("Part-Number"), ("Capacidad"),
                       ("Grado"), ("Cant. a Mano"), ("Cant. Prevista"), ("Tarifa Venta")]:
            worksheet.write(0, cur_column, column, styles.get("main_header_style"))
            col_letter = chr(cur_column + 97).upper()
            column_width = cur_column == 0 and 35 or 30
            worksheet.set_column('{c}:{c}'.format(c=col_letter), column_width)
            cur_column += 1

        list_to_order = []

        domain = []

        if self.producto:
            domain = expression.AND([domain, [('product_id', '=', self.producto.id)]])
        if self.marca:
            domain = expression.AND([domain, [('product_id.product_brand_id', '=', self.marca.id)]])
        if self.modelo:
            domain = expression.AND([domain, [('product_id.x_studio_modelo', '=', self.modelo)]])
        if self.part_number:
            domain = expression.AND([domain, [('product_id.x_studio_part_number', '=', self.part_number)]])
        if self.capacidad:
            domain = expression.AND(
                [domain, [('product_id.x_studio_capacidad_de_almacenamiento.id', '=', self.capacidad.id)]])
        if self.grado:
            domain = expression.AND([domain, [('revision_grado', '=', self.grado.id)]])
        if self.color:
            domain = expression.AND([domain, [('color', '=', self.color.id)]])
        if self.idioma:
            domain = expression.AND([domain, [('idioma', '=', self.idioma.id)]])
        if self.cargador:
            domain = expression.AND([domain, [('cargador', '=', self.cargador.id)]])
        if self.logo:
            domain = expression.AND([domain, [('logo', '=', self.logo.id)]])
        if self.aplicaciones:
            domain = expression.AND([domain, [('aplicaciones', '=', self.aplicaciones.id)]])
        if self.bloqueo:
            domain = expression.AND([domain, [('lot_id.x_studio_bloqueo', '=', self.bloqueo.id)]])
        if self.location_id:
            domain = expression.AND([domain, [('location_id', '=', self.location_id.id)]])

        mis_stock = self.env['stock.quant'].search(domain)

        product_ids = mis_stock.mapped('product_id.id')

        for product_id in product_ids:
            stock_by_grades = mis_stock.filtered(lambda x: x.product_id.id == product_id).mapped('lot_id.x_studio_revision_grado.id')
            for stock_by_grade in stock_by_grades:
                grade = self.env['x_grado'].browse(stock_by_grade)
                producto = self.env['product.product'].browse(product_id)
                a_mano = sum(mis_stock.filtered(lambda x: x.product_id.id == product_id and x.lot_id.x_studio_revision_grado.id == stock_by_grade).mapped('quantity'))
                reserved_quantity = sum(mis_stock.filtered(lambda x: x.product_id.id == product_id and x.lot_id.x_studio_revision_grado.id == stock_by_grade).mapped('reserved_quantity'))
                prevista = a_mano - reserved_quantity
                tarifa = self.env['product.pricelist.item'].search([('apply_grade_subgroup', '=', stock_by_grade), ('product_tmpl_id', '=', producto.product_tmpl_id.id), ('pricelist_id', '=', 1)]).fixed_price

                list_to_order.append({
                    'producto': producto.name,
                    'marca': producto.product_brand_id.name,
                    'modelo': producto.x_studio_modelo,
                    'part-number': producto.x_studio_part_number,
                    'capacidad': producto.x_studio_capacidad_de_almacenamiento.x_name,
                    'grado': grade.x_name,
                    'cant_a_mano': a_mano,
                    'cant_prevista': prevista,
                    'tarifa_venta': tarifa,
                })

        write_column = 1

        for data in list_to_order:
            worksheet.write(write_column, 1, data['producto'], styles.get("main_data_style"))
            worksheet.write(write_column, 2, data['marca'], styles.get("main_data_style"))
            worksheet.write(write_column, 3, data['modelo'], styles.get("main_data_style"))
            worksheet.write(write_column, 4, data['part-number'], styles.get("main_data_style"))
            worksheet.write(write_column, 5, data['capacidad'], styles.get("main_data_style"))
            worksheet.write(write_column, 6, data['grado'], styles.get("main_data_style"))
            worksheet.write(write_column, 7, data['cant_a_mano'], styles.get("main_data_style"))
            worksheet.write(write_column, 8, data['cant_prevista'], styles.get("main_data_style"))
            worksheet.write(write_column, 9, data['tarifa_venta'], styles.get("main_data_style"))

            write_column = write_column + 1

        workbook.close()

        with open(file_path, 'rb') as r:
            xls_file = base64.b64encode(r.read())
        att_vals = {
            'name': u"{}.xlsx".format("Reportes de stock"),
            'type': 'binary',
            'datas': xls_file,
        }
        attachment_id = self.env['ir.attachment'].create(att_vals)
        self.env.cr.commit()
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'self',
        }
        return action

    def action_export_excel_stock_ampliado(self):
        if not xlsxwriter:
            raise UserError(_("The Python library xlsxwriter is installed. Contact your system administrator"))

        file_path = tempfile.mktemp(suffix='.xlsx')
        workbook = xlsxwriter.Workbook(file_path)
        styles = {
            'main_header_style': workbook.add_format({
                'bold': True,
                'font_size': 11,
                'border': 1,
            }),
            'main_data_style': workbook.add_format({
                'font_size': 11,
                'border': 1,
            }),
        }
        worksheet = workbook.add_worksheet(u"Reporte de Stock Ampliado.xlsx")
        cur_column = 1
        for column in [("Producto"), ("Marca"), ("Modelo"), ("Part-Number"), ("Capacidad"),
                       ("Grado"), ("Color"), ("Idioma"), ("Cargador"), ("Logo"), ("Aplicaciones"),
                       ("Bloqueo")]:
            worksheet.write(0, cur_column, column, styles.get("main_header_style"))
            col_letter = chr(cur_column + 97).upper()
            column_width = cur_column == 0 and 35 or 30
            worksheet.set_column('{c}:{c}'.format(c=col_letter), column_width)
            cur_column += 1

        list_to_order = []

        domain = []

        if self.producto:
            domain = expression.AND([domain, [('product_id', '=', self.producto.id)]])
        if self.marca:
            domain = expression.AND([domain, [('product_id.product_brand_id', '=', self.marca.id)]])
        if self.modelo:
            domain = expression.AND([domain, [('product_id.x_studio_modelo', '=', self.modelo)]])
        if self.part_number:
            domain = expression.AND([domain, [('product_id.x_studio_part_number', '=', self.part_number)]])
        if self.capacidad:
            domain = expression.AND(
                [domain, [('product_id.x_studio_capacidad_de_almacenamiento.id', '=', self.capacidad.id)]])
        if self.grado:
            domain = expression.AND([domain, [('revision_grado', '=', self.grado.id)]])
        if self.color:
            domain = expression.AND([domain, [('color', '=', self.color.id)]])
        if self.idioma:
            domain = expression.AND([domain, [('idioma', '=', self.idioma.id)]])
        if self.cargador:
            domain = expression.AND([domain, [('cargador', '=', self.cargador.id)]])
        if self.logo:
            domain = expression.AND([domain, [('logo', '=', self.logo.id)]])
        if self.aplicaciones:
            domain = expression.AND([domain, [('aplicaciones', '=', self.aplicaciones.id)]])
        if self.bloqueo:
            domain = expression.AND([domain, [('lot_id.x_studio_bloqueo', '=', self.bloqueo.id)]])
        if self.location_id:
            domain = expression.AND([domain, [('location_id', '=', self.location_id.id)]])

        mis_stock = self.env['stock.quant'].search(domain)

        for stock in mis_stock:
            list_to_order.append({
                    'producto': stock.product_id.name,
                    'marca': stock.product_id.product_brand_id.name,
                    'modelo': stock.product_id.x_studio_modelo,
                    'part-number': stock.product_id.x_studio_part_number,
                    'capacidad': stock.product_id.x_studio_capacidad_de_almacenamiento.x_name,
                    'grado': stock.lot_id.x_studio_revision_grado.x_name,
                    'color': stock.lot_id.x_studio_color.x_name,
                    'idioma': stock.lot_id.x_studio_idioma.x_name,
                    'cargador': stock.lot_id.x_studio_cargador.x_name,
                    'logo': stock.lot_id.x_studio_logo.x_name,
                    'aplicaciones': stock.lot_id.x_studio_aplicaciones.x_name,
                    'bloqueo': stock.lot_id.x_studio_bloqueo.x_name
                })

        write_column = 1

        for data in list_to_order:
            worksheet.write(write_column, 1, data['producto'], styles.get("main_data_style"))
            worksheet.write(write_column, 2, data['marca'], styles.get("main_data_style"))
            worksheet.write(write_column, 3, data['modelo'], styles.get("main_data_style"))
            worksheet.write(write_column, 4, data['part-number'], styles.get("main_data_style"))
            worksheet.write(write_column, 5, data['capacidad'], styles.get("main_data_style"))
            worksheet.write(write_column, 6, data['grado'], styles.get("main_data_style"))
            worksheet.write(write_column, 7, data['color'], styles.get("main_data_style"))
            worksheet.write(write_column, 8, data['idioma'], styles.get("main_data_style"))
            worksheet.write(write_column, 9, data['cargador'], styles.get("main_data_style"))
            worksheet.write(write_column, 10, data['logo'], styles.get("main_data_style"))
            worksheet.write(write_column, 11, data['aplicaciones'], styles.get("main_data_style"))
            worksheet.write(write_column, 12, data['bloqueo'], styles.get("main_data_style"))

            write_column = write_column + 1

        workbook.close()

        with open(file_path, 'rb') as r:
            xls_file = base64.b64encode(r.read())
        att_vals = {
            'name': u"{}.xlsx".format("Reportes de stock"),
            'type': 'binary',
            'datas': xls_file,
        }
        attachment_id = self.env['ir.attachment'].create(att_vals)
        self.env.cr.commit()
        action = {
            'type': 'ir.actions.act_url',
            'url': '/web/content/{}?download=true'.format(attachment_id.id, ),
            'target': 'self',
        }
        return action
