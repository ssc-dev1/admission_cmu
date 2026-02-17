import pdb
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from statistics import mean, pstdev
import math
import decimal
from datetime import datetime
import logging


_logger = logging.getLogger(__name__)


def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier


def roundhalfup(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_UP
    return float(round(decimal.Decimal(str(n)), decimals))


READONLY_STATES2 = {
    'draft': [('readonly', False)],
    'current': [('readonly', False)],
    'lock': [('readonly', True)],
    'submit': [('readonly', True)],
    'disposal': [('readonly', True)],
    'approval': [('readonly', True)],
    'notify': [('readonly', True)],
    'done': [('readonly', True)],
}


class OdooCMSAssessmentType(models.Model):
    _name = 'odoocms.assessment.type'
    _description = 'Assessment Type'
    _order = 'sequence'
    
    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True)
    req_approval = fields.Boolean('Approval Required',default=False)
    uploadable = fields.Boolean('Uploadeable', default=False)
    attendance = fields.Boolean('Attendance Required', default=False)
    weightage = fields.Float('Weightage', default=0)
    final = fields.Boolean('Final',default=False)


class OdooCMSAssessmentTemplate(models.Model):
    _inherit = 'odoocms.assessment.template'
    
    domain = fields.Char('Domain')
    
    line_ids = fields.One2many('odoocms.assessment.template.line','template_id','Distribution Lines', copy=True)
    total = fields.Float('Total',compute='_get_total', store=True)
    detail_ids = fields.One2many('odoocms.assessment.template.detail','template_id','Distribution Template', copy=True)
    load_ids = fields.One2many('odoocms.assessment.template.load', 'template_id', 'Minimum Load', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Template Name already exists!"),
        ('code_uniq', 'unique(code)', "Template Code already exists!"),
    ]
    
    @api.depends('line_ids','line_ids.weightage')
    def _get_total(self):
        for rec in self:
            total = 0
            for line in rec.line_ids:
                total += line.weightage
            # if total > 100:
            #     raise ValidationError('Weightage for %s can not be greater than 100' % (rec.name,))
            rec.total = total


#Quiz=10, Assignments=15, Mid=25, Final=50  (Master)
class OdooCMSAssessmentTemplateLine(models.Model):
    _name = 'odoocms.assessment.template.line'
    _description = 'Assessments'
    _order = 'sequence'

    template_id = fields.Many2one('odoocms.assessment.template', 'Distribution Template', ondelete='cascade')
    component = fields.Selection(string='Component', related='template_id.component', store=True, help='Theory/ Lab')

    sequence = fields.Integer('Sequence')
    type_id = fields.Many2one('odoocms.assessment.type','Assessment Type')
    name = fields.Char('Assessment Name', related='type_id.name', store=True)
    code = fields.Char('Assessment Code', related='type_id.code', store=True)
    weightage = fields.Float('Weightage (%)',required=True)
    min = fields.Float('Min (%)',required=True)
    max = fields.Float('Max (%)',required=True)
    final = fields.Boolean('Final',default=False)
    freeze = fields.Boolean('Freeze', default=False)
    company_id = fields.Many2one('res.company', string='Company', related='template_id.company_id', store=True)

    @api.constrains('min','max','weightage')
    def validate_range(self):
        for rec in self:
            if rec.min < 0:
                raise ValidationError(_('Min must be a Positive value'))
            if rec.max > 100:
                raise ValidationError(_('Max must be <= 100'))
            if rec.weightage < rec.min or rec.weightage > rec.max:
                raise ValidationError(_('Weightage must be in Min & Max range'))


class OdooCMSAssessmentTemplateLoad(models.Model):
    _name = 'odoocms.assessment.template.load'
    _description = 'Assessments Load'
    _order = 'sequence'

    template_id = fields.Many2one('odoocms.assessment.template', 'Assessment Template')
    assessment_type_id = fields.Many2one('odoocms.assessment.template.line', 'Assessment Type')
    
    weightage = fields.Integer('Weightage', required=True)
    min_assessments = fields.Integer('Min Assessments', required=True)
    min = fields.Integer('Min (Demo)', required=True)
    max = fields.Integer('Max (Demo)', required=True)
    event = fields.Selection([('mid','Mid'),('final','Final')],default='final',string='Before')
    sequence = fields.Integer('Sequence')
    assessment_template_line_id = fields.Many2one('odoocms.assessment.template.line', 'Assessment Type')
    company_id = fields.Many2one('res.company', string='Company', related='template_id.company_id', store=True)

    # weightage = fields.Integer('Weightage')
    # min = fields.Integer('Min (Demo)', required=True)
    # max = fields.Integer('Max (Demo)', required=True)
    
    
class OdooCMSAssessmentTemplateDetail(models.Model):
    _name = 'odoocms.assessment.template.detail'
    _description = 'Assessment Template Detail'
    _rec_name = 'assessment_template_line_id'
    _order = 'sequence'

    template_id = fields.Many2one('odoocms.assessment.template','Assessment Template')
    assessment_template_line_id = fields.Many2one('odoocms.assessment.template.line','Assessment Type')
    assessment_name = fields.Char('Assessment Name')
    assessment_code = fields.Char('Assessment Code')
    max_marks = fields.Float('Max Marks')
    weightage = fields.Float('Weightage', default=100)
    freeze = fields.Boolean('Freeze', default=False)
    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one('res.company', string='Company', related='template_id.company_id', store=True)

    
#Quiz=10, Assignments=15, Mid=25, Final=50  (Class Level)
class OdooCMSAssessmentComponent(models.Model):
    _name = 'odoocms.assessment.component'
    _description = 'Assessment Class'
    _rec_name = 'type_id'
    _order = 'type_id'

    class_id = fields.Many2one('odoocms.class', 'Class')
    state = fields.Selection(related='class_id.state',store=True)
    type_id = fields.Many2one('odoocms.assessment.type','Assessment Type')
    min = fields.Float('Min (%)')
    max = fields.Float('Max (%)')
    
    weightage = fields.Float('Weightage (%)')
    consideration_avg = fields.Boolean('Consider Average', default=True)
    consideration_top = fields.Boolean('Consider Top', default=False)
    best = fields.Integer('Best',default=0)
    
    assessment_ids = fields.One2many('odoocms.assessment', 'assessment_component_id','Assessments')
    primary_class_id = fields.Many2one('odoocms.class.primary', 'Class Primary', related='class_id.primary_class_id')
    freeze = fields.Boolean('Freeze', default=False)
    to_be = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)

    @api.onchange('consideration_avg','consideration_top')
    def onchange_consideration(self):
        for rec in self:
            if rec.consideration_avg:
                rec.consideration_top = False
            elif rec.consideration_top:
                rec.consideration_avg = False

    @api.model
    def create(self, vals):
        recs = super(OdooCMSAssessmentComponent,self).create(vals)
        # assessments = [[5]]
        for rec in recs:
            if rec.class_id.assessment_template_id:
                for assessment in rec.class_id.assessment_template_id.detail_ids.filtered(lambda l: l.assessment_template_line_id.type_id.id == rec.type_id.id):
                    data = {
                        'name': assessment.assessment_name,
                        'code': assessment.assessment_code,
                        'weightage': assessment.weightage or 100,
                        'max_marks': assessment.max_marks,
                        'freeze': assessment.freeze,
                        'class_id': rec.class_id.id,
                        'assessment_component_id': rec.id
                    }
                    self.env['odoocms.assessment'].create(data)
        return recs
        
    @api.constrains('weightage')
    def validate_sum(self):
        for rec in self:
            if rec.min > 0 and rec.max > 0 and (rec.weightage < rec.min or rec.weightage > rec.max):
                raise ValidationError(_('Weightage for %s must be in range %s - %s') % (rec.type_id.name, rec.min, rec.max))
  

class OdooCMSAssessment(models.Model):
    _name = 'odoocms.assessment'
    _description = 'Assessment'
    _order = 'date_assessment, assessment_component_id'
    # _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, states=READONLY_STATES2)
    code = fields.Char('Code',required=True, states=READONLY_STATES2)
    assessment_component_id = fields.Many2one('odoocms.assessment.component', 'Assessment Type', states=READONLY_STATES2, ondelete='restrict')

    class_id = fields.Many2one('odoocms.class', 'Class', states=READONLY_STATES2)
    state = fields.Selection(related='class_id.state', store=True)
    
    primary_class_id = fields.Many2one('odoocms.class.primary', 'Primary Class', compute='_get_compute', store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', compute='_get_compute', store=True)
    faculty_staff_id = fields.Many2one('odoocms.faculty.staff', string='Teacher', compute='_get_compute', store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', compute='_get_compute', store=True)
    program_id = fields.Many2one('odoocms.program', 'Program', compute='_get_compute', store=True)
    department_id = fields.Many2one('odoocms.department', string="Department/Center", compute='_get_compute', store=True)
    institute_id = fields.Many2one("odoocms.institute", string="Institute", compute='_get_compute', store=True, readonly=False)
    
    date_assessment = fields.Datetime('Assessment Date', states=READONLY_STATES2)
    date_submission = fields.Datetime('Submission Date')
    max_marks = fields.Float('Max Marks', states=READONLY_STATES2)
    weightage = fields.Float('Weightage (%)', default=100, states=READONLY_STATES2)
    assessment_lines = fields.One2many('odoocms.assessment.line', 'assessment_id', 'Student Assessments', states=READONLY_STATES2)

    average = fields.Float('Average',compute='_get_average',store=True)
    min = fields.Float('Min',compute='_get_average',store=True)
    max = fields.Float('Max',compute='_get_average',store=True)
    std = fields.Float('STD',compute='_get_average',store=True)

    can_delete = fields.Boolean(compute='_can_delete',store=False)

    freeze = fields.Boolean('Freeze', default=False)
    is_visible = fields.Boolean('Visibility',default=True)
    is_locked = fields.Boolean('Locked', default=False)
    is_approved = fields.Boolean('Approved', default=False)
    is_downloadable = fields.Boolean('Downloadable', default=True)
    sequence = fields.Integer()
    parent_id = fields.Many2one('odoocms.assessment', string='Parent Assessment', states=READONLY_STATES2)
    child_ids = fields.One2many('odoocms.assessment', 'parent_id', string='Sub Assessments',)
    description = fields.Html('Description')
    to_be = fields.Boolean(default=False)
    stat = fields.Boolean()
    lock_date = fields.Datetime('Lock Date',compute='_lock_date',store=True)
    remarks = fields.Char('Remarks')
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)

    @api.depends('class_id')
    def _get_compute(self):
        for rec in self:
            if rec.class_id:
                class_id = rec.class_id
                primary_class_id = class_id.primary_class_id
                batch_id = primary_class_id.batch_id
                
                rec.primary_class_id = primary_class_id.id
                rec.term_id = class_id.term_id.id
                rec.faculty_staff_id = class_id.faculty_staff_id.id
                rec.batch_id = batch_id.id
                rec.program_id = batch_id.program_id.id
                rec.department_id = batch_id.department_id.id
                rec.institute_id = batch_id.department_id.institute_id.id
        
    def action_approve(self):
        for rec in self:
            rec.is_approved = True

    def action_refuse(self):
        for rec in self:
            rec.is_approved = False
            rec.is_locked = False

    @api.depends('is_locked')
    def _lock_date(self):
        for rec in self:
            if rec.is_locked:
                rec.lock_date = datetime.now()
                if not rec.assessment_component_id.type_id.req_approval:
                    rec.is_approved = True

    def write(self, vals):
        res = super().write(vals)
        if not vals.get('stat',True):
            for rec in self:
                stat = rec._get_statistics()
                values = {
                    'average': stat['average'],
                    'min': stat['min'],
                    'max': stat['max'],
                    'std': stat['std'],
                }
                rec.write(values)
        return res

    def _get_statistics(self):
        total = 0
        if self.parent_id:
            for child in self.parent_id.child_ids:
                total += child.max_marks

            self.parent_id.max_marks = total
            # AARSOL - FAROOQ
            # total2 = 0
            # for assessment in rec.parent_id.child_ids:
            #     cass = assessment.assessment_lines.filtered(lambda l: l.student_id.id == rec.student_id.id)
            #     total2 += cass.obtained_marks
            # cass = rec.parent_id.assessment_lines.filtered(lambda l: l.student_id.id == rec.student_id.id)
            # cass.obtained_marks = total2

        data = self.assessment_lines.filtered(lambda l: l.summary_id.registration_component_id.student_course_id.grade != 'W')\
            .mapped('obtained_marks') or [0]
        return {
            'average': roundhalfup(mean(data),2),
            'min': roundhalfup(min(data),2),
            'max': roundhalfup(max(data),2),
            'std': roundhalfup(pstdev(data),2),
            'stat': True,
        }

    # @api.depends('max_marks','assessment_lines','assessment_lines.obtained_marks')
    def _get_average(self):
        for rec in self:
            total = 0
            if rec.parent_id:
                for child in rec.parent_id.child_ids:
                    total += child.max_marks

                rec.parent_id.max_marks = total
                # AARSOL - FAROOQ
                # total2 = 0
                # for assessment in rec.parent_id.child_ids:
                #     cass = assessment.assessment_lines.filtered(lambda l: l.student_id.id == rec.student_id.id)
                #     total2 += cass.obtained_marks
                # cass = rec.parent_id.assessment_lines.filtered(lambda l: l.student_id.id == rec.student_id.id)
                # cass.obtained_marks = total2

            data = rec.assessment_lines.filtered(lambda l: l.summary_id.registration_component_id.student_course_id.grade != 'W')\
                .mapped('obtained_marks') or [0]
            rec.write({
                'average': roundhalfup(mean(data),2),
                'min': roundhalfup(min(data),2),
                'max': roundhalfup(max(data),2),
                'std': roundhalfup(pstdev(data),2),
            })

    def cron_get_average(self, limit=100):
        recs = self.env['odoocms.assessment'].search([('to_be','=',True)],limit=limit)
        for rec in recs:
            rec._get_average()
            rec.to_be = False
            
    @api.depends('assessment_lines','average')
    def _can_delete(self):
        for rec in self:
            if rec.freeze or rec.average > 0 or rec.child_ids:
                rec.can_delete = False
            else:
                rec.can_delete = True
            
    @api.constrains('max_marks')
    def check_max_marks(self):
        for rec in self:
            if rec.max_marks <= 0:
                raise ValidationError(_('Max Marks must be greater than Zero'))
        
    def name_get(self):
        res = []
        for record in self:
            name = (record.name or '') + ' - ' + (record.code or '')
            res.append((record.id, name))
        return res

    def generate_sheet(self):
        for reg in self.class_id.primary_class_id.registration_ids:
            summary_rec = self.env['odoocms.assessment.summary'].search(
                [('class_id', '=', self.class_id.id), ('student_id', '=', reg.student_id.id),
                 ('assessment_component_id', '=', self.assessment_component_id.id)])

            if not summary_rec:
                summary_vals = {
                    'class_id': self.class_id and self.class_id.id or False,
                    'student_id': reg.student_id.id,
                    'assessment_component_id': self.assessment_component_id.id,
                }
                summary_rec = self.env['odoocms.assessment.summary'].create(summary_vals)
            data = {
                'assessment_id': self.id,
                'student_id': reg.student_id.id,
                'obtained_marks': 0,
                'summary_id': (not self.parent_id) and summary_rec and summary_rec.id or False,
            }
            self.env['odoocms.assessment.line'].create(data)
            
    def assessment_result(self):
        form_view = self.env.ref('odoocms_academic.odoocms_assessment_form')
        domain = [('id', 'in', self.ids)]
        return {
            'name': _('Assessment Result'),
            'domain': domain,
            'res_model': 'odoocms.assessment',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'view_mode': 'form',
            'view_type': 'form',
            'views': [
                (form_view and form_view.id or False, 'form'),
            ],
            'res_id': self.id,
        }


class OdooCMSAssessmentLine(models.Model):
    _name = 'odoocms.assessment.line'
    _description = 'Assessment Line'
    _order = 'student_id'

    assessment_id = fields.Many2one('odoocms.assessment', 'Assessment',ondelete='cascade')
    class_id = fields.Many2one('odoocms.class', 'Class', related="assessment_id.class_id", store=True)
    student_id = fields.Many2one('odoocms.student', 'Student')
    summary_id = fields.Many2one('odoocms.assessment.summary', 'Assessment Summary',compute='_get_summary_id',store=True)
    assessment_component_id = fields.Many2one('odoocms.assessment.component', 'Assessment Type', related='assessment_id.assessment_component_id', store=True)
    max_marks = fields.Float('Max Marks', related='assessment_id.max_marks', store=True)
    weightage = fields.Float('Weightage (%)',related='assessment_id.weightage',store=True)
    obtained_marks = fields.Float('Obtained Marks')
    percentage = fields.Float('Percentage', compute='_get_percentage', store=True)
    main_assessment = fields.Boolean(compute='_test_main_assessment', store=True)
    can_edit = fields.Boolean(compute='_test_main_assessment', store=True)
    to_be = fields.Boolean(default=False)
    attachment_ids = fields.One2many('odoocms.assessment.line.attachment', 'assessment_line_id', string='Attachment')
    result = fields.Boolean('Included', default=True)
    company_id = fields.Many2one('res.company', string='Company', related='assessment_id.company_id', store=True)

    _sql_constraints = [
        ('unique_assessment', 'unique(assessment_id,student_id)', "Record already exist"),
    ]
    
    def cron_get_summary(self, limit=1000):
        recs = self.search([('to_be','=',True)], limit=limit)
        for rec in recs:
            rec._get_summary_id()
        recs.to_be = False

    @api.depends('obtained_marks')
    def _get_summary_id(self):
        for rec in self:
            if rec.main_assessment:
                summary_rec = self.env['odoocms.assessment.summary'].search(
                    [('class_id', '=', rec.class_id.id), ('student_id', '=', rec.student_id.id),
                     ('assessment_component_id', '=', rec.assessment_component_id.id)])

                if not summary_rec:
                    summary_vals = {
                        'class_id': rec.class_id.id ,
                        'student_id': rec.student_id.id,
                        'assessment_component_id': rec.assessment_component_id.id,
                    }
                    summary_rec = self.env['odoocms.assessment.summary'].create(summary_vals)
                rec.summary_id = summary_rec.id
            else:
                rec.summary_id = False
    
    @api.depends('assessment_id','assessment_id.parent_id','weightage')
    def _test_main_assessment(self):
        for rec in self:
            if rec.assessment_id.parent_id:
                rec.main_assessment = False
                rec.can_edit = True
            else:
                rec.main_assessment = True
                if rec.assessment_id.child_ids:
                    rec.can_edit = False
                else:
                    rec.can_edit = True
        
    @api.depends('max_marks', 'obtained_marks')
    def _get_percentage(self):
        for rec in self:
            if rec.assessment_id and rec.can_edit and rec.obtained_marks > rec.max_marks:
                raise UserError('Obtained Marks cannot be greater than Assessment Max. Marks')
            rec.percentage = (rec.obtained_marks or 0) / (rec.max_marks or 1) * 100


class AssessmentLineAttachment(models.Model):
    _name = 'odoocms.assessment.line.attachment'
    _description = 'Assessment Line Attachment'

    attachment = fields.Binary('Attachment', attachment=True)
    file_name = fields.Char('File Name')
    assessment_line_id = fields.Many2one('odoocms.assessment.line', string='Assessment Line')
    submission_date = fields.Datetime('Submission Date', default=fields.Datetime.now())


class OdooCMSAssessmentSummary(models.Model):
    _name = 'odoocms.assessment.summary'
    _description = 'Assessment Summary'
    _rec_name = 'assessment_component_id'

    class_id = fields.Many2one('odoocms.class', string='Class')
    # scheme_line_id = fields.Many2one('odoocms.study.scheme.line','Course Offer',related='class_id.study_scheme_line_id',store=True)
    # course_id = fields.Many2one('odoocms.subject', 'Subject', related='scheme_line_id.course_id', store=True)
    term_id = fields.Many2one('odoocms.academic.term', string='Term', related='class_id.term_id', store=True)

    student_id = fields.Many2one('odoocms.student', string='Student')
    assessment_component_id = fields.Many2one('odoocms.assessment.component','Assessment Type')
    # final = fields.Boolean('Final',related='assessment_component_id.final',store=True)
    registration_component_id = fields.Many2one('odoocms.student.course.component','Student Course Component',compute='_get_student_course_component',store=True)

    percentage = fields.Float('Percentage', compute='_get_percentage', store=True)
    percentaged_marks = fields.Float('Percentaged Marks', compute='_get_percentage', store=True)    #added by Mazhar. Need cron job for previous results
    assessment_lines = fields.One2many('odoocms.assessment.line','summary_id','Assessment Lines',)
    # company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env['res.company']._company_default_get())
    to_be = fields.Boolean(default=False)

    percentage2 = fields.Float('Percentage2')
    percentaged_marks2 = fields.Float('Percentaged Marks2')  # added by Mazhar. Need cron job for previous results
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)

    @api.depends('class_id', 'student_id')
    def _get_student_course_component(self):
        for rec in self:
            if rec.student_id and rec.class_id:
                component_id = self.env['odoocms.student.course.component'].with_context(dict(active_test=True)).search([
                    ('student_id','=',rec.student_id.id),('class_id','=',rec.class_id.id)])
                rec.registration_component_id = component_id.id


    def cron_get_percentage2(self, limit=1000):
        recs = self.env['odoocms.assessment.summary'].search([('to_be','=',True)],limit=limit)
        for rec in recs:
            rec._get_percentage2()
            rec.to_be = False

    def _get_percentage2(self):
        for rec in self:
            percentage = cnt = weightage = 0
            for assessment in rec.assessment_lines.filtered(lambda l: l.main_assessment == True).sorted(key=lambda r: r.percentage, reverse=True):
                if assessment.weightage > 0:
                    assessment_weightage = assessment.weightage or 100
                    if rec.assessment_component_id.consideration_top:
                        assessment_weightage = 100

                    if rec.assessment_component_id.consideration_avg or (rec.assessment_component_id.consideration_top and cnt < rec.assessment_component_id.best):
                        percentage += (assessment.percentage * assessment_weightage / 100.0)
                        weightage += assessment_weightage
                        cnt += 1

            rec.percentage2 = percentage / (weightage or 1) * 100
            rec.percentaged_marks2 = rec.percentage2 * rec.assessment_component_id.weightage  # added by Mazhar. Need cron job for previous results

    @api.depends('assessment_lines', 'assessment_lines.percentage','assessment_lines.weightage','assessment_component_id.best')  #
    def _get_percentage(self):
        for rec in self:
            percentage = cnt = weightage = 0
            for assessment in rec.assessment_lines.filtered(lambda l: l.main_assessment == True).sorted(key=lambda r: r.percentage,reverse=True):
                if assessment.weightage > 0:
                    assessment_weightage = assessment.weightage or 100
                    if rec.assessment_component_id.consideration_top:
                        assessment_weightage = 100

                    if rec.assessment_component_id.consideration_avg or (rec.assessment_component_id.consideration_top and cnt < rec.assessment_component_id.best):
                        percentage += (assessment.percentage * assessment_weightage / 100.0)
                        weightage += assessment_weightage
                        assessment.result = True
                        cnt += 1
                    else:
                        assessment.result = False
                else:
                    assessment.result = False

            rec.percentage = percentage / (weightage or 1) * 100
            rec.percentaged_marks = rec.percentage * rec.assessment_component_id.weightage #added by Mazhar. Need cron job for previous results

    def cron_get_course_component(self, limit=100):
        recs = self.env['odoocms.assessment.summary'].search([('registration_component_id','=',False)],limit=limit)
        for rec in recs:
            rec._get_student_course_component()
            rec.to_be = False

    def cron_get_percentage(self, limit=100):
        recs = self.env['odoocms.assessment.summary'].search([('to_be','=',True)],limit=limit)
        for rec in recs:
            rec._get_percentage()
            rec.to_be = False


class OdooCMSDBS(models.Model):
    _name = "odoocms.dbs"
    _description = "Department/Center Board of Studies"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    
    def _get_waiting_domain(self):
        domain = [('state', 'in', ('draft','current','lock'))]
        return domain
    
    def _get_submitted_domain(self):
        domain = [('state', 'in', ('submit','disposal','approval','verify','done','notify'))]
        return domain
    
    name = fields.Char('Name',help='Number', copy=False, readonly=True)
    department_id = fields.Many2one('odoocms.department','Department/Center')
    career_id = fields.Many2one('odoocms.career','Career/Degree Level')
    term_id = fields.Many2one('odoocms.academic.term','Term')
    
    date = fields.Date()
    state = fields.Selection([('new','New'),('done','Done')],'Status',default='new')
    remarks = fields.Html('Minutes')
    grade_class_ids = fields.One2many('odoocms.class.grade','dbs_id','Submitted Result',
        domain = lambda self: self._get_submitted_domain())
    waiting_ids = fields.One2many('odoocms.class.grade', 'dbs_id', string='Waiting...',
        domain=lambda self: self._get_waiting_domain())
    completed = fields.Boolean('Completed',compute='_get_status',store=True)
    to_be = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.academic.dbs') or _('New')
        res = super().create(vals)
        return res
    
    @api.depends('grade_class_ids','grade_class_ids.dbs_action')
    def _get_status(self):
        for rec in self:
            if any([line.dbs_action == 'new' for line in rec.grade_class_ids]):
                rec.completed = False
            else:
                rec.completed = True

    def assign_dbs(self):
        for rec in self:
            if rec.state == 'new':
                grade_class_ids = self.env['odoocms.class.grade'].search(
                    [('department_id','=',rec.department_id.id),('career_id', '=', rec.career_id.id),('term_id', '=', rec.term_id.id),('dbs_id', '=', False)])
                for grade_class in grade_class_ids:
                    if grade_class.primary_class_ids:
                        grade_class.write({
                            'dbs_id': rec.id,
                            'dbs_action': 'new',
                        })
    
    def approve_all(self):
        for grade_class in self.grade_class_ids:
            if grade_class.state == 'submit':
                grade_class.dbs_approve()
        
            
    def lock(self):
        self.waiting_ids.write({
            'dbs_id': False,
            'dbs_action': False,
        })
        self.state = 'done'


class OdooCMSFBS(models.Model):
    _name = "odoocms.fbs"
    _description = "Faculty Board of Studies"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    def _get_waiting_domain(self):
        domain = [('state', 'in', ('draft', 'current', 'lock','submit', 'disposal'))]
        return domain

    def _get_submitted_domain(self):
        domain = [('state', 'in', ('approval', 'verify', 'done', 'notify'))]
        return domain
    
    name = fields.Char('Name', help='Number', copy=False, readonly=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute')
    career_id = fields.Many2one('odoocms.career', 'Career/Degree Level')
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    
    date = fields.Date()
    state = fields.Selection([('new', 'New'), ('done', 'Done')], 'Status', default='new')
    remarks = fields.Html('Minutes')
    grade_class_ids = fields.One2many('odoocms.class.grade', 'fbs_id', 'Submitted Result',
        domain=lambda self: self._get_submitted_domain())
    waiting_ids = fields.One2many('odoocms.class.grade', 'fbs_id', string='Waiting...',
        domain=lambda self: self._get_waiting_domain())
    completed = fields.Boolean('Completed', compute='_get_status', store=True)
    to_be = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.academic.fbs') or _('New')
        res = super().create(vals)
        return res
    
    @api.depends('grade_class_ids', 'grade_class_ids.fbs_action')
    def _get_status(self):
        for rec in self:
            if any([line.fbs_action == 'new' for line in rec.grade_class_ids]):
                rec.completed = False
            else:
                rec.completed = True
    
    def assign_fbs(self):
        for rec in self:
            if rec.state == 'new':
                grade_class_ids = self.env['odoocms.class.grade'].search([
                    ('institute_id', '=', rec.institute_id.id), ('career_id', '=', rec.career_id.id),
                    ('term_id', '=', rec.term_id.id), ('fbs_id', '=', False),
                    ('state','=','disposal')
                ])
                for grade_class in grade_class_ids:
                    grade_class.write({
                        'fbs_id': rec.id,
                        'fbs_action': 'new',
                    })
    
    def approve_all(self):
        for grade_class in self.grade_class_ids:
            if grade_class.state == 'approval':
                grade_class.fbs_approve()
                
    def lock(self):
        self.waiting_ids.write({
            'fbs_id': False,
            'fbs_action': False,
        })
        self.state = 'done'
        

