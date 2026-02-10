from odoo import fields, models, _, api
from datetime import datetime


class EntryTestSlots(models.Model):
    _name = 'odoocms.entry.test.slots'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entry Test Room'

    @api.depends('time_from', 'time_to')
    def _get_time(self):
        for time in self:
            name = str('{0:02.0f}:{1:02.0f}'.format(*divmod(time.time_from * 60, 60))) + ' - ' + str('{0:02.0f}:{1:02.0f}'.format(*divmod(time.time_to * 60, 60)))
            time.name = name

    time_from = fields.Float(string='Time From', required=True)
    time_to = fields.Float(string='Time To', required=True)
    name = fields.Char(string='Name', compute='_get_time', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
