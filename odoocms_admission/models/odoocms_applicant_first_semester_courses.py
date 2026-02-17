# -*- coding: utf-8 -*-
import pdb
import json
from odoo import fields, models, api, _
from odoo.exceptions import UserError


class OdoocmsApplicantFirstSemesterCourses(models.Model):
    _name = 'odoocms.applicant.first.semester.courses'
    _inherit = ['mail.thread']
    _description = 'Applicant First Semester Courses'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    course_id_domain = fields.Char(compute="_compute_course_domain", readonly=True, store=False)
    course_id = fields.Many2one('odoocms.course', 'Course')
    study_scheme_id = fields.Many2one('odoocms.study.scheme', 'Study Scheme')
    study_scheme_line_id = fields.Many2one('odoocms.study.scheme.line', 'Study Scheme Line')
    credit_hours = fields.Integer('Credit Hours')
    per_credit_hour_fee = fields.Float('Per Credit Hour Fee')
    course_fee = fields.Float('Total Fee', compute="_compute_course_fee", store=True)
    application_id = fields.Many2one('odoocms.application', 'Applicant', tracking=True)
    semester_no = fields.Integer(related='study_scheme_line_id.semester_id.number', string='Semester', store=True)

    @api.depends('credit_hours', 'per_credit_hour_fee')
    def _compute_course_fee(self):
        for rec in self:
            rec.course_fee = rec.credit_hours * rec.per_credit_hour_fee

    def create(self, vals):
        updated_vals = vals.copy()  
        if isinstance(vals, list):
            for rec_vals in vals:
                std_application = self.env['odoocms.application'].search([('id', '=', rec_vals.get('application_id'))])
                program_id = std_application.preference_ids and std_application.preference_ids[0].program_id or False
                if std_application and program_id:
                    program_batch = self.env['odoocms.batch'].search([
                        ('program_id', '=', program_id.id),
                        ('session_id', '=', std_application.register_id.academic_session_id.id),
                        ('term_id', '=', std_application.register_id.term_id.id),
                        ('career_id', '=', std_application.register_id.career_id.id)
                    ])
                    if program_batch:
                        rec_vals['per_credit_hour_fee'] = program_batch.per_credit_hour_fee
                    if program_batch.study_scheme_id:
                        rec_vals['study_scheme_id'] = program_batch.study_scheme_id.id or False
                        study_scheme_line_id = program_batch.study_scheme_id.line_ids.filtered(lambda ln: ln.course_id.id == rec_vals.get('course_id'))[:1]
                        rec_vals['study_scheme_line_id'] = study_scheme_line_id and study_scheme_line_id.id or False
                        rec_vals['credit_hours'] =study_scheme_line_id and study_scheme_line_id.credits or 0.0
            res = super(OdoocmsApplicantFirstSemesterCourses, self).create(updated_vals)
        else:
            application_id =vals.get('application_id')
            study_scheme_id =vals.get('study_scheme_id')
            study_scheme_line_id=vals.get('study_scheme_line_id')
            if study_scheme_id and study_scheme_line_id:
                updated_vals['study_scheme_id']=study_scheme_id
                updated_vals['study_scheme_line_id'] =study_scheme_line_id
                res = super(OdoocmsApplicantFirstSemesterCourses, self).create(updated_vals)
            else:    
                std_application = self.env['odoocms.application'].search([('id', '=', application_id)])
                program_id = std_application.preference_ids and std_application.preference_ids[0].program_id or False

                if std_application and program_id:
                    program_batch = self.env['odoocms.batch'].search([
                        ('program_id', '=', program_id.id),
                        ('session_id', '=', std_application.register_id.academic_session_id.id),
                        ('term_id', '=', std_application.register_id.term_id.id),
                        ('career_id', '=', std_application.register_id.career_id.id)
                    ])
                    if program_batch:
                        updated_vals['per_credit_hour_fee'] = program_batch.per_credit_hour_fee
                        if program_batch.study_scheme_id:
                                updated_vals['study_scheme_id'] = program_batch.study_scheme_id.id or False
                                study_scheme_line_id = program_batch.study_scheme_id.line_ids.filtered(lambda ln: ln.course_id.id == vals.get('course_id'))
                                updated_vals['study_scheme_line_id'] = study_scheme_line_id and study_scheme_line_id.id or False
                res = super(OdoocmsApplicantFirstSemesterCourses, self).create(updated_vals)
        
        return res

    @api.constrains('course_id')
    def course_duplicate_constrains(self):
        for rec in self:
            already_exist = self.env['odoocms.applicant.first.semester.courses'].search([('course_id', '=', rec.course_id.id),
                                                                                         ('application_id', '=', rec.application_id.id),
                                                                                         ('id', '!=', rec.id)])
            if already_exist:
                raise UserError(_('Duplicate Courses Are Not Allowed.😀😀😀'))

    @api.onchange('course_id')
    def onchange_course(self):
        for rec in self:
            rec.credit_hours = rec.course_id.credits
            program_id = rec.application_id.preference_ids and rec.application_id.preference_ids[0].program_id or False
            if rec.application_id and program_id:
                program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id),
                                                                  ('session_id', '=', rec.application_id.register_id.academic_session_id.id),
                                                                  ('term_id', '=', rec.application_id.register_id.term_id.id),
                                                                  ('career_id', '=', rec.application_id.register_id.career_id.id)])
                if program_batch:
                    rec.per_credit_hour_fee = program_batch.per_credit_hour_fee
                    if not self.study_scheme_id:
                        if program_batch.study_scheme_id:
                            rec.study_scheme_id = program_batch.study_scheme_id and program_batch.study_scheme_id.id or False
                            study_scheme_line_id = program_batch.study_scheme_id.line_ids.filtered(lambda ln: ln.course_id.id == rec.course_id.id)
                            rec.study_scheme_line_id = study_scheme_line_id and study_scheme_line_id.id or False

    @api.depends('application_id', 'study_scheme_id')
    def _compute_course_domain(self):
        domain = []
        if self.study_scheme_id and self.study_scheme_id.line_ids:
            self.course_id_domain = json.dumps([('id', 'in', self.study_scheme_id.line_ids.mapped('course_id').ids)])

        if not self.study_scheme_id and self.application_id:
            program_id = self.application_id.preference_ids and self.application_id.preference_ids[0].program_id or False
            if not program_id:
                raise UserError(_('No Preference Set'))
            program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id),
                                                              ('session_id', '=', self.application_id.register_id.academic_session_id.id),
                                                              ('term_id', '=', self.application_id.register_id.term_id.id),
                                                              ('career_id', '=', self.application_id.register_id.career_id.id)])
            if program_batch:
                self.course_id_domain = json.dumps([('id', 'in', program_batch.study_scheme_id.line_ids.mapped('course_id').ids)])


