# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdoocmsStudentAppliedScholarships(models.Model):
    _name = 'odoocms.student.applied.scholarships'
    _description = 'Student Applied Scholarships'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    student_code = fields.Char('Student Code', compute='_compute_student_info', store=True)
    student_name = fields.Char('Student Name', compute='_compute_student_info', store=True)
    program_id = fields.Many2one('odoocms.program', 'Program', tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    scholarship_percentage = fields.Float('Scholarship Percentage')
    scholarship_continue_policy_id = fields.Many2one('odoocms.scholarship.continue.policy', 'Scholarship Policy')
    scholarship_continue_policy_line_id = fields.Many2one('odoocms.scholarship.continue.policy.line', 'Scholarship Policy Line')
    to_be = fields.Boolean('To Be', default=True)
    current = fields.Boolean('Current')
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('unique_student_term_scholarship', 'unique(scholarship_id,student_id,term_id)', "Duplicate Record are not Allowed."),
    ]

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdoocmsStudentAppliedScholarships, self).create(values)
        if not result.name:
            result.name = result.student_name + "-" + result.term_id.name + " Scholarship"
        return result

    @api.depends('student_id')
    def _compute_student_info(self):
        for rec in self:
            rec.student_code = rec.student_id.code
            rec.student_name = rec.student_id.name

    @api.depends('scholarship_id')
    def _compute_scholarship_percentage(self):
        for rec in self:
            rec.scholarship_percentage = rec.scholarship_id.amount