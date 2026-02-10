# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import date


class OdoocmsStudentFacultyWiseChallan(models.Model):
    _name = 'odoocms.student.faculty.wise.challan'
    _description = 'Student Challan Faculty Wise'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    def get_term_id(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name', index=True)
    sequence = fields.Char('Sequence')
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_term_id)
    date = fields.Date('Date', default=fields.Date.today(), tracking=True, index=True)
    type = fields.Selection([
        ('Faculty', 'Select Faculty ...'),
        ('All', 'All Faculties'),
    ], default='Faculty', tracking=True, index=True, string="Faculty Selection")
    program_selection_type = fields.Selection([
        ('Program', 'Select Program ...'),
        ('All', 'All Program'),
    ], default='Program', string='Program Selection', tracking=True, index=True)

    faculty_ids = fields.Many2many('odoocms.department', 'faculty_wise_challan_wiz_department_rel1', 'faculty_wise_challan_id', 'department_id', 'Departments')
    excluded_faculty_ids = fields.Many2many('odoocms.department', 'faculty_wise_challan_wiz_department_rel2', 'faculty_wise_challan_id', 'department_id', 'Excluded Departments')

    program_ids = fields.Many2many('odoocms.program', 'faculty_wise_challan_wiz_program_rel1', 'faculty_wise_challan_id', 'program_id', 'Programs')
    excluded_program_ids = fields.Many2many('odoocms.program', 'faculty_wise_challan_wiz_program_rel2', 'faculty_wise_challan_id', 'program_id', 'Excluded Programs')

    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms',tracking=True)
    adddrop_payment_term_id = fields.Many2one('account.payment.term', string='Add Drop Payment Terms',tracking=True)
    second_payment_term_id = fields.Many2one('account.payment.term', string='Second Payment Terms', tracking=True)

    office_payment_term_ids = fields.Many2many('account.payment.term','payment_term_office_rel','rec_id','payment_term_id','BackOffice Available Terms')
    student_payment_term_ids = fields.Many2many('account.payment.term','payment_term_student_rel','rec_id','payment_term_id','Student Available Terms')

    lines = fields.One2many('odoocms.student.faculty.wise.challan.line', 'faculty_wise_challan_id', 'Lines')
    state = fields.Selection([
        ('Draft', 'Draft'),
        ('Generate', 'Generate Detail'),
        ('Generated', 'Challan Generated'),
        ('Cancel', 'Cancel')
    ], string='Status', default='Draft', tracking=True, index=True)

    receipt_type_ids = fields.Many2many('odoocms.receipt.type', 'student_faculty_wise_challan_receipt_type_rel', 'invoice_id', 'receipt_type_id', string='Fee Type')
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, values):
        if not values.get('sequence', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.faculty.wise.challan')
        result = super(OdoocmsStudentFacultyWiseChallan, self).create(values)
        return result

    def unlink(self):
        for rec in self:
            if not rec.state=='Draft':
                raise UserError('You Cannot delete this Record, This Record is not in the Draft State.')
            return super(OdoocmsStudentFacultyWiseChallan, self).unlink()

    def action_detail_generate(self):
        for rec in self:
            rec.action_generate_detail()
            rec.state = 'Generate'

    def action_generate_detail(self):
        for rec in self:
            term_id = rec.term_id
            if not term_id:
                term = self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term')
                if not term:
                    raise UserError(_('Please Select Term or enter the Fee Charge Term In the Setting'))
                term_id = self.env['odoocms.academic.term'].browse(term)

            if self.type=="Faculty":
                department_ids = self.faculty_ids
            else:
                department_ids = self.env['odoocms.department'].search([], order='id asc')
            if self.excluded_faculty_ids:
                department_ids = department_ids - self.excluded_faculty_ids

            if self.program_selection_type=="Program":
                program_ids = self.program_ids
            else:
                program_ids = self.env['odoocms.program'].search([('department_id', 'in', department_ids.ids)])

            batch_ids = self.env['odoocms.batch'].search([('department_id', 'in', department_ids.ids), ('program_id', 'in', program_ids.ids)])
            for batch_id in batch_ids:
                session_ids = self.env['odoocms.academic.session'].search([], order='id asc')
                for session_id in session_ids:
                    domain = [
                        ('batch_id', '=', batch_id.id),
                        ('program_id', '=', batch_id.program_id.id),
                        ('session_id', '=', session_id.id),
                        ('term_id', '=', term_id.id),
                        ('confirm', '!=', 'no')
                    ]
                    student_terms = self.env['odoocms.student.term'].search(domain)

                    student_cnt = student_terms.mapped('student_id')
                    if len(student_cnt) > 0:
                        data_values = {
                            'faculty_wise_challan_id': rec.id,
                            'career_id': batch_id.program_id.career_id.id,
                            'faculty_id': batch_id.department_id.id,
                            'program_id': batch_id.program_id.id,
                            'session_id': session_id.id,
                            'batch_id': batch_id.id,
                            'total_students': len(student_cnt),
                            'generated_cnt': 0,
                            'not_generated_cnt': len(student_cnt),
                            'to_be': True
                        }
                        self.env['odoocms.student.faculty.wise.challan.line'].create(data_values)

    def generate_challan(self):
        for rec in self:
            fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
            fee_charge_term_rec = self.env['odoocms.academic.term'].browse(fee_charge_term)

            to_compute = rec.invoice_payment_term_id.compute(10000, date_ref=date.today(), currency=self.company_id.currency_id)
            date_due = to_compute[-1][0]

            if rec.lines:
                for line in rec.lines.filtered(lambda l: l.to_be==True):
                    # student_terms = self.env['odoocms.course.registration'].search([('student_id.batch_id', '=', line.batch_id.id),
                    #                                                                 ('program_id', '=', line.program_id.id),
                    #                                                                 ('student_id.session_id', '=', line.session_id.id)])
                    student_terms = self.env['odoocms.student.term'].search([('batch_id', '=', line.batch_id.id),
                                                                             ('program_id', '=', line.program_id.id),
                                                                             ('session_id', '=', line.session_id.id),
                                                                             ('term_id', '=', fee_charge_term_rec.id),
                                                                             ('confirm', '!=', 'no')])

                    students = student_terms.mapped('student_id')
                    for student in students:
                        registration_request = student.registration_request_ids.mapped('registration_id').filtered(lambda l: l.term_id==fee_charge_term_rec)
                        invoice_id = student.generate_invoice_new(term_id=fee_charge_term_rec, receipts=rec.receipt_type_ids, date_due=date_due, apply_taxes=False, batch_id=line.batch_id, registration_id=registration_request)
                        if invoice_id:
                            line.not_generated_cnt -= 1
                            line.generated_cnt += 1
                            registration_request.sudo().action_approve(manual=False)
                    line.to_be = False

    def action_cancel(self):
        for rec in self:
            rec.state = 'Cancel'


class OdoocmStudentFacultyWiseChallanLine(models.Model):
    _name = 'odoocms.student.faculty.wise.challan.line'
    _description = 'Student Challan Faculty Wise Detail'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    faculty_id = fields.Many2one('odoocms.department', 'Faculty')
    faculty_name = fields.Char(related='faculty_id.code', store=True, string="Faculty Name")
    program_id = fields.Many2one('odoocms.program', 'Program')
    career_id = fields.Many2one('odoocms.career', 'Academic Career')
    career_name = fields.Char(related='career_id.code', string='Career', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Session')

    batch_id = fields.Many2one('odoocms.batch', 'Batch')
    batch_name = fields.Char(related='batch_id.code', string='Batch Name', store=True)

    total_students = fields.Integer('Total Students')
    generated_cnt = fields.Integer('Generated')
    not_generated_cnt = fields.Integer('Not Generated')
    faculty_wise_challan_id = fields.Many2one('odoocms.student.faculty.wise.challan', 'Faculty Wise Challan Ref', index=True, ondelete='cascade', auto_join=True)
    to_be = fields.Boolean('To Be', default=True)
