# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class EstheticQualityTest(models.Model):
    _name = 'esthetic.quality.test'
    _description = 'Product Visual Tests'

    # Lot ID
    lot_id = fields.One2many(comodel_name="stock.production.lot", inverse_name="esthetic_test_id", string="Lot")
    # Test result
    test_result = fields.Char(compute="_compute_esthetic_test_result", string="Test Result")

    def _get_grade_display_questions(self):
        display_selection = []
        grades = self.env['x_grado'].search([('x_studio_is_grade_test', '=', True)])
        for grade in grades:
            display_selection.append((str(grade.x_studio_test_value),  grade.x_studio_display_short_description))
        return display_selection

    def _get_grade_case_questions(self):
        case_selection = []
        grades = self.env['x_grado'].search([('x_studio_is_grade_test', '=', True)])
        for grade in grades:
            case_selection.append((str(grade.x_studio_test_value),  grade.x_studio_case_short_description))
        return case_selection

    # Esthetic questions
    display_test = fields.Selection(selection='_get_grade_display_questions', string='Display Status', default='10')
    case_test = fields.Selection(selection='_get_grade_case_questions', string='Case Status', default='10')
    # Accessories Questions
    device_case = fields.Boolean(string='Device Box', default=False)
    device_charger = fields.Boolean(string='Charger', default=False)
    cables = fields.Boolean(string='Cables', default=False)
    headset = fields.Boolean(string='Headset', default=False)

    def _compute_esthetic_test_result(self):
        for esthetic_test in self:
            grade = esthetic_test.get_esthetic_result()
            esthetic_test['test_result'] = grade

    def get_esthetic_result(self):
        """
        Get esthetic test result
        :return: A, B, C, New or 14 Días
        """
        # _logger.info("GETTING ESTHETIC TEST RESULT FOR: %r", self.id)
        esthetic_matrix = {}
        grades = self.env['x_grado'].search([('x_studio_is_grade_test', '=', True)])
        for grade in grades:
            esthetic_matrix.update({grade.x_studio_test_value:  grade.x_name})
        # _logger.info("Grade Matrix: %r", esthetic_matrix)
        display_result = int(self.display_test)
        case_result = int(self.case_test)
        # _logger.info('DISPLAY GRADE VALUE: %r', display_result)
        # _logger.info('CASE GRADE VALUE: %r', case_result)
        max_value = max(display_result, case_result)
        grade = esthetic_matrix.get(max_value)
        days = all(record for record in [self.device_case, self.device_charger, self.cables, self.headset])
        if grade == 'A' and days:
            grade = '14 Días'  # todo: get this dynamically
        # _logger.info("TEST GRADE RESULT: %r", grade)
        return grade

    def name_get(self):
        res = []
        for test in self:
            res.append((test.id, test.get_esthetic_result()))
        return res


class FunctionalQualityTest(models.Model):
    _name = 'functional.quality.test'
    _description = 'Product Fucntional Tests'

    # Lot ID
    lot_id = fields.One2many(comodel_name="stock.production.lot", inverse_name="functional_test_id", string="Lot")
    # Test result
    test_pass = fields.Boolean(compute="_compute_functional_test_result", string="Test Pass")

    # Test questions
    power_on = fields.Boolean(string='Power On', default=True)
    speaker = fields.Boolean(string='Speaker', default=True)
    buttons = fields.Boolean(string='Buttons', default=True)
    fingerprint_reader = fields.Boolean(string='Fingerprint Reader', default=True)
    torch = fields.Boolean(string='Torch', default=True)
    bluetooth = fields.Boolean(string='	Bluetooth', default=True)
    wifi = fields.Boolean(string='WiFi', default=True)
    proximity_sensor = fields.Boolean(string='Proximity Sensor', default=True)
    touch_screen = fields.Boolean(string='Touch Screen', default=True)
    display_bright = fields.Boolean(string='Display Bright', default=True)
    call_test = fields.Boolean(string='Call', default=True)
    ring_tone = fields.Boolean(string='Ring Tone', default=True)
    camera = fields.Boolean(string='Camera', default=True)
    mobile_os = fields.Boolean(string='Operating System', default=True)
    user_account = fields.Boolean(string='User Account', default=True)
    security_pattern = fields.Boolean(string='Security Pattern', default=True)
    humidity = fields.Boolean(string='Humidity', default=True)

    def _compute_functional_test_result(self):
        for functional_test in self:
            result = functional_test.get_functional_result()
            functional_test['test_pass'] = result

    def get_functional_result(self):
        """
        Get functional test result
        :return: True or False
        """
        # _logger.info("GETTING FUNCTIONAL TEST RESULT FOR: %r", self.id)
        exclude_fields = ['id', 'display_name', 'create_uid', 'create_date', 'write_uid', 'write_date',
                          '__last_update', 'test_pass', 'lot_id']
        functional_obj = self.env['functional.quality.test']
        fields_to_read = [element for element in functional_obj.fields_get_keys() if element not in exclude_fields]
        # _logger.info("FUNCTIONAL FIELDS TO READ: %r", fields_to_read)
        values = self.read(fields_to_read)[0].values()
        # _logger.info("FUNCTIONAL TEST VALUES: %r", values)
        result = all(record for record in values)
        # _logger.info("FUNCTIONAL TEST RESULT: %r", result)
        return result

    def name_get(self):
        res = []
        for test in self:
            if test.test_pass:
                res.append((test.id, "Funcional"))
            else:
                res.append((test.id, "Con Avería"))
        return res
