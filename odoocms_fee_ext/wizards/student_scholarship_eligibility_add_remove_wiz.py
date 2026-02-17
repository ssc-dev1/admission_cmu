# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError, UserError
import json


class StudentScholarshipEligibilityAddRemoveWiz(models.TransientModel):
    _name = 'student.scholarship.eligibility.add.remove.wiz'
    _description = 'Student Scholarship Eligibility Add Remove'

    @api.model
    def get_student_id(self):
        if self.env.context.get('active_model', False)=='odoocms.student' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    @api.model
    def get_current_term(self):
        if self.env.context.get('active_model', False)=='odoocms.student' and self.env.context.get('active_id', False):
            fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
            fee_charge_term_rec = self.env['odoocms.academic.term'].browse(fee_charge_term)
            return fee_charge_term_rec and fee_charge_term_rec.id or False

    @api.model
    def get_scholarship_ids(self):
        if self.env.context.get('active_model', False)=='odoocms.student' and self.env.context.get('active_id', False):
            student = self.env['odoocms.student'].browse(self.env.context['active_id'])
            return student.scholarship_eligibility_ids and student.scholarship_eligibility_ids.ids or []

    student_id = fields.Many2one('odoocms.student', 'Student', default=get_student_id)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_current_term)

    remove_scholarship_lines_domain = fields.Char(compute="_compute_lines_scholarship_domain", readonly=True, store=False)
    remove_scholarship_lines = fields.Many2many('odoocms.student.scholarship.eligibility', 'scholarship_eligibility_remove_rel1',
                                                'wiz_id', 'eligibility_id', 'Remove Scholarship', default=get_scholarship_ids)
    add_scholarship_lines = fields.One2many('student.scholarship.eligibility.add.line.wiz', 'wiz_id', 'Add Scholarships')

    @api.depends('student_id')
    def _compute_lines_scholarship_domain(self):
        for rec in self:
            s_list = []
            if rec.student_id:
                s_list = rec.student_id.scholarship_eligibility_ids and rec.student_id.scholarship_eligibility_ids.ids or []
            rec.remove_scholarship_lines_domain = json.dumps([('id', 'in', s_list)])

    def action_check_eligibility_adjustment(self):
        if not self.remove_scholarship_lines and not self.add_scholarship_lines:
            raise UserError(_('There is no Add/Remove Line, Please Enter These'))

        # ***** Removal Process ***** #
        if self.remove_scholarship_lines:
            for remove_line in self.remove_scholarship_lines:
                # But First Create Deletion Log Here
                remove_line.sudo().unlink()

        # ***** Addition Process ***** #
        if self.add_scholarship_lines:
            for line in self.add_scholarship_lines:
                data_values = {
                    'student_id': self.student_id.id,
                    'student_code': self.student_id.code,
                    'student_name': self.student_id.name,
                    'program_id': self.student_id.program_id and self.student_id.program_id.id or False,
                    'applied_term_id': self.student_id.term_id and self.student_id.term_id.id or False,
                    'program_term_scholarship_id': False,
                    'scholarship_id': line.scholarship_id.id,
                    'scholarship_value': line.scholarship_value,
                    'state': 'lock',
                }
                new_rec = self.env['odoocms.student.scholarship.eligibility'].create(data_values)

        # ***** Apply Adjustment ***** #
        self.action_apply_adjustment()

    def action_apply_adjustment(self):
        # First Check if Challan Generated for that Term
        domain = [('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id)]
        invoices = self.env['account.move'].search(domain)
        if invoices:
            if not any([inv.payment_state in ('in_payment', 'paid', 'partial') for inv in invoices]):
                # Delete Old Invoices
                invoices.write({'payment_state': 'not_paid', 'state': 'draft', 'posted_before': False})
                for invoice in invoices:
                    invoice.sudo().with_context(force_delete=True).unlink()

                # New Invoices Creation
                domain = [('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id)]
                registration_id = self.env['odoocms.course.registration'].search(domain)
                if registration_id:
                    invoice_id = registration_id.student_id.generate_registration_invoice(registration_id)
                    if invoice_id:
                        registration_id.write({'generate_fee': False, 'invoice_id': invoice_id and invoice_id.id or False})


class StudentScholarshipEligibilityAddLineWiz(models.TransientModel):
    _name = 'student.scholarship.eligibility.add.line.wiz'
    _description = 'Student Scholarship Eligibility Add Lines'

    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    scholarship_value = fields.Float('Value', compute='_compute_scholarship_value', store=True)
    wiz_id = fields.Many2one('student.scholarship.eligibility.add.remove.wiz', 'Wizard Ref')
    add_scholarship_lines_domain = fields.Char(compute="_compute_add_lines_scholarship_domain", readonly=True, store=False)

    @api.depends('wiz_id.student_id')
    def _compute_add_lines_scholarship_domain(self):
        for rec in self:
            s_list = []
            student_id = rec.wiz_id.student_id
            if student_id and student_id.scholarship_eligibility_ids:
                sc_ids = student_id.scholarship_eligibility_ids.mapped('scholarship_id')
                s_list = self.env['odoocms.fee.waiver'].search([]) - sc_ids
            if s_list:
                rec.add_scholarship_lines_domain = json.dumps([('id', 'in', s_list.ids)])
            else:
                rec.add_scholarship_lines_domain = []

    @api.depends('scholarship_id')
    def _compute_scholarship_value(self):
        if self.scholarship_id:
            if self.scholarship_id.line_ids:
                self.scholarship_value = self.scholarship_id.line_ids[0].percentage
