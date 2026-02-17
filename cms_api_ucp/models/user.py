# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    secret = fields.Char('Secret')


class OdoocmsStudent(models.Model):
    _inherit = 'odoocms.student'

    secret = fields.Char('Secret')


class OdooCMSAPILog(models.Model):
    _name = 'odoocms.api.log'
    _description = "API Logs"

    name = fields.Char('End Point')
    time = fields.Datetime('Time', default=fields.Datetime.now)
    param_body = fields.Text('Param')
    response_body = fields.Text('Response')
