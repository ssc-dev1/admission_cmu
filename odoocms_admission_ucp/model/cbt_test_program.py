from odoo import models, fields

class CbtTestProgram(models.Model):
    _name = 'cbt.test.program'

    name = fields.Char(string='Test Name')
    test_program_ids = fields.Many2many('odoocms.program', string='Test Program')
    