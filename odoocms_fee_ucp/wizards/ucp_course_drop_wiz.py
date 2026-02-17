# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import pdb


class UCPOdoocmsDropCoursesWiz(models.TransientModel):
    _name = "ucp.odoocms.drop.courses.wiz"
    _description = 'This Wizard Will Drop the Courses.'

    @api.model
    def _get_student_id(self):
        if self._context.get('active_model', False) == 'odoocms.student' and self._context.get('active_id', False):
            return self.env['odoocms.student'].browse(self._context.get('active_id', False))

    @api.model
    def get_term_id(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    @api.model
    def _get_lines(self):
        lines = []
        student = self.env['odoocms.student'].browse(self._context.get('active_id'))
        if student:
            if student.course_ids:
                for course in student.course_ids:
                    line = {
                        'wizard_id': self.id,
                        'course_id': course.id,
                        'primary_class_id': course.primary_class_id.id,
                        'credit_hours': course.credits,
                    }
                    new_rec = self.env['ucp.odoocms.drop.courses.lines.wiz'].create(line)
                    lines.append(new_rec.id)
        return lines

    student_id = fields.Many2one('odoocms.student', 'Student', default=_get_student_id)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_term_id)
    challan_id = fields.Many2one('account.move', 'Challan')
    challan_type = fields.Selection(related='challan_id.challan_type')
    challan_state = fields.Selection(related='challan_id.payment_state')
    lines = fields.One2many('ucp.odoocms.drop.courses.lines.wiz', 'wizard_id', 'Lines', default=_get_lines)

    def action_drop_courses(self):
        if not self.lines:
            raise UserError(_('Please Select Course to Drop'))
        self.lines.write({'wizard_id': self.id})
        if not self.challan_id:
            raise UserError(_('Please Select The Challan'))
        if self.challan_id.payment_state in ('paid', 'in_payment'):
            raise UserError(_('Challan is in Paid status'))

        dropped_courses = self.lines.filtered(lambda a: a.drop)
        dropped_credit_hours = 0
        dropped_courses_amount = 0
        invoice_total_amount = self.challan_id.amount_total
        receivable_line = self.challan_id.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
        od_amount = 0
        mvl = self.env['account.move.line']
        if dropped_courses:
            for d in dropped_courses:
                dropped_credit_hours += d.credit_hours
                invoice_line = self.challan_id.line_ids.filtered(lambda a: a.course_id_new.id == d.primary_class_id.id)

                if invoice_line:
                    dropped_courses_amount += invoice_line.credit
                    credit_amt1 = 0
                    mvl = invoice_line
                    new_name = invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-)"
                    self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s,registration_type=%s,add_drop_no=%s where id=%s \n"
                                        , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', '1', invoice_line.id))
                    self._cr.commit()

            paid_dropped_courses_amount = dropped_courses_amount
            dropped_courses_amount = dropped_courses_amount * 2

            debit_amt = receivable_line.debit - dropped_courses_amount
            if dropped_courses_amount >= invoice_total_amount:
                od_amount = dropped_courses_amount - invoice_total_amount
                debit_amt = 0

            # ***** Receivable Line, it will Debit ***** #

            self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

            # ***** Invoice Total Update *****#
            self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, self.challan_id.id))
            self._cr.commit()

            new_name = "Adjustment in Second Installment of (Drop-Already Paid) Courses"
            if od_amount > 0:
                paid_dropped_courses_amount = paid_dropped_courses_amount - od_amount
            new_mvl = self.env.cr.execute("""insert into account_move_line 
                                        (
                                            account_id,partner_id,fee_head_id,name,move_id,currency_id,
                                            product_id,quantity,price_unit,price_total,price_subtotal,balance,
                                            amount_currency,course_gross_fee,course_credit_hours,credit,move_name,date,
                                            parent_state,journal_id,company_id,company_currency_id,account_root_id,sequence,
                                            debit,discount,reconciled,blocked,amount_residual,amount_residual_currency,
                                            exclude_from_invoice_tab,fee_category_id,student_id,career_id,program_id,session_id,
                                            institute_id,campus_id,term_id,create_uid,create_date,write_date,
                                            write_uid,registration_type) 
                                        VALUES (%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,
                                                %s,%s) RETURNING id """,
                                          (
                                              mvl.account_id.id, mvl.partner_id.id, mvl.fee_head_id.id, new_name, mvl.move_id.id, mvl.currency_id.id,
                                              mvl.product_id.id, 1.00, -paid_dropped_courses_amount, -paid_dropped_courses_amount, -paid_dropped_courses_amount, paid_dropped_courses_amount,
                                              paid_dropped_courses_amount, 0, 0, 0.0, mvl.move_name, mvl.date,
                                              mvl.parent_state, mvl.journal_id.id, mvl.company_id.id, mvl.company_currency_id.id, mvl.account_root_id.id, 250,
                                              paid_dropped_courses_amount, mvl.discount, mvl.reconciled, mvl.blocked, 0, 0,
                                              mvl.exclude_from_invoice_tab, mvl.fee_category_id.id, mvl.student_id.id, mvl.career_id.id, mvl.program_id.id, mvl.session_id.id,
                                              mvl.institute_id.id, mvl.campus_id.id, mvl.term_id.id, self.env.user.id, fields.Datetime.now(), fields.Datetime.now(),
                                              self.env.user.id, 'main'
                                          ))

            # ***** Student Ledger Update *****#
            student_ledger_rec = self.challan_id.student_ledger_id
            if student_ledger_rec:
                if student_ledger_rec.credit > dropped_courses_amount:
                    student_ledger_rec.credit = student_ledger_rec.credit - dropped_courses_amount
                else:
                    student_ledger_rec.credit = 0
            if debit_amt == 0:
                self.challan_id.write({'payment_state': 'paid'})

        #  ****** Creating Student Ledger ******#
        if od_amount > 0:
            ledger_data = {
                'student_id': self.student_id and self.student_id.id or False,
                'date': fields.Date.today(),
                'credit': 0,
                'debit': od_amount,
                'invoice_id': self.challan_id.id,
                'session_id': self.challan_id.session_id and self.challan_id.session_id.id or False,
                'career_id': self.challan_id.career_id and self.challan_id.career_id.id or False,
                'institute_id': self.challan_id.institute_id and self.challan_id.institute_id.id or False,
                'campus_id': self.challan_id.campus_id and self.challan_id.campus_id.id or False,
                'program_id': self.challan_id.program_id and self.challan_id.program_id.id or False,
                'discipline_id': self.challan_id.discipline_id and self.challan_id.discipline_id.id or False,
                'term_id': self.challan_id.term_id and self.challan_id.term_id.id or False,
                'semester_id': self.challan_id.semester_id and self.challan_id.semester_id.id or False,
                'ledger_entry_type': 'semester',
                'description': "OD",
            }
            ledger_id = self.env['odoocms.student.ledger'].create(ledger_data)


class UCPOdoocmsDropCoursesLinesWiz(models.TransientModel):
    _name = "ucp.odoocms.drop.courses.lines.wiz"
    _description = 'Courses Lines'

    wizard_id = fields.Many2one('ucp.odoocms.drop.courses.wiz', 'Wizard Ref')
    course_id = fields.Many2one('odoocms.student.course', 'Course')
    primary_class_id = fields.Many2one('odoocms.class.primary', 'Primary Class')
    credit_hours = fields.Float('Credit Hours')
    drop = fields.Boolean('Drop')
