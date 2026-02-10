# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PaymentBankChangeWiz(models.TransientModel):
    _name = 'payment.bank.change.wiz'
    _description = 'Payment Bank Change Wizard'

    @api.model
    def _get_payment_register(self):
        if self.env.context.get('active_model', False) == 'odoocms.fee.payment.register' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    @api.model
    def _get_old_bank_journal(self):
        bank_journal = False
        if self.env.context.get('active_model', False) == 'odoocms.fee.payment.register' and self.env.context.get('active_id', False):
            bank_journal = self.env['odoocms.fee.payment.register'].browse(self.env.context['active_id']).journal_id
        return bank_journal and bank_journal.id or False

    payment_register_id = fields.Many2one('odoocms.fee.payment.register', string='Payment Register', default=_get_payment_register)
    old_bank_journal_id = fields.Many2one('account.journal', string='Old Bank Journal', default=_get_old_bank_journal)
    bank_journal_id = fields.Many2one('account.journal', string='New Bank Journal', required=True)

    def action_change_payment_bank(self):
        if self.old_bank_journal_id == self.bank_journal_id:
            raise UserError('New Bank Journal and Old Bank Journal Should be Different')

        account_payment_ids = self.payment_register_id.fee_payment_ids.mapped('payment_id')
        for account_payment_id in account_payment_ids:
            account_payment_id.action_draft()
            account_payment_id.action_cancel()

        # if account_payment_ids:
        #     raise UserError('Please Cancel Account Payments First')

        self.payment_register_id.write({
            'journal_id': self.bank_journal_id.id,
            'state': 'Draft',
        })

        return {'type': 'ir.actions.act_window_close'}
