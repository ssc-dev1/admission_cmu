import pdb

from odoo import fields, models, _, api


class LastInstituteAttend(models.Model):
    _name = 'last.institute.attend'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Last Institute Attend'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

