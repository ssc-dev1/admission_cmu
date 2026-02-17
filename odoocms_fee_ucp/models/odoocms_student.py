# -*- coding: utf-8 -*-
import pdb
import math
import datetime
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _
from odoo.tools.safe_eval import safe_eval
from datetime import date
import ast
import re

import logging

_logger = logging.getLogger(__name__)


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


class OdoocmsBatch(models.Model):
    _inherit = 'odoocms.batch'

    # PGC Scholarship Configuration
    pgc_scholarship_applicable = fields.Boolean('PGC Scholarship Applicable', tracking=True)
    pgc_scholarship_applicable_semesters = fields.Char('Applicable Semesters', tracking=True)
    pgc_scholarship_merge_semester = fields.Integer('PGC Scholarship Merge Semester', tracking=True)
    pgc_scholarship_id = fields.Many2one('odoocms.fee.waiver', 'PGC Scholarship')


class OdoocmsStudent(models.Model):
    _inherit = 'odoocms.student'

    def _assign_special_scholarship_institute(self):
        if self.batch_id.pgc_scholarship_applicable and self.batch_id.pgc_scholarship_id in self.scholarship_eligibility_ids.mapped('scholarship_id'):
            domain = [
                ('policy_id', '=', self.scholarship_policy_id.id),
                ('scholarship_id', '=', self.batch_id.pgc_scholarship_id.id),
                ('program_id', '=', self.program_id.id)
            ]
            policy_lines = self.env['odoocms.scholarship.continue.policy.line'].search(domain, order='id desc', limit=1)
            if policy_lines:
                if not self.scholarship_id:
                    self.scholarship_id = policy_lines.scholarship_id.id
                elif self.scholarship_id and policy_lines.value > self.scholarship_id.amount:
                    self.scholarship_id = self.policy_line.scholarship_id.id

    def check_special_scholarship_institute(self, fee_charge_term):
        policy_line = self.env['odoocms.scholarship.continue.policy.line']
        if self.batch_id.pgc_scholarship_applicable and self.scholarship_eligibility_ids and self.scholarship_eligibility_ids.filtered(
                lambda a: a.scholarship_id == self.batch_id.pgc_scholarship_id):

            regular_domain = [('number','>=',self.session_id.first_term_id.number),('number','<=',fee_charge_term.number),('type','=','regular')]
            summer_domain = [('number', '>=', self.session_id.first_term_id.number), ('number', '<=', fee_charge_term.number), ('type', '=', 'summer')]
            regular_term_cnt = self.env['odoocms.academic.term'].search_count(regular_domain)
            summer_term = self.env['odoocms.academic.term'].search(summer_domain)
            summer_term_cnt = self.env['odoocms.student.term'].search_count([('student_id', '=', self.id),('term_id', 'in', summer_term.ids)])
            student_current_semester_no = regular_term_cnt + summer_term_cnt
            if student_current_semester_no in ast.literal_eval(self.batch_id.pgc_scholarship_applicable_semesters):
                policy_domain = [
                    ('policy_id', '=', self.scholarship_policy_id.id),
                    ('scholarship_id', '=', self.batch_id.pgc_scholarship_id.id),
                    ('program_id', '=', self.program_id.id),
                    ('value', '=', self.batch_id.pgc_scholarship_id.amount)
                ]
                policy_line = self.env['odoocms.scholarship.continue.policy.line'].search(policy_domain, order='id desc', limit=1)

            elif student_current_semester_no == self.batch_id.pgc_scholarship_merge_semester:
                credit_hours = 0.0
                cgpa = 0.0
                course_load_domain = [
                    ('student_id', '=', self.id),
                    ('term_id.type', '=', 'regular'),
                    ('term_id', '!=', fee_charge_term.id)
                ]
                course_load_student_terms = self.env['odoocms.student.term'].search(course_load_domain)
                for course_load_student_term in course_load_student_terms:
                    credit_hours += course_load_student_term.earned_credits
                    cgpa = course_load_student_term.cgpa

                policy_domain = [
                   ('policy_id', '=', self.scholarship_policy_id.id),
                   ('scholarship_id', '=', self.batch_id.pgc_scholarship_id.id),
                   ('program_id', '=', self.program_id.id),
                   ('credit_hours', '>', 0),
                   ('credit_hours', '<=', credit_hours),
                   ('cgpa', '<=', cgpa),
                   ('merge_policy_line', '=', True)
                ]
                policy_line = self.env['odoocms.scholarship.continue.policy.line'].search(policy_domain, order='cgpa desc', limit=1)

        return policy_line

    # This Function is defined for the Students having no entry in the odoocms.course.registration Table
    # Because our current method for challan genration is based on the student registration if student not
    # have entry in the registration table then We will use this function, changes are only in the registered
    # courses searching process

    def action_generate_challan_without_registration(self, term_id, receipts, date_due, due_date2, apply_taxes=False, batch_id=False, registration_id=False, add_drop_challan=False):
        _logger.info('*** Student %s', self.id)
        first_semester_flag = False
        first_term_scheme_rec = self.session_id.term_scheme_ids and self.session_id.term_scheme_ids.filtered(lambda a: a.semester_id.number == 1)
        if first_term_scheme_rec and first_term_scheme_rec.term_id == term_id:
            first_semester_flag = True

        # receipts (passed as parameter) ----> receipt_type_ids (odoocms.receipt.type)
        # which we select either its semester fee, hostel fee, ad hoc fee, in other Words,
        # These are the Fee Heads That will be Charged for that Type (this is Fee Heads Container)

        lines = []
        payment_types = ['persemester', 'persubject', 'onetime', 'admissiontime']
        student_waiver = self.env['odoocms.student.fee.waiver']
        dropped_courses_received_amount = 0
        waiver_amount_for_invoice = 0
        waivers = []

        # ***** Scholarship Policy Management ******
        self.get_scholarship_policy()
        self.compute_student_current_scholarship()

        # ***** Paid Course Discounts ****#
        paid_invoice_discounts = 0
        paid_invoices_amount = 0
        paid_invoices = self.env['account.move'].search([('student_id', '=', self.id), ('term_id', '=', term_id.id),
                                                         ('payment_state', 'in', ('paid', 'in_payment')),
                                                         ('challan_type', 'not in', ('misc_challan', 'prospectus_challan', 'hostel_fee'))])

        for paid_invoice in paid_invoices:
            pd_inv_amt = sum(paid_inv_line.price_unit for paid_inv_line in paid_invoice.line_ids.filtered(lambda a: a.fee_category_id.name == 'Tuition Fee'))
            if paid_invoice.waiver_percentage > 0 or paid_invoice.waiver_amount > 0:
                a1 = pd_inv_amt * (100 / (100 - paid_invoice.waiver_percentage or 1))
                paid_invoice_discounts += math.ceil((paid_invoice.waiver_percentage / 100) * a1)
            paid_invoices_amount += pd_inv_amt
        total_paid_invoices_amount = paid_invoices_amount + paid_invoice_discounts

        # This line is changed
        student_registered_courses = self.env['odoocms.student.course']
        invoices = self.env['account.move']

        # ****** Check here to generate Hostel Fee Along with Semester Fee or not *****#
        # semester_fee -----> Generate with Semester Fee
        # separate_fee -----> Generate a separate fee for Hostel
        hostel_fee_charge_timing = (self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.hostel_fee_charge_timing') or 'separate_fee')

        # ***** Fee Structure Search Out *****#
        # Search the Fee Structure based on the (Academic Session + Academic Term + Career)
        # There must At Least One Fee Structure for that Student
        fee_structure = self.env['odoocms.fee.structure'].search([('session_id', '=', self.session_id.id),
                                                                  ('batch_id', '=', batch_id.id),
                                                                  ('career_id', '=', self.career_id.id)
                                                                  ], order='id desc', limit=1)

        if not fee_structure or not fee_structure.current:
            raise UserError(_('Fee structure is not defined for (Student: %s, Session %s.)' % (self.code, self.session_id.name)))
        if not fee_structure.date_start or not fee_structure.date_end:
            raise UserError(_('Fee structure Effective date Period are not Entered.'))
        if fee_structure.date_start > date.today() or fee_structure.date_end < date.today():
            raise UserError(_('Fee structure is out of date. (Student: %s, Fee-Structure: %s)' % (self.code, fee_structure.id,)))

        # fee_head_ids-----> odoocms.fee.head
        fee_head_ids = receipts.mapped('fee_head_ids').ids

        # GET Fee Structure Heads from Fee Structure based on the fee_head_ids taken from receipts variable
        # Search Fee Heads in Fee Structure Heads
        # structure_fee_heads -----> odoocms.fee.structure.head
        structure_fee_heads = fee_structure.head_ids.filtered(lambda l: l.fee_head_id.id in fee_head_ids and l.current and l.payment_type in payment_types)
        date_invoice = fields.Date.context_today(self)

        arrears_amt = 0
        added_courses_amount = 0
        is_hostel_fee = False
        improve_repeat_list = ['repeat', 'improve']
        challan_type = 'main_challan'

        for structure_fee_head in structure_fee_heads:
            if structure_fee_head.line_ids:
                # structure_head_line ----> odoocms.fee.structure.head.line
                for structure_head_line in structure_fee_head.line_ids:
                    price_unit = 0
                    if self.env['odoocms.student'].search(safe_eval(structure_head_line.domain) + [('id', '=', self.id)]):
                        price_unit = (structure_head_line and structure_head_line.amount or 0)
                        course_price_unit = price_unit

                        # ***** Fee Structure Head is Tuition Fee ***** #
                        course_sequence = 10
                        line_discount = 0
                        special_scholarship_rec = self.env['odoocms.student.special.scholarship'].search([('student_id', '=', self.id),
                                                                                                          ('term_id', '=', term_id.id),
                                                                                                          ('state', '=', 'approved')])
                        if special_scholarship_rec and special_scholarship_rec.allow_scholarship_repeating_courses and "repeat" in improve_repeat_list:
                            improve_repeat_list.remove('repeat')

                        if structure_fee_head.fee_head_id.name == 'Tuition Fee':
                            student_registered_courses = self.env['odoocms.student.course'].search([('student_id', '=', self.id), ('term_id', '=', term_id.id)])
                            if student_registered_courses:
                                # ***** Creating Waiver Records *****#
                                if self.scholarship_id:
                                    waiver_fee_line = self.env['odoocms.fee.waiver.line'].search([('waiver_id', '=', self.scholarship_id.id),
                                                                                                  ('fee_head_id', '=', structure_fee_head.fee_head_id.id)
                                                                                                  ], order='id desc', limit=1)
                                    if waiver_fee_line:
                                        waivers.append(self.scholarship_id)
                                        if special_scholarship_rec:
                                            line_discount = special_scholarship_rec.scholarship_value if special_scholarship_rec.value_type == 'percentage' else special_scholarship_rec.fixed_amount_scholarship_percentage
                                        elif first_semester_flag:
                                            line_discount = self.scholarship_id.amount
                                        else:
                                            line_discount = self.scholarship_policy_line_id.value

                                    # Here Hard Coded Value "CGPA based Scholarship" need to be changed later on
                                    if not waiver_fee_line and self.scholarship_id and self.scholarship_id.name == 'CGPA based Scholarship':
                                        waivers.append(self.scholarship_id)
                                        line_discount = self.scholarship_policy_line_id.value

                                # ***** Paid Discounts MGT *****#
                                if total_paid_invoices_amount > 0:
                                    # 1):- Gross
                                    # 2):- Net = Gross - Apply New Discount
                                    # 3):- Remaining = Net - Paid
                                    # 4):- Remaining / ((100 - new discount %) / 100)

                                    challan_type = "2nd_challan"
                                    registered_credit_hours = sum(std_reg_c.credits for std_reg_c in student_registered_courses)
                                    ucp_formula_gross = registered_credit_hours * self.batch_id.per_credit_hour_fee
                                    ucp_formula_discounted_net = ucp_formula_gross - ucp_formula_gross * (line_discount / 100)
                                    ucp_formula_paid_subtract = ucp_formula_discounted_net - paid_invoices_amount
                                    # ***** Create OD here *****#
                                    if ucp_formula_paid_subtract < 0:
                                        ledger_data = {
                                            'student_id': self.id,
                                            'date': fields.Date.today(),
                                            'debit': abs(ucp_formula_paid_subtract),
                                            'credit': 0,
                                            'invoice_id': False,
                                            'session_id': self.session_id and self.session_id.id or False,
                                            'career_id': self.career_id and self.career_id.id or False,
                                            'institute_id': self.institute_id and self.institute_id.id or False,
                                            'campus_id': self.campus_id and self.campus_id.id or False,
                                            'program_id': self.program_id and self.program_id.id or False,
                                            'discipline_id': self.discipline_id and self.discipline_id.id or False,
                                            'term_id': term_id and term_id.id or False,
                                            'semester_id': False,
                                            'ledger_entry_type': 'od',
                                        }
                                        self.env['odoocms.student.ledger'].sudo().create(ledger_data)
                                        break
                                    else:
                                        ucp_formula_paid_subtract1 = ucp_formula_paid_subtract * (100 / (100 - line_discount))
                                        price_unit = (ucp_formula_paid_subtract1 / registered_credit_hours)

                                if not add_drop_challan:
                                    for course in student_registered_courses:
                                        # No Scholarship For Repeat and Improvement Courses
                                        # if course.course_type in ('repeat', 'improve'):
                                        if course.course_type in improve_repeat_list:
                                            line_discount = 0
                                        # Block Scholarship
                                        elif course.primary_class_id.course_id.block_scholarship:
                                            line_discount = 0
                                        elif self.scholarship_id:
                                            if special_scholarship_rec:
                                                line_discount = special_scholarship_rec.scholarship_value if special_scholarship_rec.value_type == 'percentage' else special_scholarship_rec.fixed_amount_scholarship_percentage

                                            elif first_semester_flag:
                                                line_discount = self.scholarship_id.amount
                                            else:
                                                line_discount = self.scholarship_policy_line_id.value

                                        course_sequence += 10
                                        same_term_invoice = self.env['account.move'].search([('student_id', '=', self.id),
                                                                                             ('term_id', '=', term_id.id),
                                                                                             ('move_type', '=', 'out_invoice'),
                                                                                             ('reversed_entry_id', '=', False),
                                                                                             ], order='id desc', limit=1)

                                        same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', self.id),
                                                                                                           ('reversed_entry_id', '=', same_term_invoice.id)])
                                        if same_term_invoice:
                                            if not same_term_invoice_reverse_entry:
                                                sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id),
                                                                                               ('registration_line_id', '=', course.id)])
                                                if sm_mvl:
                                                    continue

                                        course_credit = course.credits or 0
                                        new_name = course.primary_class_id.course_id.code + "-" + course.primary_class_id.course_id.name + " Tuition Fee"
                                        waiver_amount_for_invoice += (price_unit * course_credit) * (line_discount / 100.0)
                                        fee_lines = {
                                            'sequence': course_sequence,
                                            'name': new_name,
                                            'quantity': 1,
                                            'course_gross_fee': course_price_unit * course_credit,
                                            'price_unit': price_unit * course_credit,
                                            'product_id': structure_fee_head.fee_head_id.product_id.id,
                                            'account_id': structure_fee_head.fee_head_id.property_account_income_id.id,
                                            'fee_head_id': structure_fee_head.fee_head_id.id,
                                            'exclude_from_invoice_tab': False,
                                            'course_id_new': course.primary_class_id.id,
                                            'registration_id': False,
                                            'registration_line_id': False,
                                            'course_credit_hours': course_credit,
                                            'discount': line_discount,
                                            'registration_type': 'main',
                                            'add_drop_no': 'Main',
                                            'add_drop_paid_amount': 0,
                                        }
                                        lines.append((0, 0, fee_lines))

                                # ***** ADd DROP Challans ***** #
                                if add_drop_challan:
                                    added_courses, added_credit_hours = self.get_added_courses(registration_request=registration_id)
                                    dropped_courses, dropped_credit_hours = self.get_dropped_courses(registration_request=registration_id)
                                    # ***** New Added Courses *****#
                                    if added_courses:
                                        student_registered_courses = added_courses
                                        for course in student_registered_courses:
                                            # Block Scholarship
                                            if course.primary_class_id.course_id.block_scholarship:
                                                line_discount = 0
                                            elif self.scholarship_id:
                                                if special_scholarship_rec:
                                                    line_discount = special_scholarship_rec.scholarship_value if special_scholarship_rec.value_type == 'percentage' else special_scholarship_rec.fixed_amount_scholarship_percentage
                                                elif first_semester_flag:
                                                    line_discount = self.scholarship_id.amount
                                                else:
                                                    line_discount = self.scholarship_policy_line_id.value

                                            course_sequence += 10
                                            same_term_invoice = self.env['account.move'].search([('student_id', '=', self.id),
                                                                                                 ('term_id', '=', term_id.id),
                                                                                                 ('move_type', '=', 'out_invoice'),
                                                                                                 ('reversed_entry_id', '=', False),
                                                                                                 ], order='id desc', limit=1)

                                            same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', self.id),
                                                                                                               ('reversed_entry_id', '=', same_term_invoice.id)])
                                            if same_term_invoice:
                                                if not same_term_invoice_reverse_entry:
                                                    sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id),
                                                                                                   ('registration_line_id', '=', course.id)])
                                                    if sm_mvl:
                                                        continue

                                            course_credit = course.credits or 0
                                            new_name = course.primary_class_id.course_id.code + "-" + course.primary_class_id.course_id.name + " (Add)"
                                            waiver_amount_for_invoice += (price_unit * course_credit) * (line_discount / 100.0)
                                            added_courses_amount += (price_unit * course_credit) - ((price_unit * course_credit) * (line_discount / 100.0))
                                            dp_amount = self.get_drop_courses_paid_amount(dropped_courses, term_id)
                                            price_unit_nw = price_unit * course_credit

                                            # Remarked@Sarfraz 05-03-2023
                                            # if 0 < dp_amount < added_courses_amount:
                                            #     price_unit_nw = price_unit * course_credit
                                            # elif dp_amount > 0 and dp_amount > added_courses_amount:
                                            #     price_unit_nw = dp_amount / round(len(added_courses), 2)
                                            # else:
                                            #     price_unit_nw = price_unit * course_credit

                                            fee_lines = {
                                                'sequence': course_sequence,
                                                'name': new_name,
                                                'quantity': 1,
                                                'course_gross_fee': price_unit * course_credit,
                                                # 'price_unit': price_unit * course_credit,
                                                'price_unit': price_unit_nw,
                                                'product_id': structure_fee_head.fee_head_id.product_id.id,
                                                'account_id': structure_fee_head.fee_head_id.property_account_income_id.id,
                                                'fee_head_id': structure_fee_head.fee_head_id.id,
                                                'exclude_from_invoice_tab': False,
                                                'course_id_new': course.primary_class_id.id,
                                                'registration_id': registration_id.id,
                                                'registration_line_id': course.id,
                                                'course_credit_hours': course_credit,
                                                'discount': line_discount,
                                                'is_add_drop_line': True,
                                                'registration_type': 'add',
                                                'add_drop_paid_amount': 0,
                                                'add_drop_no': "Add->" + registration_id.add_drop_request_no_txt if registration_id.add_drop_request_no_txt else '',
                                            }
                                            lines.append((0, 0, fee_lines))

                        # ***** If other than Tuition Fee Then (Other Charges) ******#
                        else:
                            if not add_drop_challan:
                                same_term_invoice = self.env['account.move'].search([('student_id', '=', self.id),
                                                                                     ('term_id', '=', term_id.id),
                                                                                     ('move_type', '=', 'out_invoice'),
                                                                                     ('reversed_entry_id', '=', False),
                                                                                     ], order='id desc', limit=1)

                                same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', self.id),
                                                                                                   ('reversed_entry_id', '=', same_term_invoice.id)])
                                if same_term_invoice:
                                    if not same_term_invoice_reverse_entry:
                                        sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id),
                                                                                       ('fee_head_id', '=', structure_fee_head.fee_head_id.id)])
                                        if sm_mvl:
                                            continue

                                name = structure_fee_head.fee_head_id.product_id and structure_fee_head.fee_head_id.product_id.name or ''
                                line_discount = 0
                                if self.scholarship_id:
                                    waiver_fee_line = self.env['odoocms.fee.waiver.line'].search([('waiver_id', '=', self.scholarship_id.id),
                                                                                                  ('fee_head_id', '=', structure_fee_head.fee_head_id.id)
                                                                                                  ], order='id desc', limit=1)
                                    if waiver_fee_line:
                                        waivers.append(self.scholarship_id)
                                        line_discount = self.scholarship_policy_line_id.value
                                        waiver_amount_for_invoice += price_unit * (line_discount / 100.0)

                                fee_lines = {
                                    'sequence': 100,
                                    'name': name,
                                    'quantity': 1,
                                    'course_gross_fee': price_unit,
                                    'price_unit': price_unit,
                                    'product_id': structure_fee_head.fee_head_id.product_id.id,
                                    'account_id': structure_fee_head.fee_head_id.property_account_income_id.id,
                                    'fee_head_id': structure_fee_head.fee_head_id.id,
                                    'exclude_from_invoice_tab': False,
                                    "course_id_new": False,
                                    "registration_id": False,
                                    "registration_line_id": False,
                                    'course_credit_hours': 0,
                                    'discount': line_discount,
                                    'registration_type': 'main',
                                    'add_drop_no': 'Main',
                                    'add_drop_paid_amount': 0,
                                }
                                lines.append((0, 0, fee_lines))

        # ***** DROP Courses Management ***** #
        if add_drop_challan:
            added_courses, added_credit_hours = self.get_added_courses(registration_request=registration_id)
            dropped_courses, dropped_credit_hours = self.get_dropped_courses(registration_request=registration_id)
            # ***** Dropped Courses *****#
            if dropped_courses:
                dropped_courses_invoice_lines = self.env['account.move.line']
                for dropped_course in dropped_courses:
                    # ***** GET Previous Invoices ***** #
                    dropped_courses_invoice_line = self.env['account.move.line'].search([('course_id_new', '=', dropped_course.primary_class_id.id),
                                                                                         ('student_id', '=', self.id),
                                                                                         ('term_id', '=', term_id.id),
                                                                                         ('registration_type', 'in', ('main', 'add')),
                                                                                         ('move_id.payment_state', 'not in', ('in_payment', 'paid'))], order='id desc', limit=1)
                    if not dropped_courses_invoice_line:
                        dropped_courses_invoice_line = self.env['account.move.line'].search([('course_id_new', '=', dropped_course.primary_class_id.id),
                                                                                             ('student_id', '=', self.id),
                                                                                             ('term_id', '=', term_id.id),
                                                                                             ('registration_type', 'in', ('main', 'add'))], order='id desc', limit=1)

                    if dropped_courses_invoice_line:
                        dropped_courses_invoice_lines += dropped_courses_invoice_line

                if dropped_courses_invoice_lines:
                    lines = self.update_fee_invoice_lines(invoice_lines=dropped_courses_invoice_lines, term_id=term_id, registration_id=registration_id, added_courses_amount=added_courses_amount, lines=lines)

        # ***** Checking the Student Ad hoc Charges *****#
        lines = self.get_additional_charges_lines(term_id, lines)

        # ***** Checking the Student Other Fine *****#
        lines = self.get_input_other_fine_lines(term_id, lines)

        # Get the Student Arrears and Adjustment
        adjustment_lines = []
        # if lines:
        #     arrears_result = self.get_arrears_adjustments(term_id, lines, add_drop_challan=add_drop_challan)
        #     lines = arrears_result[0]
        #     arrears_amt = arrears_result[1]
        #     adjustment_lines = arrears_result[2]

        # Fine for Late Payment
        if lines:
            lines = self.create_fine_line(lines)

        # @ added on 20-08-2021
        invoice_net_amt = 0
        for nw_line in lines:
            invoice_net_amt += nw_line[2]['price_unit']

        # Remarked @26122022
        # Check Any Line having Amount Greater the Zero and Net Amount also Greater than Zero
        # if receipts and any([ln[2]['price_unit'] > 0 for ln in lines]) and invoice_net_amt > 0 and not add_drop_challan:

        # if Student Status is not Filer then Apply Taxes
        if apply_taxes and not self.filer:
            lines = self.create_tax_line(lines, term_id, fall_20=False)

        validity_date = date_due

        # ***** DATA DICT Of Fee Receipt *****#
        data = {
            'student_id': self.id,
            'partner_id': self.partner_id.id,
            'fee_structure_id': fee_structure.id,
            'journal_id': fee_structure.journal_id.id,
            'invoice_date': date_invoice,
            'invoice_date_due': date_due,
            'state': 'draft',
            'is_fee': True,
            'is_cms': True,
            'is_hostel_fee': is_hostel_fee,
            'move_type': 'out_invoice',
            'invoice_line_ids': lines,
            'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
            'waiver_percentage': self.scholarship_id.amount if first_semester_flag else self.scholarship_policy_line_id and self.scholarship_policy_line_id.value or 0,
            # 'waiver_amount': math.ceil(waiver_amount_for_invoice + paid_invoice_discounts),
            'term_id': term_id and term_id.id or False,
            'validity_date': validity_date,
            'first_installment': True if challan_type == 'main_challan' else False,
            'second_installment': True if not challan_type == 'main_challan' else False,
            'registration_id': registration_id and registration_id.id or False,
            'challan_type': challan_type,
        }

        # ***** Update Fee Receipt Data Dict Of Waiver Fields ***** #
        if waivers:
            data['waiver_ids'] = [(4, waiver.id, None) for waiver in waivers]

        # Create Fee Receipt
        invoice = self.env['account.move'].sudo().create(data)

        # ***** Assign Fee Receipt id to Waivers *****#
        for waiver in student_waiver:
            waiver.invoice_id = invoice.id

        # ***** GET Ledger Amount ***** #
        ledger_amt = invoice.amount_total

        # ***** Remarked on 22-12-2022 *****#
        # if arrears_amt < 0:
        ledger_amt = invoice.amount_total + arrears_amt

        # ***** Create Ledger Entry For Regular Invoice ***** #
        if ledger_amt > 0:
            self.create_fee_ledger_entry(invoice=invoice, debit=0, credit=ledger_amt, ledger_entry_type='semester')

        # ***** Create Dropped Course Ledger Entry *****#
        if dropped_courses_received_amount > 0:
            self.create_fee_ledger_entry(invoice=invoice, debit=dropped_courses_received_amount, credit=0, ledger_entry_type='drop')

        # ***** Assign Invoice Id to Adjustment *****#
        if adjustment_lines:
            adjustment_lines.write({'invoice_id': invoice.id})

        # ***** Create Fee Waiver Entry *****#
        if waiver_amount_for_invoice > 0:
            self.action_create_student_fee_waiver_entry(waiver_amount_for_invoice, invoice)

        # ***** Confirm Registration Request if Invoice Amount is Zero *****#
        if invoice.amount_total == 0:
            invoice.write({'state': 'posted', 'payment_state': 'paid', 'narration': 'Paid Due To OD', 'payment_date': fields.Date.today()})
            if registration_id:
                registration_id.sudo().action_approve()
        return invoice

    def create_hostel_fine_line(self, lines):
        fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Late Fine')])
        if not fee_head:
            raise UserError(_("Fine Fee Head is not defined in the System."))
        fine_line = {
            'sequence': 900,
            'price_unit': 0,
            'quantity': 1,
            'product_id': fee_head.product_id.id,
            'name': "Fine For Late Payment On Hostel Fee",
            'account_id': fee_head.property_account_income_id.id,
            # 'account_analytic_id': line.fee_head_id.account_analytic_id,
            # 'analytic_tag_ids': analytic_tag_ids,
            'fee_head_id': fee_head.id,
            'exclude_from_invoice_tab': False,
        }
        lines.append([0, 0, fine_line])
        return lines

    def get_term_discount_detail(self, student_term=False):
        discount_dict = {
            'discount_id': '',
            'discount_type': '',
            'discount_percentage': ''
        }
        if student_term:
            term_invoice = self.env['account.move'].search(
                [('student_id', '=', self.id), ('term_id', '=', student_term.term_id.id),
                 ('challan_type', 'in', ['main_challan', '2nd_challan', 'installment']),
                 ('waiver_percentage', '>', 0)
                 ], order='id asc', limit=1)
            if term_invoice:
                discount_dict.update({
                    'discount_id': term_invoice.waiver_ids.id,
                    'discount_type': term_invoice.waiver_ids.name,
                    'discount_percentage': term_invoice.waiver_percentage
                })
        return discount_dict

    def get_term_invoices_detail(self, student_term=False):
        term_invoices = self.env['account.move']
        if student_term:
            term_invoices = self.env['account.move'].search([('student_id', '=', self.id), ('term_id', '=', student_term.term_id.id)], order='id asc')
        return term_invoices

    def get_over_draft_detail(self, student_term=False):
        term_over_draft = self.env['odoocms.student.ledger']
        if student_term:
            term_over_draft = self.env['odoocms.student.ledger'].search([('student_id', '=', self.id), ('term_id.code', '=', student_term.term_id.code)], order='id asc')
        return term_over_draft

    # ***** Hostel *****#
    def generate_hostel_invoice(self, description_sub, semester, receipts, date_due, comment='', tag=False,
                                reference=False, invoice_group=False, registration_id=False, hostel_challan_months=0):

        fee_structure = self.env['odoocms.fee.structure'].search([('session_id', '=', self.session_id.id),
                                                                  ('batch_id', '=', self.batch_id.id),
                                                                  ('career_id', '=', self.career_id.id)
                                                                  ], order='id desc', limit=1)

        if not fee_structure:
            raise UserError(_('Please define fee structure for Session: %s, Batch: %s, Career: %s' % (self.session_id.name, self.batch_id.name, self.career_id.name)))

        # if not fee_structure.journal_id.sequence_id:
        #     raise UserError(_('Please define sequence on the Journal related to this Invoice.'))

        date_invoice = fields.Date.context_today(self)
        # sequence = fee_structure.journal_id.sequence_id
        # new_name = sequence.with_context(ir_sequence_date=date_invoice).next_by_id()
        lines = []
        invoices = self.env['account.move']

        if self.hostel_state == 'Allocated':
            if hostel_challan_months == 0:
                hostel_fee_charge_months = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.hostel_fee_charge_months') or '6')
            else:
                hostel_fee_charge_months = hostel_challan_months
            fee_heads = receipts.fee_head_ids
            for fee_head in fee_heads:
                name = self.hostel_id and self.hostel_id.name + ' Charges'
                sm_mvl = False

                if not sm_mvl:
                    price = self.room_id.per_month_rent
                    price_unit = round(price * hostel_fee_charge_months, 2)
                    if 'Security' in fee_head.name:
                        price_unit = self.room_id.room_type.security_fee
                        name = self.hostel_id and self.hostel_id.name + ' Security'
                    hostel_fee_line = {
                        'sequence': 10,
                        'price_unit': price_unit,
                        'course_gross_fee': price_unit,
                        'quantity': 1,
                        'product_id': fee_head.product_id.id,
                        'name': name,
                        'account_id': fee_head.property_account_income_id.id,
                        'fee_head_id': fee_head.id,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append([0, 0, hostel_fee_line])

        # Fine for Late Payment
        if lines:
            lines = self.create_hostel_fine_line(lines)

        # Previous Arrears
        if lines:
            hostel_arrears_amount = 0
            unpaid_hostel_receipts = self.env['account.move'].search([('student_id', '=', self.id),
                                                                      ('is_hostel_fee', '=', True),
                                                                      ('payment_state', '=', 'not_paid')])
            if unpaid_hostel_receipts:
                for unpaid_hostel_receipt in unpaid_hostel_receipts:
                    hostel_arrears_amount += unpaid_hostel_receipt.amount_residual
                    unpaid_hostel_receipt.mapped('line_ids').remove_move_reconcile()
                    unpaid_hostel_receipt.write({'state': 'cancel', 'cancel_due_to_arrears': True})

                arrears_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', '=', 'Arrears')], order='id', limit=1)
                hostel_arrears_amount = hostel_arrears_amount + (hostel_arrears_amount)
                arrears_line = {
                    'sequence': 1000,
                    'price_unit': round(hostel_arrears_amount),
                    'quantity': 1,
                    'product_id': arrears_fee_head.product_id and arrears_fee_head.product_id.id or False,
                    'name': arrears_fee_head.product_id and arrears_fee_head.product_id.name or 'Previous Arrears ',
                    'account_id': arrears_fee_head.property_account_income_id.id,
                    # 'analytic_tag_ids': analytic_tag_ids,
                    'fee_head_id': arrears_fee_head and arrears_fee_head.id or False,
                    'exclude_from_invoice_tab': False,
                }
                lines.append((0, 0, arrears_line))

        if receipts and any([ln[2]['price_unit'] > 0 for ln in lines]):
            validity_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.challan_validity_days') or '30')
            validity_date = date_due + datetime.timedelta(days=validity_days)

            data = {
                'student_id': self.id,
                'partner_id': self.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'registration_id': registration_id,
                'journal_id': fee_structure.journal_id.id,
                # 'name': new_name,
                'invoice_date': date_invoice,
                'invoice_date_due': date_due,
                'state': 'draft',
                'narration': cleanhtml(comment),
                'tag': tag,
                'is_fee': True,
                'is_cms': True,
                'is_hostel_fee': True,
                'reference': reference,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'waiver_amount': 0,
                'term_id': semester and semester.id or False,
                'validity_date': validity_date,
                'challan_type': 'hostel_fee',
            }
            invoice = self.env['account.move'].create(data)
            invoices += invoice
            invoice.invoice_group_id = invoice_group

            ledger_amt = invoice.amount_total
            ledger_data = {
                'student_id': self.id,
                'date': date_invoice,
                'credit': ledger_amt,
                'invoice_id': invoice.id,
                'description': 'Hostel Fee For ' + semester.name,
                'ledger_entry_type': 'hostel',
                'term_id': invoice.term_id and invoice.term_id.id or False,
            }
            ledger_id = self.env['odoocms.student.ledger'].create(ledger_data)
            invoice.student_ledger_id = ledger_id.id
        return invoices

    # This Function Create the Registration Request and Assign the Sections To Newly Admitted Students
    def action_assign_section_to_new_students(self, nlimit=10):
        students = self.env['odoocms.student'].sudo().search([('to_be', '=', True)], limit=nlimit)
        for student in students:
            compulsory_course_ids = student.sudo().action_get_section_courses()
            if compulsory_course_ids:
                data = {
                    'student_id': student.id,
                    'term_id': student.term_id.id,
                    'source': 'office',
                    'state': 'draft',
                    'compulsory_course_ids': [(6, 0, compulsory_course_ids.ids)],
                    # 'elective_course_ids': [(6, 0, self.elective_course_ids.ids)],
                    # 'spec_course_ids': [(6, 0, self.spec_course_ids.ids)],
                    # 'override_max_limit': self.override_max_limit,
                    # 'override_prereq': self.override_prereq,
                    'date_effective': fields.Date.today(),
                    'enrollment_type': 'enrollment',
                    'bypass_date':True,
                }
                reg = self.env['odoocms.course.registration'].sudo().create(data)
                student.to_be = False
                try:
                    reg.action_submit()
                    reg.action_approve()
                except Exception as e:
                    _logger.error(f"Error while submitting course registration: {e}")

    def action_get_section_courses(self):
        ret_primary_classes = self.env['odoocms.class.primary']
        # Fetch Student Courses For The Current Term
        student_course_ids = self.study_scheme_id.line_ids.filtered(lambda a: a.term_id.id == self.term_id.id).mapped('course_id')

        # Search Sections In The Current Term and Batch
        sections = self.env['odoocms.batch.term.section'].sudo().search([('term_id', '=', self.term_id.id),
                                                                         ('batch_id', '=', self.batch_id.id)])
        if not sections:
            _logger.warning("There is No Section Defined For Term:  %s and Batch %s ", self.term_id.name, self.batch_id.name)

        for section in sorted(sections, key=lambda r: r.id):
            # Search Primary classes in the current term, batch, and section
            section_dom = 'odoocms.batch.term.section,' + str(section.id)
            primary_classes = self.env['odoocms.class.primary'].sudo().search([('term_id', '=', self.term_id.id),
                                                                               ('batch_id', '=', self.batch_id.id),
                                                                               ('section_id', '=', section_dom)
                                                                               ])

            # Check if all primary classes have strength greater than their student count
            if all([primary_class.strength > primary_class.student_count for primary_class in primary_classes]):
                p_course_ids = primary_classes.mapped('course_id')
                # if student_course_ids - p_course_ids == 0:
                if student_course_ids & p_course_ids == student_course_ids:
                    ret_primary_classes |= primary_classes
                else:
                    _logger.warning("For Student %s Study Scheme Courses and Section Courses are mismatch", self.code)
        return ret_primary_classes
