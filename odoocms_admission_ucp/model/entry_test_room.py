import pdb

from odoo import fields, models, _, api


class EntryTestRoom(models.Model):
    _name = 'odoocms.entry.test.room'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entry Test Room'

    name = fields.Char(string='Room Name')
    code = fields.Char(string='Code')
    capacity = fields.Integer(string='Capacity')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

