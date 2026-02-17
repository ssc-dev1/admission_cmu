import pdb
from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)


class OdooCMSStudent(models.Model):
    _inherit = "odoocms.student"

    def set_probation_tag(self, student_term):
        probations = ['No','First Probation','Second Probation','Third Probation','Fourth Probation','Fifth Probation','Sixth Probation']
        probation_cnt = student_term.probation_cnt or 0
        for student in self:
            tags = student.tag_ids
            if probation_cnt > 0:
                probation_code = "probation_%s" % (probation_cnt)
                probation_tag = self.env['odoocms.student.tag'].sudo().search([('code', '=', probation_code)])
                if not probation_tag:
                    values = {
                        'name': probations[probation_cnt],
                        'code': probation_code,
                    }
                    probation_tag = self.env['odoocms.student.tag'].create(values)
                new_tags = tags + probation_tag
            else:
                promotion_tags = self.env['odoocms.student.tag'].search([('code', 'like', 'probation')])
                new_tags = tags - promotion_tags

            data = {
                'probation_cnt': probation_cnt
            }
            if tags.ids != new_tags.ids:
                data['tag_ids'] = [[6, 0, new_tags.ids]]

            student.sudo().write(data)


class OdooCMSCareer(models.Model):
    _inherit = "odoocms.career"

    grades = fields.Char('Grades')
    factor = fields.Char('SD Factor')


class OdooCMSCourse(models.Model):
    _inherit = 'odoocms.course'
    
    grade_method_id = fields.Many2one('odoocms.grade.method', 'Grading', ondelete='restrict', tracking=True)
    grade_id = fields.Many2one('odoocms.grade', 'Grades', ondelete='restrict', tracking=True)


class OdooCMSCourseComponent(models.Model):
    _inherit = 'odoocms.course.component'

    assessment_template_id = fields.Many2one('odoocms.assessment.template', 'Assessment Template')


class OdooCMSStudySchemeLine(models.Model):
    _inherit = 'odoocms.study.scheme.line'

    grade_method_id = fields.Many2one('odoocms.grade.method', 'Grading', ondelete='restrict', tracking=True)
    department_id = fields.Many2one('odoocms.department', 'Department/Center')

    def _compute_components(self):
        super()._compute_components()
        for rec in self:
            rec.grade_method_id = rec.course_id.grade_method_id and rec.course_id.grade_method_id.id or False

    def component_hook(self, component_data):
        course_component = self.env['odoocms.course.component'].search([
            ('course_id', '=', self.course_id.id), ('component', '=', component_data['component'])
        ])
        if course_component:
            component_data['assessment_template_id'] = course_component.assessment_template_id and course_component.assessment_template_id.id or False
        return component_data


class OdooCMSStudySchemeLineComponent(models.Model):
    _inherit = 'odoocms.study.scheme.line.component'

    assessment_template_id = fields.Many2one('odoocms.assessment.template', 'Assessment Template')


class OdooCMSGradeMethod(models.Model):
    _name = 'odoocms.grade.method'
    _description = 'Grade Method'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    name = fields.Char('Grading', required=True)
    code = fields.Char('Code', required=True)
    sequence = fields.Integer('Sequence')
    method = fields.Char('Method to Call', required=True)
    notes = fields.Html('Notes')
    grade_id = fields.Many2one('odoocms.grade', 'Grade Scheme')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    # grade_class_ids = fields.One2many('odoocms.class.grade','grade_method_id','Grade Classes')


class OdooCMSProgram(models.Model):
    _inherit = 'odoocms.program'

    @api.model
    def _get_default_method(self):
        grading_method_id = self.env['odoocms.grade.method'].search([],order='sequence',limit=1)
        if grading_method_id:
            return grading_method_id.id

    grade_method_id = fields.Many2one('odoocms.grade.method', 'Grading', ondelete='restrict', tracking=True, default=_get_default_method)


class OdooCMSBatch(models.Model):
    _inherit = 'odoocms.batch'

    @api.model
    def _get_default_method(self):
        grading_method_id = self.env['odoocms.grade.method'].search([],order='sequence',limit=1)
        if grading_method_id:
            return grading_method_id.id

    grade_method_id = fields.Many2one('odoocms.grade.method', 'Grading', ondelete='restrict', tracking=True, default=_get_default_method)

    def component_hook(self,class_data, scheme_line):
        if scheme_line and not class_data.get('assessment_template_id',False):
            sl_component = self.env['odoocms.study.scheme.line.component'].search([
                ('scheme_line_id','=',scheme_line.id),('component','=',class_data['component'])
            ])
            if sl_component:
                class_data['assessment_template_id'] = sl_component.assessment_template_id and sl_component.assessment_template_id.id or False
        return class_data


class OdooCMSCourseDrop(models.Model):
    _inherit = "odoocms.student.course.drop"

    def action_approve(self):
        super().action_approve()
        for rec in self:
            for component in rec.registration_id.component_ids:
                assessments = self.env['odoocms.assessment.line'].search([
                    ('student_id','=',rec.student_id.id),
                    ('class_id','=',component.class_id.id)
                ])
                assessments.unlink()


