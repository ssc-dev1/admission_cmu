from odoo import fields, models, _, api
from datetime import date


class InvoiceList(models.Model):
    _name = 'invoice.list'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Verified and Unverified Invoice List'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    applicant_id = fields.Many2one('odoocms.application', string='Application')
    fee_voucher = fields.Selection(string='Voucher State', related='applicant_id.fee_voucher_state')
    document_state = fields.Char(string='Documents')
    date_generated = fields.Date(string='Date Generated', default=date.today())
    generate_invoice_id = fields.Many2one('generate.invoice', 'Generate Invoice ID')
    merit_id = fields.Many2one('odoocms.merit.registers', 'Merit List')
    program_id = fields.Many2one('odoocms.program', 'Program')
    invoice_id = fields.Many2one('account.move', 'Invoice')

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)
