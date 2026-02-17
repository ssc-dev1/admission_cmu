# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdoocmsUnconfirmedPaidBankChallan(models.Model):
    _name = 'odoocms.unconfirmed.paid.bank.challan'
    _description = 'Unconfirmed Paid Bank Challans'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    sequence = fields.Integer('Sequence', default=10)
    name = fields.Char('Challan No')
    invoice_id = fields.Many2one('account.move', 'Invoice')
    challan_amount = fields.Float('Challan Amount')
    received_amount = fields.Float('Received Amount', tracking=True)
    bank = fields.Char('Bank')
    transaction_id = fields.Char('Transaction', tracking=True)
    transaction_date = fields.Date('Transaction Date')
    transaction_time = fields.Char('Transaction Time')
    processed_date = fields.Date('Processed Date')
    processed = fields.Boolean('Processed', default=False)
    type = fields.Selection([('1', 'System Error'),
                             ('2', 'Invalid Username or Password'),
                             ('3', 'Incorrect Challan Number'),
                             ('4', 'Already Paid'),
                             ('5', 'Amount Is Not Correct'),
                             ('6', 'Bill Not Payable'),
                             ('9', 'Inactive Account Status'),
                             ('10', 'Closed Account Status'),
                             ('11', 'Transaction Id Duplication')], string='Type', tracking=True)
    journal_id = fields.Many2one('account.journal', 'Bank Journal')
    payment_id = fields.Many2one('odoocms.fee.payment', 'Fee Payment')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)
    notes = fields.Char('Notes')

    def action_button_process(self):
        journal_id = self.journal_id
        if not journal_id:
            journal_id = self.env['account.journal'].search([('type', '=', 'bank')], order='id asc', limit=1)

        # ***** Create and Post the Challan Payment *****#
        already_paid = self.env['account.move'].search([('id', '=', self.invoice_id.id), ('payment_state', 'in', ('paid', 'in_payment '))])
        if not already_paid:
            payment_obj = self.env['odoocms.fee.payment'].sudo()
            payment_rec = payment_obj.fee_payment_record(self.invoice_id, self.name, journal_id, self.transaction_date)
            payment_rec.sudo().action_post_fee_payment()

            # ***** Update Invoice Data *****#
            invoice_data = {
                'payment_date': self.transaction_date,
                'paid_time': self.transaction_time,
                'transaction_id': self.transaction_id,
                'payment_state': 'paid',
            }
            self.invoice_id.sudo().write(invoice_data)

            # ***** Update Unconfirmed Paid Bank Challan Data *****#
            self.write({'processed': True,
                        'payment_id': payment_rec and payment_rec.id or False,
                        'processed_date': fields.Date.today()})

        else:
            self.write({'processed': True,
                        'processed_date': fields.Date.today(),
                        'notes': 'Already Paid in the System'})
