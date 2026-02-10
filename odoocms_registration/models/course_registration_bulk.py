from datetime import date

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json
import pdb


class OdooCMSCourseRegistrationBulk(models.Model):
    _name = "odoocms.course.registration.bulk"
    _description = 'Course Registration Bulk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    SUBMITTED_STATES = {
        'submit': [('readonly', True)],
        'approved': [('readonly', True)],
        'rejected': [('readonly', True)],
    }
    READONLY_STATES = {
        'approved': [('readonly', True)],
        'rejected': [('readonly', True)],
    }

    def _get_students(self):
        # domain="[('state','in',('enroll','deffer','extra')),('batch_id','=',batch_id),('registration_allowed','=',True)]"
        no_reg_tags = self.env['odoocms.student.tag'].search([('block_registration','=', True)])  # ('graduate_line', '=', True),
        return [('state', 'in', ('enroll','deffer','extra')),'!',('tag_ids','in',no_reg_tags.ids)]

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    student_ids = fields.Many2many('odoocms.student', string='Students', required=True, states=SUBMITTED_STATES, tracking=True, domain=_get_students)
    batch_id = fields.Many2one('odoocms.batch', 'Batch',)
    program_id = fields.Many2one('odoocms.program', 'Program',related='batch_id.program_id',store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', required=True, states=SUBMITTED_STATES, tracking=True)
    last_date = fields.Date(string = 'Registration Last Date', compute = 'get_registration_last_date', readonly= True, store = True)
    reg_date = fields.Date('Date', default = (fields.Date.today()),  readonly=True)
    date_effective = fields.Date('Effective Date', default=(fields.Date.today()),states=READONLY_STATES)
    override_max_limit = fields.Boolean('Override Maximum Limit?',default=False,states=SUBMITTED_STATES, tracking=True)
    override_prereq = fields.Boolean('Override Pre-Requisite?',default=False,states=SUBMITTED_STATES, tracking=True)
    enrollment_type = fields.Selection([('advance_enrollment','Advance'),('enrollment','Main'),('add_drop','Add/Drop')],'Enrollment')
    compulsory_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_compulsory_bulk_rel', 'register_id', 'primary_class_id',
                                             string="Core Courses", states=SUBMITTED_STATES, tracking=True)
    elective_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_elective_bulk_rel', 'register_id', 'primary_class_id',
                                           string="Elective Courses", states=SUBMITTED_STATES, tracking=True)
    spec_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_spec_bulk_rel', 'register_id', 'primary_class_id',
                                           string="Specialization Courses", states=SUBMITTED_STATES, tracking=True)
    # additional_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_additional_bulk_rel', 'register_id', 'primary_class_id',
    #                                          string="Additional Courses", states=SUBMITTED_STATES, tracking=True)
    #
    can_approve = fields.Boolean('Can Approve',compute='_can_approve', tracking=True)
    error = fields.Text('Error')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], default='draft', string='Status', copy=False, tracking=True)
    
    comp_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    elec_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    spec_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    # additional_domain = fields.Many2many('odoocms.class.primary', compute='_get_courses_domain')

    registration_ids = fields.One2many('odoocms.course.registration','bulk_id','Registrations')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.course.registration.bulk') or _('New')
        result = super().create(vals)
        return result
    
    @api.onchange('term_id', 'batch_id')
    def _can_register(self):
        if self.term_id and self.student_ids:
            advance_enrollment_status = self.student_ids[0].batch_id.can_apply('advance_enrollment', self.term_id, admin=True)
            enrollment_status = self.student_ids[0].batch_id.can_apply('enrollment', self.term_id, admin=True)
            add_drop_status = self.student_id.batch_id.can_apply('add_drop', self.term_id, admin=True)

            if not advance_enrollment_status and not enrollment_status and not add_drop_status:
                self.error = 'Date Over'
            else:
                self.error = None
        else:
            self.error = None
        
    def _can_approve(self):
        # allow_re_reg_wo_fee = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.allow_re_reg_wo_fee')
        #
        # if allow_re_reg_wo_fee == False or allow_re_reg_wo_fee == 'False':
        #     can_approve = False
        #     if self.state == 'submit':
        #         if self.compulsory_course_ids or self.elective_course_ids or self.additional_course_ids:
        #             can_approve = True
        #     self.can_approve = can_approve
        # else:
        self.can_approve = True
        
    @api.depends('student_ids','term_id')
    def _get_courses_domain(self):
        self.comp_domain = self.elec_domain = self.spec_domain = False
        if self.batch_id and self.term_id:
            # All Core Course offered in same batch
            comp_course_ids = self.batch_id.study_scheme_id.line_ids.filtered(lambda l: l.course_type == 'compulsory').mapped('course_id')
            comp_class_ids = self.env['odoocms.class.primary'].search([
                ('batch_id','=',self.batch_id.id),('term_id','=',self.term_id.id)]).filtered(
                    lambda l: l.course_id.id in comp_course_ids.ids)

            comp_class_ids += self.env['odoocms.class.primary'].search([
                ('batch_id', '=', False), ('department_id', '=', self.program_id.department_id.id),('term_id', '=', self.term_id.id)]).filtered(
                lambda l: l.course_id.id in comp_course_ids.ids)
            
            # All Elective offered in same batch
            elective_course_ids = self.batch_id.study_scheme_id.line_ids.filtered(lambda l: l.course_type == 'elective').mapped('course_id')
            elective_class_ids = self.env['odoocms.class.primary'].search([
                ('batch_id', '=', self.batch_id.id), ('term_id', '=', self.term_id.id)]).filtered(
                lambda l: l.course_id.id in elective_course_ids.ids)
            elective_class_ids += self.env['odoocms.class.primary'].search([
                ('batch_id', '=', False), ('department_id', '=', self.program_id.department_id.id),('term_id', '=', self.term_id.id)]).filtered(
                lambda l: l.course_id.id in elective_course_ids.ids)

            spec_course_ids = self.batch_id.study_scheme_id.line_ids.filtered(lambda l: l.course_type == 'specialization').mapped('course_id')
            spec_class_ids = self.env['odoocms.class.primary'].search([
                ('batch_id', '=', self.batch_id.id), ('term_id', '=', self.term_id.id)]).filtered(
                lambda l: l.course_id.id in spec_course_ids.ids)
            spec_class_ids += self.env['odoocms.class.primary'].search([
                ('batch_id', '=', False), ('department_id', '=', self.program_id.department_id.id), ('term_id', '=', self.term_id.id)]).filtered(
                lambda l: l.course_id.id in spec_course_ids.ids)
            
            self.comp_domain = [(6, 0, comp_class_ids.ids or [])]
            self.elec_domain = [(6, 0, elective_class_ids.ids or [])]
            self.spec_domain = [(6, 0, spec_class_ids.ids or [])]
           
    def action_submit(self):
        if not self.student_ids:
            raise UserError('Please Select the Students to Enroll!')
        if not (self.compulsory_course_ids or self.elective_course_ids or self.spec_course_ids):
            raise UserError('Please Select the Courses to Enroll!')
        
        for student in self.student_ids.filtered(
                lambda l: all(tag.code not in ['withdrawal', 'suspension', 'suspension of registration'] for tag in l.tag_ids)
                          and l.state == 'enroll'):
            data = {
                'student_id': student.id,
                'term_id': self.term_id.id,
                'source': 'bulk',
                'state': 'draft',
                'compulsory_course_ids': [(6, 0, self.compulsory_course_ids.ids)],
                'elective_course_ids': [(6, 0, self.elective_course_ids.ids)],
                'spec_course_ids': [(6, 0, self.spec_course_ids.ids)],
                'bulk_id': self.id,
                'override_max_limit': self.override_max_limit,
                'override_prereq': self.override_prereq,
                'date_effective': self.date_effective,
                'enrollment_type': self.enrollment_type,
            }
            reg = self.env['odoocms.course.registration'].create(data)
            reg.action_submit()
            
        self.state = 'submit'

    def action_reset_draft(self):
        self.state = 'draft'

    def action_reject(self):
        for reg in self.registration_ids:
            if reg.state in ('draft','submit'):
                reg.action_reject()
        self.state = 'rejected'

    def action_approve(self):
        # if not self.registration_ids:
        #     raise UserError('No New Registration request is there')
        
        for registration in self.registration_ids.filtered(lambda l: l.state == 'submit'):
            registration.action_approve()
            
        if all(registration.state == 'approved' for registration in self.registration_ids):
            self.state = 'approved'
        
        


    
