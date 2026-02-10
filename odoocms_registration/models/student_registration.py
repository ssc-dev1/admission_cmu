import pdb
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import date
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
from datetime import datetime
from ...cms_process.models import main as main
import json
import inflect
import markupsafe
import logging

_logger = logging.getLogger(__name__)


class OdooCMSStudentCourse(models.Model):
    _name = 'odoocms.student.course'
    _description = "Student Course Details"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'registration_no'

    READONLY_STATES = {
        'current': [('readonly', True)],
        'submit': [('readonly', True)],
        'lock': [('readonly', True)],
        'disposal': [('readonly', True)],
        'approval': [('readonly', True)],
        'dropped': [('readonly', True)],
        'withdraw': [('readonly', True)],
        'done': [('readonly', True)],
    }

    student_id = fields.Many2one('odoocms.student', 'Student', ondelete="cascade")
    registration_no = fields.Char()  # related='student_id.code',store=True
    program_id = fields.Many2one('odoocms.program', 'Program', related='student_id.program_id', store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute', related='student_id.program_id.institute_id', store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='student_id.batch_id', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year',
                                 related='student_id.session_id', store=True)
    date_effective = fields.Date('Effective Date', default=fields.Date.today(), states=READONLY_STATES)
    date_start = fields.Date('Start Date')
    date_end = fields.Date('End Date')

    primary_class_id = fields.Many2one('odoocms.class.primary', 'Primary Class', ondelete="restrict")
    grade_class_id = fields.Many2one('odoocms.class.grade', 'Grade Class', related='primary_class_id.grade_class_id',
                                     store=True)
    batch_term_id = fields.Many2one('odoocms.batch.term', 'Batch Term', compute='_get_batch_term', store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    number = fields.Integer(related='term_id.number', store=True)

    student_term_id = fields.Many2one('odoocms.student.term', 'Student Term')

    course_id = fields.Many2one('odoocms.course', 'Catalogue Course')
    credits = fields.Float('Credit Hours', related='primary_class_id.credits', store=True, readonly=False)
    credit = fields.Float('Credit')

    course_code = fields.Char('Course Code', required=True, states=READONLY_STATES)
    course_name = fields.Char('Course Name', required=True, states=READONLY_STATES)
    CourseID = fields.Char('CourseID')
    component_ids = fields.One2many('odoocms.student.course.component', 'student_course_id', 'Components')
    course_type = fields.Selection([
        ('compulsory', 'Regular'),
        ('elective', 'Elective'),
        ('repeat', 'Repeat'),
        ('improve', 'Improve'),
        ('additional', 'Additional'),
        ('alternate', 'Alternate'),
        ('minor', 'Minor'),
        ('thesis', 'Thesis'),
        ('special', 'Special'),
    ], 'Course Type', default='compulsory')

    transferred = fields.Boolean('Transferred Course', default=False)
    dropped = fields.Boolean('Dropped', default=False)
    dropped_date = fields.Datetime('Dropped Date')
    is_defer = fields.Boolean(default=False)

    repeat_code = fields.Char("RPT Code")
    tscrpt__note254 = fields.Char('TSCRPT_NOTE254')

    inc_in_cgpa = fields.Char()

    course_id_1 = fields.Many2one('odoocms.student.course')
    course_id_2 = fields.Many2one('odoocms.student.course')

    tag = fields.Char('Tag', readonly=True)
    active = fields.Boolean('Active', default=True, tracking=True)
    to_process = fields.Boolean('To Process', default=True)

    state = fields.Selection([
        ('draft', 'Draft'), ('current', 'Current'), ('lock', 'Locked'), ('withdraw', 'Withdraw'),
        ('dropped', 'Dropped'),
        ('submit', 'Submitted'), ('disposal', 'Disposal'), ('approval', 'Approval'),
        ('verify', 'Verify'), ('done', 'Done'), ('notify', 'Notify')
    ], 'Status', compute='_get_course_state', store=True, readonly=False)
    withdraw_date = fields.Datetime('Withdraw Date')
    withdraw_reason = fields.Many2one('odoocms.drop.reason', 'Withdraw Reason')

    to_be = fields.Boolean(default=False)
    prereq = fields.Boolean('Pre-req Satisfy?', default=True)
    prereq_course_id = fields.Many2one('odoocms.course')
    remarks = fields.Char('Remarks')
    company_id = fields.Many2one('res.company', string='Company', related='program_id.company_id', store=True)

    _sql_constraints = [
        ('unique_student_term_course',
         'unique(student_id,term_id,course_id,active,dropped_date)',
         'Student can take a course once in an Academic Term!'),
    ]

    def write(self, vals):
        res = super().write(vals)
        if vals.get('to_process',False):
            for rec in self:
                rec.student_term_id.to_process = True
        return res

    def cron_missing_components(self, limit=1000, to_be=False):
        if to_be:
            recs = self.search([('to_be', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=limit)
        else:
            term = self.env['odoocms.academic.term'].search([('current','=',True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='number desc', limit=1)
            student_course_ids = self.env['odoocms.student.course.component'].search([('term_id','=', term.id)]).mapped('student_course_id')
            recs = self.env['odoocms.student.course'].search([('term_id','=', term.id)]) - student_course_ids

        for rec in recs:
            if not rec.component_ids:
                for component in rec.primary_class_id.class_ids:
                    component_data = {
                        'student_course_id': rec.id,
                        'student_id': rec.student_id.id,
                        'class_id': component.id,
                        'term_id': rec.term_id.id,
                        'weightage': component.weightage,
                    }
                    self.env['odoocms.student.course.component'].create(component_data)
            rec.to_be = False

    @api.depends('batch_id', 'term_id')
    def _get_batch_term(self):
        for rec in self:
            batch_term = False
            if rec.batch_id and rec.term_id:
                batch_term = self.env['odoocms.batch.term'].search(
                    [('batch_id', '=', rec.batch_id.id), ('term_id', '=', rec.batch_id.term_id.id)]
                )
            rec.batch_term_id = batch_term and batch_term.id or False

    @api.depends('primary_class_id', 'primary_class_id.state', 'dropped')
    def _get_course_state(self):
        for rec in self:
            if rec.state == 'notify':
                rec.state = 'notify'
            if rec.dropped:
                rec.state = 'done'
            elif rec.primary_class_id:
                rec.state = rec.sudo().primary_class_id.state
            else:
                rec.state = 'done'

    def name_get(self):
        return [(rec.id,
                 (rec.student_id.code or '') + '-' +
                 (rec.course_code or rec.primary_class_id.code or '') + '-' +
                 (rec.course_name or rec.primary_class_id.name or '')
                 )
                for rec in self
                ]
        # return [
        #     (rec.id,
        #         (rec.student_id.code or '') +
        #         ('-' + (rec.primary_class_id.code or '') + '-' + (rec.primary_class_id.name or ''))
        #             if rec.primary_class_id else (rec.student_id.code or '') +
        #                 ('-' + (rec.course_code or '') + '-' + (rec.course_name or ''))
        #      ) for rec in self.sudo()
        # ]

    @api.onchange('course_id')
    def onchagene_course(self):
        course = self.course_id
        self.credits = course.credits
        self.course_code = course.code
        self.course_name = course.name

    @api.model
    def create(self, vals):
        data = {}
        res = super().create(vals)
        term = res.term_id or res.primary_class_id.term_id

        if not res.term_id and res.primary_class_id:
            data['term_id'] = res.primary_class_id.term_id.id

        if not res.course_id:
            if res.primary_class_id:
                course_id = res.primary_class_id.course_id
                data['course_id'] = course_id.id
                if not res.course_code:
                    data['course_code'] = course_id.code
                    data['course_name'] = course_id.name
            elif res.CourseID:
                course_id = self.env['odoocms.course'].search([('CourseID', '=', res.CourseID)])
                if course_id:
                    data['course_id'] = course_id.id
                    if not res.course_code:
                        data['course_code'] = course_id.code
                        data['course_name'] = course_id.name
            elif res.course_code:
                course_id = self.env['odoocms.course'].search(
                    [('code', '=', res.course_code), ('career_id', '=', res.career_id.id)])
                if course_id:
                    data['course_id'] = course_id.id
        elif not res.course_code:
            data['course_code'] = res.course_id.code
            data['course_name'] = res.course_id.name

        st_term = res.student_id.get_student_term(term)
        # if res.course_type == 'thesis':
        #     term_data['number'] = 10000
        #     term_data['term_type'] = 'thesis'

        data['student_term_id'] = st_term.id
        res.write(data)
        return res

    def course_withdraw(self):
        view = self.env.ref('odoocms_registration.view_odoocms_student_course_withdraw_form')
        wiz = self.env['odoocms.student.course.withdraw'].create({
            'type': 'withdraw',
            'student_id': self.student_id.id,
            'withdraw_registration_ids': [(6, 0, [self.id])]
        })
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Withdraw'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'odoocms.student.course.withdraw',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': wiz.id,
            'context': self.env.context,
        }

    def course_reinstate(self):
        view = self.env.ref('odoocms_registration.view_odoocms_student_course_withdraw_form')
        wiz = self.env['odoocms.student.course.withdraw'].create({
            'type': 'reinstate',
            'student_id': self.student_id.id,
            'reinstate_registration_ids': [(6, 0, [self.id])]
        })
        # TDE FIXME: a return in a loop, what a good idea. Really.
        return {
            'name': _('Reinstate'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'odoocms.student.course.withdraw',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'current',
            'res_id': wiz.id,
            'context': self.env.context,
        }


class OdooCMSStudentCourseComponent(models.Model):
    _name = 'odoocms.student.course.component'
    _description = "Student Course Component Details"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    # _order = 'semester_date,student_id'

    student_course_id = fields.Many2one('odoocms.student.course', 'Student Course', ondelete="cascade", required=True)
    student_id = fields.Many2one('odoocms.student', 'Student', required=True)
    program_id = fields.Many2one('odoocms.program', 'Program', related='student_id.program_id', store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='student_id.batch_id', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year', related='student_id.session_id', store=True)

    class_id = fields.Many2one('odoocms.class', 'Class', ondelete="restrict", required=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', required=True)
    active = fields.Boolean('Active', default=True)

    weightage = fields.Float(string='Credit Hours', default=1.0, help="Credit Hours for this Course", required=True)

    dropped = fields.Boolean(related='student_course_id.dropped', store=True)
    to_be = fields.Boolean(default=False)

    # _sql_constraints = [
    #     ('unique_student_term_course',
    #      'unique(student_id,term_id,course_id)',
    #      'Student can take a course once in an Academic Term!'),
    # ]

    def name_get(self):
        return [(rec.id, (rec.student_id.code or '') + '-' + (rec.class_id.code or '') + '-' + rec.class_id.name or "-")
                for rec in self]

    # @api.onchange('course_id')
    # def onchagene_course(self):
    #     course = self.course_id
    #     self.credits = course.weightage


class OdooCMSCourseWithdraw(models.Model):
    _name = "odoocms.student.course.withdraw"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Student Course Withdraw"
    _order = 'name desc'

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'approve': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    def _get_term(self):
        term_id, term = main.get_current_term(self)
        return term

    type = fields.Selection([('withdraw', 'Withdraw'), ('reinstate', 'Reinstate')], default='withdraw', required=True,
                            states=READONLY_STATES)
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    student_id = fields.Many2one('odoocms.student', string="Student", tracking=True, states=READONLY_STATES, store=True)
    program_id = fields.Many2one(related='student_id.program_id', string='Academic Program', states=READONLY_STATES,
                                 store=True)
    batch_id = fields.Many2one(related='student_id.batch_id', string='Class Batch', states=READONLY_STATES, store=True)

    term_id = fields.Many2one('odoocms.academic.term', string='Academic Term', default=_get_term)
    registration_id = fields.Many2one('odoocms.student.course', string='Withdraw/Drop Course')
    withdraw_registration_ids = fields.Many2many('odoocms.student.course', 'rel_withdraw_registration', 'withdraw_id',
                                                 'registration_id', string='Withdraw Course(s)')
    reinstate_registration_ids = fields.Many2many('odoocms.student.course', 'rel_reinstate_registration',
                                                  'reinstate_id', 'registration_id', string='Reinstate Course(s)')

    description = fields.Text(string='Description', states=READONLY_STATES)
    reason_id = fields.Many2one('odoocms.drop.reason', string='Reason', states=READONLY_STATES)
    date_request = fields.Date('Request Date', default=date.today(), readonly=True)
    date_effective = fields.Date('Effective Date', default=date.today(), states=READONLY_STATES)
    date_approve = fields.Date(string='Approve Date', readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('approve', 'Approved'),
        ('cancel', 'Cancel')], default='draft', string="Status", tracking=True)
    company_id = fields.Many2one('res.company', string='Company', related='program_id.company_id', store=True)

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            if vals.get('type') == 'withdraw':
                vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.course.withdraw') or _('New')
            elif vals.get('type') == 'reinstate':
                vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.course.reinstate') or _('New')
            result = super().create(vals)
        return result

    def action_submit(self):
        for rec in self:
            rec.state = 'submit'

    def action_approve(self):
        for rec in self:
            if rec.state == 'submit':
                if rec.type == 'withdraw':
                    for registration_id in rec.withdraw_registration_ids:
                        registration_id.write({
                            'grade': 'W',
                            'state': 'withdraw',
                            'withdraw_date': fields.datetime.now(),
                            'withdraw_reason': rec.reason_id.id
                        })
                # for component in rec.registration_id.component_ids:
                # 	# rec.registration_id.remove_attendance(component, rec.date_effective)
                # 	component.active = False
                else:
                    for registration_id in rec.reinstate_registration_ids:
                        registration_id.write({
                            'grade': False,
                            'state': 'current',
                            'withdraw_date': False,
                            'withdraw_reason': False
                        })
                # for component in rec.registration_id.component_ids.with_context(active_test=False):
                # 	# rec.registration_id.remove_attendance(component, rec.date_effective)
                # 	component.active = True

                rec.state = 'approve'
                rec.date_approve = date.today()
            else:
                raise UserError('Request is not confirmed yet. Please Submit the request first!')

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'


class OdooCMSStudentTerm(models.Model):
    _name = 'odoocms.student.term'
    _description = "Student Term Details"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'semester_id'
    _order = 'number,student_id'

    student_id = fields.Many2one('odoocms.student', 'Student', ondelete="cascade")
    program_id = fields.Many2one('odoocms.program', 'Program', related='student_id.program_id', store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='student_id.batch_id', store=True)
    career_id = fields.Many2one('odoocms.career', 'Career/Degree Level', related='student_id.career_id', store=True)
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year', related='student_id.session_id', store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute', related='student_id.institute_id', store=True)

    term_line_id = fields.Many2one('odoocms.academic.term.line', 'Term Schedule', compute='get_term_line', store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    number = fields.Integer(related='term_id.number', store=True)
    term_type = fields.Selection([
        ('regular', 'Regular'),
        ('defer', 'Deferred'),
        ('extra', 'Extra'),
        ('thesis', 'Thesis'),
        ('summer', 'Summer'),
        ('exchange', 'Exchange Program'),
        ('internal', 'Internal Transfer'),
        ('external', 'External Transfer'),
    ], 'Term Type', default='regular')
    # semester_date = fields.Date(related='term_id.date_start', store=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('current', 'Current'),
        ('result', 'Result'),
        ('done', 'Notified'), ], 'Status',
        compute='_get_status', store=True, readonly=False)
    student_course_ids = fields.One2many('odoocms.student.course', 'student_term_id', 'Term Courses')

    to_process = fields.Boolean('To Process', default=True)
    to_be = fields.Boolean(default=False)
    # import_identifier = fields.Many2one('ir.model.data', 'Import Identifier')  # , compute='_get_import_identifier', store=True

    next_term = fields.Many2one('odoocms.student.term', 'Next Term')
    prev_term = fields.Many2one('odoocms.student.term', 'Prev Term')
    confirm = fields.Selection([('no', 'No'), ('system', 'System'), ('student', 'Student')], default='no')
    company_id = fields.Many2one('res.company', string='Company', related='program_id.company_id', store=True)

    _sql_constraints = [
        ('unique_student_term',
         'unique(student_id,term_id)',
         'Student can enroll once in an Academic Term!'),
    ]

    def name_get(self):
        return [(rec.id, (rec.student_id.code or '') + ':' + rec.student_id.name + '-' +
                 (rec.term_id.code or rec.term_id.short_code or rec.term_id.name)) for rec in self]

    def link_term(self, prev_term=None):
        for student_term in self:
            term_id = student_term.term_id
            if not prev_term:
                prev_term = self.env['odoocms.student.term'].search([('student_id', '=', student_term.student_id.id), ('number', '<', student_term.number)], order='number desc', limit=1)

            semester_id = self.env['odoocms.semester']
            if prev_term:
                prev_term.next_term = student_term.id
                if prev_term.semester_id:
                    if term_id.type == 'regular':
                        semester_id = self.env['odoocms.semester'].search([('number', '=', prev_term.semester_id.number + 1)])
                    else:
                        semester_id = prev_term.semester_id

            else:
                first_semester = self.env['odoocms.semester'].search([('number', '=', 1)])
                if first_semester:
                    semester_id = first_semester

            student_term.write({
                'prev_term': prev_term and prev_term.id or False,
                'semester_id': semester_id and semester_id.id or False
            })

    def update_student_term(self):
        for rec in self:
            last_term = self.env['odoocms.student.term'].search([('student_id', '=', rec.student_id.id)], order='number desc', limit=1)
            rec.student_id.write({
                'term_id': last_term.term_id.id,
                'semester_id': last_term.semester_id.id
            })

    @api.model
    def create(self, vals):
        res = super().create(vals)
        res.link_term()
        res.update_student_term()
        return res

    @api.depends('student_course_ids', 'student_course_ids.state')
    def _get_status(self):
        for rec in self:
            courses = rec.student_course_ids.filtered(lambda l: l.active == True)
            if len(courses) == 0 or any([course.state in ('draft', 'current', 'lock', 'submit') for course in courses]):
                rec.state = 'current'
            elif any([course.state in ('disposal', 'approval', 'verify','done') for course in courses]):
                rec.state = 'result'
            else:
                rec.state = 'done'

    def cron_remove_empty(self, n=2000):
        recs_count = self.search_count([('to_be', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)])
        terms = self.search([('to_be', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=n, order='student_id,number')
        for term in terms:
            if not term.student_course_ids:
                term.unlink()
            else:
                term.to_be = False

    @api.depends('term_id.term_lines', 'term_id.term_lines.date_start', 'term_id.term_lines.date_end')
    def get_term_line(self):
        for st_term in self:
            term_line = self.env['odoocms.academic.term.line']
            for rec in st_term.term_id.term_lines.sorted(key=lambda s: s.sequence, reverse=False):
                term_line = rec
                if rec.campus_ids and st_term.program_id.campus_id not in rec.campus_ids:
                    continue
                elif rec.institute_ids and st_term.program_id.department_id.institute_id not in rec.institute_ids:
                    continue
                elif rec.career_ids and st_term.career_id not in rec.career_ids:
                    continue
                elif rec.program_ids and st_term.program_id not in rec.program_ids:
                    continue
                elif rec.batch_ids and st_term.batch_id not in rec.batch_ids:
                    continue
                else:
                    break
            st_term.term_line_id = term_line and term_line.id or False

    @api.model
    def cron_get_status_job(self, n=500):
        terms = self.search([('to_be', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], limit=n)
        for term in terms:
            term._get_status()
            term.to_be = False


class OdooCMSStudent(models.Model):
    _inherit = 'odoocms.student'

    def _get_drop_domain(self):
        domain = [('term_id', '=', self.term_id.id), ('dropped', '=', True), '|', ('active', '=', True), ('active', '=', False)]
        return domain

    def _get_reg_request_domain(self):
        # ('term_id', '=', self.term_id.id),
        domain = ['|',('state', 'in', ('draft', 'submit')), ('action', '=', 'drop')]
        return domain

    # registration_allowed = fields.Boolean('Registration Allowed',default=True)  --  removed
    registration_no = fields.Char('Registration No.')
    batch_section_id = fields.Many2one('odoocms.batch.section', 'Batch Section', tracking=True, readonly=True,
                                       states={'draft': [('readonly', False)]})
    term_ids = fields.One2many('odoocms.student.term', 'student_id', 'Results (Term)', domain=[('state', '=', 'done')])
    last_term = fields.Many2one('odoocms.student.term', 'Last Term', compute='_get_last_term', store=True)
    enroll_term_ids = fields.One2many('odoocms.student.term', 'student_id', 'Enrolled Terms')
    current_term_ids = fields.One2many('odoocms.student.term', 'student_id', 'Terms', domain=[('state', 'in', ('draft', 'current'))])
    course_ids = fields.One2many('odoocms.student.course', 'student_id', 'Registered Courses', domain=[('state', 'not in', ('done', 'notify'))])
    dropped_course_ids = fields.One2many('odoocms.student.course', 'student_id', 'Dropped Courses',
                                         domain=lambda self: self._get_drop_domain(), context={'active_test': False})
    result_course_ids = fields.One2many('odoocms.student.course', 'student_id', 'Courses Result',
                                        domain=[('state', 'in', ('done', 'notify'))])
    enrolled_course_ids = fields.One2many('odoocms.student.course', 'student_id', 'Enrolled Courses', )
    allow_re_reg_wo_fee = fields.Boolean(string='Allow Course Re-Registration before Fee Submit', default=False)

    registration_load_ids = fields.One2many('odoocms.student.registration.load', 'student_id', 'Registration Load')
    improve_course_count = fields.Integer(string="No of Course Improved", compute='_get_improve_course_count')

    registration_request_ids = fields.One2many('odoocms.course.registration.line', 'student_id', 'Registration Request',
                                               domain=lambda self: self._get_reg_request_domain())
    unconfirmed_registration_request_ids = fields.One2many('odoocms.course.registration.line', 'student_id',
        'Unconfirmed Registration Request', domain=[('state', 'in', ('draft', 'submit')), ('student_course_id', '=', False)])

    deficient_course_in_summer = fields.Boolean(string="Deficient Course in Summer?")
    advance_course_in_summer = fields.Boolean(string="Advance Course in Summer (Compulsory)?")
    advance_course_in_summer_elective = fields.Boolean(string="Advance Course in Summer (Elective)?")

    @api.depends('term_ids', 'term_ids.state')
    def _get_last_term(self):
        for rec in self:
            if rec.term_ids:
                rec.last_term = rec.term_ids[-1:].id

    def get_student_term(self, term_id, create_missing=True):
        st_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', self.id), ('term_id', '=', term_id.id)])
        if not st_term and create_missing:
            data = {
                'student_id': self.id,
                'term_id': term_id.id,
                'term_type': term_id.type,
            }
            st_term = self.env['odoocms.student.term'].sudo().create(data)
        return st_term

    @api.depends('enrolled_course_ids', 'enrolled_course_ids.course_id_1', 'enrolled_course_ids.course_id_2')
    def _get_improve_course_count(self):
        repeat_grades = self.env['ir.config_parameter'].sudo().get_param('odoocms.failed_grades')
        repeat_course_ids = self.result_course_ids.filtered(
            lambda l: l.grade in repeat_grades.replace(' ', '').split(',')).mapped('course_id')

        for rec in self:
            rec.improve_course_count = len(
                rec.enrolled_course_ids.filtered(lambda c: c.course_id_1 and c.id in repeat_course_ids.ids))

    def register_courses(self, primary_class_ids, term_id, st_term, date_effective, type='compulsory'):
        reg = self.env['odoocms.student.course']
        alternate_id = course_id_1 = False

        for primary_class in primary_class_ids:
            course_id = primary_class.course_id

            new_registration = self.register_course(term_id, course_id, st_term, primary_class, date_effective)
            if new_registration.get('reg', False):
                new_reg = new_registration.get('reg')
                new_reg.course_type = type
                reg += new_reg

                if type in ('additional', 'minor'):
                    new_reg.include_in_cgpa = False

                elif type == 'alternate':
                    if alternate_id and alternate_id.type == 'grade':
                        course_id_1 = self.env['odoocms.student.course'].search([
                            ('course_id', '=', alternate_id.catalogue_id.id), ('student_id', '=', self.id)
                        ])
                else:
                    course_id_1 = self.env['odoocms.student.course'].search([
                        ('course_code', '=', primary_class.course_code), ('student_id', '=', self.id), ('id', '!=', new_reg.id)
                    ])  # , ('include_in_cgpa', '=', True)

                if course_id_1:
                    course_id_1[0].course_id_2 = new_reg
                    new_reg.course_id_1 = course_id_1[0].id

            # elif new_registration.get('error',False):
        return reg

    def register_cross_course_office(self, primary_class_id, term_id, st_term, course_type, date_effective):
        alternate_id = course_id_1 = False
        course_id = primary_class_id.course_id

        new_registration = self.register_course(term_id, course_id, st_term, primary_class_id, date_effective)
        if new_registration.get('reg', False):
            new_reg = new_registration.get('reg')
            new_reg.course_type = course_type

            if course_type in ('additional', 'minor'):
                new_reg.include_in_cgpa = False

            elif course_type == 'alternate':
                if alternate_id and alternate_id.type == 'grade':
                    course_id_1 = self.env['odoocms.student.course'].search([
                        ('course_id', '=', alternate_id.catalogue_id.id), ('student_id', '=', self.id)
                    ])
            else:
                course_id_1 = self.env['odoocms.student.course'].search([
                    ('course_code', '=', primary_class_id.course_code), ('student_id', '=', self.id), ('id', '!=', new_reg.id)
                ])  # , ('include_in_cgpa', '=', True)

            if course_id_1:
                course_id_1[0].course_id_2 = new_reg
                new_reg.course_id_1 = course_id_1[0].id

        return new_registration

    def register_new_course(self, line, term_id, st_term, date_effective, strength_test=True):
        alternate_id = course_id_1 = False
        primary_class_id = line.primary_class_id.sudo()

        new_reg = self.env['odoocms.student.course']

        if not primary_class_id and line.course_id:
            course_id = line.course_id
            registration_id = self.env['odoocms.student.course'].search([
                ('student_id', '=', self.id), ('term_id', '=', term_id.id),
                ('course_id', '=', course_id.id)])

            if not registration_id:
                data = {
                    'student_id': self.id,
                    'term_id': term_id.id,
                    'course_id': course_id.id,
                    'primary_class_id': False,
                    'student_term_id': st_term.id,
                    'credits': course_id.credits,
                    'course_code': course_id.code,
                    'course_name': course_id.name,
                    'date_effective': date_effective,
                }
                registration_id = self.env['odoocms.student.course'].create(data)
            line.write({
                'state': 'approved',
                'student_course_id': registration_id.id,
            })
            return {'reg': registration_id}

        elif line.scope == 'cross' and not line.cross_id:
            data = {
                'student_id': self.id,
                'primary_class_id': primary_class_id.id,
                'course_type': line.course_type,
                'registration_line_id': line.id,
            }
            cross_id = self.env['odoocms.course.registration.cross'].create(data)
            line.cross_id = cross_id.id
            line.cross_id.action_submit()

        else:
            course_id = primary_class_id.course_id
            new_registration = self.register_course(term_id, course_id, st_term, primary_class_id, date_effective, strength_test=strength_test)
            if new_registration.get('reg', False):
                new_reg = new_registration.get('reg')
                new_reg.course_type = line.course_type

                if line.course_type in ('additional', 'minor'):
                    new_reg.include_in_cgpa = False

                elif line.course_type == 'alternate':
                    if alternate_id and alternate_id.type == 'grade':
                        course_id_1 = self.env['odoocms.student.course'].search([
                            ('course_id', '=', alternate_id.catalogue_id.id), ('student_id', '=', self.id)
                        ])
                else:
                    course_id_1 = self.env['odoocms.student.course'].search([
                        ('course_code', '=', (primary_class_id and primary_class_id.course_code or course_id.code)),
                        ('student_id', '=', self.id), ('id', '!=', new_reg.id)
                    ])  # , ('include_in_cgpa', '=', True)

                if course_id_1:
                    course_id_1[0].course_id_2 = new_reg
                    new_reg.course_id_1 = course_id_1[0].id

                line.write({
                    'state': 'approved',
                    'student_course_id': new_reg.id,
                })
                return {'reg': new_reg}

            elif new_registration.get('error', False):
                return new_registration

    def register_course(self, term, course_id, st_term, primary_class_id, date_effective, tag=False, strength_test=True):
        if course_id:
            registration_id = self.env['odoocms.student.course'].search([
                ('student_id', '=', self.id), ('term_id', '=', term.id),
                ('course_id', '=', course_id.id)])

            if not primary_class_id:
                primary_class_id = self.env['odoocms.class.primary'].search([
                    ('batch_section_id', '=', self.batch_section_id.id), ('course_id', '=', course_id.id),
                    ('term_id', '=', term.id)])

                if not primary_class_id:
                    return {'error':
                                """Primary Class not defined for Course: %s \n Section: %s \n Batch: %s""" % (
                                    course_id.name, self.batch_section_id.name, self.batch_id.name)
                            }

        if primary_class_id and not registration_id:
            registration_id = self.env['odoocms.student.course'].search([
                ('student_id', '=', self.id), ('term_id', '=', term.id),
                ('course_id', '=', primary_class_id.study_scheme_line_id.course_id.id)])

        if registration_id:
            # if not registration_id.student_term_id:
            #     registration_id.student_term_id = st_term
            return {'reg': registration_id}

        if strength_test and (not primary_class_id.strength or primary_class_id.strength < 1):
            return {'error': "Primary Class Strength is not defined!"}
        # elif strength_test and primary_class_id.student_count >= primary_class_id.strength:
        elif strength_test and primary_class_id.registration_count >= primary_class_id.strength:
            return {'error': "Primary Class Strength is fulfilled!"}
        else:
            component_ids = []
            for component in primary_class_id.class_ids:
                component_data = {
                    'student_id': self.id,
                    'class_id': component.id,
                    'term_id': term.id,
                    'weightage': component.weightage,
                }
                component_ids.append((0, 0, component_data))

            data = {
                'student_id': self.id,
                'term_id': term.id,
                'course_id': course_id.id,
                'primary_class_id': primary_class_id.id,
                'student_term_id': st_term.id,
                'credits': primary_class_id.credits,
                'course_code': primary_class_id.course_code or primary_class_id.course_id.code,
                'course_name': primary_class_id.course_name or primary_class_id.course_id.name,
                'tag': tag or "-",
                'date_effective': date_effective,
                'component_ids': component_ids,
            }
            registration_id = self.env['odoocms.student.course'].create(data)

            for component in registration_id.component_ids:
                absent_before_fee = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.absent_before_fee','True'))
                if absent_before_fee:
                    registration_id.add_attendance_absent(component, date_effective)
                else:
                    registration_id.add_attendance(component, date_effective)
            return {'reg': registration_id}

    def _prereq_satisfy(self, pre_courses, enrollment='M'):
        pass

    def _prereq_get(self, pre_courses, enrollment='M'):
        pass

    def prereq_get(self, primary_class, enrollment, samebatch=False):
        prereq = False
        if samebatch and self.batch_id == primary_class.batch_id:
            return prereq
        elif self.earned_credits < primary_class.study_scheme_line_id.req_earned_credits:
            return '<span class="uk-badge uk-badge-danger"> Registration of ' + primary_class.code + ' requires ' + \
                str(primary_class.study_scheme_line_id.req_earned_credits) + ' earned Credit Hours</span>'
        elif self.cgpa < primary_class.study_scheme_line_id.req_cgpa:
            return '<span class="uk-badge uk-badge-danger"> Registration of ' + primary_class.code + ' requires ' + \
                str(primary_class.study_scheme_line_id.req_cgpa) + ' CGPA</span>'

        else:
            study_scheme_line_id = self.study_scheme_id.line_ids.filtered(
                lambda l: l.course_id.id == primary_class.course_id.id)
            if study_scheme_line_id:
                prereq = self._prereq_get(study_scheme_line_id.prerequisite_ids, enrollment)
            elif primary_class.study_scheme_line_id:
                prereq = self._prereq_get(primary_class.study_scheme_line_id.prerequisite_ids, enrollment)
            elif primary_class.course_id:
                prereq = self._prereq_get(primary_class.course_id.prerequisite_ids, enrollment)
        return prereq

    def prereq_satisfy_old(self, primary_class, enrollment, samebatch=False):
        prereq = True
        if samebatch and self.batch_id == primary_class.batch_id:   # if classes are of same batch, then ok and display the prereq message
            return prereq
        elif primary_class.study_scheme_line_id:
            if not self._prereq_satisfy(primary_class.study_scheme_line_id.prerequisite_ids, enrollment):
                prereq = False
        else:
            study_scheme_line_id = self.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == primary_class.course_id.id)
            if study_scheme_line_id:
                if not self._prereq_satisfy(study_scheme_line_id.prerequisite_ids, enrollment):
                    prereq = False
            elif primary_class.course_id:
                if not self._prereq_satisfy(primary_class.course_id.prerequisite_ids, enrollment):
                    prereq = False
        return prereq

    def prereq_satisfy(self, primary_class, enrollment, samebatch=False):
        prereq = True
        student = self
        study_scheme_line_id = student.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == primary_class.course_id.id)
        if samebatch and student.batch_id == primary_class.batch_id:   # if classes are of same batch, then ok and display the prereq message
            return prereq
        elif study_scheme_line_id:
            if not self._prereq_satisfy(study_scheme_line_id.prerequisite_ids, enrollment):
                prereq = False
        elif primary_class.study_scheme_line_id:
            if not self._prereq_satisfy(primary_class.study_scheme_line_id.prerequisite_ids, enrollment):
                prereq = False
        elif primary_class.course_id:
            if not self._prereq_satisfy(primary_class.course_id.prerequisite_ids, enrollment):
                prereq = False
        return prereq

    def prereq_apply(self, class_ids, enrollment, samebatch=True):
        for class_id in class_ids:
            prereq = self.prereq_satisfy(class_id, enrollment, samebatch=samebatch)
            if not prereq:
                class_ids -= class_id
        return class_ids

    def get_offered_classes(self, program_domain, course_ids, new_term, portal=False, include_classes=True, tt_check=False, ds_check=False):
        domain = program_domain
        domain = expression.AND(
            [safe_eval(domain), [('term_id', '=', new_term.id), ('offer_for', 'in', ['ongoing', 'both'])]]) \
            if domain else [('term_id', '=', new_term.id), ('offer_for', 'in', ['ongoing', 'both'])]
        if portal:
            domain = expression.AND([domain, [('self_enrollment', '=', True)]])

        if tt_check:
            domain = expression.AND([domain, [('timetable_ids', '!=', False)]])
        # if ds_check:
        #     domain = expression.AND([domain, [('datesheet_ids', '!=', False)]])

        # domain = expression.AND([domain, ['|',('allowed_batch_ids', '=', False),('allowed_batch_ids')]])

        if include_classes:
            class_ids = self.env['odoocms.class.primary'].search(domain).filtered(
                lambda l: l.course_id.id in course_ids.ids
                    and (not l.allowed_batch_ids or self.batch_id.id in l.allowed_batch_ids.ids)
                    and (not l.allowed_institute_ids or self.institute_id.id in l.allowed_institute_ids.ids)
                    and (not l.allowed_program_ids or self.program_id.id in l.allowed_program_ids.ids)
            )
        else:
            class_ids = self.env['odoocms.class.primary'].search(domain).filtered(
                lambda l: l.course_id.id not in course_ids.ids
                    and (not l.allowed_batch_ids or self.batch_id.id in l.allowed_batch_ids.ids)
                    and (not l.allowed_institute_ids or self.institute_id.id in l.allowed_institute_ids.ids)
                    and (not l.allowed_program_ids or self.program_id.id in l.allowed_program_ids.ids)
            )

        # For Domain at Class Level
        #for class_id in class_ids:
        #     # domain = expression.AND([safe_eval(class_id.enroll_domain), [('id', '=', self.id)]]) if class_id.enroll_domain else []
        #     # student_rec = self.env['odoocms.student'].search(domain)
        #     # if not student_rec:
        #     #     class_ids -= class_id

            #For IM   - section_id at student is replaced with batch_section_id
            # if class_id.own_section and class_id.section_id and self.section_id and class_id.section_id.id != self.section_id.id:
            #    class_ids -= class_id

        return class_ids

    def get_possible_classes(self, new_term, portal=False, tt_check=False, ds_check=False, enrollment='M', registration=False):
        classes = {}
        if "NewId" in str(self.id) and self._origin:
            student = self._origin
        else:
            student = self
        cache = self.env['odoocms.registration.cache'].sudo().search([('student_id', '=', student.id)])
        if cache and cache.classes:
            values = json.loads(cache.classes)
            for k, v in values.items():
                classes[k] = self.env['odoocms.class.primary'].browse(v) if v else self.env['odoocms.class.primary']
        else:
            classes = self._get_possible_classes(new_term, portal=portal, tt_check=tt_check, ds_check=ds_check, enrollment=enrollment, registration=registration)
        return classes

    def _get_possible_classes(self, new_term, portal=False, tt_check=False, ds_check=False, enrollment='M', registration=False):
        start_time = datetime.now()
        registered_class_ids = comp_class_ids = elec_class_ids = additional_class_ids = alternate_class_ids = minor_class_ids = spec_class_ids = repeat_class_ids = improve_class_ids = self.env['odoocms.class.primary']
        error = False
        if "NewId" in str(self.id) and self._origin:
            student = self._origin
        else:
            student = self

        if registration:
            request_ids = registration
        else:
            request_ids = self.env['odoocms.course.registration'].search(
                [('student_id', '=', student.id), ('state', 'in', ('draft', 'submit'))])

        no_registration_tags = self.env['odoocms.student.tag'].sudo().search(['|', ('block_registration', '=', True), ('block', '=', True)])
        no_new_registration_tags = self.env['odoocms.student.tag'].sudo().search([('no_new_registration', '=', True)])

        block_registration = (student.tag_ids and no_registration_tags and any(
            tag in no_registration_tags for tag in student.tag_ids) or False)
        no_new_registration = (student.tag_ids and no_new_registration_tags and any(
            tag in no_new_registration_tags for tag in student.tag_ids) or False)

        st_term = student.enroll_term_ids.filtered(lambda l: l.term_id == new_term)
        if registration and registration.add_drop_request:
            pass
        elif student.state != 'enroll' or block_registration or (st_term and st_term.state not in ('draft', 'current')):
            if student.state != 'enroll':
                error = 'Student Status nor in Enrollment'
            elif block_registration:
                error = 'Blocked Registration tag is set'
            elif st_term and st_term.state not in (
            'draft', 'current') and registration and not registration.add_drop_request:
                error = 'Student Term is not in enrollment Status'

            return {
                'registered_class_ids': registered_class_ids,
                'comp_class_ids': comp_class_ids,
                'elec_class_ids': elec_class_ids,
                'spec_class_ids': spec_class_ids,
                'repeat_class_ids': repeat_class_ids,
                'improve_class_ids': improve_class_ids,
                'additional_class_ids': additional_class_ids,
                'alternate_class_ids': alternate_class_ids,
                'minor_class_ids': minor_class_ids,
                'error': error,
            }

        # Registered Courses in all Prev Terms
        registered_student_course_ids = student.enrolled_course_ids.filtered(lambda l: l.grade not in ('W', 'XF'))  # 'F','I'      l.include_in_cgpa and  # All states   odoocms.student.course
        registered_course_ids = registered_student_course_ids.mapped('course_id')  # odoocms.course
        registered_class_ids = registered_student_course_ids.filtered(lambda l: l.term_id.id == new_term.id).mapped('primary_class_id')
        drop_class_ids = request_ids.mapped('line_ids').filtered(lambda l: l.action == 'drop').mapped('primary_class_id')
        registered_class_ids -= drop_class_ids
        comp_course_ids = self.env['odoocms.course']
        if not no_new_registration:
            # ***************** Core Course **************
            # All Core Course - Less Registered Courses
            if new_term.type == 'regular':
                comp_course_ids = student.study_scheme_id.line_ids.filtered(lambda l: l.course_type == 'compulsory').mapped('course_id')

            elif new_term.type == 'summer':
                deficient_course_in_summer = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms.deficient_course_in_summer'))
                if deficient_course_in_summer and (student.program_id.deficient_course_in_summer or student.deficient_course_in_summer):
                    comp_course_ids += student.study_scheme_id.line_ids.filtered(lambda l: \
                        l.course_type == 'compulsory' and l.term_id and l.term_id.number <= new_term.number).mapped('course_id')
                advance_course_in_summer = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms.advance_course_in_summer'))
                if advance_course_in_summer and (student.program_id.advance_course_in_summer or student.advance_course_in_summer):
                    comp_course_ids += student.study_scheme_id.line_ids.filtered(lambda l: \
                        l.course_type == 'compulsory' and (not l.term_id or l.term_id.number >= new_term.number)).mapped('course_id')

            elif new_term.type == 'special':
                comp_course_ids = student.study_scheme_id.line_ids.filtered(lambda l: l.course_type == 'compulsory').mapped('course_id')

            drop_courses = request_ids.mapped('line_ids').filtered(lambda l: l.action == 'drop').mapped('primary_class_id').mapped('course_id')

            comp_course_ids -= (registered_course_ids - drop_courses)

            # Offered Classes of remaining Courses with applied domain criteria
            comp_class_ids = self.get_offered_classes(student.program_id.registration_domain, comp_course_ids, new_term, portal, True, tt_check, ds_check)

            # Pre - Req
            # if not any(request_ids.mapped('override_prereq')):
            #     comp_class_ids = student.prereq_apply(comp_class_ids, enrollment)

            # Less Alternate & with Pending Requests
            # alt_course_ids = student.alternate_ids.filtered(lambda l: l.state == 'approve').mapped('course_id')
            # request_course_ids = request_ids.mapped('compulsory_course_ids').mapped('course_id')
            # minus_course_ids = alt_course_ids + request_course_ids
            # minus_class_ids = comp_class_ids.filtered(lambda l: l.course_id.id in minus_course_ids.ids)
            # comp_class_ids -= minus_class_ids

            # Additional Temporarily Check
            course_ids = registered_course_ids - drop_courses
            comp_class_ids = comp_class_ids.filtered(lambda l: l.course_id.id not in course_ids.ids).sorted(
                lambda m: (m.course_id, m.batch_term_section_id, m.batch_section_id, m.section_id and m.section_id.name or 'Z'))

            # *************** Elective ****************
            # All Elective - Less Registered Courses
            elec_course_ids = self.env['odoocms.course']
            if new_term.type == 'regular':
                elec_course_ids = student.study_scheme_id.line_ids.filtered(lambda l: l.course_type in ('elective', 'gen_elective')).mapped('course_id')

            elif new_term.type == 'summer':
                deficient_course_in_summer = eval(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms.deficient_course_in_summer'))
                if deficient_course_in_summer and (student.program_id.deficient_course_in_summer or student.deficient_course_in_summer):
                    elec_course_ids += student.study_scheme_id.line_ids.filtered(lambda l: \
                        l.course_type in ('elective', 'gen_elective') and l.term_id and l.term_id.number <= new_term.number).mapped('course_id')
                advance_course_in_summer_elective = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms.advance_course_in_summer_elective'))
                if advance_course_in_summer_elective and (student.program_id.advance_course_in_summer_elective or student.advance_course_in_summer_elective):
                    elec_course_ids += student.study_scheme_id.line_ids.filtered(lambda l: \
                        l.course_type in ('elective', 'gen_elective') and (not l.term_id or l.term_id.number >= new_term.number)).mapped('course_id')

            elec_course_ids = elec_course_ids - registered_course_ids
            elec_class_ids = self.get_offered_classes(student.program_id.elec_registration_domain, elec_course_ids, new_term, portal, True, tt_check, ds_check)
            if not any(request_ids.mapped('override_prereq')):
                elec_class_ids = student.prereq_apply(elec_class_ids, enrollment, samebatch=False)  # Apply prereq and filter those classes which satisfy

            # Less Alternate & with Pending Requests
            alt_course_ids = student.alternate_ids.filtered(lambda l: l.state == 'approve').mapped('course_id')
            request_course_ids = request_ids.mapped('elective_course_ids').mapped('course_id')
            minor_course_ids = student.minor_scheme_id.line_ids.mapped('course_id')
            minus_course_ids = alt_course_ids + request_course_ids + minor_course_ids
            minus_class_ids = elec_class_ids.filtered(lambda l: l.course_id.id in minus_course_ids.ids)
            elec_class_ids -= minus_class_ids

            # *************** Specialization ****************
            # All Specialization - Less Registered Courses
            specialization_id = student.specialization_id.id
            specialization_course_ids = student.study_scheme_id.line_ids.filtered(
                lambda l: l.specialization_id.id == specialization_id and l.course_type in ('specialization')).mapped(
                'course_id')
            specialization_course_ids = specialization_course_ids - registered_course_ids

            specialization_class_ids = self.get_offered_classes(student.program_id.elec_registration_domain, specialization_course_ids, new_term, portal, True, tt_check, ds_check)
            if not any(request_ids.mapped('override_prereq')):
                specialization_class_ids = student.prereq_apply(specialization_class_ids, enrollment, samebatch=False) # Apply prereq and filter those classes which satisfy

            # Less Alternate & with Pending Requests
            alt_course_ids = student.alternate_ids.filtered(lambda l: l.state == 'approve').mapped('course_id')
            request_course_ids = request_ids.mapped('elective_course_ids').mapped('course_id')
            minor_course_ids = student.minor_scheme_id.line_ids.mapped('course_id')
            minus_course_ids = alt_course_ids + request_course_ids + minor_course_ids
            minus_class_ids = elec_class_ids.filtered(lambda l: l.course_id.id in minus_course_ids.ids)
            specialization_class_ids -= minus_class_ids

            spec_class_ids = specialization_class_ids

            # **************** Remarked - due to slow speed of system ***************************88
            # ********************* Additional ********************
            # Student Scheme Courses + Add already Registered Courses
            # all_course_ids = student.study_scheme_id.line_ids.mapped('course_id') + registered_course_ids
            #
            # additional_class_ids = self.get_offered_classes(student.program_id.additional_registration_domain, all_course_ids, new_term, portal, False, tt_check, ds_check)
            # if not any(request_ids.mapped('override_prereq')):
            #     additional_class_ids = student.prereq_apply(additional_class_ids, enrollment)
            #
            # # Less Alternate & with Pending Requests
            # request_ids2 = (request_ids.mapped('compulsory_course_ids') + request_ids.mapped('elective_course_ids') + \
            #                 request_ids.mapped('additional_course_ids') + request_ids.mapped('alternate_course_ids') + \
            #                 request_ids.mapped('minor_course_ids'))
            #
            # eq_course_ids = student.study_scheme_id.line_ids.mapped('eq_course_id')
            # alt_course_ids = student.alternate_ids.filtered(lambda l: l.state == 'approve').mapped('alternate_course_id')
            # request_course_ids = request_ids2.mapped('course_id')
            # minor_course_ids = student.minor_scheme_id.line_ids.mapped('course_id')
            # minus_course_ids = alt_course_ids + request_course_ids + minor_course_ids + eq_course_ids
            # minus_class_ids = additional_class_ids.filtered(lambda l: l.course_id.id in minus_course_ids.ids)
            # additional_class_ids -= minus_class_ids
            #
            # # *************** Alternative ****************
            # # All Alternate - less Studied
            # alt_course_ids = student.alternate_ids.filtered(lambda l: l.state == 'approve').mapped('alternate_course_id')
            # alt_course_ids = alt_course_ids - registered_course_ids
            #
            # # Offered Classes of Alternate Courses with applied domain criteria
            # alternate_class_ids = self.get_offered_classes(student.program_id.registration_domain, alt_course_ids, new_term, portal,True, tt_check, ds_check)
            # if not any(request_ids.mapped('override_prereq')):
            #     alternate_class_ids = student.prereq_apply(alternate_class_ids, enrollment)
            #
            # # Less with Pending Requests
            # less_request_class_ids = alternate_class_ids.filtered(
            #     lambda l: l.course_id.id in request_ids.mapped('alternate_course_ids').mapped('course_id').ids)
            # alternate_class_ids -= less_request_class_ids
            #
            # # **************** Minor ****************
            # # Registered Courses in all Prev Terms
            # registered_minor_course_ids = student.enrolled_course_ids.filtered(lambda l: l.course_type == 'minor').mapped('course_id')
            #
            # # All Minor - Less Registered Courses
            # minor_course_ids = student.minor_scheme_id.line_ids.mapped('course_id')
            # minor_course_ids -= registered_minor_course_ids
            #
            # # Offered Classes of remaining Courses with applied domain criteria
            # minor_class_ids = self.get_offered_classes(student.program_id.minor_registration_domain, minor_course_ids, new_term, portal,True, tt_check, ds_check)
            # if not any(request_ids.mapped('override_prereq')):
            #     minor_class_ids = student.prereq_apply(minor_class_ids, enrollment)
            #
            # # Less Alternate & with Pending Requests
            # alt_course_ids = student.alternate_ids.filtered(lambda l: l.state == 'approve').mapped('course_id')
            # request_course_ids = request_ids.mapped('minor_course_ids').mapped('course_id')
            # minus_course_ids = alt_course_ids + request_course_ids
            # minus_class_ids = minor_class_ids.filtered(lambda l: l.course_id.id in minus_course_ids.ids)
            # minor_class_ids -= minus_class_ids

        # Failed and Repeat Classes are separately handled because some universities are allowing a course to improve for specific number of time
        # ************* Repeat ******************
        failed_grades = self.env['ir.config_parameter'].sudo().get_param('odoocms.failed_grades')
        repeat_course_ids = student.result_course_ids.filtered(lambda l: l.grade in failed_grades.replace(' ', '').split(',')).mapped('course_id')

        already_improved_course_ids = student.result_course_ids.filtered(
            lambda l: l.grade not in failed_grades.replace(' ', '').split(',') and l.grade_points > 0).mapped('course_id')

        repeat_course_ids -= already_improved_course_ids
        eq_course_ids = student.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id in repeat_course_ids.ids).mapped('eq_course_id')
        repeat_course_ids += eq_course_ids

        repeat_class_ids = self.get_offered_classes(student.program_id.registration_domain, repeat_course_ids, new_term, portal, True, tt_check, ds_check)

        # if portal:
        #     repeat_class_ids = new_term.primary_class_ids.filtered(
        #         lambda l: l.course_id.id in repeat_course_ids.ids and l.self_enrollment == True)
        # else:
        #     repeat_class_ids = self.get_offered_classes(student.program_id.registration_domain, repeat_course_ids, new_term, portal, True, tt_check, ds_check)
        #     repeat_class_ids = new_term.primary_class_ids.filtered(lambda l: l.course_id.id in repeat_course_ids.ids)

        # eq_course_ids = student.study_scheme_id.line_ids.filtered(
        #     lambda l: l.course_id.id in repeat_course_ids.ids).mapped('eq_course_id')
        # eq_class_ids = new_term.primary_class_ids.filtered(lambda l: l.course_id.id in eq_course_ids.ids)
        # repeat_class_ids += eq_class_ids

        # Less with Pending Requests
        less_request_class_ids = repeat_class_ids.filtered(
            lambda l: l.course_id.id in request_ids.mapped('repeat_course_ids').mapped('course_id').ids)
        repeat_class_ids -= less_request_class_ids

        # *** Improved ***
        repeat_grades_allowed = student.program_id.repeat_grades_allowed or self.env['ir.config_parameter'].sudo().get_param('odoocms.repeat_grades_allowed')
        repeat_grades_allowed_time = self.env['ir.config_parameter'].sudo().get_param('odoocms.repeat_grades_allowed_time') or '10'
        repeat_grades_allowed_no = self.env['ir.config_parameter'].sudo().get_param('odoocms.repeat_grades_allowed_no') or '10'

        # X-Final Students Repeat time allowed
        if student.semester_id.number > 8:
            x_st_repeat_grades_allowed_time = self.env['ir.config_parameter'].sudo().get_param('odoocms.x_st_repeat_grades_allowed_time')
            repeat_grades_allowed_time = x_st_repeat_grades_allowed_time or 2

        improve_course_ids = student.result_course_ids.filtered(lambda l: l.grade and l.grade in repeat_grades_allowed.replace(' ', '').split(',')).mapped('course_id')
        improve_course_ids2 = student.result_course_ids.filtered(lambda l: l.grade and l.grade[0] == '(' and not l.course_id_1 and not l.course_id_2).mapped('course_id')
        improve_course_ids += improve_course_ids2

        eq_course_ids = student.study_scheme_id.line_ids.filtered(
            lambda l: l.course_id.id in repeat_course_ids.ids).mapped('eq_course_id')
        improve_course_ids += eq_course_ids
        improve_class_ids = self.get_offered_classes(student.program_id.registration_domain, improve_course_ids, new_term, portal, True, tt_check, ds_check)

        # if portal:
        #     improve_class_ids = new_term.primary_class_ids.filtered(lambda l: l.course_id.id in improve_course_ids.ids and l.self_enrollment == True)
        # else:
        #     improve_class_ids = new_term.primary_class_ids.filtered(lambda l: l.course_id.id in improve_course_ids.ids)
        #
        # eq_course_ids = student.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id in improve_class_ids.ids).mapped('eq_course_id')
        # eq_class_ids = new_term.primary_class_ids.filtered(lambda l: l.course_id.id in eq_course_ids.ids)
        # improve_class_ids += eq_class_ids

        # Less with Pending Requests
        less_request_class_ids = improve_class_ids.filtered(lambda l: l.course_id.id in request_ids.mapped('improve_course_ids').mapped('course_id').ids)
        improve_class_ids -= less_request_class_ids
        if student.improve_course_count > student.career_id.improve_course_limit:
            improve_class_ids = False

        # Remarked
        # minimum_cgpa = self.env['ir.config_parameter'].sudo().get_param('odoocms.minimum_cgpa') or '2.0'
        # if not(student.semester_id.number >= 8 and student.cgpa < minimum_cgpa):
        #     for line in repeat_course_ids:
        #         if len(student.result_course_ids.filtered(
        #                 lambda l: l.course_id.id == line.id and l.grade in repeat_grades_allowed.replace(' ','').split(
        #                     ','))) > int(repeat_grades_allowed_no)+1 :
        #             repeat_course_ids -= line
        #
        #     for line in repeat_course_ids:
        #         if len(student.result_course_ids.filtered(
        #                 lambda l: l.course_id.id == line.id and l.grade in repeat_grades_allowed.replace(' ','').split(',')
        #                           and l.semester_id.number < (
        #                                   student.semester_id.number - int(repeat_grades_allowed_time)))) > 0 :
        #             repeat_course_ids -= line

        # if (new_term.type == 'summer' and reregister_allow_in_summer == 'False' ) or (new_term.type == 'winter' and reregister_allow_in_winter == 'False' ):
        #     offered_r = self.env['odoocms.class.primary']
        #
        #
        # if new_term.type in ('summer','winter'):
        #     additional_class_ids = self.env['odoocms.class.primary']
        classes = {
            'registered_class_ids': registered_class_ids,
            'comp_class_ids': comp_class_ids,
            'elec_class_ids': elec_class_ids,
            'spec_class_ids': spec_class_ids,
            'repeat_class_ids': repeat_class_ids,
            'improve_class_ids': improve_class_ids,
            'additional_class_ids': additional_class_ids,
            'alternate_class_ids': alternate_class_ids,
            'minor_class_ids': minor_class_ids,
        }
        total_classes = len(registered_class_ids or []) + len(comp_class_ids or []) + len(elec_class_ids or []) + len(spec_class_ids or []) + len(repeat_class_ids or []) + len(improve_class_ids or [])
        end_time = datetime.now()
        diff_time = end_time - start_time
        _logger.warning("AARSOL: %s Filtered Classes for %s in time : %s" % (total_classes, student.code, diff_time))
        return classes

    def fill_portal_cards(self, course, course_type):
        card = {
            'class': course,
            'course_type': course_type,
            'course_id': course.course_id.id,
        }
        if self.batch_id.id == course.batch_id.id:
            card['scope'] = 'batch'
        elif self.program_id.id == course.program_id.id:
            card['scope'] = 'program'
            card['program_id'] = course.program_id.id
        elif self.institute_id.id == course.institute_id.id:
            card['scope'] = 'institute'
            card['institute_id'] = course.institute_id.id
        else:
            card['scope'] = 'cross'
        return card

    def fill_portal_cards_ucp(self, course, course_type, tentative_timetable=None, tentative_datesheet=None, registered=False):
        semester = ''
        induction = False
        if course.study_scheme_line_id:
            semester = course.study_scheme_line_id.semester_id.name
            induction = course.study_scheme_line_id.compulsory_induction or False

        course_card = {
            'course_name': course.course_id.name,
            'course_code': course.course_id.code,
            'semester': semester,
            'course_type': course_type,
            'induction': induction,
            'pre_req': False,
            'co_req': ['Nill'],
            'coreq_id': ['Nill'],
            'coreq_course_code': '',
            'registered': registered,
            'class': course.id,
            'course_id': course.course_id.id,
        }

        schedule = self.env['odoocms.datesheet.line'].sudo().search([('term_id', '=', course.term_id.id), ('course_id', '=', course.course_id.id)], order='date_id')
        if schedule:
            schedule = schedule[0]

        section_card = {
            'section_id': course.id,
            'section_name': course.section_id and course.section_id.name or '',
            'section_iname': course.code[0:course.code.rfind('-')] if course.section_id else course.code,
            'section_code': course.code,
            'faculty': course.grade_staff_id.name,
            # 'section_status': 'Open' if (course.strength - course.student_count) > 0 else 'Close',
            'section_status': 'Open' if (course.strength - course.registration_count) > 0 else 'Close',
            'section_capacity': course.strength,
            # 'seats_available': course.strength - course.student_count,
            'seats_available': course.strength - course.registration_count,
            'time_table': [],
            'date_sheet': schedule and schedule.date_id.id*1000+schedule.slot_id.id or 0,
            'clash_course': '',
            'couple_course': [],
            'couple_course_type': '',
            'registered': registered,

        }
        couple_course = []
        couple_courses_name = []
        couple_courses_code = []
        couple_type = []

        if course.couple_class_id:
            couple_course.append(course.couple_class_id.id)
            couple_courses_name.append(course.couple_class_id.course_name)
            couple_courses_code.append(course.couple_class_id.course_code)
            couple_type.append('section_couple')

        elif course.class_type in ('regular', 'elective') and course.study_scheme_line_id.coreq_course:
            section_id = course.section_id
            scl = course.study_scheme_line_id.coreq_course
            couple_class = self.env['odoocms.class.primary'].search([
                ('study_scheme_line_id', '=', scl.id), ('section_id', '=', '%s,%s' % (section_id._name, section_id.id))
            ])
            if couple_class:
                couple_course.append(couple_class.id)
                couple_courses_name.append(couple_class.name)
                couple_courses_code.append(couple_class.course_code)
                couple_type.append('coreq_couple')

        elif course.class_type in ('summer', 'winter', 'special') and self.study_scheme_id.line_ids.filtered(
                lambda l: l.course_id.id == course.course_id.id).coreq_course:
            section_id = course.section_id
            coreq_scheme_line_id = self.study_scheme_id.line_ids.filtered(
                lambda l: l.course_id.id == course.course_id.id).coreq_course
            if section_id:
                couple_class = self.env['odoocms.class.primary'].search([
                    ('course_id', '=', coreq_scheme_line_id.course_id.id), ('term_id', '=', course.term_id.id),
                    ('section_id', '=', '%s,%s' % (section_id._name, section_id.id)),
                ])
            # else:
            #     couple_class = self.env['odoocms.class.primary'].search([
            #         ('course_id', '=', coreq_scheme_line_id.course_id.id), ('section_id', '=', course.section_id.id),
            #         ('term_id', '=', course.term_id.id)
            #     ])
                if couple_class:
                    couple_course.append(couple_class.id)
                    couple_courses_name.append(couple_class.name)
                    couple_courses_code.append(couple_class.course_code)
                    couple_type.append('coreq_couple')

        if couple_course:
            section_card['couple_course'] = [
                {course.id: list(set(couple_course))}
            ]
            course_card['co_req'] = couple_courses_name[0]
            course_card['coreq_id'] = couple_course[0]
            course_card['coreq_course_code'] = couple_courses_code[0]
            course_card['couple_type'] = couple_type[0]

        # Check Timetable

        for tt in course.timetable_ids:
            for week_day in tt.week_day_ids:
                if tentative_timetable and tentative_timetable[week_day.number - 1] and not tentative_timetable[week_day.number - 1][tt.period_id.number - 1]['period'] == 0:
                    section_card.update({
                        'section_status': 'Clash',
                        'clash_course': (tentative_timetable[week_day.number - 1][tt.period_id.number - 1]['pclass'] or 'Unknown') + ' ' +
                                        (tentative_timetable[week_day.number - 1][tt.period_id.number - 1]['section'] or 'Unknown')
                    })
                tt_card = {
                    'time_from': "%02d:%02d" % (divmod(tt.time_from * 60, 60)),
                    'time_to': "%02d:%02d" % (divmod(tt.time_to * 60, 60)),
                    'faculty': tt.faculty_id and tt.faculty_id.name or '',
                    'room': tt.room_id and tt.room_id.code or '',
                    'day': week_day.code,
                    'day_number': week_day.number,
                    'period': tt.period_id.number,
                }
                section_card['time_table'].append(tt_card)

        # check Date Sheet
        check_date_sheet_clash = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.check_date_sheet_clash','False')
        if check_date_sheet_clash == 'True':
            schedule = self.env['odoocms.datesheet.line'].sudo().search([('term_id', '=', course.term_id.id), ('course_id', '=', course.course_id.id)])
            ds_index = schedule and schedule[0].date_id.id*1000+schedule[0].slot_id.id
            clash = schedule and tentative_datesheet and tentative_datesheet.get(ds_index,0) > 0 or False
            if tentative_datesheet and clash:
                section_card.update({
                    'section_status': 'Clash',
                    'clash_course': 'Date Sheet Clash'
                })

        return course_card, section_card

    # course_registration (odoocms.course.registration of student and term)
    # enrollment A/M/C
    def get_portal_classes_ucp(self, term_id, course_registration, enrollment, tentative_timetable=None, tentative_datesheet=None, tt_check=False, ds_check=False, registration=False):
        classes = self.get_possible_classes(term_id, portal=True, tt_check=tt_check, ds_check=ds_check, enrollment=enrollment, registration=registration)
        cards = {
            'registered': {},
            'regular': {},
            'special': {},
            'repeat': {},
            'alternate': {},
            'error': False,
        }
        if classes.get('error', False):
            cards['error'] = classes.get('error')

        if classes['comp_class_ids']:
            for course in classes['comp_class_ids']:

                # UCP
                # if course.class_type in ('special','summer','winter'):
                #     if not self.program_id.deficient_course_in_summer:
                #         continue

                # Already Registered
                if course_registration and len(course_registration.line_ids.filtered(
                            lambda l: l.course_code == course.course_code and l.action == 'add')) > 0:
                    continue

                # if course.id == 54029:
                #     pdb.set_trace()
                #     b = 5
                course_card, section_card = self.fill_portal_cards_ucp(course, 'compulsory', tentative_timetable, tentative_datesheet)
                course_id = course_card['course_id']
                if cards['regular'].get(course_id, False):
                    cards['regular'][course_id]['course_sections'].append(section_card)
                else:
                    cards['regular'][course_id] = course_card
                    cards['regular'][course_id]['course_sections'] = []
                    cards['regular'][course_id]['course_sections'].append(section_card)

                if not course_registration or (course_registration and not course_registration.override_prereq):
                    prereq_course = self.prereq_get(course, enrollment, samebatch=False)
                    if prereq_course:
                        course_card['pre_req'] = markupsafe.Markup(prereq_course)

                # if course.study_scheme_line_id.compulsory_induction:
                #     course_card['induction'] = True

        if classes['registered_class_ids']:
            for course in classes['registered_class_ids']:

                # if course.class_type in ('special','summer','winter'):
                #     if not self.program_id.deficient_course_in_summer:
                #         continue

                # Already in Request for Removal
                if course_registration and len(
                        course_registration.line_ids.filtered(
                            lambda l: l.course_code == course.course_code and l.action == 'drop')) > 0:
                    continue
                course_card, section_card = self.fill_portal_cards_ucp(course, 'compulsory', tentative_timetable, tentative_datesheet, registered=True)
                course_id = course_card['course_id']
                if cards['registered'].get(course_id, False):
                    cards['registered'][course_id]['course_sections'].append(section_card)
                else:
                    cards['registered'][course_id] = course_card
                    cards['registered'][course_id]['course_sections'] = []
                    cards['registered'][course_id]['course_sections'].append(section_card)

        abc = []
        for key, value in cards['registered'].items():
            abc.append(value)
        cards['registered'] = abc

        if classes['elec_class_ids'] or classes['spec_class_ids']:
            for course in classes['elec_class_ids'] + classes['spec_class_ids']:
                # if course.class_type in ('special','summer','winter') and not self.program_id.deficient_course_in_summer:
                #     continue
                if course_registration and len(
                        course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
                    continue
                course_card, section_card = self.fill_portal_cards_ucp(course, 'elective', tentative_timetable, tentative_datesheet)
                course_id = course_card['course_id']
                if cards['regular'].get(course_id, False):
                    cards['regular'][course_id]['course_sections'].append(section_card)
                else:
                    cards['regular'][course_id] = course_card
                    cards['regular'][course_id]['course_sections'] = []
                    cards['regular'][course_id]['course_sections'].append(section_card)

                if not course_registration or (course_registration and not course_registration.override_prereq):
                    prereq_course = self.prereq_get(course, enrollment, samebatch=False)
                    if prereq_course:
                        course_card['pre_req'] = markupsafe.Markup(prereq_course)

        abc = []
        for key, value in cards['regular'].items():
            abc.append(value)
        cards['regular'] = abc
        #
        if classes['additional_class_ids']:
            for course in classes['additional_class_ids']:
                # if course.class_type in ('special','summer','winter') and not self.program_id.deficient_course_in_summer:
                #     continue
                if course_registration and len(
                        course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
                    continue
                course_card, section_card = self.fill_portal_cards_ucp(course, 'additional', tentative_timetable, tentative_datesheet)
                course_id = course_card['course_id']

                if cards['special'].get(course_id, False):
                    cards['special'][course_id]['course_sections'].append(section_card)
                else:
                    cards['special'][course_id] = course_card
                    cards['special'][course_id]['course_sections'] = []
                    cards['special'][course_id]['course_sections'].append(section_card)

                if not course_registration or (course_registration and not course_registration.override_prereq):
                    prereq_course = self.prereq_get(course, enrollment, samebatch=False)
                    if prereq_course:
                        course_card['pre_req'] = markupsafe.Markup(prereq_course)

            abc = []
            for key, value in cards['special'].items():
                abc.append(value)
            cards['special'] = abc
        #
        # if classes['repeat_class_ids']:
        #     for course in classes['repeat_class_ids']:
        #         if course_registration and len(
        #                 course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         course_card, section_card = self.fill_portal_cards_ucp(course, 'repeat', tentative_timetable, tentative_datesheet)
        #         course_id = course_card['course_id']
        #         if cards['repeat'].get(course_id, False):
        #             cards['repeat'][course_id]['course_sections'].append(section_card)
        #         else:
        #             cards['repeat'][course_id] = course_card
        #             cards['repeat'][course_id]['course_sections'] = []
        #             cards['repeat'][course_id]['course_sections'].append(section_card)
        #     # abc = []
        #     # for key, value in cards['repeat'].items():
        #     #     abc.append(value)
        #     # cards['repeat'] = abc
        #
        # if classes['improve_class_ids']:
        #     for course in classes['improve_class_ids']:
        #         if course_registration and len(
        #                 course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         course_card, section_card = self.fill_portal_cards_ucp(course, 'improve', tentative_timetable, tentative_datesheet)
        #         course_id = course_card['course_id']
        #         if cards['repeat'].get(course_id, False):
        #             cards['repeat'][course_id]['course_sections'].append(section_card)
        #         else:
        #             cards['repeat'][course_id] = course_card
        #             cards['repeat'][course_id]['course_sections'] = []
        #             cards['repeat'][course_id]['course_sections'].append(section_card)

        if classes['repeat_class_ids'] or classes['improve_class_ids']:
            repeat_improve = list(set(classes['repeat_class_ids'] + classes['improve_class_ids']))
            for course in repeat_improve:
                if course_registration and len(
                        course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
                    continue
                course_card, section_card = self.fill_portal_cards_ucp(course, 'repeat', tentative_timetable, tentative_datesheet)
                course_id = course_card['course_id']
                if cards['repeat'].get(course_id, False):
                    cards['repeat'][course_id]['course_sections'].append(section_card)
                else:
                    cards['repeat'][course_id] = course_card
                    cards['repeat'][course_id]['course_sections'] = []
                    cards['repeat'][course_id]['course_sections'].append(section_card)

                if not course_registration or (course_registration and not course_registration.override_prereq):
                    prereq_course = self.prereq_get(course, enrollment, samebatch=False)
                    if prereq_course:
                        course_card['pre_req'] = markupsafe.Markup(prereq_course)

        abc = []
        for key, value in cards['repeat'].items():
            abc.append(value)
        cards['repeat'] = abc

        if classes['alternate_class_ids']:
            for course in classes['alternate_class_ids']:
                if course_registration and len(
                        course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
                    continue
                course_card, section_card = self.fill_portal_cards_ucp(course, 'alternate', tentative_timetable, tentative_datesheet)
                course_id = course_card['course_id']
                if cards['alternate'].get(course_id, False):
                    cards['alternate'][course_id]['course_sections'].append(section_card)
                else:
                    cards['alternate'][course_id] = course_card
                    cards['alternate'][course_id]['course_sections'] = []
                    cards['alternate'][course_id]['course_sections'].append(section_card)

                if not course_registration or (course_registration and not course_registration.override_prereq):
                    prereq_course = self.prereq_get(course, enrollment, samebatch=False)
                    if prereq_course:
                        course_card['pre_req'] = markupsafe.Markup(prereq_course)

            abc = []
            for key, value in cards['alternate'].items():
                abc.append(value)
            cards['alternate'] = abc

        return cards, len(cards['registered']) + len(cards['regular']) + len(cards['special']) + len(cards['repeat']) + len(cards['alternate'])

    def get_portal_classes(self, term_id, course_registration):
        classes = self.get_possible_classes(term_id, portal=True, tt_check=self.batch_id.tt_check or False, ds_check=self.batch_id.ds_check or False)
        cards = {
            'batch': [],
            'program': [],
            'institute': [],
            'cross': [],
        }
        if classes['comp_class_ids']:
            for course in classes['comp_class_ids']:
                if course_registration and len(
                        course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
                    continue
                card = self.fill_portal_cards(course, 'compulsory')
                cards[card['scope']].append(card)
        # if classes['elec_class_ids']:
        #     for course in classes['elec_class_ids']:
        #         if course_registration and len(course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         card = self.fill_portal_cards(course,'elective')
        #         cards[card['scope']].append(card)
        # if classes['repeat_class_ids']:
        #     for course in classes['repeat_class_ids']:
        #         if course_registration and len(course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         card = self.fill_portal_cards(course, 'repeat')
        #         cards[card['scope']].append(card)
        # if classes['improve_class_ids']:
        #     for course in classes['improve_class_ids']:
        #         if course_registration and len(course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         card = self.fill_portal_cards(course, 'improve')
        #         cards[card['scope']].append(card)
        # if classes['additional_class_ids']:
        #     for course in classes['additional_class_ids']:
        #         if course_registration and len(course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         card = self.fill_portal_cards(course, 'additional')
        #         cards[card['scope']].append(card)
        # if classes['alternate_class_ids']:
        #     for course in classes['alternate_class_ids']:
        #         if course_registration and len(course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         card = self.fill_portal_cards(course, 'alternate')
        #         cards[card['scope']].append(card)
        # if classes['minor_class_ids']:
        #     for course in classes['minor_class_ids']:
        #         if course_registration and len(course_registration.line_ids.filtered(lambda l: l.course_code == course.course_code)) > 0:
        #             continue
        #         card = self.fill_portal_cards(course, 'minor')
        #         cards[card['scope']].append(card)

        return cards, len(cards['regular']) + len(cards['special']) + len(cards['repeat']) + len(cards['alternate'])

    def get_registration_cards(self, term_id, registration=False, tt_check=False, ds_check=False, advance_enrollment=False):
        advance_enrollment_status = advance_enrollment or self.batch_id.can_apply('advance_enrollment', term_id, admin=registration and True or False)
        enrollment_status = self.batch_id.can_apply('enrollment', term_id, admin=registration and True or False)
        add_drop_status = self.batch_id.can_apply('add_drop', term_id, admin=registration and True or False)

        registered_courses = self.enrolled_course_ids.filtered(lambda l: l.term_id.id == term_id.id)
        if not registered_courses:
            add_drop_status = False

        # Pick or Create Registration
        if registration:
            course_registration = registration
        else:
            course_registration = self.env['odoocms.course.registration'].sudo().search(
                [('student_id', '=', self.id), ('term_id', '=', term_id.id),('state','in',('draft','submit'))])
            if len(course_registration) > 1:
                course_registration = course_registration.filtered(lambda l: l.source == 'portal')

        enrollment_status = enrollment_status or (course_registration and course_registration.bypass_date)
        enrollment = (add_drop_status and 'D') or (advance_enrollment_status and 'A') or (enrollment_status and 'M') or 'C'


        confirmed_class_ids  = registered_courses.mapped('primary_class_id').mapped('class_ids')
        reg_class_ids = course_registration.line_ids.filtered(lambda l: l.action == 'add').mapped('primary_class_id').mapped('class_ids')
        drop_class_ids = course_registration.line_ids.filtered(lambda l: l.action == 'drop').mapped('primary_class_id').mapped('class_ids')
        class_ids = (confirmed_class_ids + reg_class_ids - drop_class_ids).ids

        # timetable of registered courses
        schedules = self.env['odoocms.timetable.schedule'].sudo().search([('class_id', 'in', class_ids)], order='time_from')
        slots = self.env['odoocms.timetable.slot'].sudo().search(['|',('company_id','=',self.env.company.id),('company_id','=',False)])
        rows, cols = (7, len(slots))
        tentative_timetable = [
            [{'pclass_id': '-', 'pclass': '-', 'section': '-', 'period': 0} for i in range(cols)]
            for j in range(rows)
        ]
        for schedule in schedules:
            for week_day in schedule.week_day_ids:
                tentative_timetable[week_day.number - 1][int(schedule.period_id.number) - 1]['pclass_id'] = schedule.primary_class_id.id
                tentative_timetable[week_day.number - 1][int(schedule.period_id.number) - 1]['pclass'] = schedule.primary_class_id.name
                tentative_timetable[week_day.number - 1][int(schedule.period_id.number) - 1]['period'] = schedule.period_id.number
                tentative_timetable[week_day.number - 1][int(schedule.period_id.number) - 1]['section'] = schedule.primary_class_id.section_id and schedule.primary_class_id.section_id.name or ''
                # tentative_timetable[week_day.number - 1][int(schedule.period_id.number) - 1].append([{'class_code': schedule.class_id.name}])

        # datesheet of registered courses
        tentative_datesheet = None
        confirmed_pclass_ids = registered_courses.mapped('primary_class_id')
        reg_pclass_ids = course_registration.line_ids.filtered(lambda l: l.action == 'add').mapped('primary_class_id')
        drop_pclass_ids = course_registration.line_ids.filtered(lambda l: l.action == 'drop').mapped('primary_class_id')
        course_ids = (confirmed_pclass_ids + reg_pclass_ids - drop_pclass_ids).mapped('course_id').ids

        datesheet = self.env['odoocms.datesheet'].search([('term_id','=', term_id.id)])
        schedules = self.env['odoocms.datesheet.line'].sudo().search([('term_id', '=', term_id.id), ('course_id', 'in', course_ids)], order='date_id')
        if schedules:
            tentative_datesheet = {
                i.id*1000+j.id: 0 for i in datesheet.mapped('date_ids')
                for j in datesheet.mapped('slot_ids')
            }
            for schedule in schedules:
                tentative_datesheet[schedule.date_id.id*1000+schedule.slot_id.id] = schedule.course_id.id

        cards_no = 0
        if advance_enrollment_status or enrollment_status or add_drop_status:
            cards, cards_no = self.get_portal_classes_ucp(term_id, course_registration, enrollment, tentative_timetable, tentative_datesheet, tt_check=tt_check, ds_check=ds_check, registration=registration)

            json_card1 = json.dumps(cards)
            json_card2 = json_card1.replace(" ", "")
            json_card3 = json.dumps(json_card2)
            json_cards = json.loads(json_card3)

        show_faculty = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.show_faculty') or False
        show_class_strength = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.show_class_strength')

        request_no = ''
        if enrollment == 'D':
            p = inflect.engine()
            request_no = p.ordinal(registration.add_drop_request_no)

        values = {
            'student_id': self.id,
            'registration_id': registration and registration.id or False,
            'registration': registration or False,
            'cards': cards if cards_no > 0 else False,
            'class_cnt': len(class_ids),
            'cards_no': cards_no,
            'enrollment_status': advance_enrollment_status or enrollment_status or add_drop_status,
            'enrollment_type': enrollment,
            'json_cards': json_cards if cards_no > 0 else False,
            'tentative_timetable': tentative_timetable,
            'tentative_datesheet': tentative_datesheet,
            'show_faculty': show_faculty,
            'show_class_strength': show_class_strength,
            'request_no': request_no,

            # 'classes': classes,
            # 'course_registration': course_registration,
            # 'cart': course_registration,
        }
        return values


class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'

    course_ids = fields.One2many('odoocms.student.course', 'term_id', 'Courses')
