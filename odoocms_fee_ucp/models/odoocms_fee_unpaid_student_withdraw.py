# -*- coding: utf-8 -*-
import pdb
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdoocmsFeeUnpaidStudentsWithdraw(models.Model):
    _name = 'odoocms.fee.unpaid.student.withdraw'
    _description = 'Fee Unpaid Students Withdraw'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Date('Start Date', default=fields.Date.today(), tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term, tracking=True)
    state = fields.Selection([('draft', 'New'), ('withdraw', 'Withdraw'), ('cancel', 'Cancel')], string='Status', default='draft', tracking=True)

    lines = fields.One2many('odoocms.fee.unpaid.student.withdraw.line', 'withdraw_id', 'Lines')
    to_be = fields.Boolean('To Be', default=True)
    remarks = fields.Text('Remarks')

    def action_get_students(self):
        # ***** First Delete Existing Lines *****#
        if self.lines:
            self.lines.sudo().unlink()

        # ***** Prepare Domain *****#
        challan_type = ['main_challan', '2nd_challan', 'add_drop', 'installment']
        payment_state = ['paid', 'in_payment', 'partial']
        label_ids = self.env['account.payment.term.label'].search([('type','!=','other')])
        domain = [('state', '=', 'draft'),('label_id', 'in', label_ids.ids),('amount_total', '>', 0),('term_id', '=', self.term_id.id)]
        student_ids = self.env['odoocms.fee.barcode'].search(domain, order='student_id').mapped('student_id')

        for student_id in student_ids:
            student_domain = [('student_id', '=', student_id.id), ('state', '=', 'draft'), ('label_id', 'in', label_ids.ids),
                ('amount_residual', '>', 0), ('term_id', '=', self.term_id.id)]
            challans = self.env['odoocms.fee.barcode'].search(student_domain, order='student_id')

            total_dues = sum(challan.amount_residual for challan in challans)
            line_values = {
                'student_id': student_id.id,
                'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                'program_id': student_id.program_id and student_id.program_id.id or False,
                'total_dues': total_dues,
                'unpaid_challans': [(6, 0, challans.ids)],
                'withdraw_id': self.id
            }
            self.env['odoocms.fee.unpaid.student.withdraw.line'].sudo().create(line_values)

    def action_withdraw(self):
        if not self.lines:
            raise UserError("Line Detail Not Found")
        for line in self.lines:
            for inv in line.unpaid_invoices:
                amt = 0
                if inv.line_ids:
                    self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s,credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,course_gross_fee=%s,"
                                        "discount=%s,amount_residual=%s,amount_residual_currency=%s where id in %s \n"
                                        , (amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, tuple(inv.line_ids.ids)))

                # Invoice Total Update
                self.env.cr.execute("update account_move set amount_tax=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s,amount_tax_signed=%s, amount_total_signed=%s,"
                                    " amount_residual_signed=%s,admission_fee=%s,tuition_fee=%s,misc_fee=%s,hostel_fee=%s,fine_amount=%s,tax_amount=%s,fine_policy_amount=%s,"
                                    "semester_gross_fee=%s,waiver_amount=%s,waiver_percentage=%s,payment_state=%s where id=%s \n"
                                    , (amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, amt, 'paid', inv.id))
                self._cr.commit()
                inv.student_ledger_id.write({'credit': 0, 'description': 'Waived Due to Student Courses With Draw'})
        self.state = 'withdraw'

    def action_cancel(self):
        self.state = 'cancel'
        self.lines.write({'state': 'cancel'})

    @api.model
    def create(self, values):
        result = super(OdoocmsFeeUnpaidStudentsWithdraw, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.unpaid.student.withdraw')
        return result

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('You can delete the Records that are in the Draft State.'))
        return super(OdoocmsFeeUnpaidStudentsWithdraw, self).unlink()


class OdoocmsFeeUnpaidStudentsWithdrawLine(models.Model):
    _name = 'odoocms.fee.unpaid.student.withdraw.line'
    _description = 'Fee Unpaid Students Withdraw Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')
    program_id = fields.Many2one('odoocms.program', 'Program')
    total_dues = fields.Float('Total Dues')
    state = fields.Selection([('draft', 'New'), ('withdraw', 'Withdraw'), ('cancel', 'Cancel')], string='Status', default='draft', tracking=True)
    registration_status = fields.Selection(related='student_id.state', store=True, string='Registration Status')
    remarks = fields.Char('Remarks')
    withdraw_id = fields.Many2one('odoocms.fee.unpaid.student.withdraw', 'Withdraw Ref', index=True, ondelete='cascade', auto_join=True)
    unpaid_invoices = fields.Many2many('account.move', 'fee_unpaid_student_withdraw_inv_rel', 'withdraw_id', 'invoice_id', 'Invoices')
    unpaid_challans = fields.Many2many('odoocms.fee.barcode', 'fee_unpaid_withdraw_challan_rel', 'withdraw_id', 'challan_id', 'Challans')

    @api.model
    def create(self, values):
        result = super(OdoocmsFeeUnpaidStudentsWithdrawLine, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.unpaid.student.withdraw.line')
        return result
