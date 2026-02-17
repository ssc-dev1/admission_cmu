# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    api_user = fields.Char('API User')
