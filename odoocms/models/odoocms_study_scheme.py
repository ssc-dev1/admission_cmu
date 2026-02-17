import pdb
from odoo.osv import expression
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class OdooCMSSchemeLineTag(models.Model):
    _name = 'odoocms.scheme.line.tag'
    _description = 'Course Offer Tag'

    name = fields.Char(string='Name', required=True, help="Course Offer Tag")
    code = fields.Char(string="Code")
    sequence = fields.Integer(string='Sequence')
    color = fields.Integer('Color')
    
    
class OdooCMSStudyScheme(models.Model):
    _name = 'odoocms.study.scheme'
    _description = "CMS Study Scheme"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    name = fields.Char(string='Name', compute='_get_name_code', store=True)
    code = fields.Char(string="Code", compute='_get_name_code', store=True)
    
    sequence = fields.Integer('Sequence')
    scheme_date = fields.Date(string="Scheme Date")
    active = fields.Boolean('Active', default=True,
        help="If Unchecked, it will allow you to hide the Study Scheme without removing it.")
    credits = fields.Integer('Credit Hours',compute='_compute_credits',store=True)
    career_id = fields.Many2one("odoocms.career", string="Career/Degree Level", required=True, ondelete='restrict')
    
    session_id = fields.Many2one('odoocms.academic.session','Calendar Year', copy=False, ondelete='restrict')   # needs to remove
    program_id = fields.Many2one('odoocms.program','Program', required=True, ondelete='restrict')
    department_id = fields.Many2one('odoocms.department', 'Department', related='program_id.department_id', store=True)
    program_ids = fields.Many2many('odoocms.program','scheme_program_rel','scheme_id','program_id',string='Programs', copy=True)

    batch_ids = fields.One2many('odoocms.batch', 'study_scheme_id', 'Batches')
    batch_id = fields.Many2one('odoocms.batch','Batch',compute='_compute_batch',store=True)
    line_ids = fields.One2many('odoocms.study.scheme.line','study_scheme_id',string='Study Scheme', copy=True)
    stream_ids = fields.Many2many('odoocms.program.stream','scheme_stream_rel','scheme_id','stream_id',string='Streams', copy=True)
    scheme_type = fields.Selection([('regular', 'Regular'), ('special', 'Special'),('minor','Minor')], 'Scheme Type', default='regular')
    # import_identifier = fields.Many2one('ir.model.data', 'Import Identifier', compute='_get_import_identifier', store=True)
    can_sync = fields.Boolean('Can Sync', default=False)
    company_id = fields.Many2one('res.company', string='Company', related='program_id.company_id', store=True)

    _sql_constraints = [
        ('code', 'unique(code)', "Code already exists for another Study Scheme"),
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.depends('program_id', 'session_id')
    def _get_name_code(self):
        for rec in self:
            if rec.program_id and rec.session_id:
                ss_code = rec.program_id.code + '-' + rec.session_id.code
                ss_name = rec.program_id.name + '-' + rec.session_id.code
                rec.code = ss_code
                rec.name = ss_name

    @api.depends('batch_ids')
    def _compute_batch(self):
        for rec in self:
            rec.batch_id = rec.batch_ids and rec.batch_ids[0].id or False

    @api.onchange('career_id')
    def onchange_career(self):
        for rec in self:
            rec.program_id = False

    @api.depends('line_ids', 'line_ids.credits','line_ids.course_type')
    def _compute_credits(self):
        for rec in self:
            credits = 0
            for line in rec.line_ids.filtered(lambda l: l.course_type in ('compulsory','placeholder')):
                credits += line.credits
            rec.credits = credits

    def unlink(self):
        for rec in self:
            if rec.batch_ids:
                raise ValidationError(_("Study Scheme maps with Batches and can not be deleted, You only can Archive it."))
        super(OdooCMSStudyScheme, self).unlink()

    def cron_credits(self):
        for rec in self.search([]):
            rec._compute_credits()

    # @api.depends('code')
    # def _get_import_identifier(self):
    #     for rec in self:
    #         if rec.code and rec.id:
    #             name = 'SS-' + rec.code
    #             identifier = self.env['ir.model.data'].search(
    #                 [('model', '=', 'odoocms.study.scheme'), ('res_id', '=', rec.id)])
    #             if identifier:
    #                 identifier.module = self.env.company.identifier or 'AARSOL'
    #                 identifier.name = name
    #             else:
    #                 data = {
    #                     'name': name,
    #                     'module': self.env.company.identifier or 'AARSOL',
    #                     'model': 'odoocms.study.scheme',
    #                     'res_id': rec.id,
    #                 }
    #                 identifier = self.env['ir.model.data'].create(data)
    #             rec.import_identifier = identifier.id
            
    
class OdooCMSStudySchemeLine(models.Model):
    _name = 'odoocms.study.scheme.line'
    _description = 'CMS Study Course Offer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'semester_number'
    _rec_name = 'course_id'

    study_scheme_id = fields.Many2one('odoocms.study.scheme', string="Study Scheme", ondelete='cascade')
    scheme_type = fields.Selection(related='study_scheme_id.scheme_type',store=True)
    career_id = fields.Many2one('odoocms.career','Career/Degree Level',related='study_scheme_id.career_id',store=True)
    program_id = fields.Many2one('odoocms.program','Program', related='study_scheme_id.program_id', store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='study_scheme_id.batch_id', store=True)

    semester_id = fields.Many2one('odoocms.semester', string="Semester", tracking=True, ondelete='restrict')
    semester_number = fields.Integer(related='semester_id.number',store=True)
    course_type = fields.Selection([
        ('compulsory','Core Course'),
        ('elective','Elective'),
        ('gen_elective', 'General Elective'),
        ('specialization','Specialization'),
        ('placeholder','Elective Placeholder')
    ], 'Course Type',default='compulsory', tracking=True)
    tag_ids = fields.Many2many('odoocms.scheme.line.tag', 'scheme_line_tag_rel','scheme_line_id','tag_id','Tags', tracking=True)
    
    term_id = fields.Many2one('odoocms.academic.term',string="Term", copy=False,tracking=True, ondelete='cascade')
    course_id = fields.Many2one('odoocms.course',string='Course', tracking=True, ondelete='restrict')
    specialization_id = fields.Many2one('odoocms.specialization','Specialization')
    
    course_code = fields.Char('Course Code', tracking=True)   # needs to remove
    course_name = fields.Char('Course Name', tracking=True)   # needs to remove
    
    major_course = fields.Boolean('Major Course')
    self_enrollment = fields.Boolean('Self Enrollment', default=False)
    auto_enrollment = fields.Boolean('Auto Enrollment', default=False)
    
    component_lines = fields.One2many('odoocms.study.scheme.line.component', 'scheme_line_id',
        compute='_compute_components',store=True, string='Course Components', readonly=False, copy=True)
    credits = fields.Float('Credit Hours',compute='_compute_credits',store=True)

    room_type = fields.Many2one('odoocms.room.type', 'Room Type')
    room_ids = fields.Many2many('odoocms.room', 'scheme_line_room_rel', 'scheme_line_id', 'room_id', 'Rooms', copy=True)
    
    # prereq_mode = fields.Selection([('basic','Basic'),('advanced','Advanced')],string='Pre-requisite Mode', compute='_compute_components',store=True, readonly=False)
    # prereq_operator = fields.Selection([('and','AND'),('or','OR')],'Prereq Operator',compute='_compute_components',store=True, readonly=False)
    # prereq_ids = fields.Many2many('odoocms.course','scheme_prereq_subject_rel','scheme_line_id','subject_id',
    #     compute='_compute_components',store=True, string='Prerequisite Courses',copy=False, readonly=False)


    prereqs = fields.One2many('odoocms.study.scheme.line.prereqs', 'scheme_line_id', string='Pre-Reqs', copy=False)

    prerequisite_ids = fields.One2many('odoocms.study.scheme.line.prerequisite', 'scheme_line_id', string='Pre-Requisites', tracking=True,
        compute='_compute_components',store=True, readonly=False, copy=True)
    prereq_text = fields.Char('Pre-Requirements', compute='_get_prereq_text')
    
    coreq_course0 = fields.Many2one('odoocms.course','CO-Req')
    coreq_course = fields.Many2one('odoocms.study.scheme.line','CO-Req Course', tracking=True,compute='_compute_components',store=True, readonly=False)
    req_earned_credits = fields.Integer('Required Earned Credits', default=0)
    req_cgpa = fields.Float('Required CGPA', default=0)
    compulsory_induction = fields.Boolean('Compulsory Induction', default=False)
    
    eq_course_id = fields.Many2one('odoocms.course', 'Equivalent Course', tracking=True)
    eq_course_ids = fields.Many2many('odoocms.course', 'scheme_line_eq_courses','scheme_line_id','course_id','Equivalent Courses', copy=True)

    category_id = fields.Many2one('odoocms.course.category', 'Category')
    sub_category_id = fields.Many2one('odoocms.course.sub.category', 'Sub Category')

    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one('res.company', string='Company', related='study_scheme_id.company_id', store=True)

    to_be = fields.Boolean()
    
    # import_identifier = fields.Many2one('ir.model.data', 'Import Identifier', compute='_get_imporodoocms.timetable.viewt_identifier', store=True)

    _sql_constraints = [
        ('unique_course', 'unique(study_scheme_id, course_id)', "Course already exists in Study Scheme!"), ]

    def name_get(self):
        res = []
        for record in self:
            name = record.course_id.name
            if record.course_id.code:
                name = record.course_id.code + ' - ' + name
            res.append((record.id, name))
        return res

    # def copy(self, default=None):
    #     self.ensure_one()
    #     default = dict(default or {},
    #                    contact_list_ids=self.contact_list_ids.ids)
    #     return super().copy(default=default)

    def copy(self, default=None):
        copy_default = {k: v for k, v in default.items() if k != 'component_lines'} if default else None
        res = super().copy(default=copy_default)  # This copies the report without its lines

        # lines_map = {}  # maps original lines to their copies (using ids)
        # for line in self.get_lines_in_hierarchy():
        #     copy = line.copy({'parent_id': lines_map.get(line.parent_id.id, None), 'report_id': copied_report.id})
        #     lines_map[line.id] = copy.id
        for line in self.component_lines:
            copy = line.copy({
                'scheme_line_id': res.id,
            })
        for line in self.prerequisite_ids:
            copy = line.copy({
                'scheme_line_id': res.id,
            })
        return res

    def _get_prereq_text(self):
        for rec in self:
            msg = []
            for prerequisite in rec.prerequisite_ids:
                msg1 = []
                for prereq in prerequisite.prerequisite_ids:
                    msg1.append(prereq.code)
                
                step_msg = ' AND '.join(map(str, msg1))
                msg.append(step_msg)
                
            final_msg = ' OR '.join(map(str, msg))
            rec.prereq_text = final_msg
            
    def component_hook(self,component_data):
        return component_data

    def cron_process(self, limit=100):
        recs = self.search([('to_be','=',True)], limit=limit)
        for scl in recs:
            # for prereq in scl.prereqs:
            #     data = {
            #         'scheme_line_id': scl.id,
            #         'prerequisite_ids': [(6, 0, prereq.mapped('prerequisite_ids').ids)],
            #     }
            #     self.env['odoocms.study.scheme.line.prerequisite'].create(data)
            if scl.coreq_course0:
                co_scl = self.search([('study_scheme_id','=',scl.study_scheme_id.id),('course_id','=',scl.coreq_course0.id)])
                if co_scl:
                    scl.coreq_course = co_scl.id
        recs.to_be = False
        
    def cron_shift(self):
        for scl in self.search([]):
            if scl.prereq_ids:
                if scl.prereq_operator == 'and':
                    data = {
                        'scheme_line_id': scl.id,
                        'prerequisite_ids': [(6, 0, scl.prereq_ids.ids)],
                        'effective_date': scl.prereq_ids[0].effective_date,
                    }
                    self.env['odoocms.study.scheme.line.prerequisite'].create(data)
                elif scl.prereq_operator == 'or':
                    for prereq in scl.prereq_ids:
                        data = {
                            'scheme_line_id': scl.id,
                            'prerequisite_ids': [(6, 0, prereq.ids)],
                            'effective_date': prereq.effective_date,
                        }
                        self.env['odoocms.study.scheme.line.prerequisite'].create(data)
                        
    def cron_components(self, limit=100):
        recs = self.search([('to_be','=',True)], limit=limit)
        for rec in recs:
            rec._compute_components()
            rec._compute_credits()
        recs.to_be = False
    
    @api.depends('component_lines','component_lines.weightage')
    def _compute_credits(self):
        for rec in self:
            credits = 0
            for component in rec.component_lines:
                credits += component.weightage
            rec.credits = credits

    @api.depends('course_id')
    def _compute_components(self):
        for rec in self:
            course = rec.course_id
            coreq_course = False
            components = [[5]]
            for component_line in course.component_lines:
                component_data = {
                    'component': component_line.component,
                    'weightage': component_line.weightage,
                    'contact_hours': component_line.contact_hours,
                }
                component_data = rec.component_hook(component_data)
                components.append((0, 0,component_data))
            
            if course.coreq_course:
                coreq_course = rec.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == course.coreq_course.id).id
                if "NewId" in str(coreq_course):
                    coreq_course = coreq_course.origin
                
            rec.write({
                'course_code': course.code,  # needs to remove
                'course_name': course.name,  # needs to remove
                'major_course': course.major_course,
                'self_enrollment': course.self_enrollment,
                'component_lines': components,
                'coreq_course': coreq_course,
            })

            if course.prereq_ids:
                if course.prereq_operator == 'and':
                    data = {
                        'scheme_line_id': rec.id,
                        'prerequisite_ids': [(6, 0, course.prereq_ids.mapped('prereq_id').ids)],
                        'effective_date': course.prereq_ids[0].effective_date,
                    }
                    self.env['odoocms.study.scheme.line.prerequisite'].create(data)
                elif course.prereq_operator == 'or':
                    for prereq in course.prereq_ids:
                        data = {
                            'scheme_line_id': rec.id,
                            'prerequisite_ids': [(6, 0, prereq.mapped('prereq_id').ids)],
                            'effective_date': prereq.effective_date,
                        }
                        self.env['odoocms.study.scheme.line.prerequisite'].create(data)

    # Remarked - due to Error
    @api.onchange('course_type')  # ,'tag_ids'
    def onchagene_course_type(self):
        place_holder = self.env.ref('odoocms.course_placeholder')
        if self.course_type == 'placeholder':
            sub_domain = [('tag_ids','in',place_holder.ids)]
        else:
            sub_domain = [('tag_ids','not in',place_holder.ids)]

        return {
            'domain': {
                'course_id': sub_domain
            },
            'value': {
                'course_id': False,
            }
        }
    
    @api.model
    def create(self, vals):
        if vals.get('elective', False):
            vals['semester_id'] = False
            
        semester = vals.get('semester_id', 10)
        sequence = (vals.get('sequence', 0)) % 100
        vals['sequence'] = semester * 100 + sequence
        return super().create(vals)
            
    def write(self, vals):
        for rec in self:
            if vals.get('elective',False):
                vals['semester_id'] = False
        
            semester = vals.get('semester_id',rec.semester_id.number) or 10
            sequence = (vals.get('sequence',rec.sequence) or 0) % 100
            vals['sequence'] = semester*100+sequence
        
        ret = super().write(vals)
        return ret
    
    def cron_credits(self):
        for rec in self.search([]):
            rec._compute_credits()
    
    #     # prereq = vals.get('prereq_course',False)
    #     # if prereq:
    #     #     self.course_id.prereq_course = True
    #     # else:
    #     #     scheme_subs = self.env['odoocms.study.scheme.line'].search([('course_id','=',self.course_id.id)])
    #     #     if scheme_subs and len(scheme_subs) == 1:
    #     #         self.course_id.prereq_course = False

    # @api.depends('study_scheme_id','study_scheme_id.code','course_code')
    # def _get_import_identifier(self):
    #     for rec in self:
    #         if rec.study_scheme_id and rec.study_scheme_id.code and rec.course_code and rec.id:
    #             if rec.course_type != 'placeholder':
    #                 name = (rec.study_scheme_id.import_identifier.name or ('SS-' + rec.study_scheme_id.code)) + '-' + rec.course_code
    #                 identifier = self.env['ir.model.data'].search(
    #                     [('model', '=', 'odoocms.study.scheme.line'), ('res_id', '=', rec.id)])
    #                 if identifier:
    #                     identifier.module = self.env.company.identifier or 'AARSOL'
    #                     identifier.name = name
    #                 else:
    #                     identifier = self.env['ir.model.data'].search(
    #                         [('model', '=', 'odoocms.study.scheme.line'), ('name', '=', name)])
    #                     if identifier:
    #                         continue
    #                         #name = name + '-1'
    #                     data = {
    #                         'name': name,
    #                         'module': self.env.company.identifier or 'AARSOL',
    #                         'model': 'odoocms.study.scheme.line',
    #                         'res_id': rec.id,
    #                     }
    #                     identifier = self.env['ir.model.data'].create(data)
    #                 rec.import_identifier = identifier.id


class OdooCMSStudySchemeLineComponent(models.Model):
    _name = 'odoocms.study.scheme.line.component'
    _description = 'CMS Course Offer Component'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    scheme_line_id = fields.Many2one('odoocms.study.scheme.line', ondelete='cascade')
    component = fields.Selection([
        ('lab', 'Lab'),
        ('lecture', 'Lecture'),
        ('studio', 'Studio'),
    ], string='Component', required=True)
    weightage = fields.Float(string='Credit Hours', default=3.0, help="Weightage for this Course", tracking=True)
    contact_hours = fields.Float(string='Contact Hours', default=1.0, help="Contact Hours for this Course", tracking=True)

    _sql_constraints = [
        ('unique_schemeline_component', 'unique(scheme_line_id,component)', "Component already exists in Study Course Offer"), ]

    def name_get(self):
        return [(rec.id, (rec.scheme_line_id.course_code or '') + '-' + (rec.scheme_line_id.course_name or '') + '-' + rec.component.title()) for rec in self]


class OdooCMSStudySchemeLinePreRequisite(models.Model):
    _name = 'odoocms.study.scheme.line.prerequisite'
    _description = 'CMS Study Course Offer Pre-Requisite'
    
    scheme_line_id = fields.Many2one('odoocms.study.scheme.line', string='Course')
    prerequisite_ids = fields.Many2many('odoocms.course', 'scheme_line_prerequisite_course_rel', 'scheme_line_id', 'course_id', string='Prerequisite Courses',copy=True)
    effective_date = fields.Date(string='Effective Date', help='Effective Date of Pre-Requisite')


class OdooCMSStudySchemeLinePreReqs(models.Model):
    _name = 'odoocms.study.scheme.line.prereqs'
    _description = 'CMS Study Course Offer Pre-Reqs'
    
    scheme_line_id = fields.Many2one('odoocms.study.scheme.line', string='Course')
    prerequisite_ids = fields.Many2many('odoocms.course', 'scheme_line_prereqs_course_rel', 'scheme_line_id', 'course_id', string='Prerequisite Courses')
