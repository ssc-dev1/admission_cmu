# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdoocmsStudentScholarshipEligibility(models.Model):
    _name = 'odoocms.student.scholarship.eligibility'
    _description = 'Student Scholarship Eligibility'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    student_code = fields.Char('Student Code', compute='_compute_student_info', store=True)
    student_name = fields.Char('Student Name', compute='_compute_student_info', store=True)
    program_id = fields.Many2one('odoocms.program', 'Program', tracking=True)
    applied_term_id = fields.Many2one('odoocms.academic.term', 'Applied Term')
    program_term_scholarship_id = fields.Many2one('odoocms.program.term.scholarship', 'Program Term Scholarship')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    scholarship_value = fields.Float('Value')
    to_be = fields.Boolean('To Be', default=True)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('unique_student_scholarship', 'unique(student_id,scholarship_id)', "Duplicate Record are not Allowed."),
    ]

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdoocmsStudentScholarshipEligibility, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.student.scholarship.eligibility')
        return result

    @api.depends('student_id')
    def _compute_student_info(self):
        for rec in self:
            rec.student_code = rec.student_id.code
            rec.student_name = rec.student_id.name
