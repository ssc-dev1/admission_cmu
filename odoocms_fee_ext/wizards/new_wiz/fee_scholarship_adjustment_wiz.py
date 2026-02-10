# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
import json


class FeeScholarshipAdjustmentWiz(models.TransientModel):
    _name = "fee.scholarship.adjustment.wiz"
    _description = """Fee Scholarship Adjustment"""

    @api.model
    def _get_student(self):
        student_id = self.env['odoocms.student'].browse(self._context.get('active_id', False))
        return student_id

    def _get_term_id(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    def _get_current_scholarship(self):
        student_id = self.env['odoocms.student'].browse(self._context.get('active_id', False))
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        current_term_invoice = self.env['account.move'].search([('student_id', '=', student_id.id), ('term_id', '=', term_id.id), ('challan_type', '=', 'main_challan')], order='id asc', limit=1)
        if current_term_invoice:
            scholarship_id = current_term_invoice.waiver_ids.ids[0]
            return scholarship_id

    def _get_current_scholarship_value(self):
        student_id = self.env['odoocms.student'].browse(self._context.get('active_id', False))
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        current_term_invoice = self.env['account.move'].search([('student_id', '=', student_id.id), ('term_id', '=', term_id.id), ('challan_type', '=', 'main_challan')], order='id asc', limit=1)
        if current_term_invoice:
            scholarship_value = current_term_invoice.waiver_percentage
            return scholarship_value

    student_id = fields.Many2one('odoocms.student', 'Student', default=_get_student)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_term_id)
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    scholarship_value = fields.Float('Scholarship Value', related='scholarship_id.amount')

    current_scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Current Scholarship', compute='_compute_fee_detail', compute_sudo=True)
    current_scholarship_value = fields.Float('Current Scholarship %', compute='_compute_fee_detail', compute_sudo=True)
    current_scholarship_amount = fields.Float('Current Scholarship Amount', compute='_compute_fee_detail', compute_sudo=True)

    total_fee = fields.Float('Total Fee', compute='_compute_fee_detail', store=True, compute_sudo=True)
    total_fee_after_discount = fields.Float('Fee After Discount', compute='_compute_fee_detail', store=True, compute_sudo=True)
    paid_fee = fields.Float('Paid Fee', compute='_compute_fee_detail', store=True, compute_sudo=True)
    unpaid_fee = fields.Float('UnPaid Fee', compute='_compute_fee_detail', store=True, compute_sudo=True)
    total_waiver = fields.Float('Total Waiver', compute='_compute_fee_detail', store=True, compute_sudo=True)
    paid_waiver = fields.Float('Paid Waiver', compute='_compute_fee_detail', store=True, compute_sudo=True)
    unpaid_waiver = fields.Float('UnPaid Waiver', compute='_compute_fee_detail', store=True, compute_sudo=True)
    total_credit_hours = fields.Float('Credit Hours', compute='_compute_fee_detail', store=True, compute_sudo=True)
    per_credit_hour_fee = fields.Float('Per Credit Hour Fee', compute='_compute_fee_detail', store=True, compute_sudo=True)

    new_scholarship_amount = fields.Float('New Scholarship Amount', compute="_compute_new_scholarship_amount", store=True, compute_sudo=True)
    scholarship_amount_diff = fields.Float('Scholarship Amount Diff', compute="_compute_new_scholarship_amount", store=True, compute_sudo=True)

    scholarship_id_domain = fields.Char(compute="_compute_scholarship_domain", store=False, compute_sudo=True)

    @api.depends('student_id', 'term_id')
    def _compute_scholarship_domain(self):
        for rec in self:
            s_list = []
            full_fee_scholarship = self.env['odoocms.fee.waiver'].search([('name', '=', 'Full Fee')])
            if full_fee_scholarship:
                s_list.append(full_fee_scholarship.id)
            if self.student_id.scholarship_eligibility_ids:
                scholarships = self.student_id.scholarship_eligibility_ids.mapped('scholarship_id')
                s_list = s_list + scholarships.ids
            rec.scholarship_id_domain = json.dumps([('id', 'in', s_list)])

    @api.depends('student_id')
    def _compute_fee_detail(self):
        for rec in self:
            total_fee = 0
            paid_fee = 0
            unpaid_fee = 0
            paid_waivers = 0
            unpaid_waivers = 0
            current_scholarship = False
            current_scholarship_value = 0
            credit_hours = 0

            if rec.student_id:
                per_credit_hour_fee = rec.student_id.batch_id and rec.student_id.batch_id.per_credit_hour_fee or 0.0
                courses = rec.student_id.course_ids.filtered(lambda a: a.state in ('draft', 'current'))
                for course in courses:
                    total_fee += course.credits * rec.student_id.batch_id.per_credit_hour_fee
                    credit_hours += course.credits
                invoices = self.env['account.move'].search([('student_id', '=', rec.student_id.id),
                                                            ('challan_type', 'not in', ('hostel_fee', 'misc_challan', 'prospectus_challan')),
                                                            ('term_id', '=', rec.term_id.id)])

                # For Current Scholarship Info
                for inv in invoices.filtered(lambda a: a.payment_state not in ('paid', 'in_payment', 'partial')):
                    if not current_scholarship and inv.waiver_ids:
                        current_scholarship = inv.waiver_ids[0]
                        current_scholarship_value = inv.waiver_percentage

                if not current_scholarship:
                    applied_scholarship = self.env['odoocms.student.applied.scholarships'].sudo().search([('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id)])
                    if applied_scholarship:
                        current_scholarship = applied_scholarship.scholarship_id
                        current_scholarship_value = applied_scholarship.scholarship_percentage

                for invoice in invoices:
                    if not current_scholarship and invoice.challan_type == '2nd_challan' and invoice.waiver_ids:
                        current_scholarship = invoice.waiver_ids[0]
                        current_scholarship_value = invoice.waiver_percentage
                    elif not current_scholarship and invoice.challan_type in ('main_challan', 'admission') and invoice.waiver_ids:
                        current_scholarship = invoice.waiver_ids[0]
                        current_scholarship_value = invoice.waiver_percentage

                    if invoice.payment_state in ('paid', 'in_payment'):
                        paid_fee += invoice.amount_total
                    elif invoice.payment_state not in ('paid', 'in_payment'):
                        unpaid_fee += invoice.amount_total

                if not current_scholarship:
                    current_scholarship = rec.student_id.scholarship_id and rec.student_id.scholarship_id or False
                    if current_scholarship:
                        current_scholarship_value = current_scholarship.amount

                total_waivers = round(total_fee * (current_scholarship_value / 100))
                if unpaid_fee > 0:
                    paid_waivers, unpaid_waivers = total_waivers / 2, total_waivers / 2
                elif unpaid_fee == 0:
                    paid_waivers, unpaid_waivers = total_waivers, 0

                total_fee_after_discount = total_fee - total_waivers
                rec.write({'total_fee': total_fee,
                           'total_waiver': total_waivers,
                           'paid_fee': paid_fee,
                           'unpaid_fee': unpaid_fee,
                           'paid_waiver': paid_waivers,
                           'unpaid_waiver': unpaid_waivers,
                           'total_fee_after_discount': total_fee_after_discount,
                           'current_scholarship_id': current_scholarship.id if current_scholarship else False,
                           'current_scholarship_value': current_scholarship_value,
                           'total_credit_hours': credit_hours,
                           'per_credit_hour_fee': per_credit_hour_fee})

    @api.depends('scholarship_id', 'scholarship_value')
    def _compute_new_scholarship_amount(self):
        for rec in self:
            scholarship_amount = round(rec.total_fee * (rec.scholarship_value / 100))
            rec.new_scholarship_amount = scholarship_amount
            rec.scholarship_amount_diff = scholarship_amount - rec.total_waiver

    def action_fee_scholarship_adjustment(self):
        # self.check_program_term()
        exclude_challan_type_value = ['misc_challan', 'hostel_fee', 'prospectus_challan']
        challan_payment_status_values = ['partial', 'in_payment', 'paid']
        od_amount, unpaid_amount, unpaid_waivers, total_credit_sum = 0, 0, 0, 0
        invoices = self.env['account.move'].sudo().search([('student_id', '=', self.student_id.id),
                                                           ('term_id', '=', self.term_id.id),
                                                           ('challan_type', 'not in', exclude_challan_type_value)])

        paid_invoices = invoices.sudo().filtered(lambda a: a.payment_state in challan_payment_status_values)
        unpaid_invoices = invoices.sudo().filtered(lambda a: a.payment_state not in challan_payment_status_values)
        for unpaid_invoice in unpaid_invoices:
            unpaid_amount += unpaid_invoice.amount_total
            unpaid_waivers += unpaid_invoice.waiver_amount

        if len(unpaid_invoices) > 1:
            raise UserError(_("Please Merge the Invoices that not Paid"))

        # ***** If Difference is Zero *****#
        if self.scholarship_amount_diff == 0:
            # *****  Update Student Ledger *****#
            unpaid_invoices.write({'waiver_ids': [(6, 0, self.scholarship_id.ids)],
                                   'waiver_percentage': self.scholarship_value})

        # If Scholarship Diff is Greater than Zero
        elif self.scholarship_amount_diff > 0:
            # ***** if Term Invoices are Paid *****#
            if len(invoices) == len(paid_invoices):
                od_amount = abs(self.scholarship_amount_diff)

            # ***** If scholarship diff amount is Greater than Unpaid Invoices means To Give More Benefit *****#
            elif self.scholarship_amount_diff > unpaid_amount:
                credit_amount = 0
                debit_amt = 0
                od_amount = self.scholarship_amount_diff - unpaid_amount
                receivable_line = unpaid_invoices.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')

                for line in unpaid_invoices.invoice_line_ids.filtered(lambda ln: ln.fee_category_id.name == "Tuition Fee" and ln.course_credit_hours > 0):
                    if line.credit > 0:
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,discount=0 where id=%s \n"
                                            , (credit_amount, credit_amount, -credit_amount, -credit_amount, credit_amount, credit_amount, line.id))
                # ***** Receivable Line, it will debit *****#
                self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                    , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                # ***** Invoice Total Update *****#
                self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s,amount_total_in_currency_signed=%s where id=%s \n"
                                    , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, unpaid_invoices.id))
                self._cr.commit()
                # *****  Update Student Ledger *****#
                unpaid_invoices.write({'waiver_ids': [(6, 0, self.scholarship_id.ids)],
                                       'waiver_percentage': self.scholarship_value,
                                       'waiver_amount': self.new_scholarship_amount})
                unpaid_invoices.sudo()._compute_fee_detail()

            # ***** If Scholarship Diff Amount is Less than
            elif self.scholarship_amount_diff <= unpaid_amount:
                per_credit_hour_discount = round(self.scholarship_amount_diff / self.total_credit_hours)
                receivable_line = unpaid_invoices.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
                for line in unpaid_invoices.invoice_line_ids.filtered(lambda ln: ln.fee_category_id.name == "Tuition Fee" and ln.course_credit_hours > 0):
                    if line.credit > 0:
                        line_discount = round(per_credit_hour_discount * line.course_credit_hours)
                        credit_amount = line.price_total - line_discount
                        if credit_amount < 0:
                            credit_amount = 0

                        # ***** Update Credit Line *****#
                        total_credit_sum += credit_amount
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,discount=0 where id=%s \n"
                                            , (credit_amount, credit_amount, -credit_amount, -credit_amount, credit_amount, credit_amount, line.id))
                debit_amt = receivable_line.debit - self.scholarship_amount_diff
                if debit_amt < 0:
                    debit_amt = 0

                # To Manage The Decimal Differences
                if total_credit_sum != debit_amt:
                    debit_amt += total_credit_sum - debit_amt
                    # ***** Receivable Line, it will debit *****#
                self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                    , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                # ***** Invoice Total Update *****#
                self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s,amount_total_in_currency_signed=%s where id=%s \n"
                                    , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, unpaid_invoices.id))
                self._cr.commit()

                # *****  Update Student Ledger *****#
                unpaid_invoices.student_ledger_id.credit = debit_amt
                unpaid_invoices.write({'waiver_ids': [(6, 0, self.scholarship_id.ids)],
                                       'waiver_percentage': self.scholarship_value,
                                       'waiver_amount': self.new_scholarship_amount})
                unpaid_invoices.sudo()._compute_fee_detail()

        # ***** If Scholarship Diff Amount Less Than Zero Means To Deduct The Given Scholarship *****#
        elif self.scholarship_amount_diff < 0:
            if unpaid_invoices:
                per_credit_hour_discount = round(abs(self.scholarship_amount_diff) / self.total_credit_hours)
                receivable_line = unpaid_invoices.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
                for line in unpaid_invoices.invoice_line_ids.filtered(lambda ln: ln.fee_category_id.name == "Tuition Fee" and ln.course_credit_hours > 0):
                    if line.credit > 0:
                        line_discount = round(per_credit_hour_discount * line.course_credit_hours)
                        credit_amount = line.price_total + line_discount
                        if credit_amount < 0:
                            credit_amount = 0

                        # ***** Update Credit Line *****#
                        total_credit_sum += credit_amount
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,discount=0 where id=%s \n"
                                            , (credit_amount, credit_amount, -credit_amount, -credit_amount, credit_amount, credit_amount, line.id))
                debit_amt = receivable_line.debit + abs(self.scholarship_amount_diff)
                if debit_amt < 0:
                    debit_amt = 0

                # To Manage The Decimal Differences
                if total_credit_sum != debit_amt:
                    debit_amt += total_credit_sum - debit_amt
                    # ***** Receivable Line, it will debit *****#
                self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                    , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                # ***** Invoice Total Update *****#
                self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s,amount_total_in_currency_signed=%s where id=%s \n"
                                    , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, unpaid_invoices.id))
                self._cr.commit()

                # *****  Update Student Ledger *****#
                unpaid_invoices.student_ledger_id.credit = debit_amt
                unpaid_invoices.write({'waiver_ids': [(6, 0, self.scholarship_id.ids)],
                                       'waiver_percentage': self.scholarship_value,
                                       'waiver_amount': self.new_scholarship_amount})
                unpaid_invoices.sudo()._compute_fee_detail()
            else:
                self.action_create_fee_invoice(amount=self.scholarship_amount_diff, paid_invoices=paid_invoices)

        if od_amount > 0:
            self.action_create_over_draft_amount_entry(unpaid_invoices, od_amount)
        if unpaid_invoices.amount_total == 0:
            unpaid_invoices.write({'payment_state': 'paid', 'narration': 'Paid Due To Scholarship Adjustment'})

        # ***** Applied Scholarship *****#
        self.action_create_applied_scholarship_entry()

    def check_program_term(self):
        if self.scholarship_id:
            full_fee_scholarship = self.env['odoocms.fee.waiver'].search([('name', '=', 'Full Fee')])
            program_term_scholarship_rec = self.env['odoocms.program.term.scholarship'].sudo().search([('program_id', '=', self.student_id.program_id.id), ('term_id', '=', self.term_id.id)])
            if program_term_scholarship_rec and program_term_scholarship_rec.scholarship_ids or full_fee_scholarship:
                if not program_term_scholarship_rec.scholarship_ids.filtered(lambda a: a.id == self.scholarship_id.id):
                    if not self.scholarship_id.id == full_fee_scholarship.id:
                        raise UserError("Scholarship %s Does Not Exist For Program-%s and Term-%s" % (self.scholarship_id.name, self.student_id.program_id.code, self.term_id.code))
            else:
                raise UserError("Please Define Record in Program Term Scholarship For Program-%s and Term-%s" % (self.student_id.program_id.code, self.term_id.code))

    def action_create_over_draft_amount_entry(self, invoice, over_draft_amount):
        if over_draft_amount > 0:
            student_id = self.student_id
            ledger_data = {
                'student_id': self.student_id.id,
                'date': fields.Date.today(),
                'credit': 0,
                'debit': over_draft_amount,
                'invoice_id': invoice and invoice.id or False,
                'session_id': student_id.session_id and student_id.session_id.id or False,
                'career_id': student_id.career_id and student_id.career_id.id or False,
                'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                'campus_id': student_id.campus_id and student_id.campus_id.id or False,
                'program_id': student_id.program_id and student_id.program_id.id or False,
                'discipline_id': student_id.discipline_id and student_id.discipline_id.id or False,
                'term_id': student_id.term_id and student_id.term_id.id or False,
                'semester_id': student_id.semester_id and student_id.semester_id.id or False,
                'ledger_entry_type': 'od',
                'description': 'Over Draft Amount',
            }
            self.env['odoocms.student.ledger'].sudo().create(ledger_data)

    def action_create_applied_scholarship_entry(self):
        # Removed Existing Applied Scholarship
        already_applied_rec = self.student_id.applied_scholarship_ids.filtered(lambda a: a.term_id.id == self.term_id.id)
        if already_applied_rec:
            already_applied_rec.sudo().unlink()
        data_values = {
            'student_id': self.student_id.id,
            'student_name': self.student_id.name,
            'program_id': self.student_id.program_id.id or False,
            'term_id': self.term_id and self.term_id.id or False,
            'scholarship_id': self.scholarship_id and self.scholarship_id.id or False,
            'scholarship_continue_policy_id': False,
            'scholarship_continue_policy_line_id': False,
            'scholarship_percentage': self.scholarship_value,
            'current': True,
            'state': 'lock',
        }
        self.env['odoocms.student.applied.scholarships'].sudo().create(data_values)
        self.student_id.scholarship_id = self.scholarship_id and self.scholarship_id.id or False

    def action_create_fee_invoice(self, amount, paid_invoices):
        inv = paid_invoices[0]
        tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
        fee_head = self.env['odoocms.fee.head'].search([('name', '=', tuition_fee_head)], order='id desc', limit=1)
        lines = []
        fee_lines = {
            'sequence': 10,
            'name': 'Tution Fee',
            'quantity': 1,
            'course_gross_fee': abs(amount),
            'price_unit': abs(amount),
            'product_id': fee_head and fee_head.product_id.id or False,
            'account_id': fee_head and fee_head.property_account_income_id.id or False,
            'fee_head_id': fee_head and fee_head.id or False,
            'exclude_from_invoice_tab': False,
            'course_id_new': False,
            'registration_id': False,
            'registration_line_id': False,
            'course_credit_hours': 0,
            'discount': 0,
        }
        lines.append((0, 0, fee_lines))

        # ***** DATA DICT Of Fee Receipt *****#
        data = {
            'student_id': self.student_id.id,
            'partner_id': self.student_id.partner_id.id,
            'fee_structure_id': inv.fee_structure_id.id,
            'journal_id': inv.fee_structure_id.journal_id.id,
            'invoice_date': fields.Date.today(),
            'invoice_date_due': fields.Date.today() + relativedelta(days=7),
            'state': 'draft',
            'is_fee': True,
            'is_cms': True,
            'is_hostel_fee': False,
            'move_type': 'out_invoice',
            'invoice_line_ids': lines,
            'receipt_type_ids': [(4, receipt.id, None) for receipt in inv.receipt_type_ids],
            'waiver_percentage': 0,
            'term_id': self.term_id and self.term_id.id or False,
            'study_scheme_id': self.student_id.study_scheme_id and self.student_id.study_scheme_id.id or False,
            'validity_date': fields.Date.today() + relativedelta(days=7),
            'registration_id': inv.registration_id and inv.registration_id.id or False,
            'challan_type': 'installment',
            'semester_gross_fee': abs(amount)
        }

        # Create Fee Receipt
        invoice = self.env['account.move'].sudo().create(data)
