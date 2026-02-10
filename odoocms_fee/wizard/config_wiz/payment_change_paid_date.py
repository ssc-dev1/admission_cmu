# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class FeePaymentPaidDate(models.TransientModel):
    _name = 'fee.payment.paid.date'
    _description = 'Change Payment Date'

    @api.model
    def _get_invoices(self):
        if self.env.context.get('active_model', False) == 'odoocms.fee.payment' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    payment_ids = fields.Many2many('odoocms.fee.payment', 'fee_payment_date_change_rel', 'wiz_id', 'payment_id', string='Payments', default=_get_invoices)
    new_paid_date = fields.Date('Paid Date')

    def change_payment_date(self):
        for payment_id in self.payment_ids.sudo():
            if not payment_id.date:
                raise UserError("No Payment Date for Student %s Found" % payment_id.student_id.code)

            prev_paid_date = payment_id.date
            payment_id.date = self.new_paid_date
            payment_id.payment_id.date = self.new_paid_date
            body = 'Payment Date changed from %s to %s' % (prev_paid_date.strftime("%d/%m/%Y"), self.new_paid_date.strftime("%d/%m/%Y"))
            payment_id.message_post(body=body)
        return {'type': 'ir.actions.act_window_close'}
