# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class FeeChallanMergeWiz(models.TransientModel):
    _name = 'fee.challan.merge.wiz'
    _description = """This Wizard Will Merge Selected Challan Into One"""

    @api.model
    def _get_invoices(self):
        active_model, active_ids = self.env.context.get('active_model'), self.env.context.get('active_ids')
        if active_model == 'account.move' and active_ids:
            moves = self.env['account.move'].search([('id', 'in', active_ids),
                                                     ('payment_state', 'not in', ('paid', 'in_payment'))
                                                     ])
            return moves and moves.ids or []
        else:
            return []

    invoice_ids = fields.Many2many('account.move', 'challan_merge_wiz_invoice_rel1', 'merge_id', 'move_id', string='Invoices', default=_get_invoices)

    def action_challan_merging(self):
        if not self.invoice_ids or len(self.invoice_ids) == 1:
            raise UserError(_('Please select more than one Invoice/Challan for Merging.'))
        if len(self.invoice_ids.mapped('student_id')) > 1:
            raise UserError(_('You Can Not Merge Different Student Invoices/Challan'))

        main_invoice = self.invoice_ids.sorted(key=lambda inv: inv.id, reverse=False)[0]
        sub_invoices = self.invoice_ids - main_invoice
        receivable_main_inv_line = main_invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable' and "INV" in l.name)
        invoice_tuition_fee = main_invoice.tuition_fee

        updated_debit_amount = receivable_main_inv_line.price_unit
        merged_invoice_amount = 0
        sub_misc_amount = 0
        main_misc_amount = sum(line.price_subtotal for line in main_invoice.invoice_line_ids if line.fee_category_id and line.fee_category_id.name not in ('Tuition Fee', 'Hostel Fee'))
        for sub_invoice in sub_invoices:
            sub_misc_amount = sum(line.price_subtotal for line in sub_invoice.invoice_line_ids if line.fee_category_id and line.fee_category_id.name not in ('Tuition Fee', 'Hostel Fee'))
            invoice_tuition_fee += sub_invoice.tuition_fee
            # ***** Receivable Line *****#
            receivable_inv_line = sub_invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable' and "INV" in l.name)
            updated_debit_amount += receivable_inv_line.price_unit

            merged_invoice_amount = 0
            for line in sub_invoice.line_ids:
                if line.credit > 0:
                    search_main_inv_line = main_invoice.line_ids.filtered(lambda a: a.name == line.name)
                    if search_main_inv_line:
                        line_updated_price_unit = search_main_inv_line.price_unit + line.price_unit
                        search_main_inv_line.with_context(check_move_validity=False).write({'price_unit': line_updated_price_unit})
                        merged_invoice_amount += search_main_inv_line.credit
            self._cr.commit()

        # ***** Update Main Challan Receivable Line *****#
        merged_invoice_amount = merged_invoice_amount + main_misc_amount + sub_misc_amount
        if not merged_invoice_amount == abs(updated_debit_amount):
            diff = abs(updated_debit_amount) - merged_invoice_amount
            updated_debit_amount = updated_debit_amount + diff

        receivable_main_inv_line.with_context(check_move_validity=False).write({'price_unit': updated_debit_amount})

        main_invoice.write({
            'prev_challan_no': main_invoice.old_challan_no,
            'tuition_fee': invoice_tuition_fee,
            'payment_state': 'not_paid'
        })
        main_invoice.old_challan_no = self.env['ir.sequence'].next_by_code('odoocms.fee.receipt.challan.sequence')

        # If Waiver Percentage is given and Waiver Amount is Zero
        if main_invoice.waiver_percentage > 0 and main_invoice.waiver_amount == 0:
            if main_invoice.student_id.course_ids.filtered(lambda a: a.state == 'current'):
                total_fee = 0
                credit_hours = 0
                courses = main_invoice.student_id.course_ids.filtered(lambda a: a.state == 'current')
                per_credit_hour_fee = main_invoice.student_id.batch_id.per_credit_hour_fee
                for course in courses:
                    total_fee += course.credits * per_credit_hour_fee
                    credit_hours += course.credits
                waiver_amount = round(total_fee * (main_invoice.waiver_percentage / 100))
                main_invoice.waiver_amount = waiver_amount

        sub_invoices.sudo().unlink()

        return {'type': 'ir.actions.act_window_close'}
