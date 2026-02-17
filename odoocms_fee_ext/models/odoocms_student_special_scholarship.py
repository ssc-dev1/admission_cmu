# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil import relativedelta
from odoo.exceptions import ValidationError, UserError
from odoo.tools.safe_eval import safe_eval


class OdoocmsStudentSpecialScholarship(models.Model):
    _name = 'odoocms.student.special.scholarship'
    _description = 'Student Special Scholarship'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _order = 'name desc'

    def get_term_id(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='id desc', limit=1)
        return term_id and term_id.id or False

    def _get_special_scholarship(self):
        special_scholarship = self.env['odoocms.fee.waiver'].search([('is_special', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='id', limit=1)
        return special_scholarship and special_scholarship.id or False

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_term_id)
    date = fields.Date('Date', default=fields.Date.today())

    type = fields.Selection([('special','Special'),('regular','Regular')], 'Type')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship', default=_get_special_scholarship)
    value_type = fields.Selection([('fixed', 'Fixed'), ('percentage', 'Percentage')], string='Value Type', default='fixed', tracking=True)
    scholarship_value = fields.Float('Scholarship Value', compute='get_scholarship_value', store=True)

    state = fields.Selection([('draft', 'New'), ('approved', 'Approved'),('reject', 'Rejected')], string='Status', default='draft', tracking=True)

    to_be = fields.Boolean('To Be', default=True)
    allow_scholarship_repeating_courses = fields.Boolean('Allow Scholarship On Repeating Courses', default=False)
    remarks = fields.Text('Remarks')

    total_fee = fields.Float('Total Fee', compute='_compute_fee_detail', store=True)
    total_fee_after_discount = fields.Float('Fee After Discount', compute='_compute_fee_detail', store=True)
    paid_fee = fields.Float('Paid Fee', compute='_compute_fee_detail', store=True)
    unpaid_fee = fields.Float('Unpaid Fee', compute='_compute_fee_detail', store=True)
    total_waiver = fields.Float('Total Waiver', compute='_compute_fee_detail', store=True)
    paid_waiver = fields.Float('Paid Waiver', compute='_compute_fee_detail', store=True)
    unpaid_waiver = fields.Float('Unpaid Waiver', compute='_compute_fee_detail', store=True)
    total_credit_hours = fields.Float('Credit Hours', compute='_compute_fee_detail', store=True)
    per_credit_hour_fee = fields.Float('Per Credit Hour Fee', compute='_compute_fee_detail', store=True)
    current_scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Current Scholarship', compute='_compute_fee_detail', store=True)
    current_scholarship_value = fields.Float('Current Scholarship Value', compute='_compute_fee_detail', store=True)

    new_scholarship_amount = fields.Float('New Scholarship Amount', compute="_compute_new_scholarship_amount", store=True)
    scholarship_amount_diff = fields.Float('Scholarship Amount Diff', compute="_compute_new_scholarship_amount", store=True)
    is_special_scholarship = fields.Boolean('Is Special', related='scholarship_id.is_special', store=True)

    fixed_amount_scholarship_percentage = fields.Float('Fixed Amount %')
    move_id = fields.Many2one('account.move', 'Move')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.depends('student_id')
    def _compute_fee_detail(self):
        for rec in self:
            student_id = self.env['odoocms.student']
            total_fee = paid_fee = unpaid_fee = 0
            current_scholarship = False
            current_scholarship_value = 0
            credit_hours = 0

            if rec.student_id and rec.student_id._origin:
                student_id = rec.student_id._origin
            elif rec.student_id:
                student_id = rec.student_id

            if student_id:
                if student_id.fee_structure_id:
                    faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', self.term_id.id)], order='id desc', limit=1)
                    if not faculty_wise_fee_rec:
                        raise UserError(_('Faculty Wise Challan Configuration for this Student is not Found.'))

                    per_credit_hour_fee = 0
                    receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids
                    fee_structure = student_id._get_fee_structure(log_message=False)
                    tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
                    structure_fee_heads = student_id._get_fee_heads(fee_structure, receipt_type_ids, tuition_fee_head)  # odoocms.fee.structure on session,batch,career, odoocms.fee.structure.head of required receipts
                    for structure_fee_head in structure_fee_heads:
                        for head_line in structure_fee_head.line_ids:  # odoocms.fee.structure.head.line
                            if self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', student_id.id)]):
                                per_credit_hour_fee = head_line.amount

                else:
                    per_credit_hour_fee = student_id.batch_id and student_id.batch_id.per_credit_hour_fee or 0.0

                # if per_credit_hour_fee == 0:
                #     raise UserError('Please check Per Credit/Course Fee at Batch form')

                if student_id.course_ids:
                    courses = student_id.course_ids.filtered(lambda a: a.state in ('current', 'withdraw'))
                    for course in courses:
                        total_fee += course.credits * per_credit_hour_fee
                        credit_hours += course.credits

                elif student_id.registration_request_ids:
                    for registration_request_id in student_id.registration_request_ids:
                        total_fee += registration_request_id.credits * per_credit_hour_fee
                        credit_hours += registration_request_id.credits

                domain = [('student_id', '=', student_id.id), ('term_id', '=', rec.term_id.id), ('state', '!=', 'cancel')]
                challan_ids = self.env['odoocms.fee.barcode'].search(domain)
                challan_ids = challan_ids.filtered(lambda l: l.label_id.type in ('main','installment', 'add_drop'))

                invoice_ids = challan_ids.mapped('line_ids').mapped('move_id')
                fine_sum = 0
                for invoice_id in invoice_ids:
                    fine_lines = invoice_id.line_ids.filtered(lambda l: l.fee_category_id.name == 'Fine' and l.price_subtotal > 0)
                    for fine_line in fine_lines:
                        fine_sum += fine_line.credit

                for challan_id in challan_ids:
                    for line in challan_id.line_ids:
                        invoice = line.move_id
                        if not current_scholarship and invoice.challan_type in ('main_challan', 'admission','2nd_challan','add_drop') and invoice.waiver_ids:
                            current_scholarship = invoice.waiver_ids[0]
                            current_scholarship_value = invoice.waiver_percentage

                        if challan_id.state == 'paid':
                            paid_fee += line.debit

                        elif challan_id.state == 'draft':
                            unpaid_fee += line.debit

                if fine_sum > 0:
                    paid_fee -= fine_sum
                if paid_fee == 0:
                    unpaid_fee -= fine_sum

                if not current_scholarship:
                    current_scholarship = student_id.scholarship_id and student_id.scholarship_id or False
                    if current_scholarship:
                        current_scholarship_value = current_scholarship.amount

                waiver = 0
                if current_scholarship and not current_scholarship.scholarship_category_id.name == 'Not Applicable':
                    for invoice_id in invoice_ids:
                        course_lines = invoice_id.invoice_line_ids.filtered(lambda l: l.course_credit_hours > 0)
                        for course_line in course_lines:
                            waiver += (course_line.course_gross_fee - course_line.price_subtotal)

                total_fee_after_discount = total_fee - waiver

                rec.write({
                    'total_fee': total_fee,
                    'total_waiver': waiver,
                    'paid_fee': paid_fee,
                    'unpaid_fee': unpaid_fee,
                    'total_fee_after_discount': total_fee_after_discount,
                    'current_scholarship_id': current_scholarship.id if current_scholarship else False,
                    'current_scholarship_value': current_scholarship_value,
                    'total_credit_hours': credit_hours,
                    'per_credit_hour_fee': per_credit_hour_fee,
                    'fixed_amount_scholarship_percentage': round((rec.scholarship_value / (total_fee or 1)) * 100, 4) if rec.value_type == 'fixed' else 0,
                })

    @api.depends('scholarship_id', 'scholarship_value', 'value_type')
    def _compute_new_scholarship_amount(self):
        for rec in self:
            student_id = self.env['odoocms.student']
            if rec.student_id and rec.student_id._origin:
                student_id = rec.student_id._origin
            elif rec.student_id:
                student_id = rec.student_id

            scholarship_amount = 0
            if rec.value_type == 'fixed':
                scholarship_amount = rec.scholarship_value
                rec.new_scholarship_amount = rec.total_waiver + scholarship_amount
                rec.scholarship_amount_diff = scholarship_amount

            elif rec.value_type == 'percentage':
                if student_id.fee_structure_id:
                    faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', self.term_id.id)], order='id desc', limit=1)
                    if not faculty_wise_fee_rec:
                        raise UserError(_('Faculty Wise Challan Configuration for this Student is not Found.'))

                    per_credit_hour_fee = 0
                    receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids
                    fee_structure = student_id._get_fee_structure(log_message=False)
                    tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
                    structure_fee_heads = student_id._get_fee_heads(fee_structure, receipt_type_ids, tuition_fee_head)  # odoocms.fee.structure on session,batch,career, odoocms.fee.structure.head of required receipts
                    for structure_fee_head in structure_fee_heads:
                        for head_line in structure_fee_head.line_ids:  # odoocms.fee.structure.head.line
                            if self.env['odoocms.student'].search(safe_eval(head_line.domain) + [('id', '=', student_id.id)]):
                                per_credit_hour_fee = head_line.amount

                else:
                    per_credit_hour_fee = student_id.batch_id and student_id.batch_id.per_credit_hour_fee or 0.0

                total_fee = 0
                courses = rec.student_id.course_ids.filtered(lambda a: a.state in ('draft','current'))
                for course in courses:
                    total_fee += course.credits * per_credit_hour_fee
                    scholarship_amount = round(total_fee * (rec.scholarship_value / 100))

                rec.new_scholarship_amount = scholarship_amount
                rec.scholarship_amount_diff = scholarship_amount - rec.total_waiver

    def action_approved(self):
        if self.value_type == 'percentage' and self.scholarship_value > 100:
            raise UserError(_("You Cannot Assign Greater Than 100"))
        if self.value_type == 'fixed' and self.scholarship_value > self.total_fee:
            raise UserError(_("Scholarship Amount Should be Less Than or Equal To Total Fee"))

        search_domain = [('student_id','=',self.student_id.id),('term_id','=',self.term_id.id),('scholarship_id','=',self.scholarship_id.id)]
        search_rec = self.env['odoocms.student.applied.scholarships'].sudo().search(search_domain)
        if not search_rec:
            data_values = {
                'student_id': self.student_id.id,
                'student_code': self.student_id.code,
                'student_name': self.student_id.name,
                'program_id': self.program_id.id or False,
                'term_id': self.term_id and self.term_id.id or False,
                'scholarship_id': self.scholarship_id and self.scholarship_id.id or False,
                'scholarship_continue_policy_id': False,
                'scholarship_continue_policy_line_id': False,
                'scholarship_percentage': self.scholarship_id and self.scholarship_id.amount,
                'current': True,
                'state': 'lock',
            }
            self.env['odoocms.student.applied.scholarships'].sudo().create(data_values)
        self.student_id.scholarship_id = self.scholarship_id and self.scholarship_id.id or False
        self.state = 'approved'

        domain = [('student_id','=',self.student_id.id),('term_id','=',self.term_id.id),('state','=','submit'),('invoice_id','!=',False)]
        registration_ids = self.env['odoocms.course.registration'].search(domain)
        if registration_ids:
            for registration_id in registration_ids:
                registration_id.action_reset_draft()
                registration_id.action_submit()
        else:
            self.action_check_adjustment()

    def action_reject(self):
        # 1):- Search and Delete This Scholarship from Applied Scholarship Pool:-
        applied_scholarship_rec = self.env['odoocms.student.applied.scholarships'].search(
            [
                ('student_id', '=', self.student_id.id),
                ('term_id', '=', self.term_id.id),
                ('scholarship_id', '=', self.scholarship_id.id)
            ]
        )
        if applied_scholarship_rec:
            applied_scholarship_rec.sudo().unlink()

        # 2):-  Check the Student Continue Policy to be Applied
        self.student_id.sudo().get_scholarship_policy()
        self.student_id.sudo().compute_student_current_scholarship()

        self.state = 'reject'

    def action_turn_to_draft(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdoocmsStudentSpecialScholarship, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.student.special.scholarship')
        return result

    # Removed on Mr. Aqeel Request as he is saying A student can have more than one special scholarship in a term
    # @api.constrains('student_id', 'term_id')
    # def _unique_student_special_scholarship(self):
    #     record = self.search(
    #         [
    #             ('student_id', '=', self.student_id.id),
    #             ('term_id', '=', self.term_id.id),
    #             ('id', '!=', self.id)
    #         ]
    #     )
    #     if record:
    #         raise ValidationError('Cannot have duplicated records for Same Student And Term')

    @api.constrains('scholarship_value')
    def scholarship_value_constrains(self):
        for rec in self:
            if rec._origin.scholarship_value < 0:
                raise UserError(_('Negative Value is not Allowed.'))
            if rec._origin.scholarship_value > 100 and rec._origin.value_type == 'percentage':
                raise UserError(_('Greater Than 100 is not Allowed.'))

    @api.depends('scholarship_id')
    def get_scholarship_value(self):
        for rec in self:
            if rec.scholarship_id:
                if not rec.scholarship_id.is_special:
                    rec.scholarship_value = rec.scholarship_id.amount
                    rec.value_type = 'percentage'

    def action_check_adjustment(self):
        # ***** First Check if, Challan Generated For That Term ***** #

        domain = [('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id), ('challan_type', '!=', 'misc_challan')]
        invoices = self.env['account.move'].search(domain)
        if invoices:
            invoice = invoices[0]
            fee_structure = invoice.fee_structure_id
            receipts = invoice.receipt_type_ids
            tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
            fee_head = self.env['odoocms.fee.head'].search([('company_id','=',invoice.company_id.id),('name', '=', tuition_fee_head)], limit=1)

            lines = []
            fee_line = {
                'sequence': 10,
                'price_unit': self.scholarship_amount_diff * -1,
                'quantity': 1,
                'product_id': fee_head.product_id.id,
                'name': 'Scholarship Adjustment',
                'account_id': fee_head.property_account_income_id.id,
                # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                # 'analytic_tag_ids': analytic_tag_ids,
                'fee_head_id': fee_head.id,
                'exclude_from_invoice_tab': False,
                'course_credit_hours': 0,
                'discount': 0,
            }
            lines.append((0, 0, fee_line))

            data = {
                'student_id': self.student_id.id,
                'partner_id': self.student_id.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'journal_id': fee_structure.journal_id and fee_structure.journal_id.id or self.env['account.journal'].search([('company_id','=',invoice.company_id.id),('type', '=', 'sale')], order='id asc', limit=1).id,
                'invoice_date': self.date or fields.Date.today(),
                'invoice_date_due': fields.Date.today() + relativedelta.relativedelta(days=7),
                'state': 'draft',
                'is_fee': True,
                'is_cms': True,
                'move_type': 'out_invoice',
                # 'move_type': 'out_refund',
                'invoice_line_ids': lines,
                'program_id': self.student_id.program_id.id,
                'term_id': self.term_id and self.term_id.id or False,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'waiver_amount': 0,
                'challan_type': 'installment',
                'narration': self.remarks
                # 'invoice_payment_term_id': payment_term and payment_term.id or False,
            }
            invoice = self.env['account.move'].sudo().create(data)
            invoice.action_post()
            self.move_id = invoice.id

            if self.scholarship_amount_diff < 0:
                domain = [('student_id','=',self.student_id.id),('state','=','draft')]
                next_challan = self.env['odoocms.fee.barcode'].search(domain).filtered(lambda l: l.label_id.type in ('main','installment'))
                if next_challan:
                    receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.type in ('receivable', 'payable'))
                    receivable_line.challan_id = next_challan[-1].id
                else:
                    invoice.generate_challan_barcode(self, late_fine=0)

            elif self.scholarship_amount_diff > 0:
                receivable_lines = invoice.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                inv_domain = [('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id), ('id', '!=', invoice.id)]
                other_invoices = self.env['account.move'].sudo().search(inv_domain)
                receivable_lines2 = other_invoices.line_ids.filtered(lambda line: not line.reconciled and line.account_id.user_type_id.type in ('receivable', 'payable'))
                (receivable_lines + receivable_lines2).reconcile()
