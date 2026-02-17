import pdb
from odoo.osv import expression
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)


class OdooCMSProgramStream(models.Model):
    _name = 'odoocms.program.stream'
    _description = 'Program Stream'
    
    name = fields.Char(string='Name', required=True, help="Stream Name")
    code = fields.Char(string="Code", required=True, help="Stream Code")
    
    
class OdooCMSCourseTag(models.Model):
    _name = 'odoocms.course.tag'
    _description = 'Course Tag'

    name = fields.Char(string='Name', required=True, help="Course Tag")
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string='Sequence')
    color = fields.Integer('Color')

    _sql_constraints = [
        ('code', 'unique(code)', "Another Tag already exists with this Code!"),
        ('name', 'unique(name)', "Another Tag already exists with this Name!"),
    ]


class OdooCMSCourseType(models.Model):
    _name = 'odoocms.course.type'
    _description = 'Course Type'
    
    name = fields.Char(string='Name', required=True, help="Subject Type Name")
    code = fields.Char(string="Code", required=True, help="Subject Type Code")
    type = fields.Selection([('compulsory', 'Core Course'), ('elective', 'Elective'),('project','Project')], 'Type', default='compulsory')
    stream = fields.Boolean('Concentration Stream')
    community = fields.Boolean('Community')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSCourse(models.Model):
    _name = 'odoocms.course'
    _description = 'CMS Course'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', help="Course Name", required=True, tracking=True)
    code = fields.Char(string="Code", help="Course Code", required=False, tracking=True)
    effective_date = fields.Date(string='Effective Date', help='Effective Date of Course', tracking=True)
    active = fields.Boolean('Active', default=True, help="Current Status of Course", tracking=True)
    description = fields.Text(string='Description', help="Description about the Course")
    formal_description = fields.Text(string='Formal Description', help="Formal Description about the Course")
    career_id = fields.Many2one('odoocms.career', 'Career/Degree Level', ondelete='restrict')
    no_offer = fields.Boolean('Non Offered Course', default=False, tracking=True)
    CourseID = fields.Char('CourseID')
    course_type_id = fields.Many2one('odoocms.course.type','Course Type', tracking=True)
    # type = fields.Selection([
    #     ('earned', 'Earned'),
    #     ('additional', 'Additional'),
    #     ('minor', 'Minor'),
    #     ('major', 'Major'),
    #     ('graded', 'Graded'),
    #     ('notgraded', 'NotGraded'),
    # ], string='Type', default="earned", help="Choose the type of the Course", tracking=True)

    coreq_course = fields.Many2one('odoocms.course', 'Co-Requisite', tracking=True)
    prereq_course = fields.Boolean('Is a Prerequisite Course', default=False, help="Prerequisite Course")

    prereq_mode = fields.Selection([('basic', 'Basic'), ('advanced', 'Advanced')], string='Pre-requisite Mode',default='basic')
    prereq_operator = fields.Selection([('and','AND'),('or','OR')],'Prereq Operator',default='and')
    prereq_ids = fields.One2many('odoocms.course.prereq', 'course_id', string='PreRequisits', tracking=True)
    
    prerequisite_ids = fields.One2many('odoocms.course.prerequisite', 'course_id', string='Pre-Requisites')
    equivalent_ids = fields.One2many('odoocms.course.equivalent', 'course_id', string='Equivalent Courses')
    component_lines = fields.One2many('odoocms.course.component', 'course_id', string='Course Components')
    credits = fields.Float('Credit Hours',compute='_compute_credits', store=True)

    program_ids = fields.One2many('odoocms.course.program', 'course_id', 'Programs')
    
    tag_ids = fields.Many2many('odoocms.course.tag', 'course_tag_rel','course_id','tag_id','Tags')
    
    outline = fields.Html('Outline')
    suggested_books = fields.Text('Suggested Books')
    stream_id = fields.Many2one('odoocms.program.stream', 'Stream', tracking=True)
    major_course = fields.Boolean('Major Course', default=False)
    self_enrollment = fields.Boolean('Self Enrollment', default=True)
    
    study_scheme_line_ids = fields.One2many('odoocms.study.scheme.line','course_id','Course Offers')
    faculty_staff_ids = fields.Many2many('odoocms.faculty.staff', 'faculty_course_rel', 'course_id','faculty_staff_id', string='Faculty Staff')

    can_delete_ft = fields.Boolean('Can delete from Transcript', default=False)
    project_registration = fields.Boolean('Register as Project', default=False)

    abbreviation = fields.Char('Abbreviation')
    special_course = fields.Boolean('Special Course', default=False)
    discount_allowed = fields.Boolean('Discount Allowed', default=True)
    credits_count = fields.Boolean('Credits Count?', default=True)
    fee = fields.Float('Course Fee')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    # code_prefix = fields.Many2one('odoocms.course.prefix', 'Prefix', required=True)
    # code_code = fields.Char('Code', required=True)
    # code = fields.Char(string="Course Code", compute='_get_course_code', store=True)

    # @api.depends('code_prefix', 'code_code')
    # def _get_course_code(self):
    #     for rec in self:
    #         if rec.code_prefix and rec.code_code:
    #             rec.code = rec.code_prefix.name + rec.code_code
    #         else:
    #             rec.code = 'New'

    def cron_shift(self):
        for course in self.search([]):
            if course.prereq_ids:
                if course.prereq_operator == 'and':
                    data = {
                        'course_id': course.id,
                        'prerequisite_ids': [(6, 0, course.prereq_ids.mapped('prereq_id').ids)],
                        'effective_date': course.prereq_ids[0].effective_date,
                    }
                    self.env['odoocms.course.prerequisite'].create(data)
                elif course.prereq_operator == 'or':
                    for prereq in course.prereq_ids:
                        data = {
                            'course_id': course.id,
                            'prerequisite_ids': [(6, 0, prereq.mapped('prereq_id').ids)],
                            'effective_date': prereq.effective_date,
                        }
                        self.env['odoocms.course.prerequisite'].create(data)
            
    # _sql_constraints = [
    #     ('code', 'unique(code)', "Another Course already exists with this Code!"), ]

    # @api.model
    # def create(self, vals):
    #     if vals.get('code', False):
    #         course = self.env['odoocms.course'].search([('code','=',vals.get('code'))])
    #         if course:
    #             raise ValidationError('Course with same Code already exist!')
    #     res = super().create(vals)
    #     return res

    # def write(self, vals):
    #     if vals.get('code', False):
    #         course = self.env['odoocms.course'].search([('id','!=',self.id),('code', '=', vals.get('code'))])
    #         if course:
    #             raise ValidationError('Course with same Code already exist!')
    #     res = super().write(vals)
    #     return res
    
    
        # if vals.get('state'):
        #     field_name_id = self.env['ir.model.fields'].search([('model','=',self._name),('name','=','state')])
        #     history_data = {
        #         'student_id': self.id,
        #         'field_name_id': field_name_id and field_name_id.id or False,
        #         'field_name': 'State',
        #         'changed_from': self.state,
        #         'changed_to': vals.get('state'),
        #         'changed_by': request.env.user.id,
        #         'date': datetime.now(),
        #     }
        #     self.env['odoocms.student.history'].create(history_data)
        #
        # if vals.get('tag_ids'):
        #     to_be_removed = self.env['odoocms.student.tag']
        #     updated_tags  = self.env['odoocms.student.tag'].search([('id','in',vals.get('tag_ids')[0][2])])
        #     added_tags =  updated_tags - self.tag_ids
        #     for added_tag in added_tags:
        #         if added_tag.category_id and not added_tag.category_id.multiple:
        #             if len(added_tags.filtered(lambda l: l.category_id == added_tag.category_id)) == 1:
        #                 to_be_removed += (updated_tags - added_tags).filtered(lambda l: l.category_id == added_tag.category_id)
        #             else:
        #                 raise UserError('The following tags can not be used simultaneously %s' % (', '.join([k.name for k in added_tags.filtered(lambda l: l.category_id == added_tag.category_id)])))
        #     updated_tags -= to_be_removed
        #     vals.get('tag_ids')[0][2] = updated_tags.ids
        #
        # method = 'Manual'
        # if vals.get('tag_apply_method'):
        #     method = vals.get('tag_apply_method')
        #     vals.pop('tag_apply_method')
        # old_tags = self.tag_ids.mapped('name')
        # res = super(OdooCMSStudent, self).write(vals)
        #
        # new_tags = self.tag_ids.mapped('name')
        # if vals.get('tag_ids'):  # old_tags != new_tags
        #     history_data = {
        #         'student_id': self.id,
        #         'field_name': 'Tags',
        #         'changed_from': old_tags,
        #         'changed_to': new_tags,
        #         'changed_by': request.env.user.id,
        #         'date': datetime.now(),
        #         'method': method,
        #     }
        #     self.env['odoocms.student.history'].create(history_data)
        #
        # return res
    
    
    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.code:
                name = record.code + ' - ' + name
            res.append((record.id, name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('name', operator, name), ('code', operator, name)]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.depends('component_lines','component_lines.weightage')
    def _compute_credits(self):
        for rec in self:
            credits = 0
            for component in rec.component_lines:
                credits += component.weightage
            rec.credits = credits

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Courses'),
            'template': '/odoocms/static/xls/odoocms_course.xls'
        }]
    

class OdooCMSCourseComponent(models.Model):
    _name = 'odoocms.course.component'
    _description = 'CMS Course Component'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    course_id = fields.Many2one('odoocms.course', ondelete='cascade')
    component = fields.Selection([
        ('lab', 'Lab'),
        ('lecture', 'Lecture'),
        ('studio', 'Studio'),
    ], string='Component',required=True)
    weightage = fields.Float(string='Credit Hours', default=3.0, help="Weightage for this Course", tracking=True)
    contact_hours = fields.Float(string='Contact Hours', default=1.0, help="Contact Hours for this Course", tracking=True)

    _sql_constraints = [
        ('unique_course_component', 'unique(course_id,component)', "Component already exists in Course"), ]
    
    @api.constrains('weightage')
    def check_weightage(self):
        for rec in self:
            if rec.weightage < 0:
                raise ValidationError(_('Weightage must be Positive'))
  
    
class OdooCMSCoursePreReq(models.Model):
    _name = 'odoocms.course.prereq'
    _description = 'CMS Course PreRequist'
    
    course_id = fields.Many2one('odoocms.course', string='Course')
    prereq_id = fields.Many2one('odoocms.course', string='PreRequist')
    effective_date = fields.Date(string='Effective Date', help='Effective Date of PreRequist')


class OdooCMSCoursePreRequisite(models.Model):
    _name = 'odoocms.course.prerequisite'
    _description = 'CMS Course Pre-Requisite'
    
    course_id = fields.Many2one('odoocms.course', string='Course', ondelete='restrict')
    prerequisite_ids = fields.Many2many('odoocms.course','subject_prerequisite_subject_rel','subject_id1','subject_id2',string='Prerequisite Courses')
    effective_date = fields.Date(string='Effective Date', help='Effective Date of Pre-Requisite')
    
    
class OdooCMSCourseEquivalent(models.Model):
    _name = 'odoocms.course.equivalent'
    _description = 'CMS Course Equivalent'
    _rec_name = 'course_id'
    
    course_id = fields.Many2one('odoocms.course', string='Course')
    equivalent_id = fields.Many2one('odoocms.course', string='Equivalent', ondelete='restrict')
    effective_date = fields.Date(string='Effective Date', help='Effective Date of Equivalent')
    

class OdooCMSCourseHistory(models.Model):
    _name = 'odoocms.course.history'
    _description = 'Course History'
    _order = 'course_id'
    _rec_name = 'course_id'

    course_id = fields.Many2one('odoocms.course', 'Course', required=True)
    field_name_id = fields.Many2one('ir.model.fields', 'Change In Attribute')
    field_name = fields.Char('Change In')
    changed_from = fields.Text('Changed From')
    changed_to = fields.Text('Changed To')
    changed_by = fields.Many2one('res.users', 'Changed By')
    date = fields.Datetime('Changed At')
    method = fields.Char('By Method')


class OdooCMSCourseCategory(models.Model):
    _name = 'odoocms.course.category'
    _description = 'Course Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, help="Category Name")
    code = fields.Char(string="Code", required=True, help="Category Code")
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    color = fields.Integer('Category Color')
    active = fields.Boolean('Active', default=True,
                            help="If Unchecked, it will allow you to hide the Course Category without removing it.")
    sub_category_ids = fields.One2many('odoocms.course.sub.category', 'category_id', 'Sub Categories')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('code', 'unique(code)', "Code already exists for another Course Category!"),
        ('name', 'unique(name)', "Name already exists for another Course Category!"),
    ]


class OdooCMSCourseSubCategory(models.Model):
    _name = 'odoocms.course.sub.category'
    _description = 'Course Sub Category'

    category_id = fields.Many2one('odoocms.course.category', 'Category')
    name = fields.Char(string='Name', required=True, help="Sub Category Name")
    code = fields.Char(string="Code", required=True, help="Sub Category Code")
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    color = fields.Integer('Sub Category Color')
    active = fields.Boolean('Active', default=True,
                            help="If Unchecked, it will allow you to hide the Course Sub Category without removing it.")
    company_id = fields.Many2one('res.company', string='Company', related='category_id.company_id', store=True)

    _sql_constraints = [
        ('code', 'unique(code)', "Code already exists for another Course Sub Category!"),
        ('name', 'unique(name)', "Name already exists for another Course Sub Category!"),
    ]

class OdooCMSCourseProgram(models.Model):
    _name = 'odoocms.course.program'
    _description = 'Course Program'

    course_id = fields.Many2one('odoocms.course', 'Course')
    program_id = fields.Many2one('odoocms.program', 'Program')
    category_id = fields.Many2one('odoocms.course.category', 'Category')
    sub_category_id = fields.Many2one('odoocms.course.sub.category', 'Sub Category')
    can_offer = fields.Boolean('Can Offer?')
    company_id = fields.Many2one('res.company', string='Company', related='category_id.company_id', store=True)

    _sql_constraints = [
        ('course_program', 'unique(company_id,program_id,course_id)', "A Course can be mapped once for a Program!"),
    ]


class OdooCMSProgramRequirement(models.Model):
    _name = 'odoocms.program.requirement'
    _description = 'Program Requirement'

    program_id = fields.Many2one('odoocms.program', 'Program')
    category_id = fields.Many2one('odoocms.course.category', 'Category')
    sub_category_id = fields.Many2one('odoocms.course.sub.category', 'Sub Category')
    credits = fields.Integer('Required Credits')
    mandatory = fields.Boolean('Mandatory?', default=True)

    _sql_constraints = [
        ('course_program_req', 'unique(program_id,category_id,sub_category_id)', "A Category can be mapped once for a Program!"),
    ]


class OdooCMSBatchRequirement(models.Model):
    _name = 'odoocms.batch.requirement'
    _description = 'Batch Requirement'

    batch_id = fields.Many2one('odoocms.batch', 'Batch')
    category_id = fields.Many2one('odoocms.course.category', 'Category')
    sub_category_id = fields.Many2one('odoocms.course.sub.category', 'Sub Category')
    credits = fields.Integer('Required Credits')
    mandatory = fields.Boolean('Mandatory?', default=True)

    _sql_constraints = [
        ('course_program_req', 'unique(program_id,category_id,sub_category_id)', "A Category can be mapped once for a Program!"),
    ]

# class OdooCMSCoursePrefix(models.Model):
#     _name = 'odoocms.course.prefix'
#     _description = 'Course Prefix'
#
#     name = fields.Char('Prefix')
#     sequence = fields.Integer()
#     active = fields.Boolean(default=True)
#     description = fields.Char('Description')
