from odoo import models, fields, api, _


class ResCompany(models.Model):
    _inherit = 'res.company'

    timesheet_mail_employee_interval = fields.Integer(string='Timesheet Reminder Interval')
