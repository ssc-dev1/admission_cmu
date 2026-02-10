import pdb

from odoo import fields, models, _, api
from datetime import datetime, date

class InvoiceList(models.Model):
    _name = 'invoice.list'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Verified and Unverified Invoice List'

    # applicant_id = fields.Many2one('odoocms.application', string='Application')
    # fee_voucher = fields.Selection(string='Voucher State', related='applicant_id.fee_voucher_state')
    # document_state = fields.Char(string='Documents')
    # date_generated = fields.Date(string='Date Generated', default=date.today())
    invoice_gen_id = fields.Many2one('generate.invoice')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

