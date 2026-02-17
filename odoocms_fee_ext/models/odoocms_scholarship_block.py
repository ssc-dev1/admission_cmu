# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdoocmsStudentScholarshipBlock(models.Model):
    _name = 'odoocms.student.scholarship.block'
    _description = 'Block Student Scholarships'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    student_code = fields.Char('Student Code', compute='_compute_student_info', store=True)
    student_name = fields.Char('Student Name', compute='_compute_student_info', store=True)
    program_id = fields.Many2one('odoocms.program', 'Program', tracking=True, compute='_compute_student_info', store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', compute='_compute_student_info', store=True)
    state = fields.Selection([('draft', 'New'), ('block', 'Block'), ('unblock', 'Unblock')
                              ], string='Status', default='draft', tracking=True)
    to_be = fields.Boolean('To Be', default=True)
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_block(self):
        self.state = 'block'
        self.student_id.block_scholarship = True

    def action_unblock(self):
        self.state = 'unblock'
        self.student_id.block_scholarship = False

    def action_turn_to_draft(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdoocmsStudentScholarshipBlock, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.student.scholarship.block')
        return result

    @api.depends('student_id')
    def _compute_student_info(self):
        for rec in self:
            rec.student_code = rec.student_id.code
            rec.student_name = rec.student_id.name
            rec.program_id = rec.student_id.program_id.id
            rec.term_id = rec.student_id.term_id.id


class OdoocmsCourseScholarshipBlock(models.Model):
    _name = 'odoocms.course.scholarship.block'
    _description = 'Course Scholarship Block'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    course_id = fields.Many2one('odoocms.course', 'Course', tracking=True)
    course_code = fields.Char('Course Code', related='course_id.code', store=True)
    course_name = fields.Char('Course Name', related='course_id.name', store=True)
    course_credits = fields.Float('Credits', related='course_id.credits', store=True)
    career_id = fields.Many2one('odoocms.career', related='course_id.career_id', store=True)
    state = fields.Selection([('draft', 'New'), ('block', 'Block'), ('unblock', 'Unblock')
                              ], string='Status', default='draft', tracking=True)
    to_be = fields.Boolean('To Be', default=True)
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_block(self):
        self.state = 'block'
        self.course_id.block_scholarship = True

    def action_unblock(self):
        self.state = 'unblock'
        self.course_id.block_scholarship = False

    def action_turn_to_draft(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdoocmsCourseScholarshipBlock, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.course.scholarship.block')
        return result


class OdooCMSCourse(models.Model):
    _inherit = 'odoocms.course'

    block_scholarship = fields.Boolean('Block Scholarship', default=False)
