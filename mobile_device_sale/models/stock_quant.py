# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
import logging

_logger = logging.getLogger(__name__)


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    @api.model
    def _update_reserved_quantity(self, product_id, location_id, quantity, lot_id=None, package_id=None, owner_id=None,
                                  strict=False, specs_filter=None):
        """ Increase the reserved quantity, i.e. increase `reserved_quantity` for the set of quants
        sharing the combination of `product_id, location_id` if `strict` is set to False or sharing
        the *exact same characteristics* otherwise. Typically, this method is called when reserving
        a move or updating a reserved move line. When reserving a chained move, the strict flag
        should be enabled (to reserve exactly what was brought). When the move is MTS,it could take
        anything from the stock, so we disable the flag. When editing a move line, we naturally
        enable the flag, to reflect the reservation according to the edition.

        :return: a list of tuples (quant, quantity_reserved) showing on which quant the reservation
            was done and how much the system was able to reserve on it
        """
        #_logger.info("UPDATE RESERVED QUANTS CUSTOM")
        self = self.sudo()
        rounding = product_id.uom_id.rounding
        quants = self._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                              strict=strict)
        reserved_quants = []

        #_logger.info("QUANTS FROM UPDATE RESERVED: %r", quants)
        # Apply product specifications filter
        # if specs_filter:
            # quants = quants.filtered(lambda q: eval(specs_filter))
            # quants_filtered = self.env['stock.quant']
            # for specs in specs_filter:
            #     _logger.info("ITERATING FILTER: %r", specs)
            #     quants_filtered += quants.filtered(lambda q: eval(specs))
            #
            # quants = quants_filtered
        # _logger.info("QUANTS AFTER FILTER: %r", quants)

        if float_compare(quantity, 0, precision_rounding=rounding) > 0:
            # if we want to reserve
            available_quantity = self._get_available_quantity(product_id, location_id, lot_id=lot_id,
                                                              package_id=package_id, owner_id=owner_id, strict=strict)
            if float_compare(quantity, available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_(
                    'It is not possible to reserve more products of %s than you have in stock.') % product_id.display_name)
        elif float_compare(quantity, 0, precision_rounding=rounding) < 0:
            # if we want to unreserve
            available_quantity = sum(quants.mapped('reserved_quantity'))
            if float_compare(abs(quantity), available_quantity, precision_rounding=rounding) > 0:
                raise UserError(_(
                    'It is not possible to unreserve more products of %s than you have in stock.') % product_id.display_name)
        else:
            return reserved_quants

        if specs_filter:
            for specs in specs_filter:
                #_logger.info("!!!!!! ITERATING IN FILTER.....")

                #_logger.info("FILTER QUANTITY: %r", specs[0])
                filtered_quants = quants.filtered(lambda q: eval(specs[1]))
                quantity = specs[0]
                for quant in filtered_quants:

                    if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                        #_logger.info("IN FLOAT COMPARE")
                        #_logger.info("FLOAT COMPARE: %r", float_compare(quantity, 0, precision_rounding=rounding))
                        max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                        #_logger.info("MAX QUANT: %r", max_quantity_on_quant)
                        if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                            _logger.info("FLOAT COMPARE <= 0.... SO CONTINUE")
                            _logger.info("FLOAT COMPARE NOW: %r",
                                         float_compare(max_quantity_on_quant, 0, precision_rounding=rounding))
                            continue
                        max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                        quant.reserved_quantity += max_quantity_on_quant
                        reserved_quants.append((quant, max_quantity_on_quant))
                        quantity -= max_quantity_on_quant
                        available_quantity -= max_quantity_on_quant
                    else:
                        #_logger.info("NOT FLOAT COMPARE")
                        max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                        quant.reserved_quantity -= max_quantity_on_quant
                        reserved_quants.append((quant, -max_quantity_on_quant))
                        quantity += max_quantity_on_quant
                        available_quantity += max_quantity_on_quant

                    if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity,
                                                                                             precision_rounding=rounding):
                        break


            return reserved_quants

        else:

            for quant in quants:
                if float_compare(quantity, 0, precision_rounding=rounding) > 0:
                    #_logger.info("IN FLOAT COMPARE")
                    #_logger.info("FLOAT COMPARE: %r", float_compare(quantity, 0, precision_rounding=rounding))
                    max_quantity_on_quant = quant.quantity - quant.reserved_quantity
                    #_logger.info("MAX QUANT: %r", max_quantity_on_quant)
                    if float_compare(max_quantity_on_quant, 0, precision_rounding=rounding) <= 0:
                        #_logger.info("FLOAT COMPARE <= 0.... SO CONTINUE")
                        _logger.info("FLOAT COMPARE NOW: %r", float_compare(max_quantity_on_quant, 0, precision_rounding=rounding))
                        continue
                    max_quantity_on_quant = min(max_quantity_on_quant, quantity)
                    quant.reserved_quantity += max_quantity_on_quant
                    reserved_quants.append((quant, max_quantity_on_quant))
                    quantity -= max_quantity_on_quant
                    available_quantity -= max_quantity_on_quant
                else:

                    #_logger.info("NOT FLOAT COMPARE")
                    max_quantity_on_quant = min(quant.reserved_quantity, abs(quantity))
                    quant.reserved_quantity -= max_quantity_on_quant
                    reserved_quants.append((quant, -max_quantity_on_quant))
                    quantity += max_quantity_on_quant
                    available_quantity += max_quantity_on_quant

                if float_is_zero(quantity, precision_rounding=rounding) or float_is_zero(available_quantity,
                                                                                         precision_rounding=rounding):
                    break
            return reserved_quants

    @api.constrains('quantity')
    def check_quantity(self):
        for quant in self:
            if float_compare(quant.quantity, 1,
                             precision_rounding=quant.product_uom_id.rounding) > 0 and quant.lot_id and quant.product_id.tracking == 'serial':
                raise ValidationError(_('A serial number should only be linked to a single product. %s')%quant.lot_id.name)
