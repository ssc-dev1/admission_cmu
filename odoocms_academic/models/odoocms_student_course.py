import pdb
from odoo import models, fields, api, _
import decimal
from ...cms_process.models import main as main


def roundhalfup(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_UP
    return float(round(decimal.Decimal(str(n)), decimals))


class OdooCMSStudentCourse(models.Model):
    _inherit = 'odoocms.student.course'

    can_grace = fields.Boolean(default=False)
    grace_applied = fields.Boolean(default=False)
    grace_marks = fields.Float(default=0)
    normalized_marks = fields.Float('Normalized Marks')

    grade = fields.Char('Grade' ,size=5)
    grade_date = fields.Date('Grade Date')
    is_improved = fields.Boolean('Bracket Applied', default=False)

    total_marks = fields.Float('Total Marks', compute='_get_total_marks', store=True, readonly=False)
    r_total_marks = fields.Float('R. Total Marks' ,compute='_get_total_marks' ,store=True)
    mid_total_marks = fields.Float('Mid Total Marks')
    mid_grade = fields.Char('Mid Grade', size=5)
    mid_grade_date = fields.Date('Mid Grade Date')

    @api.depends('component_ids', 'component_ids.total_marks')
    def _get_total_marks(self):
        marks_rounding = int(self.env['ir.config_parameter'].sudo().get_param('odoocms.marks_rounding') or '2')
        for rec in self:
            total = r_total = 0
            for reg in rec.component_ids:
                total += reg.total_marks * (reg.class_id.weightage or 1)
                r_total += reg.r_total_marks * (reg.class_id.weightage or 1)
                # total += reg.total_marks
                # r_total += reg.r_total_marks

            rec.total_marks = roundhalfup(round(total / (rec.primary_class_id.credits or 1) ,2) ,marks_rounding)
            rec.r_total_marks = roundhalfup(round(r_total / (rec.primary_class_id.credits or 1) ,2), marks_rounding)

    def cron_total_marks(self ,n=2000):
        courses = self.search([('to_be' ,'=' ,True)] ,limit=n)
        for course in courses:
            course._get_total_marks()
            course.to_be = False

    def cron_assign_grade(self):
        registrations = self.env['odoocms.student.course'].search([('to_be' ,'=' ,True)])
        for registration in registrations:
            grade_line = main.get_absolute_grade(self, registration.student_id.program_id, registration.term_id, registration.normalized_marks, registration.course_id)
            if grade_line and not registration.grade in ('I', 'W', 'RW'):
                registration.grade = grade_line.name
        registrations.to_be = False


class OdooCMSStudentCourseComponent(models.Model):
    _inherit = 'odoocms.student.course.component'

    assessment_summary_ids = fields.One2many('odoocms.assessment.summary', 'registration_component_id' ,'Assessments')
    total_marks = fields.Float('Total Marks' ,compute='_get_total_marks' ,store=True)
    r_total_marks = fields.Float('R. Total Marks', compute='_get_total_marks', store=True)
    mid_total_marks = fields.Float('Mid Total Marks')
    to_be = fields.Boolean()

    @api.depends('assessment_summary_ids', 'assessment_summary_ids.percentage')
    def _get_total_marks(self):
        for reg in self:
            total = weightage = 0
            for rec in reg.assessment_summary_ids:
                # total += rec.percentage
                # total += rec.percentage * rec.assessment_component_id.weightage
                total += rec.percentaged_marks
                weightage += rec.assessment_component_id.weightage

            reg.total_marks = total / 100.0
            # reg.r_total_marks = total
            reg.r_total_marks = total / (weightage or 1.0)

    def cron_total_marks(self, limit=500):
        recs = self.env['odoocms.student.course.component'].search([('to_be' ,'=' ,True)], limit=limit)
        for rec in recs:
            rec._get_total_marks()
            rec.to_be = False

