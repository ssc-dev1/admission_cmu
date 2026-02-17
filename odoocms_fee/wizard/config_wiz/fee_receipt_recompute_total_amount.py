# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class FeeReceiptRecomputeTotalAmount(models.TransientModel):
    _name = 'fee.receipt.recompute.total.amount'
    _description = 'Recompute Receipt Total Amount'

    @api.model
    def _get_invoice(self):
        if self.env.context.get('active_model', False)=='account.move' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    invoice_id = fields.Many2one('account.move', string='Invoices', help="""Only selected Invoices will be Processed.""", default=_get_invoice)

    def action_recompute_total_amount(self):
        if self.invoice_id:
            if self.invoice_id.payment_state not in ('in_payment', 'paid'):
                self.invoice_id._compute_amount()
        else:
            raise UserError(_("This action cannot be performed on Paid or Cancel Receipts. This Receipt State is in %s") % self.invoice_id.payment_state)
        return {'type': 'ir.actions.act_window_close'}
