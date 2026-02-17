from odoo import fields, models, api
from odoo.exceptions import UserError
import json
import requests
from datetime import date

class TestDateTransfer(models.TransientModel):

    _name = 'test.date.transfer'
    _description = 'Test Date Transfer'

    
    def _get_paper_ids(self):
        if self.env.context and self.env.context.get('active_ids'):
            return self.env.context.get('active_ids')
        return []

    paper_ids = fields.Many2many('cbt.paper.export', string='paper',default=_get_paper_ids)

    new_date = fields.Date('New Date', required=True)

    def transfer_date(self):
        paper = self.env['cbt.paper.export'].sudo().search(
            [('id', 'in', self.paper_ids.ids)])
        if paper:
            for rec in paper:
                rec.test_date = self.new_date
