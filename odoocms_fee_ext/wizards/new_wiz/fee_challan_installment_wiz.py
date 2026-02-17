# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import pdb


class FeeChallanInstallmentWiz(models.TransientModel):
    _name = "fee.challan.installment.wiz"
    _description = """Challan Installment"""

    @api.model
    def _get_invoice(self):
        if self.env.context.get('active_model', False) == 'account.move' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    @api.model
    def _get_invoice_total(self):
        amt = 0
        if self.env.context.get('active_model', False) == 'account.move' and self.env.context.get('active_id', False):
            move = self.env['account.move'].browse(self.env.context['active_id'])
            if move:
                amt = move.amount_total
        return amt

    invoice_id = fields.Many2one('account.move', 'Invoice', default=_get_invoice)
    total_amount = fields.Float('Total Amount', default=_get_invoice_total)
    installment_amount = fields.Float('Installment Amount')
    invoice_date_due = fields.Date('Due Date', default=fields.Date.today())
    value_type = fields.Selection([('fixed', 'Fixed'),
                                   ('percentage', 'Percentage'),
                                   ], default='fixed', string="Type")

    def action_challan_installments(self):
        if self.value_type == 'percentage' and self.installment_amount > 100:
            raise UserError(_('Value Should be less than 100%'))
        if self.value_type == 'fixed' and self.installment_amount > self.invoice_id.amount_total:
            raise UserError(_('Installment Value Should be less than Invoice Value'))

        if self.value_type == 'fixed':
            percentage = self.installment_amount / self.invoice_id.amount_total
        else:
            percentage = self.installment_amount / 100

        new_invoice = self.invoice_id.copy(
            default={
                'name': '',
                'state': 'draft',
                'invoice_date_due': self.invoice_date_due,
                'invoice_date': fields.Date.context_today(self),
                'invoice_line_ids': False,
                'line_ids': [],
                'waiver_amount': 0.0,
                'payment_state': 'not_paid',
                'first_installment': False,
                'second_installment': True,
                'posted_before': False,
            }
        )
        new_invoice.write({'back_invoice': self.invoice_id.id})
        self.invoice_id.forward_invoice = new_invoice.id

        lines = []
        lines_total = 0
        for line in self.invoice_id.invoice_line_ids:
            analytic_tag_ids = [(4, analytic_tag.id, None) for analytic_tag in line.analytic_tag_ids]
            # amount = round(line.price_subtotal / 2, 3)
            amount = round(line.price_unit * percentage, 3)
            new_inv_amount = line.price_unit - amount
            discounted_amt = amount
            if line.discount > 0:
                discounted_amt = amount - (amount * (line.discount / 100))
            fee_line = {
                'price_unit': new_inv_amount,
                'quantity': 1.00,
                'product_id': line.product_id.id,
                'name': line.name and line.name or '',
                'account_id': line.fee_head_id.property_account_income_id.id,
                'analytic_tag_ids': analytic_tag_ids,
                'move_id': new_invoice.id,
                'fee_head_id': line.fee_head_id and line.fee_head_id.id or False,
                'exclude_from_invoice_tab': False,
                'discount': line.discount,
                'course_id_new': line.course_id_new and line.course_id_new.id or False,
                'registration_id': line.registration_id and line.registration_id.id or False,
                'registration_line_id': line.registration_line_id and line.registration_line_id.id or False,
                'course_credit_hours': line.course_credit_hours,
                'career_id': line.career_id and line.career_id.id or False,
                'term_id': line.term_id and line.term_id.id or False,
                'batch_id': line.batch_id and line.batch_id.id or False,
            }
            lines.append((0, 0, fee_line))
            # lines_total += amount
            lines_total += discounted_amt
            if line.credit > 0.0:
                self.env.cr.execute("update account_move_line set "
                                    "price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                    , (amount, discounted_amt, -discounted_amt, -discounted_amt, discounted_amt, discounted_amt, line.id))
            if line.debit > 0.0:
                self.env.cr.execute("update account_move_line set "
                                    "price_unit = %s, debit=%s, balance=%s, amount_currency=%s,price_subtotal=%s, price_total=%s, amount_residual=%s where id=%s \n"
                                    , (-amount, discounted_amt, discounted_amt, discounted_amt, -discounted_amt, -discounted_amt, discounted_amt, line.id))

        new_invoice.invoice_line_ids = lines
        # Update OLD invoice Total
        invoice_amount = lines_total
        self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                            , (invoice_amount, invoice_amount, invoice_amount, invoice_amount, invoice_amount, invoice_amount, self.invoice_id.id))

        # Update OLD Debit (Receivable Entry)
        debit_entry_id = self.env['account.move.line'].search([('move_id', '=', self.invoice_id.id), ('account_id.user_type_id.name', '=', 'Receivable')])  # 6=> 121000 Receivable
        if debit_entry_id:
            debit_entry_id = debit_entry_id[0]
            self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s, amount_currency=%s, price_subtotal=%s, price_total=%s, amount_residual=%s where id=%s \n"
                                , (-invoice_amount, invoice_amount, invoice_amount, invoice_amount, -invoice_amount, -invoice_amount, invoice_amount, debit_entry_id.id))
        self._cr.commit()

        # waiver handling
        if self.invoice_id.waiver_amount > 0:
            student_fee_waiver_rec = self.env['odoocms.student.fee.waiver'].search([('student_id', '=', self.invoice_id.student_id.id),
                                                                                    ('invoice_id', '=', self.invoice_id.id),
                                                                                    ], order='id desc', limit=1)
            if student_fee_waiver_rec:
                split_waiver_amount = self.invoice_id.waiver_amount * percentage
                self.invoice_id.waiver_amount = split_waiver_amount
                new_invoice.waiver_amount = split_waiver_amount

                new_student_fee_waiver_rec = student_fee_waiver_rec.copy()
                student_fee_waiver_rec.amount = split_waiver_amount
                new_student_fee_waiver_rec.write({'invoice_id': new_invoice.id,
                                                  'amount': split_waiver_amount,
                                                  'name': student_fee_waiver_rec.name + "-1"})

        # Student Ledger Handling
        student_ledger_rec = self.env['odoocms.student.ledger'].search([('student_id', '=', self.invoice_id.student_id.id),
                                                                        ('invoice_id', '=', self.invoice_id.id)], order='id desc', limit=1)
        if student_ledger_rec:
            # Old Entry
            student_ledger_rec.write({'credit': self.invoice_id.amount_total})

            # New Entry
            new_student_ledger_rec = student_ledger_rec.copy()
            new_invoice.write({'student_ledger_id': new_student_ledger_rec.id})
            new_student_ledger_rec.write({'credit': new_invoice.amount_total,
                                          'invoice_id': new_invoice.id})
        self._cr.commit()
        moves = self.invoice_id + new_invoice
        if moves:
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', moves.ids)],
                'name': _('Student Challans'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
