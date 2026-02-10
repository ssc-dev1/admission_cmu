# -*- coding: utf-8 -*-
import datetime
import pdb
from datetime import date
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo.tools.safe_eval import safe_eval
from odoo.tools import html_sanitize
import re
import math
import decimal

import logging
_logger = logging.getLogger(__name__)

def roundhalfdown(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_DOWN
    return float(round(decimal.Decimal(str(n)), decimals))


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


class OdooCMSStudent(models.Model):
    _inherit = 'odoocms.student'

    scholarship_eligibility_ids = fields.One2many('odoocms.student.scholarship.eligibility', 'student_id', 'Scholarships Eligibility')
    applied_scholarship_ids = fields.One2many('odoocms.student.applied.scholarships', 'student_id', 'Applied Scholarships')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Current Scholarship', tracking=True)

    scholarship_policy_id = fields.Many2one('odoocms.scholarship.continue.policy', 'Scholarship Policy', tracking=True)
    scholarship_policy_line_id = fields.Many2one('odoocms.scholarship.continue.policy.line', 'Scholarship Policy Line', tracking=True)

    block_scholarship = fields.Boolean('Block Scholarship', default=False)
    log = fields.Html('Logs:', readonly=True)

    def hook_line(self, line):
        return line

    def add_log_message(self, message, color='black'):
        log_message = f'<span style="color: {color};">{message}</span><br/>'
        if not self.log:
            self.log = ""
        self.log += html_sanitize(log_message)

    def _compute_registration_fee(self, registration_id):
        for reg in registration_id:
            student = reg.student_id
            term = reg.term_id
            selected_head_line = None

            # student.get_scholarship_policy()
            # student.compute_student_current_scholarship()

            faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', term.id)], order='id desc', limit=1)
            if not faculty_wise_fee_rec:
                raise UserError(_('Faculty Wise Challan Configuration for this Student is not Found.'))

            price_unit = 0
            qty = 1
            receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids
            fee_structure = self._get_fee_structure(log_message=False)
            tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
            structure_fee_heads = self._get_fee_heads(fee_structure, receipt_type_ids, tuition_fee_head)   # odoocms.fee.structure on session,batch,career, odoocms.fee.structure.head of required receipts
            for structure_fee_head in structure_fee_heads:
                for head_line in structure_fee_head.line_ids:  # odoocms.fee.structure.head.line
                    if self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', self.id)]):
                        price_unit = head_line.amount
                        selected_head_line = head_line

            if not selected_head_line:
                raise UserError(_('Fee Head Line not Found.'))

            student_prev_term_cnt = self.env['odoocms.student.term'].search_count([('student_id', '=', student.id), ('term_id', '!=', term.id)])
            first_semester_flag = True if student_prev_term_cnt == 0 else False

            improve_repeat_list = ['repeat', 'improve']
            domain = [('student_id', '=', student.id), ('term_id', '=', term.id), ('state', '=', 'approved')]
            special_scholarship_rec = self.env['odoocms.student.special.scholarship'].search(domain)
            if special_scholarship_rec and special_scholarship_rec.allow_scholarship_repeating_courses and "repeat" in improve_repeat_list:
                improve_repeat_list.remove('repeat')

            for course in registration_id.line_ids:
                # No Scholarship For Repeat and Improvement Courses if course.course_type in ('repeat', 'improve'):
                if course.course_type in improve_repeat_list:
                    line_discount = 0
                elif course.primary_class_id.course_id.block_scholarship:  # Block Scholarship
                    line_discount = 0
                elif student.scholarship_id:
                    if special_scholarship_rec:
                        line_discount = special_scholarship_rec.scholarship_value if special_scholarship_rec.value_type == 'percentage' else special_scholarship_rec.fixed_amount_scholarship_percentage
                    elif first_semester_flag:
                        line_discount = student.scholarship_id.amount
                    else:
                        line_discount = student.scholarship_policy_line_id.value
                else:
                    line_discount = 0

                if selected_head_line.per_fee_type == 'per_credit_hour':
                    qty = course.credits
                elif selected_head_line.per_fee_type == 'per_contact_hour':
                    qty = course.course_id.contact_hours
                elif selected_head_line.per_fee_type == 'per_course':
                    qty = 1

                course.write({
                    'qty': qty,
                    'price_unit': price_unit,
                    'discount': line_discount
                })

    def _compute_registered_courses_fee(self, student_term_id):
        student = student_term_id.student_id
        term = student_term_id.term_id

        # student.get_scholarship_policy()
        # student.compute_student_current_scholarship()

        faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', term.id)], order='id desc', limit=1)
        if not faculty_wise_fee_rec:
            raise UserError(_('Faculty Wise Challan Configuration for this Student is not Found.'))

        price_unit = 0
        receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids
        fee_structure = self._get_fee_structure(log_message=False)
        tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
        structure_fee_heads = self._get_fee_heads(fee_structure, receipt_type_ids, tuition_fee_head)   # odoocms.fee.structure on session,batch,career, odoocms.fee.structure.head of required receipts

        for structure_fee_head in structure_fee_heads:
            for head_line in structure_fee_head.line_ids:  # odoocms.fee.structure.head.line
                if self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', self.id)]):
                    price_unit = head_line.amount

        student_prev_term_cnt = self.env['odoocms.student.term'].search_count([('student_id', '=', student.id), ('term_id', '!=', term.id)])
        first_semester_flag = True if student_prev_term_cnt == 0 else False

        improve_repeat_list = ['repeat', 'improve']
        domain = [('student_id', '=', student.id), ('term_id', '=', term.id), ('state', '=', 'approved')]
        special_scholarship_rec = self.env['odoocms.student.special.scholarship'].search(domain)
        if special_scholarship_rec and special_scholarship_rec.allow_scholarship_repeating_courses and "repeat" in improve_repeat_list:
            improve_repeat_list.remove('repeat')

        price = []
        for course in student_term_id.student_course_ids:
            # No Scholarship For Repeat and Improvement Courses if course.course_type in ('repeat', 'improve'):
            if course.course_type in improve_repeat_list:
                line_discount = 0
            elif course.primary_class_id.course_id.block_scholarship:  # Block Scholarship
                line_discount = 0
            elif student.scholarship_id:
                if special_scholarship_rec:
                    line_discount = special_scholarship_rec.scholarship_value if special_scholarship_rec.value_type == 'percentage' else special_scholarship_rec.fixed_amount_scholarship_percentage
                elif first_semester_flag:
                    line_discount = student.scholarship_id.amount
                else:
                    line_discount = student.scholarship_policy_line_id.value
            else:
                line_discount = 0

            price.append({
                'price_unit': price_unit,
                'discount': line_discount,
                'credit': course.credits
            })

        return price

    def _get_registration_fee_line(self, registration_id, fee_head):
        fee_lines = []
        for course in registration_id.line_ids:
            if self.env.context.get('registered_only',False) and not course.student_course_id:
                continue
            # if not course.price_unit or not course.discount:
            self._compute_registration_fee(registration_id)

            qty = course.qty

            price_unit = course.price_unit
            new_name = (course.primary_class_id and course.primary_class_id.course_id.code or course.course_id.code) + "-" + \
                       (course.primary_class_id and course.primary_class_id.course_id.name or course.course_id.name) + " Tuition Fee"
            sequence = 201

            registration_type = 'main'
            if registration_id.add_drop_request:
                is_add_drop_line = True
                if course.action == 'add':
                    registration_type = 'add'
                elif course.action == 'drop':
                    qty = -qty
                    registration_type = 'drop'
                    adddrop_policy = self.env['odoocms.adddrop.policy'].get_policy(registration_id.term_id)
                    if adddrop_policy:
                        price_unit = price_unit * adddrop_policy.drop_percentage / 100

                add_drop_no = "Add->" + registration_id.add_drop_request_no_txt if registration_id.add_drop_request_no_txt else ''
            else:
                is_add_drop_line = False
                add_drop_no = 'Main'

            fee_line = {
                'sequence': sequence,
                'name': new_name,
                'quantity': qty,
                'course_gross_fee': price_unit * qty,
                'price_unit': price_unit,
                # 'gross': price_unit * qty,
                'product_id': fee_head.fee_head_id.product_id.id,
                'account_id': fee_head.fee_head_id.property_account_income_id.id,
                'fee_head_id': fee_head.fee_head_id.id,
                'exclude_from_invoice_tab': False,
                'course_id_new': course.primary_class_id and course.primary_class_id.id or False,
                'registration_id': course.registration_id and course.registration_id.id or False,
                'registration_line_id': course.id,
                'course_credit_hours': course.credits,
                'discount': course.discount,
                'registration_type': registration_type,
                'add_drop_no': add_drop_no,
                'add_drop_paid_amount': 0,
                'is_add_drop_line': is_add_drop_line,
                'no_split': fee_head.fee_head_id.no_split,
                'analytic_account_id': fee_head.fee_head_id.analytic_account_id and fee_head.fee_head_id.analytic_account_id.id or
                                       (self.program_id.analytic_account_id and self.program_id.analytic_account_id.id) or
                                       (self.department_id.analytic_account_id and self.department_id.analytic_account_id.id) or False,
                # 'analytic_tag_ids': analytic_tag_ids,
            }
            fee_line = self.hook_line(fee_line)
            sequence += 1
            fee_lines.append(fee_line)
        return fee_lines

    def _get_semester_fee_line(self, fee_head, qty, price_unit):
        fee_line = {
            'sequence': 10,
            'price_unit': price_unit,
            'quantity': qty,
            'product_id': fee_head.fee_head_id.product_id.id,
            'name': fee_head.fee_head_id.product_id.name,
            'account_id': fee_head.fee_head_id.property_account_income_id.id,
            'analytic_account_id': fee_head.fee_head_id.analytic_account_id and fee_head.fee_head_id.analytic_account_id.id or
                                   (self.program_id.analytic_account_id and self.program_id.analytic_account_id.id) or
                                   (self.department_id.analytic_account_id and self.department_id.analytic_account_id.id) or False,
            # 'analytic_tag_ids': analytic_tag_ids,
            'fee_head_id': fee_head.fee_head_id.id,
            'exclude_from_invoice_tab': False,
        }
        fee_line = self.hook_line(fee_line)
        return fee_line

    def _get_scholarship_discount(self, term_id, fee_head, first_semester_flag):
        special_scholarship_config = self.env['ir.config_parameter'].sudo().get_param('aarsol.special.scholarship', 'False')
        special_scholarship_handling = True if special_scholarship_config in ('True', 'Yes', '1') else False

        line_discount = 0
        waiver_domain = [('waiver_id', '=', self.scholarship_id.id), ('fee_head_id', '=', fee_head.id)]
        waiver_fee_line = self.env['odoocms.fee.waiver.line'].search(waiver_domain, order='id desc', limit=1)
        if waiver_fee_line:
            special_scholarship_domain = [('student_id', '=', self.id), ('term_id', '=', term_id.id), ('state', '=', 'approved')]
            special_scholarship_rec = self.env['odoocms.student.special.scholarship'].search(special_scholarship_domain)

            if special_scholarship_rec:
                if special_scholarship_rec.value_type == 'percentage':
                    line_discount = special_scholarship_rec.scholarship_value
                else:
                    line_discount = special_scholarship_rec.fixed_amount_scholarship_percentage

            elif first_semester_flag:
                line_discount = self.scholarship_id.amount
            elif self.scholarship_policy_line_id:
                line_discount = self.scholarship_policy_line_id.value
            elif self.scholarship_id and special_scholarship_handling:
                line_discount = self.scholarship_id.amount
            else:
                line_discount = 0

        elif self.scholarship_id.scholarship_category_id.progress_base:
            line_discount = self.scholarship_policy_line_id.value

        return line_discount

    def check_fine_policy(self, term_id, label_id):
        today = fields.Date.today()
        dom = [('start_date', '<=', today),
               ('due_date', '>=', today),
               ('state', '=', 'confirm'),
               ('term_id', '=', term_id.id),
               ('label_id', '=', label_id.id),
               ('program_id', '=', self.program_id.id),
               ('faculty_id', '=', self.department_id.id)]
        fine_policy_line = self.env['odoocms.challan.fine.policy.line'].search(dom, order='id desc', limit=1)
        return fine_policy_line

    def get_admission_fee_line(self):
        batch_domain = [('program_id', '=', self.program_id.id), ('session_id', '=', self.session_id.id),('career_id', '=', self.career_id.id)]
        program_batch = self.env['odoocms.batch'].search(batch_domain)
        adm_fee_head_id = program_batch.admission_tuition_structure_head.fee_head_id
        adm_line = {
            'sequence': 10,
            'name': "Admission Fee",
            'quantity': 1,
            'price_unit': program_batch.admission_fee,
            'product_id': adm_fee_head_id.product_id.id,
            'account_id': adm_fee_head_id.property_account_income_id.id,
            'fee_head_id': adm_fee_head_id.id,
            'exclude_from_invoice_tab': False,
            'discount': 0,
            'course_id_new': False,
            'registration_id': False,
            'registration_line_id': False,
            'course_credit_hours': 0,
            'course_gross_fee': program_batch.admission_fee,
            'registration_type': 'main',
            'partner_id': self.partner_id.id,
            'no_split': adm_fee_head_id.no_split,
            'analytic_account_id': adm_fee_head_id.analytic_account_id and adm_fee_head_id.analytic_account_id.id or
                                   (self.program_id.analytic_account_id and self.program_id.analytic_account_id.id) or
                                   (self.department_id.analytic_account_id and self.department_id.analytic_account_id.id) or False,
            # 'analytic_tag_ids': analytic_tag_ids,
        }
        adm_line = self.hook_line(adm_line)
        return adm_line

    def generate_invoice_new(self, term_id, receipts, date_due, apply_taxes=False, registration_id=None, add_drop_challan=False, payment_term=None, override_line=None, log_message=False):
        first_semester_flag = False
        first_term_scheme_rec = self.env['odoocms.student.term'].search_count([('student_id', '=', self.id),('term_id', '!=', term_id.id)]) + 1
        if first_term_scheme_rec == 1:
            first_semester_flag = True

        if not date_due:
            date_due = date.today()
        elif isinstance(date_due,str):
            date_due = datetime.datetime.strptime(date_due, '%Y-%m-%d')

        lines = []

        student_waiver = self.env['odoocms.student.fee.waiver']
        waiver_amount_for_invoice = 0
        waivers = []
        all_repeating_courses = False
        invoice_discount_list = []

        assign_prev_scholarship = self.env['ir.config_parameter'].sudo().get_param('aarsol.assign_prev_scholarship','False')
        if assign_prev_scholarship in ('True','Yes','1'):
            b = 5
        else:
            self.get_scholarship_policy(log_message=log_message)
            self.compute_student_current_scholarship(term_id,registration_id, log_message=log_message)

        # Remarked by Farooq
        paid_invoices_amount = 0
        paid_invoice_discounts = 0
        paid_domain = [('student_id', '=', self.id), ('term_id', '=', term_id.id), ('payment_state', 'in', ('paid', 'in_payment')),
                ('challan_type', 'not in', ('misc_challan', 'prospectus_challan', 'hostel_fee'))
            ]
        paid_invoices = self.env['account.move'].search(paid_domain)
        for paid_invoice in paid_invoices:
            pd_inv_amt = sum(paid_inv_line.price_unit for paid_inv_line in paid_invoice.line_ids.filtered(lambda a: a.fee_category_id.name == 'Tuition Fee'))
            if paid_invoice.waiver_percentage > 0 or paid_invoice.waiver_amount > 0:
                a1 = pd_inv_amt * (100 / (100 - paid_invoice.waiver_percentage or 1))
                paid_invoice_discounts += math.ceil((paid_invoice.waiver_percentage / 100) * a1)
            paid_invoices_amount += pd_inv_amt
        # End remarked

        # Search the Fee Structure based on the (Academic Session + Academic Term + Career)
        # There must At Least One Fee Structure for that Student
        fee_structure = self._get_fee_structure(log_message=log_message)
        structure_fee_heads = self._get_fee_heads(fee_structure, receipts, log_message=log_message)
        date_invoice = fields.Date.context_today(self)
        if not fee_structure:
            if log_message:
                self.add_log_message(f": No Fee structure found for {str(self.code)} ", 'red')
                return False
            else:
                raise UserError('No Fee Structure Found for ' % (self.code))
        if not structure_fee_heads:
            if log_message:
                self.add_log_message(f": No Fee Heads found in Structure {fee_structure.name} ", 'red')
                return False
            else:
                raise UserError('No Fee Heads found in Structure: %s' % (fee_structure.name))

        is_hostel_fee = False
        improve_repeat_list = ['repeat', 'improve']
        challan_type = 'main_challan'

        if log_message:
            self.add_log_message(f": Fee Structure {fee_structure.name}, Structur Fee Heads {''.join(structure_fee_heads.mapped('fee_head_id').mapped('name'))} ", 'blue')

        for fee_head in structure_fee_heads:
            for head_line in fee_head.line_ids: # odoocms.fee.structure.head.line
                if head_line.domain and self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', self.id)]):
                    override_fee_line = False
                    if override_line:
                        override_fee_line = override_line.filtered(lambda l: l.fee_head_id.id == fee_head.fee_head_id.id)

                    price_unit = override_fee_line and override_fee_line.fee_amount or (head_line and head_line.amount) or 0
                    if not head_line.currency_id.id == self.env.company.currency_id.id:
                        price_unit = head_line.currency_id._convert(price_unit, self.env.company.currency_id, self.env.company, date_invoice)

                    # qty = 1
                    # if fee_head.payment_type == 'persubject' and reg:
                    #     qty = len(reg.failed_subject_ids) + len(reg.to_improve_subject_ids)

                    # ***** Fee Structure Head is Tuition Fee ***** #
                    course_sequence = 10
                    line_discount = 0

                    special_scholarship_domain = [('student_id', '=', self.id), ('term_id', '=', term_id.id), ('state', '=', 'approved')]
                    special_scholarship_rec = self.env['odoocms.student.special.scholarship'].search(special_scholarship_domain)
                    if log_message:
                        self.add_log_message(f": Special Scholarship Domain - {str(special_scholarship_domain)}", '#FFA500')
                        if special_scholarship_rec:
                            self.add_log_message(f": Special Scholarship Record - {str(special_scholarship_rec.id)} - {str(special_scholarship_rec.name)}", 'green')
                        else:
                            self.add_log_message(f": Special Scholarship Record - Not Found ", 'red')

                    if special_scholarship_rec and special_scholarship_rec.allow_scholarship_repeating_courses and "repeat" in improve_repeat_list:
                        improve_repeat_list.remove('repeat')

                    tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
                    if fee_head.fee_head_id.name == tuition_fee_head:     # fee_head.category_id.name (may be)
                        # if self.check_tuition_fee_deferment():
                        #     defer_line_fee_head = fee_head
                        #     tut_defer_line, defer_regular_invoice_amount, defer_invoice_amount, defer_invoice_date_due = self.action_create_tuition_deferment_entry(head_line)
                        #     # price_unit = tut_defer_line.deferment_id.approved_tuition_fee
                        #     price_unit = defer_regular_invoice_amount

                        if self.scholarship_id:
                            line_discount = self._get_scholarship_discount(term_id, fee_head.fee_head_id, first_semester_flag)
                            if log_message:
                                self.add_log_message(f": Discount - {str(line_discount)}", 'blue')
                            waivers.append(self.scholarship_id)
                            invoice_discount_list.append(line_discount)

                        if registration_id:
                            if all([rc.course_type == 'repeat' for rc in registration_id.line_ids]):
                                all_repeating_courses = True

                            if registration_id:
                                fee_lines = self._get_registration_fee_line(registration_id, fee_head)
                                for fee_line in fee_lines:
                                    lines.append((0, 0, fee_line))
                                if self.env.context.get('with_admission',False):
                                    lines.append((0, 0, self.get_admission_fee_line()))
                        else:
                            fee_line = self._get_semester_fee_line(fee_head, qty=1, price_unit=price_unit)
                            lines.append((0, 0, fee_line))

                    # ***** If other than Tuition Fee Then (Other Charges) ******#
                    else:
                        if not add_drop_challan:
                            same_term_invoice = self.env['account.move'].search(
                                [
                                    ('student_id', '=', self.id),
                                    ('term_id', '=', term_id.id),
                                    ('move_type', '=', 'out_invoice'),
                                    ('reversed_entry_id', '=', False),
                                ],
                                order='id desc', limit=1)

                            same_term_invoice_reverse_entry = self.env['account.move'].search(
                                [
                                    ('student_id', '=', self.id),
                                    ('reversed_entry_id', '=', same_term_invoice.id),
                                ]
                            )
                            if same_term_invoice:
                                if not same_term_invoice_reverse_entry:
                                    sm_mvl = self.env['account.move.line'].search(
                                        [
                                            ('move_id', '=', same_term_invoice.id),
                                            ('fee_head_id', '=', fee_head.fee_head_id.id)
                                        ]
                                    )
                                    if sm_mvl:
                                        continue

                            name = fee_head.fee_head_id.product_id and fee_head.fee_head_id.product_id.name or ''
                            line_discount = 0
                            if self.scholarship_id:
                                waiver_fee_line = self.env['odoocms.fee.waiver.line'].search(
                                    [
                                        ('waiver_id', '=', self.scholarship_id.id),
                                        ('fee_head_id', '=', fee_head.fee_head_id.id)
                                    ],
                                    order='id desc', limit=1)
                                if waiver_fee_line:
                                    waivers.append(self.scholarship_id)
                                    line_discount = self.scholarship_policy_line_id.value
                                    waiver_amount_for_invoice += round(price_unit * (line_discount / 100.0))
                            invoice_discount_list.append(line_discount)

                            qty = 1
                            if fee_head.payment_type == 'persubject' and registration_id:
                                add = len(registration_id.line_ids.filtered(lambda l: l.action == 'add'))
                                drop = len(registration_id.line_ids.filtered(lambda l: l.action == 'drop'))
                                qty =  add - drop

                            elif fee_head.payment_type == 'percredit' and registration_id:
                                add = sum(registration_id.line_ids.filtered(lambda l: l.action == 'add').mapped('credits'))
                                drop = sum(registration_id.line_ids.filtered(lambda l: l.action == 'drop').mapped('credits'))
                                qty =  add - drop

                            fee_line = {
                                'sequence': 100,
                                'name': name,
                                'quantity': qty,
                                'course_gross_fee': price_unit * qty,
                                'price_unit': price_unit,
                                'product_id': fee_head.fee_head_id.product_id.id,
                                'account_id': fee_head.fee_head_id.property_account_income_id.id,
                                'fee_head_id': fee_head.fee_head_id.id,
                                'exclude_from_invoice_tab': False,
                                "course_id_new": False,
                                "registration_id": False,
                                "registration_line_id": False,
                                'course_credit_hours': 0,
                                'discount': line_discount,
                                'registration_type': 'main',
                                'add_drop_no': 'Main',
                                'add_drop_paid_amount': 0,
                                'no_split': fee_head.fee_head_id.no_split,
                                'analytic_account_id': fee_head.fee_head_id.analytic_account_id and fee_head.fee_head_id.analytic_account_id.id or
                                       (self.program_id.analytic_account_id and self.program_id.analytic_account_id.id) or
                                       (self.department_id.analytic_account_id and self.department_id.analytic_account_id.id) or False,
                                # 'analytic_tag_ids': analytic_tag_ids,
                            }
                            fee_line = self.hook_line(fee_line)

                            lines.append((0, 0, fee_line))
                # waiver_percentage = line_discount

        waiver_percentage = max(invoice_discount_list) if invoice_discount_list else 0
        if log_message:
            self.add_log_message(f": Waiver Percentage - {str(waiver_percentage)}", 'blue')

        adjustment_lines = []
        lines, additional_charge_lines = self.get_additional_charges_lines(term_id, lines)
        lines, input_other_fine_lines = self.get_input_other_fine_lines(term_id, lines)
        lines, attendance_fine_lines  = self.get_attendance_fine_lines(lines)
        lines, overdraft_lines  = self.get_overdraft_lines(term_id, lines)

        if registration_id and registration_id.add_drop_request:
            lines = self.get_adddrop_payment_discount(registration_id, lines)
            if not registration_id.add_drop_fine_exempt:
                lines = self.get_adddrop_charge_lines(registration_id, lines)

        # if lines:
        #     lines, arrears_amt, adjustment_lines = self.get_arrears_adjustments(term_id, lines, add_drop_challan=add_drop_challan)

        # Fine for Late Payment
        # if lines:
        #     lines = self.create_fine_line(lines)

        # if Student Status is not Filer then Apply Taxes
        if apply_taxes and not self.filer:
            lines = self.create_tax_line(lines, term_id, fall_20=False)

        validity_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.challan_validity_days') or '30')
        validity_date = date_due + datetime.timedelta(days=validity_days)

        # ***** DATA DICT Of Fee Receipt *****#
        if registration_id and not registration_id.add_drop_request:
            waiver_amount_for_invoice = waiver_amount_for_invoice + paid_invoice_discounts

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
            # 'move_type': 'out_refund',
            'invoice_line_ids': lines,
            'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
            'waiver_percentage': waiver_percentage if not all_repeating_courses else 0,
            'term_id': term_id and term_id.id or False,
            'validity_date': validity_date,
            'registration_id': registration_id and registration_id.id or False,
            'challan_type': challan_type,
            'invoice_payment_term_id': payment_term and payment_term.id or False,
        }

        # ***** Update Fee Receipt Data Dict Of Waiver Fields ***** #
        if waivers and not all_repeating_courses:
            data['waiver_ids'] = [(4, waiver.id, None) for waiver in waivers]

        # Create Fee Receipt
        invoice = self.env['account.move'].sudo().create(data)
        invoice.action_post()

        # ***** Assign Fee Receipt id to Waivers *****#
        for waiver in student_waiver:
            waiver.invoice_id = invoice.id

        additional_charge_lines.sudo().write({'receipt_id': invoice.id})
        input_other_fine_lines.sudo().write({'receipt_id': invoice.id})
        attendance_fine_lines.sudo().write({'move_id': invoice.id})

        if adjustment_lines:
            adjustment_lines.write({'invoice_id': invoice.id})

        # ***** Create Fee Waiver Entry *****#
        if waiver_amount_for_invoice > 0:
            self.action_create_student_fee_waiver_entry(waiver_amount_for_invoice, invoice)

        return invoice

    def get_additional_charges_lines(self, term_id, lines):
        lines, adhoc_charges = self.env['odoocms.fee.additional.charges'].get_additional_charges_lines(self.id, term_id.id, lines)
        return lines, adhoc_charges

    def get_input_other_fine_lines(self, term_id, lines):
        lines, other_fine_recs = self.env['odoocms.input.other.fine'].get_input_other_fine_lines(self.id, term_id.id, lines)
        return lines, other_fine_recs

    def get_attendance_fine_lines(self, lines):
        lines, term_att_fine_recs = self.env['odoocms.student.attendance.fine'].get_attendance_fine_lines(self.id, lines)
        return lines, term_att_fine_recs

    def get_overdraft_lines(self, term_id, lines):
        lines, overdraft_recs = self.env['odoocms.overdraft'].get_overdraft_lines(self.id, term_id.id, lines)
        return lines, overdraft_recs

    def get_adddrop_charge_lines(self, registration, lines):
        lines = self.env['odoocms.adddrop.policy'].get_adddrop_charge_lines(registration, lines)
        return lines

    def get_adddrop_payment_discount(self, registration, lines):
        domain = [('student_id','=',registration.student_id.id),('term_id','=',registration.term_id.id),('label_id.type','=','main')]
        main_challan = self.env['odoocms.fee.barcode'].search(domain, limit=1)

        if main_challan and main_challan.state == 'paid' and main_challan.discount > 0:
            # fee_head_domain = self.env['ir.config_parameter'].sudo().get_param('aarsol.adddrop_charges_head', 'Adddrop Charges')
            # domain = [('name', '=', fee_head_domain), '|', ('company_id', '=', False), ('company_id', '=', registration.student_id.company_id.id)]
            # fee_head = self.env['odoocms.fee.head'].sudo().search(domain)

            to_drop_lines = registration.line_ids.filtered(lambda l: l.action == 'drop')
            tuition_fee = 0
            for line in to_drop_lines:
                tuition_fee = sum(line.price_subtotal)
            amount = roundhalfdown(tuition_fee * main_challan.line_ids[0].move_id.invoice_payment_term_id.discount / 100)

            adddrop_charges_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.adddrop_charges_head', 'Adddrop Charges')
            domain = [('name', '=', adddrop_charges_head),'|',('company_id','=',False),('company_id','=',registration.student_id.company_id.id)]
            fee_head = self.env['odoocms.fee.head'].sudo().search(domain)
            company = registration.student_id.company_id
            account_id = fee_head.product_id.with_company(company).property_account_income_id

            data_dict = {
                'sequence': 500,
                'price_unit': amount,
                'quantity': 1,
                'product_id': fee_head.product_id.id,
                'name': fee_head.name,
                'account_id': account_id.id,
                'fee_head_id': fee_head.id,
                'exclude_from_invoice_tab': False,
                'no_split': fee_head.no_split,
            }
            lines.append((0, 0, data_dict))
        return lines


    # def get_arrears_adjustments(self, term_id, lines, add_drop_challan=False):
    #     lines_sum = 0
    #     for line in lines:
    #         lines_sum += line[2]['price_unit']
    #
    #     adjustment_lines = []
    #     adjustment_amount = 0
    #     balance = 0
    #     credit_sum = debit_sum = 0
    #     qty = 1
    #     ledger_lines = self.env['odoocms.student.ledger'].search([('student_id', '=', self.id), ('is_defer_entry', '!=', True)])
    #
    #     for ledger_line in ledger_lines:
    #         if not ledger_line.invoice_id.is_hostel_fee:
    #             credit_sum += ledger_line.credit
    #             debit_sum += ledger_line.debit
    #             balance = (credit_sum - debit_sum)
    #
    #     # If Student Have The Arrears
    #     if balance > 0 and not add_drop_challan:
    #         open_invoices = self.env['account.move'].search(
    #             [
    #                 ('payment_state', '=', 'not_paid'),
    #                 ('student_id', '=', self.id),
    #                 ('move_type', '=', 'out_invoice'),
    #                 ('sub_invoice', '=', False),
    #                 ('is_scholarship_fee', '!=', True),
    #                 ('student_ledger_id.is_defer_entry', '!=', True)
    #             ]
    #         )
    #         # Added at 22-08-2021
    #         # Cancel the Previous Invoices
    #         if open_invoices:
    #             for open_invoice in open_invoices:
    #                 open_invoice.mapped('line_ids').remove_move_reconcile()
    #                 open_invoice.write({'state': 'cancel', 'cancel_due_to_arrears': True})
    #
    #         arrears_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', '=', 'Arrears')], order='id', limit=1)
    #         arrears_line = {
    #             'sequence': 1000,
    #             'price_unit': round(balance),
    #             'quantity': qty,
    #             'product_id': arrears_fee_head.product_id and arrears_fee_head.product_id.id or False,
    #             'name': arrears_fee_head.product_id and arrears_fee_head.product_id.name or 'Previous Arrears ',
    #             'account_id': arrears_fee_head.property_account_income_id.id,
    #             # 'analytic_tag_ids': analytic_tag_ids,
    #             'fee_head_id': arrears_fee_head.id,
    #             'exclude_from_invoice_tab': False,
    #             'no_split': arrears_fee_head.no_split,
    #             'registration_type': 'add' if add_drop_challan else 'main',
    #         }
    #         lines.append((0, 0, arrears_line))
    #
    #     # If Student Have The Paid the Extra Amount, then make the Adjustment in the Fee Receipt
    #     # ******* Added @ 01-08-2021 ******** #
    #     # To Manage Adjustment Issue in Ledger Double effect
    #     adjustment_amt = 0
    #     adjustment_lines = self.env['odoocms.fee.adjustment.request'].search([('student_id', '=', self.id),
    #          ('adjustment_term_id', '=', term_id.id), ('charged', '=', False)])
    #     if adjustment_lines:
    #         for adjustment_line in adjustment_lines:
    #             if not self.env['odoocms.fee.adjustment.request.reversal'].search([('adjustment_request_id', '=', adjustment_line.id)]):
    #                 adjustment_amt += adjustment_line.total_refund_amount
    #                 adjustment_line.charged = True
    #     # ******* End @ 01-08-2021 ********
    #
    #     if balance < 0 or adjustment_amt > 0:
    #         adjustment_amount = 0
    #         if adjustment_amt > 0:
    #             adjustment_amount = -adjustment_amt
    #         if balance < 0:
    #             adjustment_amount = balance - adjustment_amt
    #
    #         # Suppose if invoice amount is 15000 and adjustment amount is 25000 then it
    #         if abs(adjustment_amount) > lines_sum:
    #             adjustment_amount = -lines_sum
    #
    #         adjustment_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', 'in', ("Previous Month's Fee Adjustment", "OD Adjustment", "Adjustment"))],
    #             order='id', limit=1)
    #         adjustment_line_values = {
    #             'price_unit': round(adjustment_amount),
    #             'quantity': qty,
    #             'product_id': adjustment_fee_head.product_id and adjustment_fee_head.product_id.id or False,
    #             'name': adjustment_fee_head.product_id and adjustment_fee_head.product_id.name or 'Adjustment',
    #             'account_id': adjustment_fee_head.property_account_income_id.id,
    #             # 'analytic_tag_ids': analytic_tag_ids,
    #             'fee_head_id': adjustment_fee_head.id,
    #             'exclude_from_invoice_tab': False,
    #             'no_split': adjustment_fee_head.no_split,
    #             'registration_type': 'add' if add_drop_challan else 'main',
    #         }
    #         lines.append((0, 0, adjustment_line_values))
    #         balance = abs(adjustment_amount)
    #
    #     return lines, adjustment_amount, adjustment_lines

    # def get_overdraft_adjustments(self, lines, waiver_discount):
    #     od_amt = 0
    #     od_rec = self.env['odoocms.student.ledger'].search([('student_id', '=', self.id)], order='id desc', limit=1)
    #     if od_rec.balance > 0:
    #         invoice_disc_able_amt = 0
    #         invoice_other_amt = 0
    #         for nw_line in lines:
    #             invoice_disc_able_amt += nw_line[2]['price_unit'] if nw_line[2].get('discount', False) and nw_line[2]['discount'] > 0 else 0
    #             invoice_other_amt += nw_line[2]['price_unit'] if not nw_line[2].get('discount', False) else 0
    #
    #         disc_amt = round(invoice_disc_able_amt * (waiver_discount / 100 or 1))
    #         adjustment_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', 'ilike', 'Fee Adjustment')], order='id', limit=1)
    #         od_amt = -od_rec.balance if (invoice_disc_able_amt + invoice_other_amt - disc_amt) > od_rec.balance else -(invoice_disc_able_amt + invoice_other_amt - disc_amt)
    #         adjustment_line_values = {
    #             'price_unit': od_amt,
    #             'quantity': 1,
    #             'product_id': adjustment_fee_head.product_id and adjustment_fee_head.product_id.id or False,
    #             'name': adjustment_fee_head.product_id and adjustment_fee_head.product_id.name or 'Adjustment',
    #             'account_id': adjustment_fee_head.property_account_income_id.id,
    #             # 'analytic_tag_ids': analytic_tag_ids,
    #             'fee_head_id': adjustment_fee_head.id,
    #             'exclude_from_invoice_tab': False,
    #             'no_split': adjustment_fee_head.no_split,
    #         }
    #         lines.append((0, 0, adjustment_line_values))
    #     return lines, od_amt

    def generate_challan_without_registration(self, term_id, receipt_type_ids=None, payment_term_id=None, date_due=None):
        self.log = ''
        if not receipt_type_ids:
            faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', term_id.id)], order='id desc', limit=1)
            if not faculty_wise_fee_rec:
                raise UserError(_('Faculty Wise Challan Configuration for this Student is not Found.'))

            receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids
            payment_term_id = faculty_wise_fee_rec.invoice_payment_term_id
            date_due = faculty_wise_fee_rec.date

        invoice_id = self.generate_invoice_new(term_id=term_id, receipts=receipt_type_ids, date_due=date_due,
                                           apply_taxes=False, registration_id=False, add_drop_challan=False, payment_term=payment_term_id)

        if invoice_id:
            challan_type = 'main_challan'

            if invoice_id.amount_total > 0:
                invoice_id.generate_challan_barcode(self)

            invoice_id.challan_type = challan_type
            return invoice_id

    def generate_registration_invoice(self, registration_id, receipt_type_ids=None, payment_term_id=None, date_due=None):
        log_message_config = self.env['ir.config_parameter'].sudo().get_param('aarsol.log', 'False')
        log_message = True if log_message_config in ('True', 'Yes', '1') else False
        if log_message:
            self.log = ''
            self.add_log_message(f": generate_registration_invoice method is called at {datetime.datetime.now().strftime('%m/%d/%Y, %H:%M:%S')}", 'blue')

        term_id = registration_id.term_id
        add_drop_challan = False
        if registration_id.add_drop_request:
            add_drop_challan = True
        if not add_drop_challan:  # check, if this is required
            if any([r.add_drop_request for r in self.registration_request_ids.mapped('registration_id').filtered(lambda l: l.term_id.id == term_id.id)]):
                add_drop_challan = True

        if log_message and add_drop_challan:
            self.add_log_message(f": Add-Drop is True ", 'black')

        if not receipt_type_ids:
            faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', term_id.id)], order='id desc', limit=1)
            if not faculty_wise_fee_rec:
                raise UserError(_('Faculty Wise Challan Configuration for this Student is not Found.'))

            receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids
            payment_term_id = faculty_wise_fee_rec.invoice_payment_term_id
            if not payment_term_id:
                raise UserError(_('Payment Term is not configured in Faculty Wise Challan Configuration.'))
            to_compute = payment_term_id.compute(10000, date_ref=date.today(), currency=self.company_id.currency_id)
            date_due = to_compute[-1][0]

            if add_drop_challan:
                payment_term_id = faculty_wise_fee_rec.adddrop_payment_term_id
                if not payment_term_id:
                    raise UserError(_('Add/Drop Payment Term is not configured in Faculty Wise Challan Configuration.'))
                to_compute = payment_term_id.compute(10000, date_ref=date.today(), currency=self.company_id.currency_id)
                date_due = to_compute[-1][0]

            if not receipt_type_ids:
                if log_message:
                    self.add_log_message(f": No receipt type extracted from Faculty Wise Challan Configuration, Invoice cannot be generated", 'red')
                    return False
                else:
                    raise UserError(_('No receipt type extracted from Faculty Wise Challan Configuration'))

            if not payment_term_id:
                if log_message:
                    self.add_log_message(f": No payment term extracted from Faculty Wise Challan Configuration, Invoice cannot be generated", 'red')
                    return False
                else:
                    raise UserError(_('No payment term extracted from Faculty Wise Challan Configuration'))

            if log_message:
                self.add_log_message(f": {''.join(receipt_type_ids.mapped('name'))} receipt types and {payment_term_id.name} extracted from Faculty Wise Challan Configuration", 'green')

        invoice_id = self.generate_invoice_new(term_id=term_id, receipts=receipt_type_ids, date_due=date_due,
            apply_taxes=False, registration_id=registration_id, add_drop_challan=add_drop_challan,payment_term=payment_term_id, log_message=log_message)

        if not invoice_id and log_message:
            self.add_log_message(f": Invoice not generated", 'red')
            return False

        challan_type = 'add_drop' if add_drop_challan else 'main_challan'

        if log_message:
            self.add_log_message(f": {invoice_id.name} generated with challan type {challan_type}", 'blue')

        registration_id.invoice_id = invoice_id.id

        if invoice_id.amount_total == 0:   # Confirm Registration Request if Invoice Amount is Zero
            auto_approve_registration_zero_invoice = self.env['ir.config_parameter'].sudo().get_param('aarsol.auto_approve_registration_zero_invoice', 'True')
            if auto_approve_registration_zero_invoice in ('True','Yes', '1'):
                if registration_id and registration_id.state == 'submit':
                    registration_id.sudo().action_approve()

                invoice_id.write({
                    'state': 'posted',
                    'payment_state': 'paid',
                    'narration': 'Auto Paid state Due To Zero Balance',
                    'payment_date': fields.Date.today()
                })
        elif invoice_id.amount_total > 0:
            invoice_id.generate_challan_barcode(self)

        else: # Create Credit Note and apply on Invoice
            receivable_lines = invoice_id.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            inv_domain = [('student_id', '=', registration_id.student_id.id), ('state','=','posted'),('term_id', '=', term_id.id), ('id','!=', invoice_id.id)]
            other_invoices = self.env['account.move'].sudo().search(inv_domain)
            receivable_lines2 = other_invoices.line_ids.filtered(lambda line: not line.reconciled and line.account_id.user_type_id.type in ('receivable', 'payable'))
            (receivable_lines + receivable_lines2).reconcile()

            if registration_id and registration_id.state == 'submit':
                registration_id.sudo().action_approve()

            invoice_id.write({
                'state': 'posted',
                'payment_state': 'paid',
                'narration': 'Auto Paid - Credit Note',
                'payment_date': fields.Date.today()
            })

            invoice_id.challan_type = challan_type

            # domain = [
            #     ('term_id', '=', invoice_id.term_id.id),
            #     ('faculty_id', '=', invoice_id.student_id.institute_id.id),
            #     ('program_id', '=', invoice_id.student_id.program_id.id),
            #     ('type', '=', '2nd_challan'),
            #     ('state', '=', 'confirm')
            # ]
            # find_show_on_portal_rec = self.env['odoocms.show.challan.on.portal.line'].search(domain)
            # if find_show_on_portal_rec:
            #     show_challan_on_portal = True
            # invoice_id.write({
            #     'challan_type': '2nd_challan',
            #     'semester_gross_fee': invoice_id.semester_gross_fee,
            #     'show_challan_on_portal': True,
            # })

        return invoice_id


    # Assign Continue Policy to student, if not already assigned
    def get_scholarship_policy(self, log_message=False):
        for rec in self:
            # To Be Un-Remark For Production
            # application_id = rec.application_id
            application_id = False

            if not rec.scholarship_policy_id:
                scholarship_policy_id = False

                # ***** First Of All Check The Student Admission Application *****#
                if application_id:
                    admission_term = rec.application_id.register_id.term_id
                    if admission_term:
                        scholarship_policy_id = self.env['odoocms.scholarship.continue.policy'].search([('start_term.number', '<=', admission_term.number)], order="id desc", limit=1)

                    if not admission_term:
                        scholarship_policy_id = self.env['odoocms.student.applied.scholarships'].search([('student_id', '=', rec.id)], order='id desc', limit=1)
                    if scholarship_policy_id:
                        rec.scholarship_policy_id = scholarship_policy_id.id

                # ***** For Exiting Student ******#
                if not application_id:
                    academic_term = rec.batch_id.term_id
                    if not academic_term:
                        student_term = self.env['odoocms.student.term'].search([('student_id', '=', self.id)], order='id asc', limit=1)
                        if student_term:
                            academic_term = student_term.term_id
                    if academic_term:
                        scholarship_policy_id = self.env['odoocms.scholarship.continue.policy'].search([('start_term.number', '<=', academic_term.number)], order="id desc", limit=1)
                        rec.scholarship_policy_id = scholarship_policy_id and scholarship_policy_id.id or False

    def get_eligible_scholarships(self, term_id, registration_id, policy_lines, log_message=False):
        last_regular_term_domain = [('term_id', '!=', term_id.id), ('student_id', '=', self.id), ('term_id.type', '=', 'regular'), ('term_id.code', '!=', 'TC'), ('earned_credits', '>', 0)]
        course_load_last_term = self.env['odoocms.student.term'].search(last_regular_term_domain, order='number desc', limit=1)

        registered_courses = self.env['odoocms.student.course'].search([('student_id', '=', self.id), ('term_id', '=', term_id.id), ('grade', 'not in', ('W', 'F'))])

        sum_credits, sum_non, sum_repeat, sum_courses, reg_credits, reg_courses, req_credits, req_courses, drop_credits, drop_courses = registration_id._register_limit(registered_courses, registration_id.line_ids)

        if log_message:
            self.add_log_message(f": --------------------------", '#A5FF00')
            self.add_log_message(f": course load Student Term - {str(last_regular_term_domain)}", '#FFA500')
            if course_load_last_term:
                self.add_log_message(f": course load Student Term - {str(course_load_last_term.id)}", 'green')
            else:
                self.add_log_message(f": course load Student Term - Not Found ", 'red')

        # course_load_student_term = course_load_student_term_recs and course_load_student_term_recs[-1:] or course_load_student_term_recs
        w_grades = course_load_last_term.student_course_ids.filtered(lambda l: l.grade in ('W', 'N', 'I'))
        w_grade_load = sum([w_grade.credits for w_grade in w_grades])
        course_cnt = len(course_load_last_term.student_course_ids) - len(w_grades)
        credit_hours = course_load_last_term.earned_credits

        notified_term_domain = [('term_id', '!=', term_id.id), ('term_id.code', '!=', 'TC'),  ('student_id', '=', self.id), ('state', '=', 'done')]
        notified_term = self.env['odoocms.student.term'].search(notified_term_domain, order='number desc', limit=1)
        # course_cgpa_student_term = course_cgpa_student_terms and course_cgpa_student_terms[-1:] or course_cgpa_student_terms
        cgpa = notified_term.cgpa
        sgpa = notified_term.sgpa
        sgpa_check_in_scholarship_policy = self.env['ir.config_parameter'].sudo().get_param('aarsol.sgpa_check_in_scholarship_policy', 'False')
        if log_message:
            self.add_log_message(f": Credit Hours - {str(credit_hours)}, CGPA - {str(cgpa)}", 'blue')

        if self.scholarship_policy_id:    # to do, is there any need of this if
            scholarship_eligibility_ids = self.scholarship_eligibility_ids
            # if registration_id.enrollment_type == 'advance_enrollment':
            #     scholarship_eligibility_ids = scholarship_eligibility_ids.filtered(lambda l: l.scholarship_id.advance_enrollment)

            for scholarship_eligibility_id in scholarship_eligibility_ids:
                domain = [
                    ('policy_id', '=', self.scholarship_policy_id.id),
                    ('scholarship_id', '=', scholarship_eligibility_id.scholarship_id.id),
                    ('program_id', '=', self.program_id.id),
                    ('credit_hours', '>', 0),
                    ('credit_hours', '<=', credit_hours),
                    ('current_credit_hours', '<=', sum_credits),
                    ('cgpa', '<=', cgpa)
                ]
                if sgpa_check_in_scholarship_policy in ('True','Yes','1'):
                    domain.append(('sgpa', '<=', sgpa))

                policy_line = self.env['odoocms.scholarship.continue.policy.line'].search(domain, order='cgpa desc', limit=1)
                if log_message:
                    self.add_log_message(f": --------------------------", '#A5FF00')
                    self.add_log_message(f": Continue Policy Line - {str(domain)}", '#FFA500')
                    if policy_line:
                        self.add_log_message(f": Continue Policy Line - {str(policy_line.id)}", 'green')
                    else:
                        self.add_log_message(f": Continue Policy Line - Not Found ", 'red')

                if policy_line:
                    policy_lines |= policy_line
                else:
                    domain = [
                        ('policy_id', '=', self.scholarship_policy_id.id),
                        ('scholarship_id', '=', scholarship_eligibility_id.scholarship_id.id),
                        ('program_id', '=', self.program_id.id),
                        ('course_count', '>', 0),
                        ('course_count', '<=', course_cnt),
                        ('current_course_count', '<=', sum_courses),
                        ('cgpa', '<=', cgpa)
                    ]
                    if sgpa_check_in_scholarship_policy in ('True','Yes','1'):
                        domain.append(('sgpa', '<=', sgpa))

                    policy_line = self.env['odoocms.scholarship.continue.policy.line'].search(domain, order='cgpa desc', limit=1)
                    if log_message:
                        self.add_log_message(f": Continue Policy Line - {str(domain)}", '#FFA500')
                        if policy_line:
                            self.add_log_message(f": Continue Policy Line - {str(policy_line.id)}", 'green')
                        else:
                            self.add_log_message(f": Continue Policy Line - Not Found ", 'red')

                    if policy_line:
                        policy_lines |= policy_line

            # 'CGPA based Scholarship'
            cgpa_base_scholarship = self.env['odoocms.fee.waiver'].search([]).filtered(lambda l: l.scholarship_category_id.progress_base)
            domain = [
                ('policy_id', '=', self.scholarship_policy_id.id),
                ('scholarship_id', 'in', cgpa_base_scholarship.ids),
                ('program_id', '=', self.program_id.id),
                ('credit_hours', '>', 0),
                ('credit_hours', '<=', credit_hours),
                ('current_credit_hours', '<=', sum_credits),
                ('cgpa', '<=', cgpa)
            ]
            if sgpa_check_in_scholarship_policy in ('True','Yes','1'):
                domain.append(('sgpa', '<=', sgpa))

            cgpa_policy_line = self.env['odoocms.scholarship.continue.policy.line'].search(domain, order='cgpa desc', limit=1)
            if log_message:
                self.add_log_message(f": Continue Policy Line - {str(domain)}", '#FFA500')
                if cgpa_policy_line:
                    self.add_log_message(f": Continue Policy Line - {str(cgpa_policy_line.id)}", 'green')
                else:
                    self.add_log_message(f": Continue Policy Line - Not Found ", 'red')

            if cgpa_policy_line:
                policy_lines += cgpa_policy_line
            else:
                domain = [
                    ('policy_id', '=', self.scholarship_policy_id.id),
                    ('scholarship_id', 'in', cgpa_base_scholarship.ids),
                    ('program_id', '=', self.program_id.id),
                    ('course_count', '>', 0),
                    ('course_count', '<=', course_cnt),
                    ('current_course_count', '<=', sum_courses),
                    ('cgpa', '<=', cgpa)
                ]
                if sgpa_check_in_scholarship_policy in ('True','Yes','1'):
                    domain.append(('sgpa', '<=', sgpa))

                cgpa_policy_line = self.env['odoocms.scholarship.continue.policy.line'].search(domain, order='cgpa desc', limit=1)
                if log_message:
                    self.add_log_message(f": Continue Policy Line - {str(domain)}", '#FFA500')
                    if cgpa_policy_line:
                        self.add_log_message(f": Continue Policy Line - {str(cgpa_policy_line.id)}", 'green')
                    else:
                        self.add_log_message(f": Continue Policy Line - Not Found ", 'red')

                if cgpa_policy_line:
                    policy_lines |= cgpa_policy_line

        return policy_lines

    def get_applied_scholarship(self, term_id, log_message=False):
        domain = [('student_id', '=', self.id), ('term_id', '=', term_id.id)]
        applied_scholarship = self.env['odoocms.student.applied.scholarships'].search(domain)
        if log_message:
            self.add_log_message(f": --------------------------", '#A5FF00')
            self.add_log_message(f": Student Applied Scholarships - {str(domain)}", '#FFA500')
            if applied_scholarship:
                self.add_log_message(f": Student Applied Scholarships - {str(applied_scholarship.id)}", 'green')
            else:
                self.add_log_message(f": Student Applied Scholarships - Not Found ", 'green')
        return applied_scholarship

    def shortlist_policy(self, term_id, policy_lines, applied_scholarship, log_message=False):
        short_listed_policy_line = policy_lines.sorted(key=lambda line: line.value, reverse=True)[0]
        if log_message:
            self.add_log_message(f": Short Listed Policy Line {str(short_listed_policy_line)}", 'red')

        self.write({
            'scholarship_id': short_listed_policy_line and short_listed_policy_line.scholarship_id.id or False,
            'scholarship_policy_line_id': short_listed_policy_line and short_listed_policy_line.id or False
        })
        if not applied_scholarship.scholarship_id == self.scholarship_id:
            applied_scholarship.sudo().unlink()
            applied_scholarship = False

        if not applied_scholarship:
            if short_listed_policy_line:
                data_values = {
                    'student_id': self.id,
                    'student_code': self.code,
                    'student_name': self.name,
                    'program_id': self.program_id.id or False,
                    'term_id': term_id and term_id.id or False,
                    'scholarship_id': self.scholarship_id and self.scholarship_id.id or False,
                    'scholarship_continue_policy_id': short_listed_policy_line.policy_id.id,
                    'scholarship_continue_policy_line_id': short_listed_policy_line.id,
                    'scholarship_percentage': short_listed_policy_line.value or 0,
                    'current': True,
                    'state': 'lock',
                }
                self.env['odoocms.student.applied.scholarships'].sudo().create(data_values)

    def check_special_scholarship(self, term_id, log_message=False):
        special_scholarship_domain = [('student_id', '=', self.id), ('term_id', '=', term_id.id), ('state', '=', 'approved')]
        special_scholarship_id = self.env['odoocms.student.special.scholarship'].search(special_scholarship_domain)
        if log_message:
            self.add_log_message(f": Special Scholarship Domain - {str(special_scholarship_domain)}", '#FFA500')
            if special_scholarship_id:
                self.add_log_message(f": Special Scholarship Record - {str(special_scholarship_id.id)} - {str(special_scholarship_id.name)}", 'green')
            else:
                self.add_log_message(f": Special Scholarship Record - Not Found ", 'red')

        if special_scholarship_id:
            self.scholarship_id = special_scholarship_id.scholarship_id and special_scholarship_id.scholarship_id.id or False
        return special_scholarship_id

    def _assign_special_scholarship_institute(self):
        pass

    def check_special_scholarship_institute(self, term_id):
        policy_line = self.env['odoocms.scholarship.continue.policy.line']
        return policy_line

    def compute_student_current_scholarship(self, term_id=False, registration_id=False, log_message=False):
        if log_message:
            self.add_log_message(f": compute_student_current_scholarship", 'black')

        for rec in self:
            # ***** Check if Scholarship is Blocked For This Student *****#
            if rec.block_scholarship:
                rec.scholarship_id = False
                if log_message:
                    self.add_log_message(f": Scholarship Blocked", 'red')
                continue

            # ***** Get Fee Charge Term ***** #
            if not term_id:
                fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
                if not fee_charge_term:
                    raise UserError(_('Please Specify Fee Charging Term in CMS Fee Configuration Setting.'))
                term_id = self.env['odoocms.academic.term'].browse(fee_charge_term)

            if rec.check_special_scholarship(term_id, log_message):
                continue

            policy_lines = self.env['odoocms.scholarship.continue.policy.line']
            first_semester_flag = False

            # ***** For First Semester Student Just Check the Eligibility *****#
            semester_no = self.env['odoocms.student.term'].search_count([('student_id', '=', self.id), ('term_id', '!=', term_id.id)]) + 1
            if semester_no == 1 and rec.scholarship_eligibility_ids:
                first_semester_flag = True
                short_listed_policy_lines = rec.scholarship_eligibility_ids.sorted(key=lambda line: line.scholarship_value, reverse=True)
                rec.scholarship_id = short_listed_policy_lines[0] and short_listed_policy_lines[0].scholarship_id.id or False

                # **** PGC One Year *****#
                rec._assign_special_scholarship_institute()

            if not first_semester_flag and registration_id:
                policy_lines |= rec.check_special_scholarship_institute(term_id)
                policy_lines |= rec.get_eligible_scholarships(term_id, registration_id, policy_lines, log_message=False)

            applied_scholarship = rec.get_applied_scholarship(term_id)

            if policy_lines:
                rec.shortlist_policy(term_id, policy_lines, applied_scholarship, log_message)

            elif applied_scholarship:
                if log_message:
                    self.add_log_message(f": ------ Applied Scholarship --------", '#A5FF00')
                    self.add_log_message(f": Applied Scholarship {str(applied_scholarship.scholarship_id.name)}", 'yellow')
                rec.scholarship_id = applied_scholarship.scholarship_id and applied_scholarship.scholarship_id.id or False

            else:
                rec.scholarship_policy_line_id = False
                full_fee_scholarship = self.env['odoocms.fee.waiver'].sudo().search([('name', '=', 'Full Fee')])
                if full_fee_scholarship:
                    rec.scholarship_id = full_fee_scholarship.id
                    data_values = {
                        'student_id': rec.id,
                        'student_code': rec.code,
                        'student_name': rec.name,
                        'program_id': rec.program_id.id or False,
                        'term_id': term_id and term_id.id or False,
                        'scholarship_id': full_fee_scholarship.id,
                        'scholarship_continue_policy_id': False,
                        'scholarship_continue_policy_line_id': False,
                        'scholarship_percentage': full_fee_scholarship.amount,
                        'current': True,
                        'state': 'lock',
                    }
                    self.env['odoocms.student.applied.scholarships'].sudo().create(data_values)

            if log_message:
                self.add_log_message(f": scholarship_id: {str(rec.scholarship_id and rec.scholarship_id.name or 'False')}", 'green')
                self.add_log_message(f": scholarship_line_id: {str(rec.scholarship_policy_line_id and rec.scholarship_policy_line_id.name or 'False')}", 'green')

    def action_create_student_fee_waiver_entry(self, amount, invoice):
        student_fee_waiver_data = {
            'student_id': self.id,
            'invoice_id': invoice and invoice.id or False,
            'term_id': invoice.term_id and invoice.term_id.id or False,
            'waiver_type': 'percentage',
            'amount': amount,
            'amount_percentage': 0,
            'waiver_line_id': False
        }
        self.env['odoocms.student.fee.waiver'].create(student_fee_waiver_data)

    # ***** Cron Job to Generate the Challan at the Time of Result Notify *****#
    @api.model
    def cron_fee_challan_generation(self, nlimit=10):
        registrations = self.env['odoocms.course.registration'].search([('generate_fee', '=', True),
                                                                        ('invoice_id', '=', False)], limit=nlimit)
        if registrations:
            for registration in registrations:
                fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
                if not fee_charge_term:
                    raise UserError(_('Please define Fee Charge Term in Configuration Setting.'))
                student_term = self.env['odoocms.student.term'].search([('student_id', '=', registration.student_id.id),
                                                                        ('term_id', '=', fee_charge_term)])
                if student_term:
                    invoice_id = registration.student_id.generate_registration_invoice(student_term)
                    if invoice_id:
                        registration.generate_fee = False
                        registration.invoice_id = invoice_id and invoice_id.id or False

    def get_added_courses(self, registration_request=False):
        if registration_request:
            added_credit_hours = 0
            added_courses = registration_request.line_ids.filtered(lambda a: a.action == "add")
            if added_courses:
                added_credit_hours = sum([c.credits for c in added_courses])
            return added_courses, added_credit_hours

    def get_dropped_courses(self, registration_request=False):
        if registration_request:
            dropped_credit_hours = 0
            dropped_courses = registration_request.line_ids.filtered(lambda a: a.action == "drop")
            if dropped_courses:
                dropped_credit_hours = sum([d.credits for d in dropped_courses])
            return dropped_courses, dropped_credit_hours

    # **********************************************************************************************
    # This Function Will Update The Invoice And Delete The Dropped Course Line                     *
    # For the Add And Drop, there are two cases                                                    *
    # i):-  Dropped Courses Credit hours and Add Courses Credit Hours are Equal                    *
    # ii):- Dropped Courses Credit Hours and Add Courses Credit Hours are not Equal                *
    #                                                                                              *
    # in Case-i) Further there are three cases;                                                    *
    # a):- no of dropped courses are equal to on add courses                                       *
    # b):- no of dropped courses are greater than no of added courses                              *
    # c):- no of dropped courses are less than no of added courses                                 *
    #   In All these Cases first we manage the Add Drop Challan, in which Added courses are added  *
    #   then dropped courses paid and unpaid amount lines are separately added in add drop challan *
    #   secondly we check if line is not payment then we also modify that dropped course Unpaid    *
    #   Line with name Adding Dropped and setting Amount values zero                               *
    #   Thirdly we add the Added Course in the Existing Invoice with Unpaid line amount            *
    #   in this Case existing Invoice ledger is not updated, because added courses and dropped     *
    #   Courses credit are same.                                                                   *
    # in 2nd Case,                                                                                 *
    #   We find the                                                                                *
    #   Dropped Lines Total Amount                                                                 *
    #   Paid Lines Amount                                                                          *
    #   Unpaid Lines Amount                                                                        *
    #   Adding Dropped Course line in the Fee lines with debit amount                              *
    #   Than if line is not Paid then modify the line name with 'Dropped' adding in it             *
    #   and Setting Amount values to Zero                                                          *
    #   Create Adjustment Create in Add Drop Invoice                                               *
    #   Create Adjustment Entry in 2nd Installment                                                 *
    #   Update Receivable Line, it will Debit                                                      *
    #   Invoice Total Update                                                                       *
    #   Student Ledger Update                                                                      *
    #   ---->End:-                                                                                 *
    # **********************************************************************************************

    def update_fee_invoice_lines(self, invoice_lines=None, term_id=None, registration_id=None, added_courses_amount=0, lines=None):
        if term_id is None:
            return
        if invoice_lines is None:
            return
        if registration_id is None:
            return

        dropped_courses, dropped_credit_hours = self.get_dropped_courses(registration_request=registration_id)
        added_courses, added_credit_hours = self.get_added_courses(registration_request=registration_id)
        # if added_credit_hours and dropped_credit_hours Are Equal *****#
        if 0 < added_credit_hours == dropped_credit_hours > 0:
            # ***** if Dropped and Added Course are Equal ***** #
            if len(added_courses) == len(dropped_courses):
                drop_no = 0
                global_paid_invoice_line = self.env['account.move.line']
                for invoice_line in sorted(invoice_lines, key=lambda x: x.course_credit_hours, reverse=True):
                    ad_course = added_courses[drop_no]
                    dp_course = dropped_courses[drop_no]
                    line_add_drop_paid_amt = 0

                    # ***** If Amount Are Same *****#
                    if lines and lines[drop_no][2]['price_unit'] == invoice_line.price_unit:
                        fee_lines = self.prepare_dropped_invoice_lines(invoice_line, registration_id, dp_course)
                        lines.append((0, 0, fee_lines))

                        if invoice_line.move_id.payment_state not in ('in_payment', 'paid'):
                            credit_amt1 = 0
                            new_name = invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-)"
                            add_drop_no_txt = str(invoice_line.add_drop_no) + " , Drop->" + registration_id.add_drop_request_no_txt
                            self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s, registration_type=%s,add_drop_no=%s where id=%s \n"
                                                , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', add_drop_no_txt, invoice_line.id))
                            self._cr.commit()

                        ##################
                        new_name = ad_course.primary_class_id.course_id.code + "-" + ad_course.primary_class_id.course_id.name + " (Add)"
                        new_mvl = self.account_move_line_credit_line_insert(invoice_line, ad_course, lines[drop_no][2]['price_unit'], lines[drop_no][2]['price_unit'], registration_id, new_name, 'add')
                        self._cr.commit()

                    # ***** Amounts Are not Equal *****
                    elif lines and not lines[drop_no][2]['price_unit'] == invoice_line.price_unit:
                        paid_inv_line = self.env['account.move.line']
                        unpaid_inv_line = self.env['account.move.line']

                        if invoice_line.move_id.payment_state in ('in_payment', 'paid'):
                            paid_inv_line = invoice_line
                        else:
                            unpaid_inv_line = invoice_line

                        if unpaid_inv_line:
                            paid_inv_line = self.env['account.move.line'].search([('course_id_new', '=', invoice_line.course_id_new.id),
                                                                                  ('student_id', '=', self.id),
                                                                                  ('term_id', '=', term_id.id),
                                                                                  ('move_id.payment_state', 'in', ('in payment', 'paid'))], order='id desc', limit=1)

                        if paid_inv_line:
                            unpaid_inv_line = self.env['account.move.line'].search([('course_id_new', '=', invoice_line.course_id_new.id),
                                                                                    ('student_id', '=', self.id),
                                                                                    ('term_id', '=', term_id.id),
                                                                                    ('move_id.payment_state', 'not in', ('in payment', 'paid'))], order='id desc', limit=1)

                        if paid_inv_line:
                            global_paid_invoice_line = paid_inv_line
                            line_add_drop_paid_amt = paid_inv_line.price_unit
                            fee_lines = self.prepare_dropped_invoice_lines(paid_inv_line, registration_id, dp_course)
                            lines.append((0, 0, fee_lines))
                        if unpaid_inv_line:
                            global_paid_invoice_line = unpaid_inv_line
                            fee_lines = self.prepare_dropped_invoice_lines(unpaid_inv_line, registration_id, dp_course)
                            lines.append((0, 0, fee_lines))

                            new_name = ad_course.primary_class_id.course_id.code + "-" + ad_course.primary_class_id.course_id.name + " (Add)"
                            add_drop_no_txt = str(invoice_line.add_drop_no) + " , Drop->" + registration_id.add_drop_request_no_txt

                        ##########
                        lines[drop_no][2]['add_drop_paid_amount'] = line_add_drop_paid_amt
                        if lines[drop_no][2]['registration_type'] == 'add' and lines[drop_no][2]['add_drop_paid_amount'] > 0:
                            line_amt = lines[drop_no][2]['price_unit'] - lines[drop_no][2]['add_drop_paid_amount']
                            new_name = lines[drop_no][2]['name'] + " (Add)"
                            ad_course = self.env['odoocms.course.registration.line'].search([('id', '=', lines[drop_no][2]['registration_line_id'])])
                            new_mvl = self.account_move_line_credit_line_insert(global_paid_invoice_line, ad_course, line_amt, line_amt, registration_id, new_name, 'add')

                        if invoice_line.move_id.payment_state not in ('in_payment', 'paid'):
                            credit_amt1 = 0
                            new_name = invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-)"
                            self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s,registration_type=%s,add_drop_no=%s where id=%s \n"
                                                , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', add_drop_no_txt, invoice_line.id))
                            self._cr.commit()
                    drop_no += 1

            # ***** If Dropped Course Greater Than Added Courses Then Dropped Extra Dropped Courses ***** #
            else:
                dp_no = 0
                lines_paid_amount = 0
                # ***** Managed Dropped Courses *****#
                for invoice_line in invoice_lines:
                    dp_course = dropped_courses[dp_no]
                    paid_inv_line = self.env['account.move.line']
                    unpaid_inv_line = self.env['account.move.line']

                    if invoice_line.move_id.payment_state in ('in_payment', 'paid'):
                        paid_inv_line = invoice_line
                    else:
                        unpaid_inv_line = invoice_line

                    if unpaid_inv_line and not paid_inv_line:
                        paid_inv_line = self.env['account.move.line'].search([('course_id_new', '=', invoice_line.course_id_new.id),
                                                                              ('student_id', '=', self.id),
                                                                              ('term_id', '=', term_id.id),
                                                                              ('move_id.payment_state', 'in', ('in payment', 'paid'))], order='id desc', limit=1)

                    if paid_inv_line and not unpaid_inv_line:
                        unpaid_inv_line = self.env['account.move.line'].search([('course_id_new', '=', invoice_line.course_id_new.id),
                                                                                ('student_id', '=', self.id),
                                                                                ('term_id', '=', term_id.id),
                                                                                ('move_id.payment_state', 'not in', ('in payment', 'paid'))], order='id desc', limit=1)

                    if paid_inv_line:
                        fee_lines = self.prepare_dropped_invoice_lines(paid_inv_line, registration_id, dp_course)
                        lines.append((0, 0, fee_lines))
                        lines_paid_amount += paid_inv_line.price_unit

                    # @SARFRAZ
                    # if unpaid_inv_line:
                    #     fee_lines = self.prepare_dropped_invoice_lines(unpaid_inv_line, registration_id, dp_course)
                    #     lines.append((0, 0, fee_lines))

                    # Update Existing/Opening Invoice Line
                    if invoice_line.move_id.payment_state not in ('in_payment', 'paid'):
                        credit_amt1 = 0
                        new_name = invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-)"
                        add_drop_no_txt = str(registration_id.add_drop_request_no_txt) + " , Drop->" + registration_id.add_drop_request_no_txt
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s, registration_type=%s,add_drop_no=%s where id=%s \n"
                                            , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', add_drop_no_txt, invoice_line.id))
                        self._cr.commit()
                    dp_no += 1

                # ***** Managed Added Course *****#
                for ad_course in added_courses:
                    invoice_lines = invoice_lines.filtered(lambda a: a.move_id.payment_state not in ('in_payment', 'paid'))
                    invoice_line = invoice_lines and invoice_lines[0] or False
                    if invoice_line and invoice_line.move_id.payment_state not in ('in_payment', 'paid'):
                        line_amt = 0
                        if lines_paid_amount > 0:
                            line_amt = round(lines_paid_amount / len(added_courses), 2)
                        else:
                            line_amt = self.batch_id.per_credit_hour_fee * ad_course.primary_class_id.credits
                        new_name = ad_course.primary_class_id.course_id.code + "-" + ad_course.primary_class_id.course_id.name + " (Add)"
                        new_mvl = self.account_move_line_credit_line_insert(invoice_line, ad_course, line_amt, line_amt, registration_id, new_name, 'add')

                        if invoice_line.move_id.payment_state not in ('in_payment', 'paid') and "Dropped" not in invoice_line.name:
                            credit_amt1 = 0
                            new_name = invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-)"
                            add_drop_no_txt = str(invoice_line.add_drop_no) + " , Drop->" + registration_id.add_drop_request_no_txt
                            self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s,registration_type=%s,add_drop_no=%s where id=%s \n"
                                                , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', add_drop_no_txt, invoice_line.id))
                            self._cr.commit()

        # ***** if added_credit_hours and dropped_credit_hours are not equal *****#
        else:
            if invoice_lines is not None:
                lines_total_amount = 0
                paid_lines_amount = 0
                unpaid_lines_amount = 0
                remaining_paid_amount, ledger_remaining_paid_amount = 0, 0

                od_amount = 0
                debit_amt = 0
                unpaid_invoice_line = False
                invoice_total_amount = 0
                global_paid_invoice_line = self.env['account.move.line']

                # ***** First I Search Out the 2nd Challan *****#
                open_challan = self.env['account.move'].search(
                    [
                        ('student_id', '=', self.id),
                        ('term_id', '=', invoice_lines[0].term_id.id),
                        ('challan_type', '=', '2nd_challan'),
                        ('payment_state', 'not in', ('in_payment', 'paid'))
                    ]
                )

                # ***** If 2nd Challan not found then search the open Challan *****#
                if not open_challan:
                    open_challan = self.env['account.move'].search(
                        [
                            ('student_id', '=', self.id),
                            ('term_id', '=', invoice_lines[0].term_id.id),
                            ('payment_state', 'not in', ('in_payment', 'paid')),
                        ],
                        order='id asc', limit=1)

                if open_challan:
                    move_id = open_challan
                else:
                    move_id = invoice_lines[0].move_id

                if move_id:
                    invoice_total_amount = move_id.amount_total
                    receivable_line = move_id.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
                    if not receivable_line:
                        raise UserError(_("Receivable Line not Found"))

                # ***** (1) ***** #
                bb = 0
                for invoice_line in invoice_lines:
                    od_amount += invoice_line.price_subtotal if not open_challan and not term_id.type == 'summer' else 0

                    line_add_drop_paid_amt = 0
                    dropped_course_fee_amt = invoice_line.course_credit_hours * self.batch_id.per_credit_hour_fee
                    if invoice_line.move_id.payment_state not in ('in_payment', 'paid'):
                        global_paid_invoice_line = invoice_line
                        unpaid_lines_amount += invoice_line.price_subtotal
                        lines_total_amount += invoice_line.price_subtotal
                        paid_invoice_line = self.env['account.move.line']
                        if invoice_line.registration_id:
                            paid_invoice_line = self.env['account.move.line'].search(
                                [
                                    ('course_id_new', '=', invoice_line.course_id_new.id),
                                    ('student_id', '=', self.id),
                                    ('term_id', '=', term_id.id),
                                    ('move_id.payment_state', 'in', ('in_payment', 'paid')),
                                    ('price_unit', '>', 0),
                                    ('registration_id', '=', invoice_line.registration_id.id),
                                    ('registration_type', 'in', ('main', 'add')),
                                ],
                                order='id desc', limit=1)
                        if not paid_invoice_line:
                            paid_invoice_line = self.env['account.move.line'].search(
                                [
                                    ('course_id_new', '=', invoice_line.course_id_new.id),
                                    ('student_id', '=', self.id),
                                    ('term_id', '=', term_id.id),
                                    ('move_id.payment_state', 'in', ('in_payment', 'paid')),
                                    ('price_unit', '>', 0),
                                    ('registration_type', 'in', ('main', 'add')),
                                ],
                                order='id desc', limit=1)

                        if paid_invoice_line:
                            line_add_drop_paid_amt = paid_invoice_line.price_subtotal
                            paid_lines_amount += paid_invoice_line.price_subtotal
                            lines_total_amount += paid_invoice_line.price_subtotal
                            fee_lines = self.prepare_dropped_invoice_lines(paid_invoice_line, registration_id, invoice_line.registration_line_id)
                            lines.append((0, 0, fee_lines))

                        lines[bb][2]['add_drop_paid_amount'] = line_add_drop_paid_amt
                        bb += 1
                        credit_amt1 = 0
                        new_name = invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-"
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s,registration_type=%s,add_drop_no=%s where id=%s \n"
                                            , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', registration_id.add_drop_request_no_txt, invoice_line.id))
                        self._cr.commit()

                    elif invoice_line.move_id.payment_state in ('in_payment', 'paid'):
                        paid_lines_amount += invoice_line.price_subtotal
                        lines_total_amount += invoice_line.price_subtotal

                        fee_lines = self.prepare_dropped_invoice_lines(invoice_line, registration_id, invoice_line.registration_line_id)
                        lines.append((0, 0, fee_lines))

                        unpaid_invoice_line = self.env['account.move.line'].search(
                            [
                                ('course_id_new', '=', invoice_line.course_id_new.id),
                                ('student_id', '=', self.id),
                                ('term_id', '=', term_id.id),
                                ('move_id.payment_state', '=', 'not_paid'),
                                ('price_unit', '>', 0),
                                ('registration_type', 'in', ('main', 'add')),
                            ],
                            order='id desc', limit=1)

                        if unpaid_invoice_line:
                            # assuming that there is only one open invoice in system  for this student
                            move_id = unpaid_invoice_line.move_id
                            invoice_total_amount = move_id.amount_total
                            receivable_line = move_id.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')

                            unpaid_lines_amount += unpaid_invoice_line.price_subtotal
                            lines_total_amount += unpaid_invoice_line.price_subtotal

                            if not dropped_course_fee_amt == invoice_line.price_subtotal:
                                lines_total_amount += unpaid_invoice_line.price_subtotal
                                fee_lines = self.prepare_dropped_invoice_lines(unpaid_invoice_line, registration_id, invoice_line.registration_line_id, invoice_line.price_unit)
                                lines.append((0, 0, fee_lines))

                            credit_amt1 = 0
                            new_name = unpaid_invoice_line.name + " (Dropped =" + str(invoice_line.price_unit) + "/-)"
                            self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, discount=0,name=%s,registration_type=%s,add_drop_no=%s where id=%s \n"
                                                , (credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, credit_amt1, new_name, 'drop', registration_id.add_drop_request_no_txt, unpaid_invoice_line.id))
                            self._cr.commit()

                # ***** (2) ******* #
                debit_amt = lines_total_amount - paid_lines_amount
                if paid_lines_amount > added_courses_amount:
                    remaining_paid_amount = paid_lines_amount - added_courses_amount
                    ledger_remaining_paid_amount = remaining_paid_amount
                    # ***** Create Adjustment In Add Drop Invoice *****#
                    adj_lines = self.prepare_adjustment_invoice_line(invoice_lines, registration_id, remaining_paid_amount)
                    lines.append((0, 0, adj_lines))

                    if open_challan:
                        sec_inst_line = open_challan.line_ids.filtered(lambda a: a.credit > 0)[0]
                        if (open_challan.amount_total - unpaid_lines_amount) > remaining_paid_amount:
                            self.account_move_line_debit_line_insert(sec_inst_line,
                                                                     sec_inst_line.registration_line_id,
                                                                     remaining_paid_amount,
                                                                     remaining_paid_amount,
                                                                     registration_id,
                                                                     ' Adjustment in Second Installment of (Drop) Courses',
                                                                     'drop')
                        elif (open_challan.amount_total - unpaid_lines_amount) <= remaining_paid_amount:
                            self.account_move_line_debit_line_insert(sec_inst_line,
                                                                     sec_inst_line.registration_line_id,
                                                                     open_challan.amount_total - unpaid_lines_amount,
                                                                     open_challan.amount_total - unpaid_lines_amount,
                                                                     registration_id,
                                                                     ' Adjustment in Second Installment of (Drop) Courses',
                                                                     'drop')

                    # ***** Adjust debit_amt *****#
                    if invoice_total_amount > 0:
                        debit_amt = invoice_total_amount - (unpaid_lines_amount + remaining_paid_amount)

                # Decide Here Debit Amount and OD
                if invoice_total_amount > (unpaid_lines_amount + remaining_paid_amount):
                    debit_amt = invoice_total_amount - (unpaid_lines_amount + remaining_paid_amount)

                elif invoice_total_amount < (unpaid_lines_amount + remaining_paid_amount):
                    debit_amt = 0
                    od_amount = (unpaid_lines_amount + remaining_paid_amount) - invoice_total_amount
                elif invoice_total_amount == (unpaid_lines_amount + remaining_paid_amount):
                    debit_amt = 0

                # (3) ***** Updating Invoice Receivable and Invoice Total Amount *****#
                if move_id.payment_state not in ('in_payment', 'paid'):
                    # ***** Receivable Line, it will Debit ***** #
                    self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                        , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                    # ***** Invoice Total Update *****#
                    self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                        , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, move_id.id))
                    self._cr.commit()

                    # ***** Student Ledger Update *****#
                    student_ledger_rec = self.env['odoocms.student.ledger'].search([('invoice_id', '=', move_id.id),
                                                                                    ('ledger_entry_type', '=', 'semester')])
                    if student_ledger_rec:
                        if invoice_total_amount > (unpaid_lines_amount + ledger_remaining_paid_amount):
                            student_ledger_rec.credit = student_ledger_rec.credit - (unpaid_lines_amount + ledger_remaining_paid_amount)
                        elif invoice_total_amount <= (unpaid_lines_amount + ledger_remaining_paid_amount):
                            student_ledger_rec.credit = 0

                elif unpaid_invoice_line:
                    receivable_line = unpaid_invoice_line.move_id.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
                    # ***** Receivable Line, it will Debit ***** #
                    self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                        , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                    # ***** Invoice Total Update *****#
                    self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                        , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, unpaid_invoice_line.move_id.id))
                    self._cr.commit()

                    # ***** Student Ledger Update *****#
                    student_ledger_rec = self.env['odoocms.student.ledger'].search(
                        [
                            ('invoice_id', '=', unpaid_invoice_line.move_id.id),
                            ('ledger_entry_type', '=', 'semester')
                        ]
                    )
                    if student_ledger_rec:
                        if invoice_total_amount > (unpaid_lines_amount + ledger_remaining_paid_amount):
                            student_ledger_rec.credit = student_ledger_rec.credit - (unpaid_lines_amount + ledger_remaining_paid_amount)
                        elif invoice_total_amount <= (unpaid_lines_amount + ledger_remaining_paid_amount):
                            student_ledger_rec.credit = 0

                # ***** Step (5) ***** #
                if move_id.amount_total == 0:
                    move_id.write(
                        {
                            'state': 'posted',
                            'payment_state': 'paid',
                            'narration': 'Paid Due To OD'
                        }
                    )
                    if registration_id:
                        registration_id.sudo().action_approve()

        return lines

    def prepare_dropped_invoice_lines(self, invoice_line, registration_id, course, amt=0):
        # ***** Prepare Drop Course line *****#
        paid_status = 'Unpaid Status'
        if invoice_line.move_id.payment_state in ('in_payment', 'paid'):
            paid_status = 'Paid Status'
        fee_line = {
            'sequence': invoice_line.sequence + 200,
            'name': invoice_line.course_id_new.course_id.code + "-" + invoice_line.course_id_new.course_id.name + " Of " + paid_status + " (Drop)",
            'quantity': 1,
            'course_gross_fee': invoice_line.course_gross_fee,
            'price_unit': -invoice_line.price_unit if amt == 0 else -amt,
            'product_id': invoice_line.product_id.id,
            'account_id': invoice_line.account_id.id,
            'fee_head_id': invoice_line.fee_head_id.id,
            'exclude_from_invoice_tab': False,
            'course_id_new': invoice_line.course_id_new.id,
            'registration_id': registration_id.id,
            'registration_line_id': course.id,
            'course_credit_hours': invoice_line.course_credit_hours,
            'discount': invoice_line.discount,
            'is_add_drop_line': True,
            'dropped_mvl_id': invoice_line.id,
            'registration_type': 'drop',
            'add_drop_no': str(invoice_line.add_drop_no) + ", Drop->" + registration_id.add_drop_request_no_txt,
            'analytic_account_id': invoice_line.fee_head_id.analytic_account_id and invoice_line.fee_head_id.analytic_account_id.id or
                                   (self.program_id.analytic_account_id and self.program_id.analytic_account_id.id) or
                                   (self.department_id.analytic_account_id and self.department_id.analytic_account_id.id) or False,
            # 'analytic_tag_ids': analytic_tag_ids,
        }
        fee_line = self.hook_line(fee_line)
        return fee_line


    def prepare_adjustment_invoice_line(self, invoice_line=None, registration_id=None, amt=0):
        # ***** Prepare Adjustment line *****#
        if invoice_line is not None:
            invoice_line = invoice_line[0]
        else:

            invoice_line = False
        fee_line = {
            'sequence': invoice_line.sequence + 200,
            'name': "Adjustment in Second Installment of (Drop-Already Paid) Courses",
            'quantity': 1,
            'course_gross_fee': 0,
            'price_unit': amt,
            'product_id': invoice_line.product_id.id if invoice_line else False,
            'account_id': invoice_line.account_id.id if invoice_line else self.env['account.account'].search([('id', '=', 2)]).id,
            'fee_head_id': invoice_line.fee_head_id.id if invoice_line else False,
            'exclude_from_invoice_tab': False,
            'course_id_new': False,
            'registration_id': registration_id.id,
            'registration_line_id': False,
            'course_credit_hours': 0,
            'discount': 0,
            'is_add_drop_line': False,
            'add_drop_no': str(invoice_line.add_drop_no) + ", Adj->" + registration_id.add_drop_request_no_txt,
            'analytic_account_id': invoice_line.fee_head_id.analytic_account_id and invoice_line.fee_head_id.analytic_account_id.id or
                                   (self.program_id.analytic_account_id and self.program_id.analytic_account_id.id) or
                                   (self.department_id.analytic_account_id and self.department_id.analytic_account_id.id) or False,
            # 'analytic_tag_ids': analytic_tag_ids,
        }
        fee_line = self.hook_line(fee_line)
        return fee_line

    # ***** TO Insert a line in account_move_line*****#
    def account_move_line_credit_line_insert(self, mvl, ad_course, credit_amt, price_unit, registration_id, new_name, registration_type):
        credit_amt = math.ceil(credit_amt)
        course_gross_fee = ad_course.primary_class_id.credits * self.batch_id.per_credit_hour_fee
        new_mvl = self.env.cr.execute("""
                                        insert into account_move_line 
                                        (
                                            account_id,partner_id,fee_head_id,is_add_drop_line,name,move_id,currency_id,product_id,quantity,price_unit,
                                            price_total,price_subtotal,balance,amount_currency,course_gross_fee,course_credit_hours,course_id_new,credit,registration_id,registration_line_id,
                                            move_name,date,parent_state,journal_id,company_id,company_currency_id,account_root_id,sequence,debit,discount,
                                            reconciled,blocked,amount_residual,amount_residual_currency,exclude_from_invoice_tab,fee_category_id,student_id,career_id,program_id,session_id,
                                            institute_id,campus_id,term_id,create_uid,create_date,write_date,write_uid,registration_type,add_drop_no
                                        )
                                        VALUES 
                                            (
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s
                                            ) 
                                        RETURNING id """,
                                      (
                                          mvl.account_id.id, mvl.partner_id.id, mvl.fee_head_id.id, True, new_name, mvl.move_id.id, mvl.currency_id.id, mvl.product_id.id, 1.00, credit_amt,
                                          credit_amt, credit_amt, -credit_amt, -credit_amt, course_gross_fee, ad_course.primary_class_id.credits, ad_course.primary_class_id.id, credit_amt, registration_id.id, ad_course.id,
                                          mvl.move_name, mvl.date, mvl.parent_state, mvl.journal_id.id, mvl.company_id.id, mvl.company_currency_id.id, mvl.account_root_id.id, 250, 0.00, mvl.discount,
                                          mvl.reconciled, mvl.blocked, mvl.amount_residual, mvl.amount_residual_currency, mvl.exclude_from_invoice_tab, mvl.fee_category_id.id, mvl.student_id.id, mvl.career_id.id, mvl.program_id.id, mvl.session_id.id,
                                          mvl.institute_id.id, mvl.campus_id.id, mvl.term_id.id, self.env.user.id, fields.Datetime.now(), fields.Datetime.now(), self.env.user.id, registration_type, (registration_type.capitalize() + "->" + registration_id.add_drop_request_no_txt)
                                      ))
        return new_mvl

    # ***** TO Insert a line in account_move_line *****#
    def account_move_line_debit_line_insert(self, mvl, ad_course, debit_amt, price_unit, registration_id, new_name, registration_type):
        debit_amt = math.ceil(debit_amt)
        course_gross_fee = ad_course.primary_class_id.credits * self.batch_id.per_credit_hour_fee
        new_mvl = self.env.cr.execute("""   
                                        insert into account_move_line 
                                        (
                                            account_id,partner_id,fee_head_id,is_add_drop_line,name,move_id,currency_id,product_id,quantity,price_unit,
                                            price_total,price_subtotal,balance,amount_currency,course_gross_fee,course_credit_hours,course_id_new,credit,registration_id,registration_line_id,
                                            move_name,date,parent_state,journal_id,company_id,company_currency_id,account_root_id,sequence,debit,discount,
                                            reconciled,blocked,amount_residual,amount_residual_currency,exclude_from_invoice_tab,fee_category_id,student_id,career_id,program_id,session_id,
                                            institute_id,campus_id,term_id,create_uid,create_date,write_date,write_uid,registration_type,add_drop_no
                                        ) 
                                        VALUES 
                                        (
                                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                            %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                            %s,%s,%s,%s,%s,%s,%s,%s,%s
                                        ) 
                                        RETURNING id """,
                                      (
                                          mvl.account_id.id, mvl.partner_id.id, mvl.fee_head_id.id, True, new_name, mvl.move_id.id, mvl.currency_id.id, mvl.product_id.id, 1.00, -debit_amt,
                                          -debit_amt, -debit_amt, debit_amt, debit_amt, course_gross_fee, ad_course.primary_class_id.credits, (ad_course and ad_course.primary_class_id.id) or None, 0.00, registration_id.id, ad_course and ad_course.id or None,
                                          mvl.move_name, mvl.date, mvl.parent_state, mvl.journal_id.id, mvl.company_id.id, mvl.company_currency_id.id, mvl.account_root_id.id, 250, debit_amt, mvl.discount,
                                          mvl.reconciled, mvl.blocked, mvl.amount_residual, mvl.amount_residual_currency, mvl.exclude_from_invoice_tab, mvl.fee_category_id.id, mvl.student_id.id, mvl.career_id.id, mvl.program_id.id, mvl.session_id.id,
                                          mvl.institute_id.id, mvl.campus_id.id, mvl.term_id.id, self.env.user.id, fields.Datetime.now(), fields.Datetime.now(), self.env.user.id, registration_type, (registration_type.capitalize() + "->" + registration_id.add_drop_request_no_txt)
                                      ))
        return new_mvl

    def get_drop_courses_paid_amount(self, dropped_courses=None, term_id=None):
        paid_amount = 0
        if dropped_courses is not None and term_id is not None:
            for dropped_course in dropped_courses:
                invoice_line = self.env['account.move.line'].search([('course_id_new', '=', dropped_course.primary_class_id.id),
                                                                     ('student_id', '=', self.id),
                                                                     ('term_id', '=', term_id.id),
                                                                     ('registration_type', 'in', ('main', 'add')),
                                                                     ('move_id.payment_state', 'in', ('in_payment', 'paid'))], order='id desc', limit=1)

                paid_amount += invoice_line.price_subtotal
        return paid_amount


