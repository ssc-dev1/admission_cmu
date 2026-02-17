from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from datetime import date
from ...cms_process.models import main as main
import pdb

READONLY_STATES = {
    'draft': [('readonly', False)],
    'current': [('readonly', True)],
    'lock': [('readonly', True)],
    'merge': [('readonly', True)],
    'submit': [('readonly', True)],
    'disposal': [('readonly', True)],
    'approval': [('readonly', True)],
    'notify': [('readonly', True)],
    'done': [('readonly', True)],
}


class OdooCMSTermScheme(models.Model):
    _name = 'odoocms.term.scheme'
    _description = 'Term Scheme'
    _order = 'term_id,sequence'

    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term', required=True)
    session_id = fields.Many2one('odoocms.academic.session','Calendar Year')
    semester_id = fields.Many2one('odoocms.semester', string="Semester", required=True)
    semester_number = fields.Integer('Semester Number',related='semester_id.number', store=True)
    term_number = fields.Integer('Term Number',related='term_id.number', store=True)
    state = fields.Selection([('draft','Draft'),('approve','Approved')],string='Status',default='draft')
    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('session_term_unique', 'unique(session_id, term_id)', "Term Scheme already exists in Academic Term"),
    ]

    def name_get(self):
        return [(rec.id, (rec.session_id.code or '') + '-' + (rec.term_id.code or '')) for rec in self]
        
    def approve_scheme(self):
        for rec in self:
            next_term = self.env['odoocms.academic.term'].search([
                ('type', '=', 'regular'), ('number', '>', rec.term_id.number),'|',('company_id','=',self.env.company.id),('company_id','=',False)])

            study_schemes = self.env['odoocms.study.scheme'].search([('session_id','=',rec.session_id.id),'|',('company_id','=',self.env.company.id),('company_id','=',False)])
            for study_scheme in study_schemes:
                for line in study_scheme.line_ids.filtered(lambda l: l.semester_id.id == rec.semester_id.id):
                    line.term_id = rec.term_id.id
                if len(next_term) <= 1:
                    for line in study_scheme.line_ids.filtered(lambda l: l.semester_id.number > rec.semester_id.number):
                        line.term_id = next_term or False
            self.state = 'approve'

    def reset_draft(self):
        for rec in self:
            self.state = 'draft'
            
    def unlink(self):
        for rec in self:
            if rec.state == 'approve':
                raise ValidationError(_("Approved Term Scheme can not be deleted."))
        super(OdooCMSTermScheme, self).unlink()


class OdooCMSStudentRegistrationLoad(models.Model):
    _name = 'odoocms.student.registration.load'
    _description = 'Registration Load'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'
    
    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    min = fields.Integer('Min Load')
    max = fields.Integer('Max Load')
    max_courses = fields.Integer('Max Courses')
    non = fields.Integer('Non-CR Load')
    repeat = fields.Integer('Repeat Load')
    type = fields.Selection([('regular','Regular Semester'),('summer','Summer Semester')])
    
    domain = fields.Char('Condition')
    
    tag_id = fields.Many2one('odoocms.student.tag','Tag',)
    student_id = fields.Many2one('odoocms.student','Student')
    program_id = fields.Many2one('odoocms.program','Program')
    batch_id = fields.Many2one('odoocms.batch','Batch')
    career_id = fields.Many2one('odoocms.career','Career/Degree Level')
    default_global = fields.Boolean('Global',default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('unique_rule', 'unique(default_global,career_id,batch_id,program_id,student_id)', "Rule already exists!"),
    ]
    
    # def write(self,vals):
    #     load = super().write(vals)
    #     global_load = self.env['odoocms.student.registration.load'].search([('default_global','=',True)])
    #     if len(global_load) > 1:
    #         raise UserError('')


class OdooCMSStudentTag(models.Model):
    _inherit = "odoocms.student.tag"

    registration_load_ids = fields.One2many('odoocms.student.registration.load', 'tag_id', 'Registration Load')
    
    
class OdooCMSCareer(models.Model):
    _inherit = "odoocms.career"

    registration_load_ids = fields.One2many('odoocms.student.registration.load', 'career_id', 'Registration Load')
    
    
class OdooCMSBatch(models.Model):
    _inherit = 'odoocms.batch'

    registration_load_ids = fields.One2many('odoocms.student.registration.load','batch_id','Registration Load')
   
    sections = fields.Integer('No. of Sections')
    section_ids = fields.One2many('odoocms.batch.section', 'batch_id', string='Sections')
    student_ids = fields.One2many('odoocms.student','batch_id','Students')
    tt_check = fields.Boolean('TT Check', default=False, help='Register only Classes with Timetable assigned.')
    ds_check = fields.Boolean('Date Sheet Check', default=False, help='Register only Classes with Date Sheet assigned.')
    allow_re_reg_wo_fee = fields.Boolean(string='Allow Course Re-Registration before Fee Submit', default = False)
    required_credit_hour = fields.Float('Required Credit Hours')

    sequence_id = fields.Many2one('ir.sequence', string='ID Sequence',
        help="This field contains the information related to the registration numbering of the Student.", copy=False)
    sequence_number_next = fields.Integer(string='Next Number',
        help='The next sequence number will be used for the next Student Registration in the Batch.',
        compute='_compute_seq_number_next', inverse='_inverse_seq_number_next')

    grade_class_ids = fields.One2many('odoocms.class.grade', 'batch_id', string='Grade Classes', compute='_compute_grade_class_ids')

    def _compute_grade_class_ids(self):
        for rec in self:
            grade_classes = self.env['odoocms.class.grade'].search([('batch_id','=',rec.id),('term_id','=',rec.term_id.id)])
            rec.grade_class_ids = grade_classes.ids or False
            
    # do not depend on 'sequence_id.date_range_ids', because
    # sequence_id._get_current_sequence() may invalidate it!
    @api.depends('sequence_id.use_date_range', 'sequence_id.number_next_actual')
    def _compute_seq_number_next(self):
        for batch in self:
            if batch.sequence_id:
                sequence = batch.sequence_id._get_current_sequence()
                batch.sequence_number_next = sequence.number_next_actual
            else:
                batch.sequence_number_next = 1

    def _inverse_seq_number_next(self):
        for batch in self:
            if batch.sequence_id and batch.sequence_number_next:
                sequence = batch.sequence_id._get_current_sequence()
                sequence.sudo().number_next = batch.sequence_number_next

    @api.model
    def _get_sequence_prefix(self, code):
        if self.code:
            prefix = code.upper()
            return prefix    # + '/%(range_year)s/'

    @api.model
    def _create_sequence(self, vals, refund=False):
        code = vals.get('code',False)
        if not code:
            code = self.code
        prefix = self._get_sequence_prefix(code)
        seq_name = code
        seq = {
            'name': _('%s Sequence') % seq_name,
            'implementation': 'no_gap',
            'prefix': prefix,
            'padding': 4,
            'number_increment': 1,
            #'use_date_range': True,
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        seq = self.env['ir.sequence'].create(seq)
        #seq_date_range = seq._get_current_sequence()
        #seq_date_range.number_next = refund and vals.get('refund_sequence_number_next', 1) or vals.get('sequence_number_next', 1)
        seq.number_next = vals.get('sequence_number_next', 1)
        return seq
    
    # @api.model
    # def create(self, vals):
    #     if not vals.get('sequence_id'):
    #         vals.update({'sequence_id': self.sudo()._create_sequence(vals).id})
    #     batch = super(OdooCMSBatch, self).create(vals)
    #     return batch
    #
    # def write(self, vals):
    #     res = super(OdooCMSBatch, self).write(vals)
    #     for batch in self:
    #         if not batch.sequence_id:
    #             batch.sequence_id = batch.sudo()._create_sequence(vals).id
    #     return res

    def unlink(self):
        for rec in self:
            if rec.section_ids:
                raise ValidationError(_("There are Sections mapped in this Batch, Batch can not be deleted; You can only Archive it."))
    
            if rec.student_ids:
                raise ValidationError(_("There are Students mapped in this Batch, Batch can not be deleted; You can only Archive it."))
        super(OdooCMSBatch, self).unlink()
    
    def component_hook(self,class_data, scheme_line):
        return class_data

    def batch_term_hook(self,batch_term_data):
        return batch_term_data
        

class OdooCMSBatchSection(models.Model):
    _name = "odoocms.batch.section"
    _description = "Batch Section"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'
    
    sequence = fields.Integer('Sequence')
    name = fields.Char(string='Section Name', required=True, size=1)
    code = fields.Char(string='Code', compute='_section_code',store=True)
    color = fields.Integer(string='Color Index')
    strength = fields.Integer('Max Strength',default=45)
    batch_id = fields.Many2one('odoocms.batch','Program Batch', ondelete='cascade')

    primary_class_ids = fields.One2many('odoocms.class.primary', 'batch_section_id', 'Primary Classes')
    student_ids = fields.One2many('odoocms.student', 'batch_section_id', string='Students')
    student_count = fields.Integer(string='Enrolled Students', compute='_get_student_count')
    room_id = fields.Many2one('odoocms.room','Room')
    to_be = fields.Boolean(default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    
    _sql_constraints = [
        ('section_unique', 'unique(batch_id,name)', "Unique Section name is required for a Batch"), ]

    @api.depends('batch_id','batch_id.code','name')
    def _section_code(self):
        for rec in self:
            if rec.batch_id and rec.name:
                rec.code = rec.batch_id.code + '-' + rec.name

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
    
    def _get_student_count(self):
        for rec in self:
            student_count = len(rec.student_ids)
            rec.update({
                'student_count': student_count
            })

    @api.constrains('strength')
    def validate_strength(self):
        for rec in self:
            if rec.strength < 0:
                raise ValidationError(_('Strength must be a Positive value'))

    def unlink(self):
        for rec in self:
            if rec.student_ids:
                raise ValidationError(_("There are Students mapped with this Section, Section can not be deleted; You can only Archive it."))
        super(OdooCMSBatchSection, self).unlink()


class OdooCMSClassGrade(models.Model):
    _name = "odoocms.class.grade"
    _description = "CMS Grading Class"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'
    
    sequence = fields.Integer('Sequence')
    name = fields.Char(string='Name', compute='_get_code', store=True)
    code = fields.Char(string="Code", compute='_get_code', store=True)

    term_id = fields.Many2one('odoocms.academic.term', 'Term', states=READONLY_STATES)
    course_id = fields.Many2one('odoocms.course', 'Catalogue Course', states=READONLY_STATES, ondelete='cascade')
    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', states=READONLY_STATES)
    career_id = fields.Many2one('odoocms.career', states=READONLY_STATES)
    program_id = fields.Many2one('odoocms.program', states=READONLY_STATES)
    department_id = fields.Many2one('odoocms.department', states=READONLY_STATES)
    institute_id = fields.Many2one('odoocms.institute', related='department_id.institute_id', store=True)
    study_scheme_id = fields.Many2one('odoocms.study.scheme', 'Study Scheme', states=READONLY_STATES)
    study_scheme_line_id = fields.Many2one('odoocms.study.scheme.line', 'Scheme Course', states=READONLY_STATES)

    batch_term_id = fields.Many2one('odoocms.batch.term','Batch Term', states=READONLY_STATES)
    primary_class_ids = fields.One2many('odoocms.class.primary','grade_class_id','Primary Classes', states=READONLY_STATES)
    grade_staff_id = fields.Many2one('odoocms.faculty.staff', string='Faculty for Grading', states=READONLY_STATES)
    registration_ids = fields.One2many('odoocms.student.course', 'grade_class_id', string='Students')
    student_count = fields.Integer(string='Enrolled Students', compute='_get_student_count',store=True)
    
    state = fields.Selection([
        ('draft', 'Draft'), ('current', 'Current'), ('lock', 'Locked'),
        ('submit', 'Submitted'), ('disposal', 'Disposal'), ('approval', 'Approval'),
        ('verify','Verify'),('done', 'Done'), ('notify','Notified')
    ], 'Status', default='draft', tracking=True)
    to_be = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    # _sql_constraints = [
    #     ('code', 'unique(code)', "Code already exists for another Grading Class"), ]

    @api.depends('batch_id', 'term_id', 'course_id', 'primary_class_ids.section_id')
    def _get_code(self):
        for rec in self:
            if rec.term_id and rec.course_id:
                class_code = rec.course_id.code
                class_name = rec.course_id.name
                if rec.term_id:
                    class_code = class_code + '-' + rec.term_id.short_code
                    class_name = class_name + '-' + rec.term_id.short_code
                if rec.batch_id:
                    # class_code = class_code + '-' + rec.batch_id.institute_id.code
                    class_code = class_code + '-' + rec.batch_id.code
                    class_name = class_name + '-' + rec.batch_id.code

                if rec.primary_class_ids and rec.primary_class_ids[0].section_id and rec.primary_class_ids[0].section_id.name:
                    class_code = class_code + '-' + rec.primary_class_ids[0].section_id.name
                    class_name = class_name + '-' + rec.primary_class_ids[0].section_id.name

                # class_name = class_code
            
                rec.code = class_code
                rec.name = class_name

    @api.depends('registration_ids')
    def _get_student_count(self):
        for rec in self:
            student_count = len(rec.registration_ids)
            rec.update({
                'student_count': student_count
            })

    def name_get(self):
        return [(rec.id, (rec.code or '') + '-' + rec.name) for rec in self]
    
    def unlink(self):
        for rec in self:
            if rec.primary_class_ids:
                raise ValidationError(_("There are Classes mapped with this Grading Class, it can not be deleted; You only can Archive it."))
        super(OdooCMSClassGrade, self).unlink()

    def lock_class(self):
        self.state = 'lock'
        self.primary_class_ids.state = 'lock'
        self.primary_class_ids.mapped('class_ids').state = 'lock'
        
    def unlock_class(self):
        self.state = 'current'
        self.primary_class_ids.state = 'current'
        self.primary_class_ids.mapped('class_ids').state = 'current'
    
    def final_grade_report(self):
        if self.primary_class_ids:
            class_id = self.primary_class_ids[0].class_ids[0].id
            return {
                'type': 'ir.actions.act_url',
                'url': f'/final/marks/report/download/{class_id}/',
                'target': 'new',
            }
    

class OdooCMSClassPrimary(models.Model):
    _name = 'odoocms.class.primary'
    _description = 'CMS Primary Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'ac_sem_seq, ac_ses_seq'

    def _selection_section_model(self):
        model_ids = self.env['ir.model'].search([('model', 'in', ('odoocms.batch.section','odoocms.batch.term.section'))])
        return [(model.model, model.name) for model in model_ids]

    name = fields.Char(string='Name', compute='_get_code', store=True)
    code = fields.Char(string="Code", compute='_get_code', store=True)
    description = fields.Text(string='Description')

    class_type = fields.Selection([
        ('regular', 'Regular'), ('elective', 'Elective'), ('special', 'Special'), ('summer', 'Summer'), ('winter', 'Winter')
    ], 'Class Type', default='regular', states=READONLY_STATES)

    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', states=READONLY_STATES)
    career_id = fields.Many2one('odoocms.career', 'Career/Degree Level', states=READONLY_STATES)
    program_id = fields.Many2one('odoocms.program', 'Program', related='batch_id.program_id', store=True)
    department_id = fields.Many2one('odoocms.department', "Department/Center", related='batch_id.department_id', store=True)
    institute_id = fields.Many2one("odoocms.institute", "Institute", related='department_id.institute_id', store=True, readonly=False)
    campus_id = fields.Many2one('odoocms.campus', 'Campus', related='institute_id.campus_id', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year')
    ac_ses_seq = fields.Integer('Session Seq.', related='session_id.sequence', store=True)

    grade_class_id = fields.Many2one('odoocms.class.grade', 'Grade Class', states=READONLY_STATES, ondelete='cascade')
    grade_staff_id = fields.Many2one('odoocms.faculty.staff', string='Faculty for Grading',
                                     compute='_get_grade_faculty', store=True, readonly=False)
    batch_term_id = fields.Many2one('odoocms.batch.term', 'Batch Term', related='grade_class_id.batch_term_id', store=True)

    # Have to remove these three
    batch_section_id = fields.Many2one('odoocms.batch.section', 'Batch Section')
    batch_term_section_id = fields.Many2one('odoocms.batch.term.section', 'Batch Term Section')
    section_name = fields.Char('Section Name')

    section_id = fields.Reference(selection='_selection_section_model', string="Section",
        compute="_compute_section", store=True, states=READONLY_STATES)

    allowed_batch_ids = fields.Many2many('odoocms.batch', 'primary_class_batch_rel', 'primary_class_id', 'batch_id', 'Allowed Batches')
    allowed_institute_ids = fields.Many2many('odoocms.institute', 'primary_class_institute_rel', 'primary_class_id', 'institute_id', 'Allowed Faculties')
    allowed_program_ids = fields.Many2many('odoocms.program', 'primary_class_program_rel', 'primary_class_id', 'program_id', 'Allowed Programs')

    course_id = fields.Many2one('odoocms.course', 'Catalogue Course', states=READONLY_STATES, ondelete='cascade')
    study_scheme_id = fields.Many2one('odoocms.study.scheme', 'Study Scheme', states=READONLY_STATES)
    study_scheme_line_id = fields.Many2one('odoocms.study.scheme.line', 'Course Offer', states=READONLY_STATES)
    
    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term', required=True, states=READONLY_STATES)
    ac_sem_seq = fields.Integer('Term Seq.', related='term_id.sequence', store=True)

    couple_class_id = fields.Many2one('odoocms.class.primary','Coupled Class')
    class_ids = fields.One2many('odoocms.class','primary_class_id','Classes', states=READONLY_STATES)

    strength = fields.Integer(string='Max. Class Strength', help="Total Max Strength of the Class")
    credits = fields.Float('Credit Hours',compute='_compute_credits',store=True, readonly=False)
    manual_credits = fields.Float('M Credit Hours',default=0.0)
    offer_for = fields.Selection([('new', 'New Students'), ('ongoing', 'On Going Students'), ('both', 'Both')], 'Offer For', default='both')
    own_section = fields.Boolean('Own Section Only', default=False)

    registration_request_ids = fields.One2many('odoocms.course.registration.line','primary_class_id','Registrations', domain=[('state','in',('draft','submit'))])
    registration_ids = fields.One2many('odoocms.student.course', 'primary_class_id', string='Students')
    student_count = fields.Integer(string='Confirmed Students', compute='_get_student_count',store=True)
    registration_count = fields.Integer('Registered Students', compute='get_registration_count',store=True)
    reserved = fields.Integer('Reserved')
    status = fields.Selection([('open','Open'),('close','Closed')], 'Reg. Status')
    course_code = fields.Char('Course Code', tracking=True)
    course_name = fields.Char('Course Name', tracking=True)
    major_course = fields.Boolean('Major Course')
    self_enrollment = fields.Boolean('Self Enrollment')
    generator_id = fields.Many2one('odoocms.class.generator','Generator')
    enroll_domain = fields.Char('Enrollment Domain', tracking=True)
    
    CourseID = fields.Char('CourseID')
    active = fields.Boolean('Active', default=True)
    
    state = fields.Selection([
        ('draft', 'Draft'), ('current', 'Current'), ('lock', 'Locked'),
        ('submit', 'Submitted'), ('disposal', 'Disposal'), ('approval', 'Approval'),
        ('verify', 'Verify'), ('done', 'Done'), ('notify', 'Notified')
    ], 'Status', default='draft', tracking=True)
    tt_html = fields.Html(string='Timetable.',compute='_get_tt_html')

    is_parent = fields.Boolean('Is Parent Class', default=False)
    parent_id = fields.Many2one('odoocms.class.primary','Parent Class')
    child_ids = fields.One2many('odoocms.class.primary','parent_id','Merged Classes')
    merge_cnt = fields.Integer(compute='_get_merge_cnt',store=True)

    to_be = fields.Boolean(default=False)
    
    finalize_weightage = fields.Boolean('Finalize Weightage',default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    # import_identifier = fields.Many2one('ir.model.data', 'Import Identifier', compute='_get_import_identifier', store=True)

    # _sql_constraints = [
    #     ('code_term', 'unique(code, active)', "Another Primary Class already exists with same Code!"), ]

    @api.depends('child_ids')
    def _get_merge_cnt(self):
        for rec in self:
            rec.merge_cnt = len(rec.child_ids)

    @api.depends('batch_section_id','batch_term_section_id')
    def _compute_section(self):
        for rec in self:
            if rec.batch_section_id:
                rec.section_id = '%s,%s' % ('odoocms.batch.section', rec.batch_section_id.id)
            elif rec.batch_term_section_id:
                rec.section_id = '%s,%s' % ('odoocms.batch.term.section', rec.batch_term_section_id.id)
            else:
                rec.section_id = False

    @api.onchange('section_id')
    def _return_section_domain(self):
        return {'domain': {'section_id': [('batch_id', '=', self.batch_id.id)]}}

    def cron_grade_classes(self, term=False, limit=100):
        if not term:
            current_term = self.env['odoocms.academic.term'].search([('current','=',True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='number desc', limit=1)
            term = current_term.id
        primary_classes = self.env['odoocms.class.primary'].search([('term_id','=',term),('grade_class_id','=',False)], limit=limit)
        for primary_class in primary_classes:
            if not primary_class.grade_class_id:
                SL = primary_class.study_scheme_line_id or None
                grade_method = False
                if primary_class.batch_id:
                    if primary_class.batch_id.grade_method_id:
                        grade_method = primary_class.batch_id.grade_method_id.id
                    else:
                        grade_method = primary_class.batch_id.program_id.grade_method_id and primary_class.batch_id.program_id.grade_method_id.id
                elif SL:
                    grade_method = SL.grade_method_id and SL.grade_method_id.id or False
                else:
                    grade_method = primary_class.program_id.grade_method_id and primary_class.program_id.grade_method_id.id or False
                grade_class_data = {
                    'name': primary_class.name,
                    'code': primary_class.code,
                    'batch_id': primary_class.batch_id.id,
                    'career_id': primary_class.career_id.id,
                    'program_id': primary_class.program_id.id,
                    'department_id': primary_class.department_id.id,
                    'term_id': primary_class.term_id.id,
                    'grade_method_id': grade_method,
                    'study_scheme_id': primary_class.batch_id.study_scheme_id.id or False,
                    'study_scheme_line_id': SL and SL.id or False,
                    'batch_term_id': primary_class.batch_term_section_id.batch_term_id.id or False,
                    'grade_staff_id': primary_class.grade_staff_id.id,
                }
                grade_class_id = self.env['odoocms.class.grade'].create(grade_class_data)
                primary_class.grade_class_id = grade_class_id.id
            primary_class.to_be = False

    def cron_component_classes(self, limit=100):
        primary_classes = self.env['odoocms.class.primary'].search([('to_be','=',True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=limit)
        for primary_class in primary_classes:
            class_data = {
                'primary_class_id': primary_class.id,
                'name': primary_class.name,
                'code': primary_class.code,
                'component': primary_class.course_id.component_lines[0].component,
                'weightage': primary_class.course_id.component_lines[0].weightage,
                'contact_hours': primary_class.course_id.component_lines[0].contact_hours,
                'batch_section_id': False,  # check section_name
                'batch_term_section_id': primary_class.section_id and primary_class.section_id.id or False,
                # 'assessment_template_id': assessment_template_id,
            }
            component_class_id = self.env['odoocms.class'].create(class_data)
            primary_class.to_be = False

    def cron_sections(self, limit=100):
        line_ids = self.env['odoocms.class.primary'].search([('to_be','=',True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=limit)
        for line in line_ids:
            batch = line.batch_id
            if batch:
                batch_term = self.env['odoocms.batch.term'].search(
                    [('batch_id', '=', batch.id), ('term_id', '=', line.term_id.id)])
                if not batch_term:
                    batch_term_data = {
                        'name': batch.code + '-' + line.term_id.code,
                        'code': batch.code + '-' + line.term_id.code,
                        'batch_id': batch.id,
                        'term_id': line.term_id.id,
                    }
                    batch_term_data = batch.batch_term_hook(batch_term_data)
                    batch_term = self.env['odoocms.batch.term'].create(batch_term_data)

                if line.section_id:
                    line.section_name = line.section_id.name
                # else:
                #     section_name = line.code[line.code.rfind('-') + len('-'):]

                # batch_term_section_id = self.env['odoocms.batch.term.section'].search(
                #     [('batch_term_id', '=', batch_term.id), ('name', '=', section_name)])
                # if not batch_term_section_id:
                #     data = {
                #         'name': section_name,
                #         'code': batch_term.code + '-' + section_name,
                #         # batch_term.batch_id.code + '-' + batch_section.name,
                #         'batch_term_id': batch_term.id,
                #     }
                #     batch_term_section_id = self.env['odoocms.batch.term.section'].create(data)
                #
                # line.batch_term_section_id = batch_term_section_id.id

            line.to_be = False

    def action_archive(self):
        for rec in self:
            if rec.grade_staff_id:
                raise UserError('Teacher: %s assigned to %s, you cannot archive it.' %(rec.grade_staff_id.name, rec.code))
            elif rec.class_ids:
                for component in rec.class_ids:
                    if component.faculty_staff_id:
                        raise UserError('Teacher: %s assigned to %s, you cannot archive Primary Class.' % (component.faculty_staff_id.name, component.code))
            elif rec.student_count:
                raise UserError('%s students have confirmed registration in %s, you cannot archive it.' % (rec.student_count, rec.code))
            elif rec.registration_count:
                raise UserError('%s students have registration requests in %s, you cannot archive it.' % (rec.student_count, rec.code))
            
            for component in rec.class_ids:
                component.active = False
                
        res = super().action_archive()
        
    def _get_tt_html(self):
        for rec in self:
            html = """<table><tr><td>Day</td><td>Room</td><td>Time</td></tr>"""
            for tt in rec.timetable_ids:
                for wday in tt.week_day_ids:
                    time_form = "%02d:%02d" % (divmod(tt.time_from * 60, 60))
                    time_to = "%02d:%02d" % (divmod(tt.time_to * 60, 60))
                    html += "<tr><td>"+wday.name+"</td><td>"+tt.room_id.name+"</td><td>"+time_form+"</td></tr>"
            html += "</table>"
            rec.tt_html = html
            
    @api.depends('registration_request_ids','registration_ids')
    def get_registration_count(self):
        for rec in self:
            # rec.registration_count = len(rec.registration_ids.mapped('student_id'))
            direct_reg = rec.registration_ids.mapped('student_id') - rec.registration_request_ids.mapped('student_id')
            rec.registration_count = len(rec.registration_request_ids) + len(direct_reg)
        
    @api.depends('batch_id','term_id','study_scheme_line_id','course_id','section_id')
    def _get_code(self):
        for rec in self:
            if rec.term_id and (rec.study_scheme_line_id or rec.course_id):
                class_code = rec.course_code or (rec.study_scheme_line_id and rec.study_scheme_line_id.course_code and rec.study_scheme_line_id.course_code or rec.course_id.code)
                if rec.term_id:
                    class_code = class_code + '-' + rec.term_id.short_code
                if rec.batch_id:
                    # class_code = class_code + '-' + rec.batch_id.institute_id.code
                    class_code = class_code + '-' + rec.batch_id.code
                
                if rec.section_id:
                    class_code = class_code + '-' + rec.section_id.name
                
                class_name = rec.course_name or (rec.study_scheme_line_id and rec.study_scheme_line_id.course_name and rec.study_scheme_line_id.course_name or rec.course_id.name)
                
                rec.code = class_code
                rec.name = class_name

    @api.depends('registration_ids')
    def _get_student_count(self):
        for rec in self:
            student_count = len(rec.registration_ids)
            rec.update({
                'student_count': student_count
            })

    def name_get(self):
        return [(rec.id, (rec.code or '') + '-' + (rec.name or '')) for rec in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
   
    @api.depends('class_ids', 'class_ids.weightage')
    def _compute_credits(self):
        for rec in self:
            credits = 0
            for component in rec.class_ids:
                credits += component.weightage
            rec.credits = rec.manual_credits if rec.manual_credits > 0 else credits
            
    def write(self, vals):
        for rec in self:
            if vals.get('section_id'):
                section_split = vals.get('section_id').split(',')
                if section_split[0] == 'odoocms.batch.term.section':
                    section_id = self.env['odoocms.batch.term.section'].browse(int(section_split[1]))
                    if section_id.batch_term_id.batch_id.id != rec.batch_id.id:
                        raise UserError("Batch of Class and Section does not Match.")
        return super().write(vals)

    @api.model
    def create(self, vals):
        res = super().create(vals)
        data = {}
        if not res.course_id:
            if res.CourseID:
                course_id = self.env['odoocms.course'].search([('CourseID', '=', res.CourseID)])
                if course_id:
                    data['course_id'] = course_id.id
                    if not res.course_code:
                        data['course_code'] = course_id.code
                        data['course_name'] = course_id.name

            elif res.study_scheme_line_id:
                course_id = res.study_scheme_line_id.course_id
                data['course_id'] = course_id.id
                if not res.course_code:
                    data['course_code'] = course_id.code
                    data['course_name'] = course_id.name
            
            elif res.course_code:
                course_id = self.env['odoocms.course'].search([('code','=',res.course_code),('career_id','=',res.career_id.id)])
                if course_id:
                    data['course_id'] = course_id.id
        elif not res.course_code:
            data['course_code'] = res.course_id.code
            data['course_name'] = res.course_id.name
            
        if data:
            res.write(data)
        return res

    @api.depends('class_ids', 'class_ids.faculty_staff_id', 'class_ids.sequence')
    def _get_grade_faculty(self):
        for rec in self:
            staff_id = rec.class_ids.sorted(key=lambda r: r.sequence)[:1]
            if staff_id:
                rec.grade_staff_id = staff_id.faculty_staff_id.id
                rec.grade_class_id.grade_staff_id = staff_id.faculty_staff_id.id

    def view_students(self):
        self.ensure_one()
    
        students_list = self.registration_ids.mapped('student_id')
        return {
            'domain': [('id', 'in', students_list.ids)],
            'name': _('Students'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'odoocms.student',
            'view_id': False,
            'context': {'default_primary_class_id': self.id},
            'type': 'ir.actions.act_window'
        }
    
    def unlink(self):
        for rec in self.sudo():
            if rec.registration_ids:
                raise ValidationError(_("Students are registered in the Primary Class, Class can not be deleted."))
        
            grade_class = rec.grade_class_id
            for component_class in rec.class_ids:
                component_class.unlink()

            #.with_context(dict(active_test=False))
            ctx = self.env.context.copy()
            ctx['active_test'] = False
            dropped_courses = self.env['odoocms.student.course'].sudo().with_context(ctx).search([
                ('primary_class_id', '=', rec.id), ('active', '=', False)])
            dropped_courses.sudo().unlink()
            
            super().unlink()
            grade_class.unlink()
            
    def set_to_draft(self):
        if self.state == 'current':
            self.state = 'draft'
            self.grade_class_id.state = 'draft'
            for rec in self:
                rec.class_ids.state = 'draft'

    def set_to_current(self):
        if self.state == 'draft':
            self.state = 'current'
            self.grade_class_id.state = 'current'
            for rec in self:
                rec.class_ids.state = 'draft'
            

class OdooCMSClassPrimaryCouple(models.Model):
    _name = 'odoocms.class.primary.couple'
    _description = "Couple Classes"
    
    sequence = fields.Integer('Sequence')
    term_id = fields.Many2one('odoocms.academic.term','Term', required=True)
    batch_id = fields.Many2one('odoocms.batch','Batch', required=True)
    course_id = fields.Many2one('odoocms.study.scheme.line','Course', required=True)
    couple_course_id = fields.Many2one('odoocms.study.scheme.line','Coupled Course', required=True)
    course_domain = fields.Many2many('odoocms.study.scheme.line', compute='_get_courses_domain')
    active = fields.Boolean('Active', default=True)
    state = fields.Selection([('draft','Draft'),('approve','Approved')],'Status')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('course_term_unique', 'unique(term_id, course_id)', "Duplicate Coupling"),
        ('couple_course_term_unique', 'unique(term_id, couple_course_id)', "Duplicate Coupled Course"),
    ]

    @api.depends('batch_id', 'term_id')
    def _get_courses_domain(self):
        for rec in self:
            rec.course_domain = False
            if rec.batch_id and rec.term_id:
                # All Core Course offered in same batch
                course_ids = self.env['odoocms.class.primary'].search([
                    ('term_id','=',rec.term_id.id),('batch_id','=',rec.batch_id.id)]).mapped('study_scheme_line_id')
                rec.course_domain = [(6, 0, course_ids.ids or [])]
    
    def _get_couple_section(self, primary_class_id):
        scl = primary_class_id.study_scheme_line
        course = self.env['odoocms.class.primary.couple'].search([('course_id','=',scl.id)])
        if course:
            couple_class = self.env['odoocms.class.primary'].search([
                ('study_scheme_line_id','=',course.couple_course_id.study_scheme_line.id), ('section_id','=', primary_class_id.section_id.name)
            ])
            return couple_class.id
        return False


class OdooCMSClass(models.Model):
    _name = 'odoocms.class'
    _description = 'CMS Class'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    def _selection_section_model(self):
        model_ids = self.env['ir.model'].search([('model', 'in', ('odoocms.batch.section','odoocms.batch.term.section'))])
        return [(model.model, model.name) for model in model_ids]

    name = fields.Char(string='Name', help="Class Name",states=READONLY_STATES, compute='_get_code', store=True)
    code = fields.Char(string="Code", help="Code",states=READONLY_STATES, compute='_get_code', store=True)
    description = fields.Text(string='Description')
    
    primary_class_id = fields.Many2one('odoocms.class.primary','Primary Class',states=READONLY_STATES, ondelete='cascade')
    course_id = fields.Many2one('odoocms.course', 'Catalogue Course', related='primary_class_id.course_id',store=True, ondelete='cascade')
    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term', related='primary_class_id.term_id',store=True)
    batch_section_id = fields.Many2one('odoocms.batch.section', 'Batch Section', states=READONLY_STATES)
    batch_term_section_id = fields.Many2one('odoocms.batch.term.section','Term Section')

    section_id = fields.Reference(related='primary_class_id.section_id', string="Section", store=True)
    section_name = fields.Char('Section Name')
    
    faculty_staff_id = fields.Many2one('odoocms.faculty.staff', string='Primary Faculty',compute='_get_primary_faculty',store=True)
    faculty_ids = fields.One2many('odoocms.class.faculty', 'class_id',string='Faculty Staff')
    allow_secondary_staff = fields.Boolean('Access to Secondary Staff',default=False)

    department_id = fields.Many2one('odoocms.department', 'Department', related='primary_class_id.department_id', store=True)
    program_id = fields.Many2one('odoocms.program', 'Program', related='primary_class_id.program_id', store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', related='primary_class_id.batch_id', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year', related='primary_class_id.session_id', store=True)
    career_id = fields.Many2one('odoocms.career', 'Career/Degree Level', related='primary_class_id.career_id', store=True)

    institute_id = fields.Many2one('odoocms.institute', 'Institute/Faculty', related='primary_class_id.institute_id', store=True)
    # campus_id = fields.Many2one('odoocms.campus', 'Campus', related='institute_id.campus_id', store=True)

    component = fields.Selection([
        ('lab', 'Lab'),
        ('lecture', 'Lecture'),
        ('studio', 'Studio'),
    ], string='Component', states=READONLY_STATES)
    weightage = fields.Float(string='Credit Hours', default=3.0, help="Weightage for this Course", states=READONLY_STATES, tracking=True)
    contact_hours = fields.Float(string='Contact Hours', default=1.0, help="Contact Hours for this Course", states=READONLY_STATES, tracking=True)

    building_id = fields.Many2one('odoocms.building', 'Building')
    floor_id = fields.Many2one('odoocms.building.floor', 'Floor')
    room_type = fields.Many2one('odoocms.room.type', 'Room Type')
    room_ids = fields.Many2many('odoocms.room', 'class_room_rel', 'class_id', 'room_id', 'Rooms')
    
    registration_component_ids = fields.One2many('odoocms.student.course.component', 'class_id', string='Students', domain=[('dropped','=',False)])
    student_count = fields.Integer(string='Enrolled Students', compute='_get_student_count')
    sequence = fields.Integer('Priority')
    active = fields.Boolean('Active',default=True)
    
    state = fields.Selection([
        ('draft', 'Draft'), ('current', 'Current'), ('lock', 'Locked'), ('merge','Merged'),
        ('submit', 'Submitted'), ('disposal', 'Disposal'), ('approval', 'Approval'),
        ('verify', 'Verify'), ('done', 'Done'), ('notify', 'Notified')
    ], 'Status', default='draft', tracking=True)
    merge_id = fields.Many2one('odoocms.class','Merge with')
    to_be = fields.Boolean(default=False)
    tracking_ids = fields.One2many('odoocms.class.faculty.tracking', 'class_id', 'Faculty Tracking')

    course_requirements = fields.Html('Course Requirements')
    course_objectives = fields.Html('Course Objectives')
    learning_outcome = fields.Html('Learning Outcome')
    methodology = fields.Html('Methodology')
    additional_info_ids = fields.One2many('odoocms.class.additional.info','class_id','Additional Course Information')
    suggested_book_ids = fields.One2many('odoocms.class.books','class_id','Course Books')
    break_ids = fields.One2many('odoocms.class.breakdown', 'class_id', 'Calendar of Activities')
    web_resource_ids = fields.One2many('odoocms.class.resource','class_id','Web Resources')
    news_ids = fields.One2many('odoocms.class.news','class_id','Course News')
    material_ids = fields.One2many('odoocms.class.material','class_id','Course Material')
    query_ids = fields.One2many('odoocms.class.query','class_id','Query')
    mail_notify_ids = fields.One2many('student.mail.notify','class_id','Mail Notify')

    week_cnt = fields.Integer('Week Count',compute='_compute_course_website')
    book_cnt = fields.Integer('Book Count',compute='_compute_course_website')
    webresource_cnt = fields.Integer('Web Resource Count',compute='_compute_course_website')
    special_edit = fields.Boolean('Edit after Notify', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    # _sql_constraints = [
    #     ('code', 'unique(code,active)', "Another Class already exists with same Code!"), ]

    # @api.depends('batch_section_id', 'batch_term_section_id')
    # def _compute_section(self):
    #     for rec in self:
    #         if rec.batch_section_id:
    #             rec.section_id = '%s,%s' % ('odoocms.batch.section', rec.batch_section_id.id)
    #         elif rec.batch_term_section_id:
    #             rec.section_id = '%s,%s' % ('odoocms.batch.term.section', rec.batch_term_section_id.id)
    #         else:
    #             rec.section_id = False
    #

    def _compute_course_website(self):
        for rec in self:
            rec.week_cnt = len(rec.break_ids)
            rec.book_cnt = len(rec.suggested_book_ids)
            rec.webresource_cnt = len(rec.web_resource_ids)
            
    @api.depends('batch_id', 'term_id', 'course_id', 'section_id', 'component')  # ,'section_id.name'
    def _get_code(self):
        for rec in self:
            if rec.term_id and rec.course_id:
                class_code = rec.primary_class_id.course_code or rec.course_id.code
                if rec.term_id:
                    class_code = class_code + '-' + rec.term_id.short_code
                if rec.batch_id:
                    # class_code = class_code + '-' + rec.batch_id.institute_id.code
                    class_code = class_code + '-' + rec.batch_id.code
            
                if rec.section_id:
                    class_code = class_code + '-' + rec.section_id.name

                if len(rec.primary_class_id.class_ids) > 1:
                    class_code = class_code + '-' + rec.component.capitalize()
            
                class_name = rec.primary_class_id.course_name or rec.course_id.name
            
                rec.code = class_code
                rec.name = class_name
                
    def write(self, vals):
        removed_recs = self.env['odoocms.class.faculty']
        added_recs = self.env['odoocms.class.faculty']

        if len(vals) > 1 and vals.get('timetable_ids',False):
            del vals['timetable_ids']

        if vals.get('faculty_ids'):
            for faculty_rec in vals.get('faculty_ids'):
                if faculty_rec[0] == 0:
                    # [0, 'virtual_270', {'faculty_staff_id': 683, 'role_id': 2, 'active': True}]
                    fac_rec = faculty_rec[2]
                    data = {
                        'class_id': self.id,
                        'action': 'Added',
                        'action_by': self.env.user.id,
                        'faculty_staff_id': fac_rec['faculty_staff_id'],
                        'role_id': fac_rec.get('role_id',False),
                        'track_time': fields.Datetime.now(),
                    }
                    self.env['odoocms.class.faculty.tracking'].create(data)
                    register_ids = self.env['odoocms.class.attendance'].search([
                        ('class_id','=',self.id),('date_class','>=', date.today()),('state','=','draft')
                    ])
                    for register in register_ids:
                        register.faculty_id = fac_rec['faculty_staff_id']
                elif faculty_rec[0] == 1:
                    fac_rec = faculty_rec[2]
                    if fac_rec.get('faculty_staff_id',False):
                        data = {
                            'class_id': self.id,
                            'action': 'Added',
                            'action_by': self.env.user.id,
                            'faculty_staff_id': fac_rec['faculty_staff_id'],
                            'role_id': fac_rec.get('role_id',False),
                            'track_time': fields.Datetime.now(),
                        }
                        self.env['odoocms.class.faculty.tracking'].create(data)
                        register_ids = self.env['odoocms.class.attendance'].search([
                            ('class_id','=',self.id),('date_class','>=', date.today()),('state','=','draft')
                        ])
                        for register in register_ids:
                            register.faculty_id = fac_rec['faculty_staff_id']

                elif faculty_rec[0] == 2:
                    # {'faculty_ids': [[2, 31061, False]]}
                    rec_id = faculty_rec[1]
                    fac_rec = self.env['odoocms.class.faculty'].browse(rec_id)
                    class_id = fac_rec.class_id
                    faculty_staff_id = fac_rec.faculty_staff_id
                    if class_id.faculty_staff_id.id == faculty_staff_id.id:
                        vals['faculty_staff_id'] = False


            # updated_recs = self.env['odoocms.class.faculty'].search([('id', 'in', vals.get('faculty_ids')[0][2])])
            # added_recs = updated_recs - self.faculty_ids
            # removed_recs = self.faculty_ids - updated_recs
        result = super(OdooCMSClass, self).write(vals)
        # for added_rec in added_recs:
        #     data = {
        #         'class_id': self.id,
        #         'action': 'Added',
        #         'action_by': self.env.user.id,
        #         'faculty_staff_id': added_rec.faculty_staff_id.id,
        #         'roll_id': added_rec.roll_id.id,
        #         'track_time': fields.Datetime.now(),
        #     }
        #     self.env['odoocms.class.faculty.tracking'].create(data)
        # for removed_rec in removed_recs:
        #     data = {
        #         'class_id': self.id,
        #         'action': 'Removed',
        #         'action_by': self.env.user.id,
        #         'faculty_staff_id': removed_rec.faculty_staff_id.id,
        #         'roll_id': removed_rec.roll_id.id,
        #         'track_time': fields.Datetime.now(),
        #     }
        #     self.env['odoocms.class.faculty.tracking'].create(data)

        return result
    
    @api.constrains('weightage')
    def check_weightage(self):
        for rec in self:
            if rec.weightage < 0:
                raise ValidationError(_('Weightage must be Positive'))

    @api.depends('faculty_ids','faculty_ids.role_id')
    def _get_primary_faculty(self):
        for rec in self:
            staff_ids = rec.faculty_ids.filtered(lambda l: (l.role_id.code  or "").upper() == 'PRIMARY')
            for staff in staff_ids:
                rec.faculty_staff_id = staff.faculty_staff_id.id

    def action_marge_class(self):
        for reg in self.registration_component_ids:
            reg.class_id = self.merge_id.id
        self.state = 'merge'
        self.active = False
   
    # @api.onchange('study_scheme_line_id')
    # def onchagene_scheme_line(self):
    #     subject = self.study_scheme_line_id
    #     self.weightage = subject.weightage
    #     self.lecture = subject.lecture
    #     self.lab = subject.lab
    #     self.course_code = subject.course_code or subject.subject_id.code
    #     self.course_name = subject.course_name or subject.subject_id.name
    #

    def name_get(self):
        return [(rec.id, (rec.code or '') + '-' + rec.name) for rec in self]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
        
    def set_to_draft(self):
        if self.state == 'current':
            self.state = 'draft'
            self.primary_class_id.state = 'draft'
            self.primary_class_id.grade_class_id.state = 'draft'

    def set_to_current(self):
        if self.state == 'draft':
            self.state = 'current'
            self.primary_class_id.state = 'current'
            self.primary_class_id.grade_class_id.state = 'current'

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Class Section'),
            'template': '/odoocms_registration/static/xls/odoocms_class.xls'
        }]

    def view_students(self):
        self.ensure_one()
        
        students_list = self.registration_component_ids.mapped('student_id')
        return {
            'domain': [('id', 'in', students_list.ids)],
            'name': _('Students'),
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'odoocms.student',
            'view_id': False,
            'context': {'default_class_id': self.id},
            'type': 'ir.actions.act_window'
        }
    
    def _get_student_count(self):
        for rec in self:
            student_count = len(rec.registration_component_ids)
            rec.update({
                'student_count': student_count
            })

    def course_website_catalog(self):
        action=self.env.ref('odoocms_registration.complete_course_catalog_action').id
        menu = self.env.ref('odoocms_registration.course_website_report_menu').id
        return {
            'type': 'ir.actions.act_url',
            'target': 'new',
            'url': f"/web#menu_id={menu}&action={action}&model=odoocms.class&active_id={ self.id }",
        }


class OdooCMSClassFaculty(models.Model):
    _name = 'odoocms.class.faculty'
    _description = 'CMS Class Faculty'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_primary_role(self):
        role_id = self.env['odoocms.faculty.staff.position'].search(['|',('name','=','Primary'),('code','=','Primary')], limit=1)
        if role_id:
            return role_id.id

    class_id = fields.Many2one('odoocms.class','Component Class')
    term_id = fields.Many2one('odoocms.academic.term', related="class_id.term_id", string='Academic Term', store=True)
    credits = fields.Float('Credit Hours',related='class_id.weightage',store=True)
    student_count = fields.Integer('Student Count', related='class_id.student_count')
    faculty_staff_id = fields.Many2one('odoocms.faculty.staff','Faculty Member')
    role_id = fields.Many2one('odoocms.faculty.staff.position','Role', default=_get_primary_role)
    active = fields.Boolean(default=True)
    faculty_domain = fields.Many2many('odoocms.faculty.staff', compute='_get_faculty_domain', store=False)
    
    @api.depends('class_id')
    def _get_faculty_domain(self):
        self.faculty_domain = False
        if self.class_id:
            available_teachers = self.class_id.course_id.faculty_staff_ids

            course_tags = self.class_id.course_id.tag_ids.ids
            domain = [('state','in',('active','notice_period')),('course_tag_ids','in',course_tags),'|',('company_id','=',self.env.company.id),('company_id','=',False)]
            faculty_tags = self.env['odoocms.faculty.staff'].search(domain)
            self.faculty_domain = [(6, 0, (available_teachers.ids + faculty_tags.ids) or [])]

    def write(self, vals):
        res = super().write(vals)
        if vals.get('faculty_staff_id',False):
            teacher_id = self.faculty_staff_id
            class_tt_ids = self.env['odoocms.timetable.schedule'].search([('class_id','=',self.class_id.id)])
            for class_tt in class_tt_ids:
                class_tt.faculty_id = teacher_id.id
            class_tt_ids.check_teacher()
        return res


class ClassFacultyTracking(models.Model):
    _name = 'odoocms.class.faculty.tracking'
    _description = 'Class Faculty Tracking'

    class_id = fields.Many2one('odoocms.class', 'Class',required=True)
    action = fields.Char('Action',required=True)
    action_by = fields.Many2one('res.users', 'Action By',required=True)
    faculty_staff_id = fields.Many2one('odoocms.faculty.staff', 'Faculty Member',required=True)
    role_id = fields.Many2one('odoocms.faculty.staff.position', 'Role')
    track_time = fields.Datetime('Track Time')
    

class OdooCMSClassMaterial(models.Model):
    _name = 'odoocms.class.material'
    _description = 'Course Material'

    class_id = fields.Many2one('odoocms.class', string='Class')
    material_file = fields.Binary('Material File')
    file_name = fields.Char('File Name')
    description = fields.Html('Description')
    

class OdooCMSLabIP(models.Model):
    _name='odoocms.lab.ip'
    _description = 'Lab IP Info'

    name = fields.Char('name')
    lab_id = fields.Many2one('odoocms.lab','Lab')
    company_id = fields.Many2one('res.company', string='Company', related='lab_id.company_id', store=True)
    
    
class OdooCMSLab(models.Model):
    _name='odoocms.lab'
    _description = 'Lab Info'

    sequence = fields.Integer('Sequence')
    name = fields.Char('name')
    ip_ids = fields.One2many('odoocms.lab.ip','lab_id','IP Addresses')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSClassQuery(models.Model):
    _name = 'odoocms.class.query'
    _description = 'Course Queries'
    
    class_id = fields.Many2one('odoocms.class', string='Class/Section')
    student_id = fields.Many2one('odoocms.student', 'Student')
    subject = fields.Char('Subject')
    question = fields.Html('Question')
    date_question = fields.Datetime('Question Time')
    answer = fields.Html('Answer')
    date_answer = fields.Datetime('Answer Time')
    answered = fields.Boolean('Answered', default=False)
    answer_read = fields.Boolean('Answer Read', default=False)
    read = fields.Boolean(string='Read', default=False)
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)

    
class OdooCMSClassAdditionalInfo(models.Model):
    _name = 'odoocms.class.additional.info'
    _description = 'Class Additional Info'
    
    class_id = fields.Many2one('odoocms.class','Class')
    subject = fields.Char('Subject', required=True)
    description = fields.Html('Description')
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)

    
class StudentMailNotify(models.Model):
    _name = 'student.mail.notify'
    _description = 'Email Notify'
    
    class_id = fields.Many2one('odoocms.class','Class')
    subject = fields.Char('Subject', required=True)
    body = fields.Html('Body',required=True)


class OdooCMSClassBooks(models.Model):
    _name = 'odoocms.class.books'
    _description = 'Course Books'

    class_id = fields.Many2one('odoocms.class', 'Class')
    book_type = fields.Selection([('text','Text Book'),('reference','Reference Book')], 'Book Type')
    title = fields.Char('Title', required=True)
    authors = fields.Char('Authors')
    edition = fields.Char('Edition')
    publisher = fields.Char('Publisher')
    year = fields.Char('Year')
    description = fields.Html('Description')
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)


class OdooCMSClassBreakdownAttachment(models.Model):
    _name = 'odoocms.class.breakdown.attachment'
    _description = 'Breakdown Attachment'
    
    breakdown_id = fields.Many2one('odoocms.class.breakdown', string='Breakdown')
    name = fields.Char('File Name')  # , ,compute='_get_file_name',store=True   readonly=False
    attachment = fields.Binary('Attachment', attachment=True)
    
    # @api.depends('attachment')
    # def _get_file_name(self):
    #     for rec in self:
    #         if rec.attachment:
    #             rec.name = rec.attachment.datas_fname


class OdooCMSClassBreakdown(models.Model):
    _name = 'odoocms.class.breakdown'
    _description = 'Course Breakdown'
    
    class_id = fields.Many2one('odoocms.class', 'Class')
    name = fields.Char('Week Name')
    contents = fields.Html('Contents')
    assessment = fields.Char('Task/ Activities')
    attachment_ids = fields.One2many('odoocms.class.breakdown.attachment', 'breakdown_id', string='attachment')
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)


class OdooCMSClassResource(models.Model):
    _name = 'odoocms.class.resource'
    _description = 'Course Web Resource'

    class_id = fields.Many2one('odoocms.class', 'Class')
    url = fields.Char('URL')
    description = fields.Html('Description')
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)


class OdooCMSClassNews(models.Model):
    _name = 'odoocms.class.news'
    _description = 'Course News'
    
    class_id = fields.Many2one('odoocms.class', 'Class')
    subject = fields.Char('Subject', required=True)
    description = fields.Html('Description')
    attachment = fields.Binary('Attachment', attachment=True)
    attachment_filename = fields.Char('Attachment Filename')
    date = fields.Date('Date')
    date_expiry = fields.Date('Date Expiry')
    company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)

    
class OdooCMSStudySchemeLine(models.Model):
    _inherit = 'odoocms.study.scheme.line'
    
    primary_class_ids = fields.One2many('odoocms.class.primary','study_scheme_line_id','Primary Classes')

    def unlink(self):
        for rec in self:
            if rec.primary_class_ids:
                raise ValidationError(_("Course Offer maps with Primary Classes and can not be deleted, You only can Archive it."))
        super().unlink()
        

class OdooCMSCourse(models.Model):
    _inherit = 'odoocms.course'
    
    primary_class_ids = fields.One2many('odoocms.class.primary','course_id','Primary Classes')
    registration_ids = fields.One2many('odoocms.student.course','course_id','Registrations')

    def unlink(self):
        for rec in self:
            if rec.primary_class_ids:
                raise ValidationError(_("Course maps with Primary Classes and can not be deleted, You only can Archive it."))
        super().unlink()


class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'
    
    term_scheme_ids = fields.One2many('odoocms.term.scheme', 'term_id', 'Study Schemes')
    primary_class_ids = fields.One2many('odoocms.class.primary', 'term_id', 'Primary Classes')

    # scheme_lines = fields.One2many('odoocms.term.scheme', 'term_id', 'Study Schemes')
    state = fields.Selection([('draft', 'Draft'), ('approve', 'Approved')], string='Status', default='draft')

    def generate_scheme(self):
        session_ids = self.term_scheme_ids.mapped('session_id')
        for session in self.env['odoocms.academic.session'].search([('current_active','=',True),('id','not in', session_ids.ids),'|',('company_id','=',self.env.company.id),('company_id','=',False)]):
            domain = [('session_id','=',session.id),('term_number','<',self.number),'|',('company_id','=',self.env.company.id),('company_id','=',False)]
            term_rec = self.env['odoocms.term.scheme'].search(domain, order='semester_number desc',limit=1)
            if not term_rec:
                next_number = 1
            elif term_rec and term_rec.semester_number < 8:
                next_number = term_rec.semester_number + 1
            else:
                continue
            
            next_semester = self.env['odoocms.semester'].search([('number','=',next_number)])
            data = {
                'term_id': self.id,
                'session_id': session.id,
                'semester_id': next_semester.id
            }
            self.env['odoocms.term.scheme'].create(data)
            
    def approve_scheme(self):
        for rec in self.term_scheme_ids:
            rec.approve_scheme()
        self.state = 'approve'

    def reset_draft(self):
        for rec in self.term_scheme_ids:
            rec.reset_draft()
        self.state = 'draft'
        

class OdooCMSAcademicSession(models.Model):
    _inherit = 'odoocms.academic.session'
    
    term_scheme_ids = fields.One2many('odoocms.term.scheme', 'session_id', 'Study Scheme')
    batch_ids = fields.One2many('odoocms.batch', 'session_id', 'Batches')
    

class OdooCMSProgram(models.Model):
    _inherit = 'odoocms.program'

    registration_load_ids = fields.One2many('odoocms.student.registration.load', 'program_id', 'Registration Load')

    repeat_grades_allowed = fields.Char(string="Repeat Grades Allowed", help='Grades that are allowed as Repeat')
    repeat_grades_allowed_time = fields.Char(string="Repeat Time-Gap Allowed",
                                             help='No of Semesters Time-gap Allowed for course re-enrollment.')
    repeat_grades_allowed_max = fields.Char(string="Max Repeats Allowed",
                                            help='Max number of repeats allowed in Transcript')
    repeat_grades_allowed_no = fields.Char(string="Course Repeat Allowed (Max)",
                                           help='How many number of times a course can be re-registered.')

    deficient_course_in_summer = fields.Boolean(string="Deficient Course in Summer?")
    advance_course_in_summer = fields.Boolean(string="Advance Course in Summer (Compulsory)?")
    advance_course_in_summer_elective = fields.Boolean(string="Advance Course in Summer (Elective)?")

    registration_domain = fields.Char('Registration Domain for Core Course')
    elec_registration_domain = fields.Char('Registration Domain For Elective Courses')
    additional_registration_domain = fields.Char('Registration Domain For Additional Courses')
    minor_registration_domain = fields.Char('Registration Domain For Minor Courses')
    repeat_registration_domain = fields.Char('Registration Domain For Repeat Courses')
    
    
class OdooCMSStudent(models.Model):
    _inherit = 'odoocms.student'

    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', tracking=True, readonly=True,
        states={'draft': [('readonly', False)]})
    batch_section_id = fields.Many2one('odoocms.batch.section', 'Batch Section', tracking=True, readonly=True,
        states={'draft': [('readonly', False)]})
    
    
class OdooCMSBatchTerm(models.Model):
    _name = 'odoocms.batch.term'
    _description = "Batch Term"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name desc'

    def _get_waiting_domain(self):
        domain = [('state', 'in', ('draft','current','lock','submit'))]
        return domain
    
    name = fields.Char(string='Name', compute='_get_code', store=True)
    code = fields.Char(string="Code", compute='_get_code', store=True)
    
    sequence = fields.Integer('Sequence')
    color = fields.Integer(string='Color Index')
    batch_id = fields.Many2one('odoocms.batch','Batch')
    department_id = fields.Many2one('odoocms.department', string="Department/Center", related='batch_id.department_id', store=True)
    career_id = fields.Many2one('odoocms.career', string="Career/Degree Level", related='batch_id.career_id', store=True)
    program_id = fields.Many2one('odoocms.program', string="Program", related='batch_id.program_id', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year', related='batch_id.session_id')
    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term')

    grade_class_ids = fields.One2many('odoocms.class.grade', 'batch_term_id', string='Grade Classes')
    registration_ids = fields.One2many('odoocms.student.course', 'batch_term_id', string='Registrations')
    waiting_ids = fields.One2many('odoocms.student.course', 'batch_term_id', string='Waiting...',
        domain=lambda self: self._get_waiting_domain())
    
    state = fields.Selection([
        ('draft', 'Draft'), ('disposal', 'Disposal'), ('approval', 'Approval'),
        ('verify', 'Verify'), ('done', 'Done'), ('notify', 'Notify')
    ], 'Status', compute='get_status', store=True)
    section_ids = fields.One2many('odoocms.batch.term.section','batch_term_id','Sections')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('code', 'unique(code)', "Code already exists for some other Batch Term"),
    ]

    @api.depends('batch_id', 'term_id')
    def _get_code(self):
        for rec in self:
            if rec.term_id and rec.batch_id:
                name = rec.batch_id.code + '-' + rec.term_id.code
                rec.code = name
                rec.name = name

    @api.depends('grade_class_ids.state')
    def get_status(self):
        for rec in self:
            if any([line.state == 'notify' for line in rec.grade_class_ids]):
                rec.state = 'notify'
            elif any([line.state == 'done' for line in rec.grade_class_ids]):
                rec.state = 'done'
            elif any([line.state == 'verify' for line in rec.grade_class_ids]):
                rec.state = 'verify'
            elif any([line.state == 'approval' for line in rec.grade_class_ids]):
                rec.state = 'approval'
            elif any([line.state == 'disposal' for line in rec.grade_class_ids]):
                rec.state = 'disposal'
            else:
                rec.state = 'draft'


class OdooCMSBatchTermSection(models.Model):
    _name = "odoocms.batch.term.section"
    _description = "Batch Term Section"
    _order = 'sequence, name desc'
    
    name = fields.Char(string='Name', copy=False)
    code = fields.Char(string='Code', compute='_get_code',store=True)
    sequence = fields.Integer('Sequence')
    batch_term_id = fields.Many2one('odoocms.batch.term','Batch Term')
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='batch_term_id.batch_id',store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Current Term', related='batch_term_id.term_id',store=True)
    primary_class_ids = fields.One2many('odoocms.class.primary','batch_term_section_id','Primary Classes')
    company_id = fields.Many2one('res.company', string='Company', related='batch_term_id.company_id', store=True)

    _sql_constraints = [
        ('batch_term_section_unique', 'unique(term_id, batch_id, name)', "Same Section name already exist for Term and Batch"),
    ]

    @api.depends('name','batch_term_id','batch_term_id.code')
    def _get_code(self):
        for rec in self:
            if rec.name and rec.batch_term_id:
                rec.code = rec.batch_term_id.code + '-' + rec.name

    def write(self, vals):
        res = super().write(vals)
        if vals.get('name',False):
            for primary_class_id in self.primary_class_ids:
                primary_class_id._get_code()
                for class_id in primary_class_id.class_ids:
                    class_id._get_code()
                primary_class_id.grade_class_id._get_code()
        return res


class OdooCMSFacultyStaff(models.Model):
    _inherit = 'odoocms.faculty.staff'

    class_ids = fields.One2many('odoocms.class.faculty','faculty_staff_id','Classes')  # ,domain=lambda self: [('term_id', '=', self.term_id.id)]          , domain=[('term_id','=','term_id')]
    credits = fields.Float('Credit Load',compute='_compute_load_credits',store=True)
#     course_ids = fields.Many2many('odoocms.course','faculty_course_rel','faculty_id','course_id','Courses')
    term_id = fields.Many2one('odoocms.academic.term','Term')
#
    
    # @api.onchange('term_id')
    # def onchange_term_id(self):
    #     if self.term_id:
    #         return {'domain': {'class_ids': [('term_id', '=', self.term_id.id)]}}

    def cron_compute_load_credits(self, term=False):
        if term:
            term_id = self.env['odoocms.academic.term'].sudo().browse(term)
        else:
            term_id, term = main.get_current_term(self)

        recs = self.search(['|',('company_id','=',self.env.company.id),('company_id','=',False)])
        for rec in recs:
            if term_id and rec.term_id.id != term_id.id:
                rec.term_id = term_id.id
        recs._compute_load_credits()
                
    @api.depends('term_id', 'class_ids')
    def _compute_load_credits(self):
        extra_credit_over_strength = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.extra_credit_over_strength') or 1000)
        extra_two_credit_over_courses = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.extra_two_credit_over_courses') or 100)
        extra_one_credit_over_courses = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.extra_one_credit_over_courses') or 1000)
        
        for rec in self:
            credits = 0
            classes = rec.class_ids.filtered(lambda l: l.term_id.id == rec.term_id.id).mapped('class_id')
            for pclass in classes:
                credits += pclass.weightage
                if pclass.student_count > extra_credit_over_strength:
                    credits += 1
            courses = classes.mapped('course_id')
            if len(courses) > extra_two_credit_over_courses:
                credits += 2
            elif len(courses) > extra_one_credit_over_courses:
                credits += 1
            rec.credits = credits
        
    
