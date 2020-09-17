# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
import base64
import xlrd
import logging

_logger = logging.getLogger(__name__)


class FunctionalTest(models.TransientModel):
    _name = 'mobile.quality.test.wizard'
    _inherit = ['functional.quality.test', 'esthetic.quality.test']
    _description = 'Quality test'

    # Serial Batch Import

    def _get_current_company(self):
        return self.env.company.id

    def _get_product_domain(self):
        context = self.env.context.copy() or {}
        picking_id = context.get('active_id')
        picking = self.env['stock.picking'].search([('id', '=', picking_id)])
        ids = picking.move_ids_without_package.product_id.ids
        return [('id', 'in', ids)]

    company_id = fields.Many2one(comodel_name='res.company', string="Company", default=_get_current_company)
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=_get_product_domain)
    rebu_sale_regime = fields.Boolean(string='REBU Sale Regime')
    product_sku = fields.Char(string="Product SKU", readonly=True)

    color = fields.Many2one(comodel_name='x_color', string="Color")
    lock_status = fields.Many2one(comodel_name='x_bloqueo', string="Lock Status")
    logo = fields.Many2one(comodel_name='x_logo', string="Logo")
    charger = fields.Many2one(comodel_name='x_cargador', string="Charger")
    network_type = fields.Many2one(comodel_name='x_red', string="Network Type")
    lang = fields.Many2one(comodel_name='x_idioma_terminal', string="Language")
    applications = fields.Many2one(comodel_name='x_terminal_aplicaciones', string="Applications")

    device_condition = fields.Selection(selection=[('new', 'New'), ('used', 'Used')], default='new')
    print_labels = fields.Boolean(string="Print Labels", default=True)
    ean = fields.Char(string='EAN')

    serial_file = fields.Binary(string="File")
    lot_id = fields.Char(string="Find Lot")
    new_lot_ids = fields.Many2many(comodel_name='stock.production.lot')

    @api.onchange('product_id')
    def product_change(self):
        _logger.info("PRODUCT CHANGED")
        if self.product_id:
            _logger.info("PRODUCT ID: %r", self.product_id.id)
            _logger.info("PRODUCT SKU: %r", self.product_id.product_tmpl_id.product_sku)
            if self.product_id.product_tmpl_id.product_sku:
                self['product_sku'] = self.product_id.product_tmpl_id.product_sku
            else:
                raise ValidationError("SKU code is missing for this product")

    @api.depends('product_id', 'company_id')
    @api.onchange('lot_id')
    def onchange_lot_id(self):
        if self.lot_id and self.product_id and self.company_id:
            piking_id = self.env.context.get('active_id')
            picking = self.env['stock.picking'].browse(piking_id)
            move_qty = picking.move_lines.filtered(lambda m: m.product_id.id == self.product_id.id).product_uom_qty
            move_lot_done = picking.move_line_ids.filtered(lambda m: m.lot_id.id and m.product_id.id == self.product_id.id)
            _logger.info("LOTS DONE: %r", len(move_lot_done))
            lots_done = len(self.new_lot_ids)

            existing_lot = self.env['stock.production.lot'].search([('name', '=', self.lot_id)])

            existing_lot_processed = self.env['stock.move.line'].search([('lot_id.name', '=', self.lot_id),
                                                                         ('picking_id', '!=', piking_id)])

            existing_lot_move = self.env['stock.move.line'].search([('lot_id.name', '=', self.lot_id),
                                                                    ('picking_id', '=', piking_id)])

            # First check if there is more product qty to supply a lot id
            # if lots_done < move_qty:
            #     # Then create the lot

            if move_qty != len(move_lot_done):

                free_to_pickup = move_qty - len(move_lot_done)

                if lots_done < free_to_pickup:

                    if not existing_lot:
                        lot_value = {
                            'name': self.lot_id,
                            'product_id': self.product_id.id,
                            'company_id': self.company_id.id
                        }
                        lot = self.env['stock.production.lot'].create(lot_value)
                        self.update({'new_lot_ids': [(4, lot.id, 0)]})
                    elif existing_lot and not existing_lot_processed:
                        self.update({'new_lot_ids': [(4, existing_lot.id, 0)]})
                    elif existing_lot and existing_lot_processed:
                        raise ValidationError("The lot %s have been processed. Lots must be unique" % self.lot_id)
                else:
                    raise ValidationError("You can't process more IMEIs Because this product have all lots registered.")
            elif move_qty == len(move_lot_done) and existing_lot and existing_lot_move:
                self.update({'new_lot_ids': [(4, existing_lot.id, 0)]})
            elif move_qty == len(move_lot_done) and not existing_lot:
                raise ValidationError("You can't process more IMEIs Because this product have all lots registered.")
            else:
                raise ValidationError("You can't process more IMEIs Because this product have all lots registered.")

            # else:
            #     raise ValidationError("You can't process more lot quantities than product quantities. You have %s lots "
            #                           "for %s products to process" % (lots_done, move_qty))
            self.lot_id = False

    @api.depends('product_id', 'company_id')
    @api.onchange('serial_file')
    def onchange_serial_file(self):
        if self.serial_file and self.product_id and self.company_id:
            piking_id = self.env.context.get('active_id')
            picking = self.env['stock.picking'].browse(piking_id)
            move_qty = picking.move_lines.filtered(lambda m: m.product_id.id == self.product_id.id).product_uom_qty
            move_lot_done = picking.move_line_ids.filtered(
                lambda m: m.lot_id.id and m.product_id.id == self.product_id.id)
            lots_done = len(self.new_lot_ids)
            # process the .xls file
            file_decoded = base64.decodebytes(self.serial_file)
            book = xlrd.open_workbook(file_contents=file_decoded)
            sheet = book.sheet_by_index(0)
            serial_values = []
            for rowx, row in enumerate(map(sheet.row, range(sheet.nrows)), 1):
                for colx, cell in enumerate(row, 1):
                    if type(cell.value) in [float, int]:
                        value = str(int(cell.value))
                    else:
                        value= cell.value
                    serial_values.append(value)
            # First check if there is more product qty to supply a lot id
            if lots_done < move_qty:
                lots_to_fill = move_qty - lots_done
                if move_lot_done:
                    lots_to_fill = lots_to_fill - len(move_lot_done)
                # Check if the product qty to fill a lot is greater or equal than number of serials uploaded
                if lots_to_fill >= len(serial_values):
                    # Then create the lots
                    for serial in serial_values:
                        existing_lot = self.env['stock.production.lot'].search([('name', '=', serial)])
                        existing_lot_processed = self.env['stock.move.line'].search([('lot_id.name', '=', serial),
                                                                                     ('picking_id', '!=', piking_id)])
                        if not existing_lot:
                            lot_value = {
                                'name': serial,
                                'product_id': self.product_id.id,
                                'company_id': self.company_id.id
                            }
                            lot = self.env['stock.production.lot'].create(lot_value)
                            self.update({'new_lot_ids': [(4, lot.id, 0)]})
                        elif existing_lot and not existing_lot_processed:
                            self.update({'new_lot_ids': [(4, existing_lot.id, 0)]})
                        elif existing_lot and existing_lot_processed:
                            raise ValidationError("The lot %s have been processed. Lots must be unique" % serial)
                elif lots_to_fill == 0:
                    edition_mode = True
                    lot_names = move_lot_done.mapped('lot_id').mapped('name')
                    for serial in serial_values:
                        if serial not in lot_names:
                            edition_mode = False
                    if edition_mode:
                        for serial in serial_values:
                            existing_lot = self.env['stock.production.lot'].search([('name', '=', serial)])
                            existing_lot_processed = self.env['stock.move.line'].search([('lot_id.name', '=', serial),
                                                                                         ('picking_id', '!=',
                                                                                          piking_id)])
                            if existing_lot and not existing_lot_processed:
                                self.update({'new_lot_ids': [(4, existing_lot.id, 0)]})
                            elif existing_lot and existing_lot_processed:
                                raise ValidationError("The lot %s have been processed. Lots must be unique" % serial)
                    else:
                        raise ValidationError("You can't process more IMEIs Because this product have all lots registered.")

                else:
                    raise ValidationError(
                        "You can't process more lot quantities than product quantities. You have uploaded %s lots "
                        "to process %s products" % (len(serial_values), lots_to_fill))
            else:
                raise ValidationError("You can't process more lot quantities than product quantities. "
                                      "You have uploaded %s lots to process %s products" % (lots_done, move_qty))

    def process_test(self):
        # _logger.info("RUNNING FUNCTIONAL TEST")
        if self.product_id:
            functional_test_obj = self.env['functional.quality.test']
            esthetic_test_obj = self.env['esthetic.quality.test']

            exclude_fields = ['id', 'display_name', 'create_uid', 'create_date', 'write_uid',
                              'write_date', '__last_update', 'serial_file', 'lot_id',
                              'new_lot_ids', 'company_id', 'product_id']

            functional_fields = [element for element in
                                 functional_test_obj.fields_get_keys() if element not in exclude_fields]
            esthetic_fields = [element for element in
                               esthetic_test_obj.fields_get_keys() if element not in exclude_fields]

            if self.device_condition == 'new':
                functional_test_values = {
                    'power_on': True,
                    'speaker': True,
                    'buttons': True,
                    'fingerprint_reader': True,
                    'torch': True,
                    'bluetooth': True,
                    'wifi': True,
                    'proximity_sensor': True,
                    'touch_screen': True,
                    'display_bright': True,
                    'call_test': True,
                    'ring_tone': True,
                    'camera': True,
                    'mobile_os': True,
                    'user_account': True,
                    'security_pattern': True,
                    'humidity': True
                }

                new_grade_id = self.env['ir.config_parameter'].sudo().get_param('mobile_device_reception.new_grade')
                new_grade_obj = self.env['x_grado'].search([('id', '=', int(new_grade_id))])
                grade_value = new_grade_obj.x_studio_test_value
                esthetic_test_values = {
                    'display_test': str(grade_value),
                    'case_test': str(grade_value),
                    'device_case': True,
                    'device_charger': True,
                    'cables': True,
                    'headset': True
                }
            else:
                functional_test_values = self.read(functional_fields)[0]
                functional_test_values.pop('id')

                esthetic_test_values = self.read(esthetic_fields)[0]
                esthetic_test_values.pop('id')

            # _logger.info(functional_test_values)
            # _logger.info(esthetic_test_values)

            functional_obj = functional_test_obj.create(functional_test_values)
            # _logger.info("FUNCTIONAL RESULT ON WIZARD: %r", functional_obj.test_pass)
            esthetic_obj = esthetic_test_obj.create(esthetic_test_values)
            grade_object = self.env['x_grado'].search([('x_name', '=', esthetic_obj.test_result)])

            # SKU code
            product_sku = self.product_id.product_tmpl_id.product_sku
            grade_sku = grade_object.x_studio_grade_sku
            color_sku = self.color.x_color_code
            if self.rebu_sale_regime:
                sale_regime_sku = 'R'
            else:
                sale_regime_sku = 'N'
            if not grade_sku:
                raise ValidationError("Grade %s. Missing SKU code grade identifier" % grade_object.x_name)
            if not color_sku:
                raise ValidationError("Color %s. Missing SKU code color identifier" % self.color.x_name)
            lot_sku = product_sku + sale_regime_sku + grade_sku + color_sku

            _logger.info("LOTS SKU: %r", lot_sku)

            piking_id = self.env.context.get('active_id')
            picking = self.env['stock.picking'].browse(piking_id)
            move_lines = picking.move_line_ids.filtered(
                lambda m: m.product_id.id == self.product_id.id
            )
            stock_move = picking.move_lines.filtered(
                lambda m: m.product_id.id == self.product_id.id
            )

            for lot in self.new_lot_ids:

                lot.write({
                    # EAN
                    'x_studio_lot_ean': self.ean,
                    # SKU
                    'x_studio_lot_sku': lot_sku,
                    # Specifications
                    'x_studio_color': self.color.id,
                    'x_studio_bloqueo': self.lock_status.id,
                    'x_studio_red': self.network_type.id,
                    'x_studio_logo': self.logo.id,
                    'x_studio_idioma': self.lang.id,
                    'x_studio_cargador': self.charger.id,
                    'x_studio_aplicaciones': self.applications.id,
                    # Test
                    'esthetic_test_id': esthetic_obj.id,
                    'functional_test_id': functional_obj.id,
                    'x_studio_revision_estetica': True,
                    'x_studio_revision_grado': grade_object.id,
                    'x_studio_revision_funcional': True,
                    'x_studio_resultado': 'Funcional' if functional_obj.test_pass else 'Con Avería',
                })
                self.process_lot_stock_valuation_layer(lot, stock_move)

            processing_lot_ids = self.new_lot_ids.ids
            for move in move_lines:
                if move.lot_id.id:
                    if move.lot_id.id in processing_lot_ids:
                        processing_lot_ids.remove(move.lot_id.id)
                        # move.write({
                        #     'quality_test_done': True,
                        # })
            move_lines_no_lot = picking.move_line_ids.filtered(
                lambda m: m.product_id.id == self.product_id.id and not m.lot_id
            )
            for move_by_lot in zip(processing_lot_ids, move_lines_no_lot):
                move_by_lot[1].write({
                        'quality_test_done': True,
                        'lot_id': move_by_lot[0],
                        'qty_done': 1
                    })
            if self.print_labels:
                return self._print_labels()

            message = self.env['message.popup']
            text_message = '%s lots processed ' % len(self.new_lot_ids)
            return message.popup(message=text_message)
        else:
            raise ValidationError("No product selected to process in this test")

    def process_lot_stock_valuation_layer(self, lot, stock_move):
        valuation_layer = self.env['stock.valuation.layer']
        purchase_line = stock_move.move_orig_ids.purchase_line_id
        # todo: conditional purchase_line_id
        values = {
            'active': True,
            # 'product_id': lot.product_id.id,
            'lot_id': lot.id,
            'company_id': purchase_line.company_id.id,
            'quantity': 1,
            'remaining_qty': 1,
            'unit_cost': purchase_line.price_unit,
            'value': purchase_line.price_unit,
            'remaining_value': purchase_line.price_unit,
            'stock_move_id': stock_move.id,
            'description': 'Cost for %s - %s' % (lot.product_id.name, lot.name)
        }
        valuation_layer_entry = valuation_layer.create(values)
        _logger.info("VALUATION LAYER FOR LOT %s: %s" % (lot.name, valuation_layer_entry.id))
        return True

    def _print_labels(self):
        self.ensure_one()
        action = self._action_print_labels()
        action.update({'close_on_report_download': True})
        return action

    def _action_print_labels(self):
        lots = self.new_lot_ids
        return self.env.ref('mobile_device_reception.product_lots_label').report_action(lots)
