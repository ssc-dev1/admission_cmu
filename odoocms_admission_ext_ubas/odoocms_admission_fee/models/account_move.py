# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    application_id = fields.Many2one('odoocms.application', 'Application')
    application_ref_no = fields.Char(related='application_id.application_no', string='Application No')


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    study_scheme_line = fields.Many2one('odoocms.study.scheme.line', string='Study Scheme Line')
