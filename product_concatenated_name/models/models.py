# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.onchange('product_brand_id', 'x_studio_capacidad_de_almacenamiento', 'x_studio_modelo',
                  'x_studio_part_number', 'categ_id', 'x_studio_condition','x_studio_memoria_ram')
    def change_product_name(self):
        _logger.info("CHANGED PARAMETER")
        if self.categ_id.name == 'Teléfonos':
            name = 'Teléfono'
            brand = self.product_brand_id.name or ''
            if brand:
                name += ' ' + brand
            model = self.x_studio_modelo or ''
            if model:
                name = name + ' ' + model
            part_number = self.x_studio_part_number or ''
            if part_number:
                name += ' / ' + part_number
            capacity = self.x_studio_capacidad_de_almacenamiento.x_name or ''
            if capacity:
                name += ' / ' + capacity
            condition = self.x_studio_condition or ''
            if condition:
                name += ' / ' + condition

            ram = self.x_studio_memoria_ram.x_name
            if ram:
                name += ' / ' + ram


            self['name'] = name

    @api.model
    def create(self, vals):
        # _logger.info("PRODUCT CREATE VALS: %r", vals)
        phone_cat_id = self.env['product.category'].search([('name', '=', 'Teléfonos')]).id
        # Concatenated name
        if vals['categ_id'] == phone_cat_id:
            name = 'Teléfono'
            if vals['product_brand_id']:
                brand_name = self.env['product.brand'].browse(vals['product_brand_id']).name
                name += ' ' + brand_name
            if vals['x_studio_modelo']:
                name += ' ' + vals['x_studio_modelo']
            if vals['x_studio_part_number']:
                name += ' / ' + vals['x_studio_part_number']
            if vals['x_studio_capacidad_de_almacenamiento']:
                capacity = self.env['x_capacidad'].browse(vals['x_studio_capacidad_de_almacenamiento']).x_name
                name += ' / ' + capacity
            if vals['x_studio_condition']:
                name += ' / ' + vals['x_studio_condition']
            if vals.get('x_studio_memoria_ram',False):
                x_studio_memoria_ram = self.env['x_memoria.ram'].browse(vals['x_studio_memoria_ram']).x_name
                name += ' / ' + x_studio_memoria_ram
            vals['name'] = name

        res = super(ProductTemplate, self).create(vals)
        return res

    def write(self, vals):
        if len(self) == 1:
            phone_cat_id = self.env['product.category'].search([('name', '=', 'Teléfonos')]).id
            # Concatenated name
            if ('categ_id' in vals.keys() and vals['categ_id'] == phone_cat_id) or self.categ_id.id == phone_cat_id:
                name = 'Teléfono'

                if 'product_brand_id' in vals.keys() and vals['product_brand_id']:
                    brand_name = self.env['product.brand'].browse(vals['product_brand_id']).name
                    name += ' ' + brand_name
                elif self.product_brand_id.name:
                    brand_name = self.product_brand_id.name
                    name += ' ' + brand_name

                if 'x_studio_modelo' in vals.keys() and vals['x_studio_modelo']:
                    name += ' ' + vals['x_studio_modelo']
                elif self.x_studio_modelo:
                    name += ' ' + self.x_studio_modelo

                if 'x_studio_part_number' in vals.keys() and vals['x_studio_part_number']:
                    name += ' / ' + vals['x_studio_part_number']
                elif self.x_studio_part_number:
                    name += ' / ' + self.x_studio_part_number

                if 'x_studio_capacidad_de_almacenamiento' in vals.keys() and vals['x_studio_capacidad_de_almacenamiento']:
                    capacity = self.env['x_capacidad'].browse(vals['x_studio_capacidad_de_almacenamiento']).x_name
                    name += ' / ' + capacity
                elif self.x_studio_capacidad_de_almacenamiento:
                    name += ' / ' + self.x_studio_capacidad_de_almacenamiento.x_name

                if 'x_studio_condition' in vals.keys() and vals['x_studio_condition']:
                    name += ' / ' + vals['x_studio_condition']
                elif self.x_studio_condition:
                    name += ' / ' + self.x_studio_condition


                if 'x_studio_memoria_ram' in vals.keys() and vals['x_studio_memoria_ram']:
                    x_studio_memoria_ram = self.env['x_memoria.ram'].browse(vals['x_studio_memoria_ram']).x_name
                    name += ' / ' + x_studio_memoria_ram
                elif self.x_studio_memoria_ram:
                    name += ' / ' + self.x_studio_memoria_ram.x_name


                vals['name'] = name

        res = super(ProductTemplate, self).write(vals)
        return res
