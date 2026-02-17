import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from datetime import date
from dateutil.relativedelta import relativedelta
import re


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


class OdoocmsStudentFeePublic(models.AbstractModel):
    _name = 'odoocms.student.fee.public'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'image.mixin']
    _description = 'Students Public Model'

    session_id = fields.Many2one('odoocms.academic.session', 'Academic Session', compute='_compute_student_data', store=True, tracking=True)
    career_id = fields.Many2one('odoocms.career', 'Career', compute='_compute_student_data', store=True)
    program_id = fields.Many2one('odoocms.program', 'Academic Program', tracking=True, compute='_compute_student_data', store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute', compute='_compute_student_data', store=True)
    discipline_id = fields.Many2one('odoocms.discipline', 'Discipline', compute='_compute_student_data', store=True)
    campus_id = fields.Many2one('odoocms.campus', 'Campus', compute='_compute_student_data', store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Current Term', compute='_compute_student_data', store=True, tracking=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester', compute='_compute_student_data', store=True, tracking=True)
    to_be = fields.Boolean('To Be', default=False)

    @api.depends('student_id')
    def _compute_student_data(self):
        for rec in self:
            student = rec.student_id
            if student:
                rec.session_id = student.session_id.id if student.session_id else False
                rec.career_id = student.career_id.id if student.career_id else False
                rec.institute_id = student.institute_id.id if student.institute_id else False
                rec.campus_id = student.campus_id.id if student.campus_id else False
                rec.program_id = student.program_id.id if student.program_id else False
                rec.discipline_id = student.discipline_id.id if student.discipline_id else False
                rec.term_id = student.term_id.id if student.term_id else False
                rec.semester_id = student.semester_id.id if student.semester_id else False


class OdooCMSStudent(models.Model):
    _inherit = 'odoocms.student'

    feemerit = fields.Selection([('regular', 'Regular'), ('self', 'Self Finance'), ('rationalized', 'Rationalized')], 'Group Code', default='regular')
    hostel_facility = fields.Boolean('Hostel Facility')
    hostel_cubical = fields.Boolean('Cubical')

    waiver_ids = fields.Many2many('odoocms.fee.waiver', 'student_waiver_rel', 'student_id', 'waiver_id', 'Fee Waivers')
    son_waiver_flag = fields.Boolean(string='Employee Son Association', default=False)
    kinship_flag = fields.Boolean(string='Kinship Association ', default=False)

    waiver_association_son = fields.Many2one('hr.employee', 'Employee Association')
    waiver_association_kinship = fields.Many2one('odoocms.student', string='Student Association')

    fee_structure_id = fields.Many2one('odoocms.fee.structure', 'Fee Structure', tracking=True)
    fee_structure_ids = fields.One2many('odoocms.fee.structure.student', 'student_id', string='Fee Lines')
    receipt_ids = fields.One2many('account.move', 'student_id', 'Fee Receipts')
    receipt_line_ids = fields.One2many('account.move.line', 'student_id', 'Fee Receipt Lines', domain=[('account_id.user_type_id.type','in',('receivable', 'payable'))])

    ledger_lines = fields.One2many('odoocms.student.ledger', 'student_id', 'Ledger Lines')
    refund_request_ids = fields.One2many('odoocms.fee.refund.request', 'student_id', 'Refund Requests')
    waiver_line_ids = fields.One2many('odoocms.student.fee.waiver', 'student_id', 'Fee Waiver Detail')
    student_ledger_balance = fields.Float('Student Balance', compute='_compute_ledger_balance', store=True)

    exclude_library_fee = fields.Boolean('Exclude Library Fee', default=False)
    fee_generated = fields.Boolean('Fee Generated', default=False)

    registration_allowed = fields.Boolean(tracking=True)

    # Temporary These two fields required
    receipt_installment = fields.Boolean('Installment', compute='_compute_ledger_balance', store=True)
    installment_paid = fields.Boolean('Installment Paid', compute='_compute_ledger_balance', store=True)
    student_tags_row = fields.Char('Student Tags Row', compute='_compute_student_tags_row', store=True)
    to_be = fields.Boolean('To Be', default=False)

    def post_fee_payment(self):
        domain = [('student_id','=',self.id),('state','=','posted'),('move_type','=','out_invoice'),('payment_state','=','paid'),('payment_id','=',False),
                ('is_fee','=',True),('is_fee','=',True)]
        lines = self.env['account.move'].search(domain).filtered(lambda l: l.amount_total > 0 and l.amount_total == l.amount_residual)
        lines.post_fee_payment()

    def _get_fee_structure(self, log_message=False):
        fee_structure = False
        if self.fee_structure_id:
            fee_structure = self.fee_structure_id
        if not fee_structure:
            if self.batch_id.fee_structure_id:
                fee_structure = self.batch_id.fee_structure_id

        if log_message and not fee_structure:
            self.add_log_message(f": No Fee structure linked with Student nor with Batch, Now checking with domain ", 'red')
        if not fee_structure:
            structure_domain = [('session_id', '=', self.session_id.id), ('career_id', '=', self.career_id.id),('batch_id', '=', self.batch_id.id)]
            if log_message:
                self.add_log_message(f": Searching with Domain - {str(structure_domain)}", '#FFA500')
            fee_structure = self.env['odoocms.fee.structure'].search(structure_domain, order='id desc', limit=1)

        if not fee_structure:
            structure_domain = [('session_id', '=', self.session_id.id), ('career_id', '=', self.career_id.id)]
            if log_message:
                self.add_log_message(f":    Now Searching with Domain - {str(structure_domain)}", '#FFA500')
            fee_structure = self.env['odoocms.fee.structure'].search(structure_domain, order='id desc', limit=1)

        if not fee_structure:
            structure_domain = [('session_id', '=', self.session_id.id)]
            if log_message:
                self.add_log_message(f":         Now Searching with Domain - {str(structure_domain)}", '#FFA500')
            fee_structure = self.env['odoocms.fee.structure'].search(structure_domain, order='id desc', limit=1)

        if not fee_structure:
            structure_domain = []
            if log_message:
                self.add_log_message(f":         Now Searching with out any Domain ", '#FFA500')
            fee_structure = self.env['odoocms.fee.structure'].search(structure_domain)
            if len(fee_structure) != 1:
                fee_structure = False

        if not fee_structure:
            if log_message:
                self.add_log_message(f": No Fee Structure Found", 'red')
            else:
                raise UserError(_('Fee structure is not defined for (Student: %s, Session: %s.' % (self.code, self.session_id.name)))

        elif not fee_structure.current:
            fee_structure = False
            if log_message:
                self.add_log_message(f": No Fee Structure Found", 'red')
            else:
                raise UserError(_('Fee structure is not defined for (Student: %s, Session: %s.' % (self.code, self.session_id.name)))

        elif not fee_structure.date_start or not fee_structure.date_end:
            if log_message:
                self.add_log_message(f": Fee structure Effective date Period are not Entered. for Fee structure {str(fee_structure.id)}", 'blue')
                fee_structure = False
            else:
                fee_structure = False
                raise UserError(_('Fee structure Effective date Period are not Entered.'))

        if fee_structure.date_start > date.today() or fee_structure.date_end < date.today():
            if log_message:
                self.add_log_message(f": Fee structure is out of date. Fee structure {str(fee_structure.id)}", 'blue')
                fee_structure = False
            else:
                fee_structure = False
                raise UserError(_('Fee structure is out of date. (Student: %s, Fee-Structure: %s)' % (self.code, fee_structure.id,)))

        return fee_structure

    def _get_fee_heads(self, fee_structure, receipts, head_name=False, log_message=False):
        fee_head_ids = receipts.mapped('fee_head_ids') # fee_head_ids-----> odoocms.fee.head
        if head_name:
            fee_head_ids = fee_head_ids.filtered(lambda l: l.name == head_name)

        # GET Fee Structure Heads from Fee Structure based on the fee_head_ids taken from receipts variable
        # structure_fee_heads -----> odoocms.fee.structure.head
        payment_types = [
            'persemester',
            'persubject',
            'percredit',
            'onetime',
            'admissiontime'
        ]
        structure_fee_heads = fee_structure.head_ids.filtered(lambda l: l.fee_head_id.id in fee_head_ids.ids and l.current and l.payment_type in payment_types)
        return structure_fee_heads

    def generate_invoice_old(self, semester, receipts, date_due, comment='', tag=False, reference=False, override_line=False, reg=False, invoice_group=False, registration_id=False, charge_annual_fee=False, apply_taxes=False):
        # Check here to generate Hostel Fee Along with Semester Fee or not
        # semester_fee -----> Generate with Semester Fee
        # separate_fee -----> Generate a separate fee for Hostel

        lines = []
        hostel_fee_charge_timing = (self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.hostel_fee_charge_timing') or 'separate_fee')
        semester_defer = False
        student_defer_or_suspension_flag = False
        defer_domain = [('student_id', '=', self.id), ('term_id', '=', semester.id), ('state', '!=', 'cancel')]
        semester_defer_rec = self.env['odoocms.student.term.defer'].sudo().search(defer_domain, order='id desc', limit=1)

        if semester_defer_rec:
            semester_defer = True
            student_defer_or_suspension_flag = True
        if self.tag_ids.filtered(lambda t: t.name == 'Suspension'):
            student_defer_or_suspension_flag = True

        registration_id = registration_id.id
        waiver_amount_for_invoice = 0
        scholarship_amount_for_invoice = 0
        # receipts ----> receipt_type_ids (odoocms.receipt.type) which we select either its semester fee, hostel fee, ad hoc fee, in other Words,
        # These are the Fee Heads That will be Charged for that Type (this is Fee Heads Container)
        student_receipts = receipts

        # Search the Fee Structure based on the (Academic Session + Academic Term + Career)
        # There must At Least One Fee Structure for that Student
        fee_structure = self._get_fee_structure(log_message=False)
        structure_fee_heads = self._get_fee_heads(fee_structure, receipts)

        invoices = self.env['account.move']
        date_invoice = fields.Date.context_today(self)

        # if charge_annual_fee:
        #     payment_types.append('peryear')

        waivers = []
        # Receipt Waiver Lines
        r_waiver_lines = []
        student_waiver = self.env['odoocms.student.fee.waiver']
        if semester_defer:
            lines = self.get_semester_defer_fee_lines(lines, structure_fee_heads, semester_defer_rec, semester)

        tut_defer_line = False
        arrears_amt = 0
        donor_invoice = False
        is_hostel_fee = False
        summer_courses_fee_flag = False

        # if not semester_defer or not suspended_student_fee:
        # if student_defer_or_suspension_flag:
        #     return
        for fee_head in structure_fee_heads:
            name = fee_head.fee_head_id.product_id.name
            # if not line.domain or self.env['odoocms.student'].search(safe_eval(line.domain)).filtered(lambda l: l.id == self.id):

            if fee_head.line_ids:
                # structure_head_line ----> odoocms.fee.structure.head.line
                for head_line in fee_head.line_ids:
                    if self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', self.id)]):
                        override_fee_line = False
                        if override_line:
                            override_fee_line = override_line.filtered(lambda l: l.fee_head_id.id == fee_head.fee_head_id.id)
                        qty = 1
                        if fee_head.payment_type == 'persubject' and reg:
                            qty = len(reg.failed_subject_ids) + len(reg.to_improve_subject_ids)

                        price_unit = override_fee_line and override_fee_line.fee_amount or (head_line and head_line.amount) or 0
                        if not head_line.currency_id.id == self.env.company.currency_id.id:
                            price_unit = head_line.currency_id._convert(price_unit, self.env.company.currency_id, self.env.company, date_invoice)

                        if fee_head.category_id.name == 'Tuition Fee':
                            if self.check_tuition_fee_deferment():
                                defer_line_fee_head = fee_head
                                tut_defer_line, defer_regular_invoice_amount, defer_invoice_amount, defer_invoice_date_due = self.action_create_tuition_deferment_entry(head_line)
                                # price_unit = tut_defer_line.deferment_id.approved_tuition_fee
                                price_unit = defer_regular_invoice_amount

                        waiver_fee_lines = self.env['odoocms.fee.waiver.line'].search([('fee_head_id', '=', fee_head.fee_head_id.id)])
                        if waiver_fee_lines and not semester.type == 'summer':
                            student_id = False
                            # Added @ 08102021
                            original_price_unit = price_unit
                            for waiver_fee_line in waiver_fee_lines:
                                # if self.env['odoocms.student'].search(safe_eval(waiver_fee_line.waiver_id.domain) + [('id', '=', self.id)]):
                                if waiver_fee_line.waiver_id.domain:
                                    student_id = self.env['odoocms.student'].search(safe_eval(waiver_fee_line.waiver_id.domain) + [('id', '=', self.id)])
                                if not waiver_fee_line.waiver_id.domain:
                                    student_id = self
                                if student_id and student_id.tag_ids.filtered(lambda f: f.name not in 'Extra Semester') and waiver_fee_line.waiver_id.type == 'waiver':
                                    # For Hazara Univ I have to Change this
                                    # if waiver_fee_line.waiver_id not in waivers:
                                    # From waivers to r_waiver_lines
                                    if waiver_fee_line not in r_waiver_lines:
                                        r_waiver_lines.append(waiver_fee_line)
                                        waivers.append(waiver_fee_line.waiver_id)
                                        if waiver_fee_line.waiver_type == 'percentage':
                                            # waiver_price_unit = round(price_unit * waiver_fee_line.percentage / 100.0)
                                            waiver_price_unit = round(original_price_unit * waiver_fee_line.percentage / 100.0)
                                        if waiver_fee_line.waiver_type == 'fixed':
                                            waiver_price_unit = waiver_fee_line.percentage
                                        if waiver_fee_line.waiver_type == 'remaining':
                                            waiver_price_unit = price_unit - waiver_fee_line.percentage
                                        # price_unit = price_unit - waiver_price_unit
                                        waiver_amount_for_invoice += waiver_price_unit

                                        data = {
                                            'student_id': self.id,
                                            'name': waiver_fee_line.waiver_id.name,
                                            'waiver_line_id': waiver_fee_line.id,
                                            'term_id': semester.id,
                                            # 'semester_id': self.env['odoocms.term.scheme'].search([('session_id', '=', self.session_id.id), ('semester_id', '=', self.semester_id.id)]).semester_id.id,
                                            'amount': waiver_price_unit,
                                            'amount_percentage': waiver_fee_line.percentage,
                                            'waiver_type': waiver_fee_line.waiver_type,
                                        }
                                        student_waiver += self.env['odoocms.student.fee.waiver'].create(data)

                                        # Invoice Line generation
                                        waiver_value_invl_data = {
                                            'sequence': 1050,
                                            'price_unit': -(round(waiver_price_unit)),
                                            'quantity': qty,
                                            'product_id': waiver_fee_line.fee_head_id.product_id and waiver_fee_line.fee_head_id.product_id.id or False,
                                            'name': waiver_fee_line.waiver_id.name + " (Discounts)",
                                            'account_id': waiver_fee_line.fee_head_id.property_account_income_id.id,
                                            # 'fee_head_id': waiver_fee_line.fee_head_id and waiver_fee_line.fee_head_id.id or False,
                                            # 'analytic_tag_ids': analytic_tag_ids,
                                            'exclude_from_invoice_tab': False,
                                        }
                                        lines.append((0, 0, waiver_value_invl_data))

                                if student_id and (student_id.tag_ids.filtered(lambda f: f.name not in 'Extra Semester') or (semester.type != 'summer')) and waiver_fee_line.waiver_id.type == 'scholarship':
                                    donor_invoice = self.action_create_donor_invoice(waiver_fee_line, price_unit, semester, fee_head,
                                                                                     fee_structure, invoice_group, receipts, registration_id, date_invoice, date_due, comment, tag, reference)
                                    price_unit = price_unit - donor_invoice.amount_total

                        # 19-07-2021
                        # if fee_head.category_id.name=='Tuition Fee' and self.tag_ids.filtered(lambda f: f.name in ('Summer', 'Extra Semester')):
                        if not summer_courses_fee_flag:
                            if fee_head.category_id.name == 'Tuition Fee' and ((self.tag_ids.filtered(lambda f: f.name == 'Extra Semester')) or (semester.type == 'summer')) and not self.program_id.code == 'NBS-751':
                                lines = self.action_summer_extra_course_fee(lines, head_line, semester)
                                summer_courses_fee_flag = True
                            else:
                                fee_line = {
                                    'sequence': 10,
                                    'price_unit': price_unit,
                                    'quantity': qty,
                                    'product_id': fee_head.fee_head_id.product_id.id,
                                    'name': name,
                                    'account_id': fee_head.fee_head_id.property_account_income_id.id,
                                    # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                                    # 'analytic_tag_ids': analytic_tag_ids,
                                    'fee_head_id': fee_head.fee_head_id.id,
                                    'exclude_from_invoice_tab': False,
                                }
                                lines.append((0, 0, fee_line))

                    # Added 28-07-2021
                    else:
                        if not summer_courses_fee_flag and fee_head.category_id.name == 'Tuition Fee' and semester.type == 'summer' and not self.program_id.code == 'NBS-751':
                            lines = self.action_summer_extra_course_fee(lines, head_line, semester)
                            summer_courses_fee_flag = True

        # Check the Student Hostel Fee
        giki = False
        if giki and self.hostel_state == 'Allocated' and hostel_fee_charge_timing == 'semester_fee':
            lines = self.get_hostel_fee(lines, semester)
            is_hostel_fee = True

        # Checking the Student Ad hoc Charges
        lines, additional_charge_lines = self.get_additional_charges_lines(semester, lines)
        # Get the Student Arrears and Adjustment
        # if lines:
        #     arrears_result = self.get_arrears_adjustments(semester, lines)
        #     lines = arrears_result[0]
        #     arrears_amt = arrears_result[1]
        #     adjustment_lines = arrears_result[2]

        # Fine for Late Payment
        # if lines:
        #     lines = self.create_fine_line(lines)

        # @ added on 20-08-2021
        invoice_net_amt = 0
        for nw_line in lines:
            invoice_net_amt += nw_line[2]['price_unit']

        # Check Any Line having Amount Greater the Zero and Net Amount also Greater then Zero
        if receipts and any([ln[2]['price_unit'] > 0 for ln in lines]) and invoice_net_amt > 0:
            # if Student Status is not Filer then Apply Taxes
            if apply_taxes and not self.filer:
                lines = self.create_tax_line(lines, semester, fall_20=False)

            validity_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.challan_validity_days') or '30')
            validity_date = date_due + datetime.timedelta(days=validity_days)

            # DATA DICT Of Fee Receipt
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
                'is_hostel_fee': is_hostel_fee,
                'reference': reference,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'waiver_amount': waiver_amount_for_invoice,
                'term_id': semester and semester.id or False,
                'study_scheme_id': self.study_scheme_id and self.study_scheme_id.id or False,
                'session_id': self.session_id and self.session_id.id or False,
                'validity_date': validity_date,
            }

            # Update Fee Receipt Data Dict Of Waiver Fields
            if waivers:
                data['waiver_ids'] = [(4, waiver.id, None) for waiver in waivers]

            # Create Fee Receipt
            invoice = self.env['account.move'].sudo().create(data)

            # Assign Fee Receipt Id to Waivers
            for waiver in student_waiver:
                waiver.invoice_id = invoice.id

            # Assign Fee Group to Invoice
            invoice.invoice_group_id = invoice_group

            # GET Ledger Amount
            ledger_amt = invoice.amount_total
            if arrears_amt > 0:
                ledger_amt = invoice.amount_total - arrears_amt

            if semester_defer_rec:
                semester_defer_rec.invoice_id = invoice

            if reg:  # If Subject Registration
                reg.invoice_id = invoice.id

            invoices += invoice
            if donor_invoice:
                invoices += donor_invoice

            return invoices
        else:
            return self.env['account.move']

    # Call from generate_invoice()
    def get_semester_defer_fee_lines(self, lines, structure_fee_heads, semester_defer_rec=False, term_id=False):
        for student in self:
            ug_first_semester_defer_value = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.ug_first_semester_defer_value') or '100')
            pg_first_semester_defer_value = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.pg_first_semester_defer_value') or '50')
            second_semester_defer_value = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.second_semester_defer_value') or '25')

            # Check Here if structure Head Line Receipt have been Generated.
            same_term_invoice = self.env['account.move'].search([('student_id', '=', student.id), ('term_id', '=', term_id.id), ('move_type', '=', 'out_invoice'),
                ('reversed_entry_id', '=', False)], order='id desc', limit=1)

            same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', student.id), ('reversed_entry_id', '=', same_term_invoice.id)])

            per_factor = 0
            semester = semester_defer_rec.semester_id.number if semester_defer_rec else student.semester_id.number

            if semester == 1:
                if self.career_id.code == 'UG':
                    per_factor = ug_first_semester_defer_value
                if not self.career_id.code == 'UG':
                    per_factor = pg_first_semester_defer_value
            else:
                per_factor = second_semester_defer_value

            for structure_fee_head in structure_fee_heads.filtered(lambda h: h.category_id.name == 'Tuition Fee'):
                for head_line in structure_fee_head.line_ids:
                    if same_term_invoice:
                        if not same_term_invoice_reverse_entry:
                            sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id), ('fee_head_id', '=', structure_fee_head.fee_head_id.id)])
                            if sm_mvl:
                                continue

                    if self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', self.id)]):
                        price_unit = head_line.amount or 0
                        if not head_line.currency_id.id == self.env.company.currency_id.id:
                            price_unit = head_line.currency_id._convert(price_unit, self.env.company.currency_id, self.env.company, fields.Date.today())
                        price_unit = round(price_unit * per_factor / 100, 2)
                        defer_sem_tut = {
                            'sequence': 1001,
                            'price_unit': price_unit,
                            'quantity': 1,
                            'product_id': structure_fee_head.fee_head_id.product_id.id,
                            'name': structure_fee_head.category_id.name,
                            'account_id': structure_fee_head.fee_head_id.property_account_income_id.id,
                            'fee_head_id': structure_fee_head.fee_head_id.id,
                            'exclude_from_invoice_tab': False,
                        }
                        lines.append((0, 0, defer_sem_tut))

            rep_courses = self.env['odoocms.student.course'].search([('student_id', '=', student.id), ('term_id', '=', term_id.id)])
            if rep_courses:
                extra_fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Tuition Fee Per Course')])
                if not extra_fee_head:
                    extra_fee_head = self.env['odoocms.fee.head'].search([('id', '=', '73')])
                local_student_credit_hour_fee = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.local_student_credit_hour_fee') or '5000')
                foreign_student_credit_hour_fee = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.foreign_student_credit_hour_fee') or '40')

                for course in rep_courses:
                    currency_id = self.env['res.currency'].search([('id', '=', 2)])
                    course_credit = course.course_id and course.course_id.credits or 0
                    # price = 5000
                    price = local_student_credit_hour_fee
                    if student.tag_ids.filtered(lambda t: t.code == 'NFS'):
                        # price = 40
                        price = foreign_student_credit_hour_fee
                        price = currency_id._convert(price, self.env.company.currency_id, self.env.company, fields.Date.today())
                    price_unit = price * course_credit
                    new_name = course.primary_class_id.code + "-" + course.primary_class_id.name + " Tuition Fee"

                    if same_term_invoice:
                        if not same_term_invoice_reverse_entry:
                            sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id), ('course_id', '=', course.id)])
                            if sm_mvl:
                                continue

                    defer_sem_tut = {
                        'name': new_name,
                        'quantity': 1,
                        'price_unit': price_unit,
                        'product_id': extra_fee_head and extra_fee_head.id or False,
                        'account_id': extra_fee_head and extra_fee_head.property_account_income_id.id or False,
                        'fee_head_id': extra_fee_head and extra_fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append((0, 0, defer_sem_tut))
        return lines

    # Call from generate_invoice()
    def check_tuition_fee_deferment(self):
        for student in self:
            ret_value = False
            rec_exist = self.env['odoocms.tuition.fee.deferment.request'].search([('student_id', '=', student.id), ('career_id', '=', student.career_id.id), ('state', '=', 'approved')])
            if rec_exist:
                ret_value = True
        return ret_value

    # Call from generate_invoice()
    def action_create_tuition_deferment_entry(self, structure_head_line):
        for student in self:
            defer_invoice_amount = 0
            regular_invoice_amount = 0
            defer_invoice_date_due = False
            new_defer_line = False
            defer_rec = self.env['odoocms.tuition.fee.deferment.request'].search([('student_id', '=', student.id), ('career_id', '=', student.career_id.id), ('state', '=', 'approved')])

            if defer_rec:
                if structure_head_line:
                    amount = structure_head_line.amount
                    if defer_rec.defer_type == 'percentage':
                        defer_invoice_amount = round(amount * (defer_rec.defer_value / 100), 3)
                        regular_invoice_amount = amount - defer_invoice_amount
                    if defer_rec.defer_type == 'fixed':
                        defer_invoice_amount = defer_rec.approved_tuition_fee
                        regular_invoice_amount = amount - defer_invoice_amount

                defer_values = {
                    'student_id': student.id,
                    'deferment_id': defer_rec.id,
                    'amount': defer_invoice_amount,
                    'state': 'draft',
                }
                new_defer_line = self.env['odoocms.tuition.fee.deferment.line'].create(defer_values)
                last_defer_line_entry = self.env['odoocms.tuition.fee.deferment.line'].search_count([('student_id', '=', student.id), ('deferment_id', '=', defer_rec.id)])

                defer_invoice_date_due = defer_rec.installments_start_date + relativedelta(months=+last_defer_line_entry)

        return new_defer_line, regular_invoice_amount, defer_invoice_amount, defer_invoice_date_due

    # Call from generate_invoice()
    def action_summer_extra_course_fee(self, lines, structure_head_line, term_id):
        for student in self:
            extra_fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Tuition Fee Per Course')])
            if not extra_fee_head:
                extra_fee_head = self.env['odoocms.fee.head'].search([('id', '=', '73')])

            local_student_credit_hour_fee = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.local_student_credit_hour_fee') or '5000')
            foreign_student_credit_hour_fee = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.foreign_student_credit_hour_fee') or '40')

            extra_courses = self.env['odoocms.student.course'].search([('student_id', '=', student.id), ('term_id', '=', term_id.id)])
            if extra_courses:
                for course in extra_courses:
                    # price = 5000
                    # Check Here if structure Head Line Receipt have been Generated.
                    same_term_invoice = self.env['account.move'].search([('student_id', '=', student.id), ('term_id', '=', term_id.id),
                        ('move_type', '=', 'out_invoice'), ('reversed_entry_id', '=', False)], order='id desc', limit=1)
                    same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', student.id),
                        ('reversed_entry_id', '=', same_term_invoice.id)])
                    if same_term_invoice:
                        if not same_term_invoice_reverse_entry:
                            sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id), ('course_id', '=', course.id)])
                            if sm_mvl:
                                continue

                    price = local_student_credit_hour_fee
                    course_credit = course.course_id and course.course_id.credits or 0
                    price_unit = price * course_credit
                    if student.tag_ids.filtered(lambda t: t.code == 'NFS'):
                        # price = 40
                        price = foreign_student_credit_hour_fee
                        if structure_head_line.currency_id == self.env.company.currency_id:
                            currency_id = self.env['res.currency'].search([('name', '=', 'USD')])
                            price = currency_id._convert(price, self.env.company.currency_id, self.env.company, fields.Date.today())
                        else:
                            price = structure_head_line.currency_id._convert(price, self.env.company.currency_id, self.env.company, fields.Date.today())
                        price_unit = price * course_credit
                    new_name = course.primary_class_id.code + "-" + course.primary_class_id.name + " Tuition Fee"
                    extra_fee_lines = {
                        'name': new_name,
                        'quantity': 1,
                        'price_unit': price_unit,
                        'course_id': course.id,
                        'product_id': extra_fee_head and extra_fee_head.id or False,
                        'account_id': extra_fee_head and extra_fee_head.property_account_income_id.id or False,
                        'fee_head_id': extra_fee_head and extra_fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                        # 'analytic_tag_ids': analytic_tag_ids,
                    }
                    lines.append((0, 0, extra_fee_lines))
        return lines

    def get_courses(self, term_id=False):
        for rec in self:
            if term_id:
                courses = self.env['odoocms.student.course'].sudo().search([
                    ('student_id', '=', rec.id), ('session_id', '=', rec.session_id.id), ('term_id', '=', term_id.id)])
                if courses:
                    return courses
        return []

    # Checking the Student Arrears and Advance Payment Paid
    # def get_arrears_adjustments(self, term_id, lines):
    #     adjustment_lines = []
    #     balance = 0
    #     for rec in self:
    #         qty = 1
    #         ledger_lines = self.env['odoocms.student.ledger'].search([('student_id', '=', rec.id),
    #                                                                   ('is_defer_entry', '!=', True)])
    #         if ledger_lines:
    #             credit_sum = 0
    #             debit_sum = 0
    #             for ledger_line in ledger_lines:
    #                 if not ledger_line.invoice_id.is_hostel_fee:  # Temp Added This Condition For Spring 2021
    #                     credit_sum += ledger_line.credit
    #                     debit_sum += ledger_line.debit
    #                     balance = (credit_sum - debit_sum)
    #
    #             # If Student Have The Arrears
    #             if balance > 0:
    #                 open_invoices = self.env['account.move'].search([('payment_state', '=', 'not_paid'),
    #                                                                  ('student_id', '=', rec.id),
    #                                                                  ('move_type', '=', 'out_invoice'),
    #                                                                  ('sub_invoice', '=', False),
    #                                                                  ('is_scholarship_fee', '!=', True),
    #                                                                  ('student_ledger_id.is_defer_entry', '!=', True)])
    #                 # Added at 22-08-2021
    #                 # Cancel the Previous Invoices
    #                 if open_invoices:
    #                     for open_invoice in open_invoices:
    #                         open_invoice.mapped('line_ids').remove_move_reconcile()
    #                         open_invoice.write({'state': 'cancel', 'cancel_due_to_arrears': True})
    #
    #                 arrears_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', '=', 'Arrears')], order='id', limit=1)
    #                 arrears_line = {
    #                     'sequence': 1000,
    #                     'price_unit': round(balance),
    #                     'quantity': qty,
    #                     'product_id': arrears_fee_head.product_id and arrears_fee_head.product_id.id or False,
    #                     'name': arrears_fee_head.product_id and arrears_fee_head.product_id.name or 'Previous Arrears ',
    #                     'account_id': arrears_fee_head.property_account_income_id.id,
    #                     # 'analytic_tag_ids': analytic_tag_ids,
    #                     'fee_head_id': arrears_fee_head.id,
    #                     'exclude_from_invoice_tab': False,
    #                 }
    #                 lines.append((0, 0, arrears_line))
    #
    #             # If Student Have The Paid the Extra Amount, then make the Adjustment in the Fee Receipt
    #             # ******* Added @ 01-08-2021 ******** #
    #             # To Manage Adjustment Issue in Ledger Double effect
    #             adjustment_amt = 0
    #             adjustment_lines = self.env['odoocms.fee.adjustment.request'].search([('student_id', '=', rec.id),
    #                                                                                   ('adjustment_term_id', '=', term_id.id),
    #                                                                                   ('charged', '=', False)])
    #             if adjustment_lines:
    #                 for adjustment_line in adjustment_lines:
    #                     if not self.env['odoocms.fee.adjustment.request.reversal'].search([('adjustment_request_id', '=', adjustment_line.id)]):
    #                         adjustment_amt += adjustment_line.total_refund_amount
    #                         adjustment_line.charged = True
    #             # ******* End @ 01-08-2021 ********
    #
    #             if balance < 0 or adjustment_amt > 0:
    #                 adjustment_amount = 0
    #                 if adjustment_amt > 0:
    #                     adjustment_amount = -adjustment_amt
    #                 if balance < 0:
    #                     adjustment_amount = balance - adjustment_amt
    #
    #                 adjustment_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', '=', "Previous Month's Fee Adjustment")], order='id', limit=1)
    #                 adjustment_line_values = {
    #                     'price_unit': round(adjustment_amount),
    #                     'quantity': qty,
    #                     'product_id': adjustment_fee_head.product_id and adjustment_fee_head.product_id.id or False,
    #                     'name': adjustment_fee_head.product_id and adjustment_fee_head.product_id.name or 'Adjustment',
    #                     'account_id': adjustment_fee_head.property_account_income_id.id,
    #                     # 'analytic_tag_ids': analytic_tag_ids,
    #                     'fee_head_id': adjustment_fee_head.id,
    #                     'exclude_from_invoice_tab': False,
    #                 }
    #                 lines.append((0, 0, adjustment_line_values))
    #                 balance = adjustment_amount
    #     return lines, balance, adjustment_lines

    def create_fine_line(self, lines):
        fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Late Fine')])
        if not fee_head:
            raise UserError(_("Late Fine Head is not defined in the System."))
        fine_line = {
            'sequence': 900,
            'price_unit': 0,
            'quantity': 1,
            'product_id': fee_head.product_id.id,
            'name': "Fine For Late Payment of Tuition Fee",
            'account_id': fee_head.property_account_income_id.id,
            'fee_head_id': fee_head.id,
            'exclude_from_invoice_tab': False,
            'no_split': fee_head.no_split,
        }
        lines.append([0, 0, fine_line])
        return lines

    def get_hostel_fee(self, lines, term_id):
        for rec in self:
            hostel_fee_charge_months = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.hostel_fee_charge_months') or '6')
            fee_head = self.env['odoocms.fee.head'].search([('hostel_fee', '=', True)], order='id', limit=1)
            if not fee_head:
                raise UserError(_("Hostel Fee Head is not defined in the System."))
            name = self.hostel_id and self.hostel_id.name or ''

            # Check Here if structure Head Line Receipt have been Generated.
            same_term_invoice = self.env['account.move'].search([('student_id', '=', self.id),
                                                                 ('term_id', '=', term_id.id),
                                                                 ('move_type', '=', 'out_invoice'),
                                                                 ('reversed_entry_id', '=', False)], order='id desc', limit=1)
            same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', self.id),
                                                                               ('reversed_entry_id', '=', same_term_invoice.id)])
            if same_term_invoice:
                if not same_term_invoice_reverse_entry:
                    sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id),
                                                                   ('fee_head_id', '=', fee_head.id)])
                    if sm_mvl:
                        continue

            price = 0
            price_unit = 0
            if self.tag_ids:
                is_nfs_student = self.tag_ids.filtered(lambda t: t.code == 'NFS')
                if is_nfs_student:
                    price = self.room_id.per_month_rent_int
                    price = self.room_id.room_type.currency_id._convert(price, self.env.company.currency_id, self.env.company, fields.Date.today())
                    price_unit = round(price * hostel_fee_charge_months, 2)
                else:
                    price = self.room_id.per_month_rent
                    price_unit = round(price * hostel_fee_charge_months, 2)

            hostel_fee_line = {
                'sequence': 500,
                'price_unit': price_unit,
                'quantity': 1,
                'product_id': fee_head.product_id.id,
                'name': name + " Fee",
                'account_id': fee_head.property_account_income_id.id,
                # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                # 'analytic_tag_ids': analytic_tag_ids,
                'fee_head_id': fee_head.id,
                'exclude_from_invoice_tab': False,
            }
            lines.append([0, 0, hostel_fee_line])
        return lines

    def create_tax_line(self, lines, term_id, fall_20):
        tax_rate = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.tax_rate') or '5')
        taxable_amount = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.taxable_amount') or '200000')
        taxable_fee_heads = self.env['odoocms.fee.head'].search([('taxable', '=', True)])

        previous_term_taxable_amt = 0
        current_term_taxable_amt = 0
        net_amount = 0
        tax_amount = 0

        # This Variable is used to skip the previous balance amount tax
        nfs = True
        for rec in self:
            if not fall_20 and not nfs:
                prev_term_inv = self.env['account.move'].search([('student_id', '=', rec.id),
                                                                 ('is_scholarship_fee', '!=', True),
                                                                 ('term_id', '!=', term_id.id)], order='id desc', limit=1)
                if prev_term_inv:
                    previous_term = prev_term_inv.term_id
                    prev_term_invoices = self.env['account.move'].search([('student_id', '=', rec.id),
                                                                          ('is_scholarship_fee', '!=', True),
                                                                          ('term_id', '=', previous_term.id)])
                    if prev_term_invoices:
                        if taxable_fee_heads:
                            for prev_term_invoice in prev_term_invoices:
                                taxable_lines = prev_term_invoice.invoice_line_ids.filtered(lambda l: l.fee_head_id.id in taxable_fee_heads.ids)
                                if taxable_lines:
                                    for taxable_line in taxable_lines:
                                        previous_term_taxable_amt += taxable_line.price_subtotal

            # For this Set fall_20 True from Calling point
            if fall_20:
                fall20_fee_recs = self.env['nust.student.fall20.fee'].search([('student_id', '=', rec.id)])
                if fall20_fee_recs:
                    for fall20_fee_rec in fall20_fee_recs:
                        fall20_fee_rec.fee_status = 'c'
                        previous_term_taxable_amt += fall20_fee_rec.amount

            for line in lines:
                # if not 'Discounts' in line[2]:
                if line[2]['price_unit'] < 0:
                    current_term_taxable_amt += line[2]['price_unit']
                else:
                    if line[2]['fee_head_id'] in taxable_fee_heads.ids:
                        current_term_taxable_amt += line[2]['price_unit']

            net_amount = previous_term_taxable_amt + current_term_taxable_amt

            if net_amount > taxable_amount:
                tax_amount = round(net_amount * (tax_rate / 100), 3)

            fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Advance Tax')])
            if not fee_head:
                raise UserError(_("Advance Tax Fee Head is not defined in the System."))
            if tax_amount > 0:
                tax_line = {
                    'sequence': 900,
                    'price_unit': tax_amount,
                    'quantity': 1,
                    'product_id': fee_head.product_id.id,
                    'name': "Tax Charged on Fee",
                    'account_id': fee_head.property_account_income_id.id,
                    # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                    # 'analytic_tag_ids': analytic_tag_ids,
                    'fee_head_id': fee_head.id,
                    'exclude_from_invoice_tab': False,
                }
                lines.append([0, 0, tax_line])
        return lines

    def action_create_donor_invoice(self, waiver_fee_line, price_unit, semester, structure_fee_head, fee_structure,
                                    invoice_group, receipts, registration_id, date_invoice, date_due, comment, tag, reference):
        due_date = (date_due + relativedelta(months=+6))
        sequence = fee_structure.journal_id.sequence_id
        new_name = sequence.with_context(ir_sequence_date=date_invoice).next_by_id()
        for rec in self:
            student_scholarship = self.env['odoocms.student.fee.scholarship']
            scholarship_amount_for_invoice = 0
            if waiver_fee_line.waiver_type == 'percentage':
                scholarship_price_unit = round(price_unit * waiver_fee_line.percentage / 100.0)
            if waiver_fee_line.waiver_type == 'fixed':
                scholarship_price_unit = waiver_fee_line.percentage
            price_unit = price_unit - scholarship_price_unit
            scholarship_amount_for_invoice += scholarship_price_unit

            data = {
                'student_id': self.id,
                'name': waiver_fee_line.waiver_id.name,
                'waiver_line_id': waiver_fee_line.id,
                'term_id': semester.id,
                # 'semester_id': self.env['odoocms.term.scheme'].search([('session_id', '=', self.session_id.id), ('semester_id', '=', self.semester_id.id)]).semester_id.id,
                'amount': scholarship_price_unit,
                'amount_percentage': waiver_fee_line.percentage,
                'waiver_type': waiver_fee_line.waiver_type,
                'donor_id': waiver_fee_line.waiver_id.donor_id and waiver_fee_line.waiver_id.donor_id.id or False,
            }
            student_scholarship += self.env['odoocms.student.fee.scholarship'].create(data)

            lines = []
            fee_line = {
                'price_unit': scholarship_amount_for_invoice,
                'quantity': 1,
                'product_id': structure_fee_head.fee_head_id.product_id.id,
                'name': waiver_fee_line.waiver_id.name,
                'account_id': structure_fee_head.fee_head_id.property_account_income_id.id,
                # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                # 'analytic_tag_ids': analytic_tag_ids,
                'fee_head_id': structure_fee_head.fee_head_id.id,
                'exclude_from_invoice_tab': False,
            }
            lines.append([0, 0, fee_line])

            data = {
                'student_id': self.id,
                'partner_id': waiver_fee_line.waiver_id.donor_id.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'registration_id': registration_id,
                'journal_id': fee_structure.journal_id.id,
                'name': new_name,
                'invoice_date': date_invoice,
                'invoice_date_due': due_date,
                'state': 'draft',
                'narration': comment,
                'tag': tag,
                'is_fee': True,
                'is_cms': True,
                'is_scholarship_fee': True,
                'reference': reference,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'waiver_amount': 0,
                'term_id': semester and semester.id or False,
                'study_scheme_id': self.study_scheme_id and self.study_scheme_id.id or False,
                'donor_id': waiver_fee_line.waiver_id.donor_id.id,
            }
            invoice = self.env['account.move'].create(data)
            for scholarship in student_scholarship:
                scholarship.invoice_id = invoice.id
            invoice.invoice_group_id = invoice_group
        return invoice


    @api.depends('ledger_lines', 'ledger_lines.balance')
    def _compute_ledger_balance(self):
        for rec in self:
            if rec.ledger_lines:
                last_ledger_line = self.env['odoocms.student.ledger'].sudo().search([('id', 'in', rec.ledger_lines.ids)], order='id desc', limit=1)
                if last_ledger_line.balance < 0:
                    rec.student_ledger_balance = last_ledger_line.balance
                    fall_receipts = self.env['account.move'].search([('student_id', '=', rec.id),
                                                                     ('term_id', '=', 215)])
                    if fall_receipts:
                        if any(f.forward_invoice for f in fall_receipts):
                            rec.receipt_installment = True
                        if any(r.forward_invoice and r.payment_state in ('in_payment', 'paid') for r in fall_receipts):
                            rec.installment_paid = True
                else:
                    rec.student_ledger_balance = 0

    # This Method update Individual Student Ledger
    def update_student_ledger_balance(self):
        for rec in self:
            balance = 0
            lines = self.env['odoocms.student.ledger'].search([('student_id', '=', rec.id)])
            for line in lines:
                balance = round((line.debit - line.credit + balance), 4)
                if balance < 0:
                    line.balance = balance
                    line.balance_str = "(" + str(abs(balance)) + ")"
                else:
                    line.balance_str = str(balance)
                    line.balance = balance

    @api.depends('tag_ids')
    def _compute_student_tags_row(self):
        for rec in self:
            if rec.tag_ids:
                student_groups = ''
                for tag in rec.tag_ids:
                    if tag.code:
                        student_groups = student_groups + tag.code + ", "
                rec.student_tags_row = student_groups
