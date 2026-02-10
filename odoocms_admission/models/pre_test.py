import pdb

from odoo import fields, models, _, api


class PreTest(models.Model):
    _name = 'odoocms.pre.test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Pre Test'

    name = fields.Char(string='Test Name')
    code = fields.Char(string='Code')
    pre_test_total_marks = fields.Integer(string='Total Marks')
    compulsory = fields.Boolean(string='Compulsory Test')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
