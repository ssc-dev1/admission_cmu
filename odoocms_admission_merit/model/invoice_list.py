import pdb

from odoo import fields, models, _, api


class InvoiceList(models.Model):
    _name = 'invoice.list'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Verified and Unverified Invoice List'

    applicant_id = fields.Many2one('odoocms.application', string='Application')
    fee_voucher = fields.Selection(string='Voucher State', related='applicant_id.fee_voucher_state')
    document_state = fields.Char(string='Documents')

