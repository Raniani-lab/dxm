# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_sku = fields.Char(string="Product SKU", compute="_generate_sku")

    def _generate_sku(self):
        for record in self:
            sku_completed = False
            if record.product_brand_id:
                brand_sku_part = record.product_brand_id.name[0:2].upper()
                if record.x_studio_model_code or record.x_studio_modelo:
                    model_sku_part = record.x_studio_modelo
                    model_sku_part = model_sku_part[0:3].upper()
                    if record.x_studio_part_number:
                        part_number_sku_part = record.x_studio_part_number.upper()
                        if record.x_studio_capacidad_de_almacenamiento:
                            capacity_sku_part = record.x_studio_capacidad_de_almacenamiento.x_name.replace(' ', '')[0:3]
                            record[
                                'product_sku'] = brand_sku_part + model_sku_part + part_number_sku_part + capacity_sku_part
                            sku_completed = True
                    else:
                        model_sku_code_part = record.x_studio_model_code
                        if record.x_studio_capacidad_de_almacenamiento:
                            capacity_sku_part = record.x_studio_capacidad_de_almacenamiento.x_name.replace(' ', '')[0:3]
                            record[
                                'product_sku'] = brand_sku_part + model_sku_part +model_sku_code_part+ capacity_sku_part
                            sku_completed = True

            if not sku_completed:
                record['product_sku'] = False
