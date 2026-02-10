import pdb
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval
import inflect
import logging

_logger = logging.getLogger(__name__)


class OdooCMSCourseRegistration(models.Model):
    _name = 'odoocms.course.registration'
    _description = 'Course Registration'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    SUBMITTED_STATES = {
        'submit': [('readonly', True)],
        'part_approved': [('readonly', True)],
        'approved': [('readonly', True)],
        'rejected': [('readonly', True)],
    }
    READONLY_STATES = {
        'part_approved': [('readonly', True)],
        'approved': [('readonly', True)],
        'rejected': [('readonly', True)],
    }

    def _get_students(self):
        no_reg_tags = self.env['odoocms.student.tag'].search([('block_registration','=', True)])  # ('graduate_line', '=', True),
        return [('state', 'in', ('enroll','extra')),'!',('tag_ids','in',no_reg_tags.ids)]

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    student_id = fields.Many2one('odoocms.student', 'Student', required=True, states=SUBMITTED_STATES, tracking=True, domain=_get_students)
    program_id = fields.Many2one('odoocms.program', 'Program', related='student_id.program_id',store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='student_id.batch_id',store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute/Faculty', related='student_id.institute_id',store=True)

    term_id = fields.Many2one('odoocms.academic.term', 'Term', required=True, states=SUBMITTED_STATES, tracking=True)
    last_date = fields.Date(string = 'Registration Last Date', compute = 'get_registration_last_date', readonly= True, store = True)
    reg_date = fields.Date('Date', default = (fields.Date.today()),  readonly=True)
    date_effective = fields.Date('Effective Date', default = (fields.Date.today()),states=READONLY_STATES)
    enrollment_type = fields.Selection([('advance_enrollment', 'Advance'), ('enrollment', 'Main'),('add_drop','Add/Drop')], 'Enrollment')
    source = fields.Selection([
        ('office','Back Office'),
        ('portal','Portal'),
        ('bulk','Bulk Process'),
        ('bulk2','Bulk Process2'),
    ],'Source',default='office',readonly=True, copy=False)
    portal_confirm = fields.Boolean('Portal Confirm',default=False)
    bulk_id = fields.Many2one('odoocms.course.registration.bulk','Bulk ID')
    bulk_id2 = fields.Many2one('odoocms.course.registration.bulk2','Bulk ID2')
    new_courses = fields.Boolean(compute='_can_enroll_new_courses',store=True)
    override_max_limit = fields.Boolean('Override Maximum Limit?',default=False,states=READONLY_STATES, tracking=True)
    override_prereq = fields.Boolean('Override Pre-Requisite?',default=False,states=READONLY_STATES, tracking=True)

    registered_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_registered_rel', 'register_id', 'primary_class_id',
            string="Registered Courses", states=READONLY_STATES, tracking=True,compute='get_registered_courses',store=True,)

    compulsory_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_compulsory_rel', 'register_id', 'primary_class_id',
            string="Core Courses", states=READONLY_STATES, tracking=True)
    elective_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_elective_rel', 'register_id', 'primary_class_id',
            string="Elective Courses", states=READONLY_STATES, tracking=True)
    spec_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_spec_rel', 'register_id', 'primary_class_id',
                                           string="Specialization Courses", states=READONLY_STATES, tracking=True)
    repeat_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_failed_rel', 'register_id', 'primary_class_id',
            string="Failed Courses", states=READONLY_STATES, tracking=True)
    improve_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_improve_rel', 'register_id', 'primary_class_id',
            string="Repeat for Improvement Courses", states=READONLY_STATES, tracking=True)
    additional_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_additional_rel', 'register_id', 'primary_class_id',
            string="Additional Courses", states=READONLY_STATES, tracking=True)
    alternate_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_alternate_rel', 'register_id', 'primary_class_id',
                                             string="Alternate Courses", states=READONLY_STATES, tracking=True)
    minor_course_ids = fields.Many2many('odoocms.class.primary', 'class_course_minor_rel', 'register_id', 'primary_class_id',
                                            string="Minor Courses", states=READONLY_STATES, tracking=True)
    other_course_ids = fields.Many2many('odoocms.course', 'class_course_other_rel', 'register_id', 'course_id',
                                        string='Other Courses', states=READONLY_STATES)

    other_request_id = fields.Many2one('odoocms.course.registration','Other Pending Request',readonly=True, store=True)

    other_course_amount = fields.Float('Amount')

    # invoice_id = fields.Many2one('account.move','Invoice')
    # invoice_status = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('unpaid', 'Unpaid'),
    #     ('open', 'Open'),
    #     ('in_payment', 'In Payment'),
    #     ('paid', 'Paid'),
    #     ('cancel', 'Cancelled')], related='invoice_id.state', tracking=True)
    
    register_backend = fields.Boolean('Register from this Interface', default=False)
    can_approve = fields.Boolean('Can Approve',compute='_can_approve', tracking=True)
    # can_invoice = fields.Boolean('Can Invoice', compute='_can_invoice', tracking=True)
    error = fields.Text('Error')
    limit_error = fields.Boolean('Over Limit',default=False)
    limit_error_text = fields.Text(default='')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('error','Error'),
        ('part_approved','Partially Approved'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel','Cancel')], default='draft', string='Status', copy=False, tracking=True)
    
    comp_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    elec_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    spec_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    repeat_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    improve_domain = fields.Many2many('odoocms.class.primary',compute='_get_courses_domain')
    additional_domain = fields.Many2many('odoocms.class.primary', compute='_get_courses_domain')
    alternate_domain = fields.Many2many('odoocms.class.primary', compute='_get_courses_domain')
    minor_domain = fields.Many2many('odoocms.class.primary', compute='_get_courses_domain')

    repeat_domain_bool = fields.Boolean(compute='_get_courses_domain')
    improve_domain_bool = fields.Boolean(compute='_get_courses_domain')
    additional_domain_bool = fields.Boolean(compute='_get_courses_domain')
    alternate_domain_bool = fields.Boolean(compute='_get_courses_domain')
    minor_domain_bool = fields.Boolean(compute='_get_courses_domain')

    line_ids = fields.One2many('odoocms.course.registration.line','registration_id','Course to Enroll',domain=[('state','!=','error')])
    failed_line_ids = fields.One2many('odoocms.course.registration.line', 'registration_id', 'Failed to Enroll', domain=[('state', '=', 'error')])
    cnt = fields.Integer('Count')
    
    generate_fee = fields.Boolean('Generate Fee', default=False)
    restrict_to_main = fields.Boolean('Restrict to Main', default=False)
    invoice_id = fields.Many2one('account.move','Invoice')
    add_drop_request = fields.Boolean('Add/Drop Request',default=False)
    add_drop_request_no = fields.Integer('Add/Drop Request No')
    add_drop_request_no_txt = fields.Char('Add/Drop Request No.')
    active = fields.Boolean(default=True)
    to_be = fields.Boolean(default=False)
    bypass_date = fields.Boolean(default=False)
    bypass_probation = fields.Boolean('Bypass Probation', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_retest_limits(self):
        for reg in self:
            reg._can_register()
            reg._test_register_limit()
            error = False
            if reg.error:
                for reg_line in reg.line_ids.filtered(lambda l: not l.student_course_id):
                    if (not reg_line.primary_class_id.strength) or reg_line.primary_class_id.strength < 1:
                        reg.error = "Primary Class Strength is not defined!"
                        error = True
                    elif reg_line.primary_class_id.registration_count >= reg_line.primary_class_id.strength:  # and not
                        return {'error': "Primary Class Strength is fulfilled!"}
                    if not error:
                        reg.error = False

    @api.onchange('override_max_limit')
    def onchange_override_max_limit(self):
        for rec in self:
            rec._test_register_limit()
    
    @api.model
    def create(self, vals):
        recs = self.search([
            ('student_id', '=', vals['student_id']),
            ('term_id', '=', vals['term_id']),
            ('state','not in',('cancel','rejected','approved','part_approved'))
        ])
        if len(recs) > 0:
            raise UserError('Registration Request for Same Student and Term already exist!')

        add_drop_request_exist = self.env['odoocms.course.registration'].search_count([
            ('student_id', '=', vals['student_id']), ('term_id', '=', vals['term_id']), ('add_drop_request', '=', True),('state','in', ('draft','submit'))
        ])
        if add_drop_request_exist:
            raise UserError('Add-Drop for Same Student and Term already exist for processing!')
        
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.course.registration') or _('New')

        student = self.env['odoocms.student'].browse(vals['student_id'])
        # registered_student_course_ids = student.enrolled_course_ids  # All states
        # enrolled_courses = registered_student_course_ids.filtered(lambda l: l.term_id.id == vals['term_id'])
        prev_request = self.env['odoocms.course.registration'].search([
            ('student_id', '=', vals['student_id']), ('term_id', '=', vals['term_id']), ('state', 'not in', ('cancel', 'rejected'))
        ])
        if prev_request:
            if prev_request[0].state in ('draft','submit'):
                raise UserError('Registration Request for Same Student and Term already exist!')

            vals['add_drop_request'] = True
            add_drop_request_no = self.env['odoocms.course.registration'].search_count([
                ('student_id','=',vals['student_id']),('term_id','=',vals['term_id']),('add_drop_request','=',True)
            ])
            vals['add_drop_request_no'] = add_drop_request_no + 1
            p = inflect.engine()
            vals['add_drop_request_no_txt'] = p.ordinal(add_drop_request_no + 1)
        else:
            vals['add_drop_request'] = False
            vals['add_drop_request_no'] = 0
            vals['add_drop_request_no_txt'] = False
            
        result = super().create(vals)
        return result

    def write(self, vals):
        for rec in self:
            recs = self.search([
                ('student_id', '=', vals.get('student_id', rec.student_id.id)),
                ('term_id', '=', vals.get('term_id', rec.term_id.id)),
                ('add_drop_request_no','=',vals.get('add_drop_request_no',rec.add_drop_request_no)),
                ('state', 'not in', ('cancel', 'rejected','approved','part_approved'))
            ])
            if len(recs) > 1:
                raise UserError('Registration Request for Same Student and Term already exist!')
        
        # student_id = vals.get('student_id', self.student_id.id)
        # term_id = vals.get('term_id', self.term_id.id)
        #
        # student = self.env['odoocms.student'].browse(student_id)
        # registered_student_course_ids = student.enrolled_course_ids  # All states
        # enrolled_courses = registered_student_course_ids.filtered(lambda l: l.term_id.id == term_id)
        # if enrolled_courses:
        #     vals['add_drop_request'] = True
        #     add_drop_request_no = self.env['odoocms.course.registration'].search_count([
        #         ('student_id', '=', student_id), ('term_id', '=', term_id), ('add_drop_request', '=', True)
        #     ])
        #     vals['add_drop_request_no'] = add_drop_request_no + 1
        # else:
        #     vals['add_drop_request'] = False
        #     vals['add_drop_request_no'] = 0
            
        ret = super().write(vals)
        return ret

    def _compute_access_url(self):
        super(OdooCMSCourseRegistration, self)._compute_access_url()
        for rec in self:
            rec.access_url = '/student/enrollment/cards/%s/%s' % (rec.id, rec.access_token)

    def web_registration(self):
        self.ensure_one()
        if not self.bypass_probation:
            probation_1_2 = self.env['odoocms.student.tag'].search([('code', 'in', ('probation_1', ('probation_2')))])
            probation_3_above_tags = self.env['odoocms.student.tag'].search([('code', 'like', 'probation_')]) - probation_1_2

            disposal_cat = self.env['odoocms.student.tag.category'].search([('code', '=', 'disposal')])
            if disposal_cat:
                student_disposal_tag = self.student_id.tag_ids.filtered(lambda l: l.category_id.id == disposal_cat.id)
                probation_tag = (student_disposal_tag and probation_3_above_tags and any(
                    tag in probation_3_above_tags for tag in student_disposal_tag) or False)
                if probation_tag:
                    raise UserError('%s id on %s. Enrollment is not possible!' % (self.student_id.code, student_disposal_tag[-1:].name))
        return {
            'type': 'ir.actions.act_url',
            'target': 'self',
            'url': self.get_portal_url(),
        }
    
    @api.depends('student_id', 'term_id')
    def get_registered_courses(self):
        for rec in self:
            rec.registered_course_ids = False
            if rec.student_id and rec.term_id:
                registered_class_ids = rec.student_id.enrolled_course_ids.filtered(
                    lambda l: l.term_id.id == rec.term_id.id).mapped('primary_class_id')
                rec.registered_course_ids = [(6, 0, registered_class_ids.ids)]
                domain = [('student_id', '=', rec.student_id.id), ('state', 'in', ('draft', 'submit'))]

                if "NewId" in str(rec.id) and rec._origin:
                    domain = expression.AND([domain, [('id', '!=', rec._origin.id)]])
                elif rec.id:
                    domain = expression.AND([domain, [('id', '!=', rec.id)]])
                    
                request_ids = self.env['odoocms.course.registration'].search(domain)
                rec.other_request_id = request_ids and request_ids[0] or False
                
    @api.depends('student_id')
    def _can_enroll_new_courses(self):
        for rec in self:
            can_enroll = True
            student_tags = rec.student_id.tag_ids.mapped('name')
            if 'Deferred' in student_tags or 'Extra' in student_tags or 'Semester Deferment' in student_tags:
                can_enroll = False
            self.new_courses = can_enroll

    @api.onchange('term_id', 'student_id','bypass_date')
    def _can_register(self):
        if self.term_id and self.student_id and not self.bypass_date:
            if self.other_course_ids:
                self.error = None
            else:
                no_reg_tags = self.env['odoocms.student.tag'].search([('block_registration', '=', True)])  # ('graduate_line', '=', True),
                reg_student = self.env['odoocms.student'].sudo().search([
                    ('id', '=', self.student_id.id), ('state', 'in', ('enroll', 'extra')), '!', ('tag_ids', 'in', no_reg_tags.ids)
                ])
                if not reg_student:
                    self.error = 'Registration for this student is not Allowed'
                else:
                    advance_enrollment_status = self.student_id.batch_id.can_apply('advance_enrollment', self.term_id, admin=True)
                    enrollment_status = self.student_id.batch_id.can_apply('enrollment', self.term_id, admin=True)
                    add_drop_status = self.student_id.batch_id.can_apply('add_drop', self.term_id, admin=True)

                    if not advance_enrollment_status and not enrollment_status and not add_drop_status:
                        self.error = 'Date Over'
                    else:
                        self.error = None
        else:
            self.error = None
            
    def _can_approve(self):
        allow_re_reg_wo_fee = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.allow_re_reg_wo_fee')
        self.can_approve = True
        # if allow_re_reg_wo_fee == False or allow_re_reg_wo_fee == 'False':
        #     can_approve = False
        #     if self.state == 'submit':
        #         if self.compulsory_course_ids or self.elective_course_ids or self.additional_course_ids:
        #             can_approve = True
        #         elif self.repeat_course_ids:
        #             if self.invoice_id and self.invoice_status == 'paid':
        #                 can_approve = True
        #     if self.state == 'part_approved':
        #        if self.repeat_course_ids:
        #             if self.invoice_id and self.invoice_status == 'paid':
        #                 can_approve = True
        #     self.can_approve = can_approve
        # else:
        #     self.can_approve = True

    # def _can_invoice(self):
    #     allow_re_reg_wo_fee = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.allow_re_reg_wo_fee')
    #
    #     if allow_re_reg_wo_fee == False or allow_re_reg_wo_fee == 'False':
    #         can_invoice = False
    #         if self.state in ('submit','part_approved'):
    #             if self.repeat_course_ids:
    #                 if not self.invoice_id:
    #                     can_invoice = True
    #         self.can_invoice = can_invoice
    #     else:
    #         can_invoice = False
    #
        
    @api.depends('student_id','term_id','register_backend')
    def _get_courses_domain(self):
        for rec in self:
            rec.comp_domain = rec.elec_domain = rec.spec_domain = rec.repeat_domain = rec.improve_domain = rec.additional_domain = rec.alternate_domain = rec.minor_domain = False
            rec.minor_domain_bool = rec.repeat_domain_bool = rec.improve_domain_bool = rec.additional_domain_bool = rec.alternate_domain_bool = False
            if rec.student_id and rec.term_id and rec.register_backend:
                classes = rec.student_id.get_possible_classes(rec.term_id, tt_check=rec.student_id.batch_id.tt_check or False, ds_check=rec.student_id.batch_id.ds_check or False)
                request_ids = self.env['odoocms.course.registration'].search(
                    [('student_id', '=', rec.student_id.id), ('state', 'in', ('draft', 'submit'))])

                student_tags = rec.student_id.tag_ids.mapped('name')
                if 'Deferred' in student_tags or 'Extra' in student_tags or 'Semester Deferment' in student_tags:
                    rec.comp_domain = []
                    rec.elec_domain = []
                    rec.spec_domain = []
                else:
                    rec.comp_domain = [(6, 0, classes['comp_class_ids'] and len(classes['comp_class_ids']) > 0 and classes['comp_class_ids'].ids or [])]
                    rec.elec_domain = [(6, 0, classes['elec_class_ids'] and len(classes['elec_class_ids']) > 0 and classes['elec_class_ids'].ids or [])]
                    rec.spec_domain = [(6, 0, classes['spec_class_ids'] and len(classes['spec_class_ids']) > 0 and classes['spec_class_ids'].ids or [])]
                
                if classes['repeat_class_ids'] and len(classes['repeat_class_ids']) > 0:
                    rec.repeat_domain = [(6, 0, classes['repeat_class_ids'].ids)]
                    rec.repeat_domain_bool = True
                
                if classes['improve_class_ids'] and len(classes['improve_class_ids']) > 0:
                    rec.improve_domain = [(6, 0, classes['improve_class_ids'].ids)]
                    rec.improve_domain_bool = True
                    
                if classes['additional_class_ids'] and len(classes['additional_class_ids']) > 0:
                    rec.additional_domain = [(6, 0, classes['additional_class_ids'].ids)]
                    rec.additional_domain_bool = True
                    
                if classes['alternate_class_ids'] and len(classes['alternate_class_ids']) > 0:
                    rec.alternate_domain = [(6, 0, classes['alternate_class_ids'].ids)]
                    rec.alternate_domain_bool = True
                    
                if classes['minor_class_ids'] and len(classes['minor_class_ids']) > 0:
                    rec.minor_domain = [(6, 0, classes['minor_class_ids'].ids)]
                    rec.minor_domain_bool = True
                    
                if request_ids and len(request_ids.mapped('repeat_course_ids')) > 0:
                    rec.repeat_domain_bool = True
                if request_ids and len(request_ids.mapped('improve_course_ids')) > 0:
                    rec.improve_domain_bool = True
                if request_ids and len(request_ids.mapped('additional_course_ids')) > 0:
                    rec.additional_domain_bool = True
                if request_ids and len(request_ids.mapped('alternate_course_ids')) > 0:
                    rec.alternate_domain_bool = True
                if request_ids and len(request_ids.mapped('minor_course_ids')) > 0:
                    rec.minor_domain_bool = True

    def _coreq_satisfy(self, course_id):
        all_courses = self.registered_course_ids + self.compulsory_course_ids + self.elective_course_ids + self.spec_course_ids + self.repeat_course_ids + self.improve_course_ids + self.additional_course_ids + self.alternate_course_ids + self.minor_course_ids
        if course_id.id not in all_courses.mapped('course_id').ids:
            return False
        else:
            return True

    def cron_check_coreq(self):
        recs = self.env['odoocms.course.registration.line'].search([('state','=','error'),('error','=','Prereq/Coreq Failed')])
        for rec in recs:
            primary_class = rec.primary_class_id
            registration = rec.registration_id
            coreq = registration.coreq_satisfy(primary_class)
            if coreq:
                rec.write({
                    'state': 'draft',
                    'error': False
                })
            
    def coreq_satisfy(self, primary_class):
        coreq = True
        if primary_class.study_scheme_line_id and primary_class.study_scheme_line_id.coreq_course:
            if not self._coreq_satisfy(primary_class.study_scheme_line_id.coreq_course.course_id):
                coreq = False
        elif primary_class.course_id and primary_class.course_id.coreq_course:
            if not self._coreq_satisfy(primary_class.course_id.coreq_course):
                coreq = False
        return coreq
    
    def add_course(self, primary_class, type, registered=False, enrollment='M', check_coreq=False, recheck_reqs=False):
        if not recheck_reqs:
            c1 = self.line_ids.filtered(lambda l: l.primary_class_id.id == primary_class.id)
            if c1:
                return c1

        new_line = self.env['odoocms.course.registration.line']
        prereq = registered or self.override_prereq or self.student_id.prereq_satisfy(primary_class, enrollment, samebatch=False)  # it was True
        if not registered and check_coreq:
            coreq = self.coreq_satisfy(primary_class)
        else:
            coreq = True
            
        regs = self.env['odoocms.student.course'].search([
            ('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id), ('course_code', '=', primary_class.course_code)
        ])
        
        if not regs:
            new_line = (self.failed_line_ids + self.line_ids).filtered(lambda line: line.primary_class_id.id == primary_class.id)
            if new_line and len(new_line) == 1 and registered:
                new_line.write({
                    'state': 'draft' if (prereq and coreq) else 'error',
                    'error': False if (prereq and coreq) else 'Prereq/Coreq Failed'
                })
                
            else:
                if len(new_line) > 0:
                    new_line.unlink()
                data = {
                    'registration_id': self.id,
                    'primary_class_id': primary_class.id,
                    'course_type': type,
                    'batch_id': self.student_id.batch_id.id,
                    'state': 'draft' if (prereq and coreq) else 'error',
                    'error': False if (prereq and coreq) else 'Prereq/Coreq Failed'
                }
                if self.student_id.batch_id.id == primary_class.batch_id.id:
                    data['scope'] = 'batch'
                elif self.student_id.program_id.id == primary_class.program_id.id:
                    data['scope'] = 'program'
                    data['course_batch_id'] = primary_class.batch_id.id
                elif self.student_id.institute_id.id == primary_class.institute_id.id:
                    data['scope'] = 'institute'
                    data['course_program_id'] = primary_class.program_id.id
                else:
                    data['scope'] = 'cross'
                    data['course_institute_id'] = primary_class.institute_id.id
                
                new_line.create(data)
        
        elif regs:   #  and registered
            data = {
                'registration_id': self.id,
                'primary_class_id': primary_class.id,
                'course_type': type,
                'batch_id': self.student_id.batch_id.id,
                'state': 'draft' if (prereq and coreq) else 'error',
                'error': False if (prereq and coreq) else 'Prereq/Coreq Failed',
                'action': 'drop' if registered else 'add',
            }
            new_line.create(data)
        return new_line

    def action_self_enroll_draft(self):
        for rec in self:
            rec._test_register_limit()

    def get_recheck_req(self):
        return False

    def add_course_lines(self):
        recheck_reqs = self.get_recheck_req()
        for rec in self:
            lines = rec.line_ids
            for primary_class in rec.compulsory_course_ids:
                lines -= rec.add_course(primary_class, 'compulsory', check_coreq=True, recheck_reqs=recheck_reqs)
            for primary_class in rec.elective_course_ids:
                lines -= rec.add_course(primary_class, 'elective', check_coreq=True, recheck_reqs=recheck_reqs)
            for primary_class in rec.spec_course_ids:
                lines -= rec.add_course(primary_class, 'elective', check_coreq=True)
            for primary_class in rec.repeat_course_ids:
                lines -= rec.add_course(primary_class, 'repeat', check_coreq=True)
            for primary_class in rec.improve_course_ids:
                lines -= rec.add_course(primary_class, 'improve', check_coreq=True)
            for primary_class in rec.additional_course_ids:
                lines -= rec.add_course(primary_class, 'additional', check_coreq=True)
            for primary_class in rec.alternate_course_ids:
                lines -= rec.add_course(primary_class, 'alternate', check_coreq=True)
            for primary_class in rec.minor_course_ids:
                lines -= rec.add_course(primary_class, 'minor', check_coreq=True)
            for course_id in rec.other_course_ids:
                new_line = self.env['odoocms.course.registration.line']
                data = {
                    'registration_id': self.id,
                    'course_id': course_id.id,
                    'course_type': 'project',
                    'batch_id': self.student_id.batch_id.id,
                    'state': 'draft',
                    'error': False,
                    'action': 'add',
                    'amount': self.other_course_amount
                }
                new_line.create(data)
                # lines -= new_line
            if len(lines) != len(rec.line_ids):
                lines.unlink()

    def action_submit(self, web=False):
        for rec in self:
            if not self.bypass_probation:
                probation_1_2 = self.env['odoocms.student.tag'].search([('code', 'in', ('probation_1', ('probation_2')))])
                probation_3_above_tags = self.env['odoocms.student.tag'].search([('code', 'like', 'probation_')]) - probation_1_2

                disposal_cat = self.env['odoocms.student.tag.category'].search([('code', '=', 'disposal')])
                if disposal_cat:
                    student_disposal_tag = self.student_id.tag_ids.filtered(lambda l: l.category_id.id == disposal_cat.id)
                    probation_tag = (student_disposal_tag and probation_3_above_tags and any(
                        tag in probation_3_above_tags for tag in student_disposal_tag) or False)
                    if probation_tag:
                        raise UserError('%s id on %s. Enrollment is not possible!' % (self.student_id.code, student_disposal_tag[-1:].name))

            rec._can_register()
            if rec.error:
                return rec.error
            if web:
                b = 5
            elif rec.source in ('office','bulk','bulk2'):
                rec.add_course_lines()

            elif rec.source == 'portal':
                b = 5
            
            # rec.with_user(self.env.user).line_ids.state = 'submit'
            # rec.with_user(self.env.user).write({
            #     'state': 'submit',
            #     'cnt': len(rec.line_ids),
            # })

            rec.line_ids.state = 'submit'
            rec.write({
                'state': 'submit',
                'cnt': len(rec.line_ids),
            })
            rec._test_register_limit()
            # rec._test_timetable()
        return 'Submitted Successfully'

    def action_reset_draft(self):
        for rec in self:
            rec.line_ids.state = 'draft'
            rec.state = 'draft'

    def action_reject(self):
        for rec in self:
            rec.line_ids.state = 'rejected'
            rec.state = 'rejected'

    def action_cancel(self):
        for rec in self:
            rec.line_ids.state = 'cancel'
            rec.state = 'cancel'
        
    def action_approve(self, manual=True):
        reg = self.env['odoocms.student.course']
        for rec in self:
            if not rec.line_ids:
                if not rec.bulk_id or not rec.bulk_id2:
                    rec.error = 'No New Registration request is there'
                    rec.state = 'error'
                    continue
                    # raise UserError('No New Registration request is there')
                else:
                    rec.error = 'No New Registration request is there'
                    rec.state = 'error'
                    continue
                    
            # Here we will add term_line_id instead of term_id
            # Check on Limit check is removed on 25-09-2023 on request of Aqeel
            if rec.get_recheck_req():
                rec._test_register_limit()
                if rec.limit_error:
                    return

            st_term = rec.student_id.get_student_term(rec.term_id)

            student_tags = rec.student_id.tag_ids.mapped('name')
            if 'Deferred' in student_tags:
                st_term.term_type = 'defer'
            if rec.student_id.state == 'extra' or 'Extra' in student_tags or 'Semester Deferment' in student_tags:
                st_term.term_type = 'extra'
                
            # line_count = len(rec.line_ids)
            # line_processed = 0
            
            # Repeat Limit - Times
            # if (record.student_id.repeat_courses_count + len(course_ids2) ) > record.student_id.career_id.repeat_course_limit:
            #     raise UserError('Repeat course limit for %s is %s and student have already repeated for %s times.'
            #         %(record.student_id.career_id.name, str(record.student_id.career_id.repeat_course_limit), str(record.student_id.repeat_courses_count),))
           
    #         allow_re_reg_wo_fee = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.allow_re_reg_wo_fee')
            allow_re_reg_wo_fee = True
            if (allow_re_reg_wo_fee == False):   #and (record.invoice_id and record.invoice_status == 'paid'):
                reg += rec.student_id.register_courses(rec.compulsory_course_ids, rec.term_id, st_term, rec.date_effective, 'compulsory')
                reg += rec.student_id.register_courses(rec.elective_course_ids, rec.term_id, st_term, rec.date_effective, 'elective')
                reg += rec.student_id.register_courses(rec.spec_course_ids, rec.term_id, st_term, rec.date_effective, 'elective')
                reg += rec.student_id.register_courses(rec.additional_course_ids, rec.term_id, st_term, rec.date_effective, 'additional')
                reg += rec.student_id.register_courses(rec.alternate_course_ids, rec.term_id, st_term, rec.date_effective, 'alternate')
                reg += rec.student_id.register_courses(rec.minor_course_ids, rec.term_id, st_term, rec.date_effective, 'minor')

            elif allow_re_reg_wo_fee == True:
                for line in rec.line_ids:
                    if line.action == 'add':
                        new_registration = rec.student_id.register_new_course(line, rec.term_id, st_term,rec.date_effective, strength_test=False)
                        if line.scope == 'cross':
                            continue
                        if new_registration.get('reg',False):
                            reg += new_registration.get('reg')
                            # line_processed += 1
                        elif new_registration.get('error',False):
                            rec.error = new_registration.get('error')
                            
                    elif line.action == 'drop':
                        registered_course = rec.student_id.enrolled_course_ids.filtered(lambda l: l.term_id.id == rec.term_id.id and l.primary_class_id.id == line.primary_class_id.id)
                        if registered_course:
                            registered_course.unlink()
                        line.state = 'approved'
                        # line_processed += 1

            if all(line.state == 'approved' for line in rec.line_ids):
                rec.state = 'approved'
            elif any(line.state == 'approved' for line in rec.line_ids):
                rec.state = 'part_approved'

            # Changed to above
            # if line_processed == line_count:
            #     rec.state = 'approved'
            # elif line_processed > 0:
            #     rec.state = 'part_approved'

        reg_list = reg.mapped('id')
        if manual:
            return {
                'domain': [('id', 'in', reg_list)],
                'name': _('Student Registration'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'odoocms.student.course',
                'view_id': False,
                # 'context': {'default_primary_class_id': self.id},
                'type': 'ir.actions.act_window'
            }
        else:
            return True

    def action_part_approve(self, manual=True):
        reg = self.env['odoocms.student.course']
        for rec in self:
            if not rec.line_ids:
                if not rec.bulk_id or not rec.bulk_id2:
                    rec.error = 'No New Registration request is there'
                    rec.state = 'error'
                    continue
                    # raise UserError('No New Registration request is there')
                else:
                    rec.error = 'No New Registration request is there'
                    rec.state = 'error'
                    continue

            # Here we will add term_line_id instead of term_id
            # Check on Limit check is removed on 25-09-2023 on request of Aqeel
            # if rec.get_recheck_req():
            #     rec._test_register_limit()
            #     if rec.limit_error:
            #         return

            st_term = rec.student_id.get_student_term(rec.term_id)

            student_tags = rec.student_id.tag_ids.mapped('name')
            if 'Deferred' in student_tags:
                st_term.term_type = 'defer'
            if rec.student_id.state == 'extra' or 'Extra' in student_tags or 'Semester Deferment' in student_tags:
                st_term.term_type = 'extra'

            # line_count = len(rec.line_ids)
            # line_processed = 0

            # Repeat Limit - Times
            # if (record.student_id.repeat_courses_count + len(course_ids2) ) > record.student_id.career_id.repeat_course_limit:
            #     raise UserError('Repeat course limit for %s is %s and student have already repeated for %s times.'
            #         %(record.student_id.career_id.name, str(record.student_id.career_id.repeat_course_limit), str(record.student_id.repeat_courses_count),))

            #         allow_re_reg_wo_fee = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.allow_re_reg_wo_fee')
            allow_re_reg_wo_fee = True
            if (allow_re_reg_wo_fee == False):  # and (record.invoice_id and record.invoice_status == 'paid'):
                reg += rec.student_id.register_courses(rec.compulsory_course_ids, rec.term_id, st_term, rec.date_effective, 'compulsory')
                reg += rec.student_id.register_courses(rec.elective_course_ids, rec.term_id, st_term, rec.date_effective, 'elective')
                reg += rec.student_id.register_courses(rec.spec_course_ids, rec.term_id, st_term, rec.date_effective, 'elective')
                reg += rec.student_id.register_courses(rec.additional_course_ids, rec.term_id, st_term, rec.date_effective, 'additional')
                reg += rec.student_id.register_courses(rec.alternate_course_ids, rec.term_id, st_term, rec.date_effective, 'alternate')
                reg += rec.student_id.register_courses(rec.minor_course_ids, rec.term_id, st_term, rec.date_effective, 'minor')

            elif allow_re_reg_wo_fee == True:
                for line in rec.line_ids.filtered(lambda l: l.state not in ('approved','rejected','cancel')):
                    if line.action == 'add':
                        new_registration = rec.student_id.register_new_course(line, rec.term_id, st_term,
                                                                              rec.date_effective, strength_test=False)
                        if line.scope == 'cross':
                            continue
                        if new_registration.get('reg', False):
                            reg += new_registration.get('reg')
                            # line_processed += 1
                        elif new_registration.get('error', False):
                            rec.error = new_registration.get('error')

                    elif line.action == 'drop':
                        registered_course = rec.student_id.enrolled_course_ids.\
                            filtered(lambda l: l.term_id.id == rec.term_id.id and l.primary_class_id.id == line.primary_class_id.id)
                        if registered_course:
                            registered_course.unlink()
                        line.state = 'approved'
                            # line_processed += 1

            # line_processed = len(rec.line_ids.filtered(lambda l: l.state == 'approved'))
            if all(line.state == 'approved' for line in rec.line_ids):
                rec.write({
                    'state': 'approved',
                    'error': False,
                })
            elif any(line.state == 'approved' for line in rec.line_ids):
                rec.state = 'part_approved'

            # if line_processed == line_count:
            #     rec.write({
            #         'state': 'approved',
            #         'error': False,
            #     })
            # elif line_processed > 0:
            #     rec.state = 'part_approved'

        reg_list = reg.mapped('id')
        if manual:
            return {
                'domain': [('id', 'in', reg_list)],
                'name': _('Student Registration'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'odoocms.student.course',
                'view_id': False,
                # 'context': {'default_primary_class_id': self.id},
                'type': 'ir.actions.act_window'
            }
        else:
            return True
    
    def _test_timetable(self):
        result = True
        registered_classes = self.env['odoocms.student.course'].search([
            ('student_id', '=', self.student_id.id),
            ('term_id', '=', self.term_id.id),
            ('grade', 'not in', ('W', 'F'))
        ]).mapped('primary_class_id').mapped('class_ids')
        new_classes = self.line_ids.mapped('primary_class_id').mapped('class_ids')
        classes = registered_classes + new_classes
        for rec in self.env['odoocms.timetable.schedule'].search([('class_id','in',classes.ids)]):
            if rec.term_id and rec.class_id and rec.week_day_ids:
                for weekday in rec.week_day_ids:
                    class_ids = self.env['odoocms.timetable.schedule'].search([
                        ('term_id', '=', rec.term_id.id),
                        ('class_id', 'in', classes.ids),
                        ('time_from', '<', rec.time_to), ('time_to', '>', rec.time_from),
                        ('id', '!=', rec.id)]).filtered(lambda l: weekday in (l.week_day_ids))
            
                    class_ids2 = self.env['odoocms.timetable.schedule'].search([
                        ('term_id', '=', rec.term_id.id),
                        ('class_id', 'in', classes.ids),
                        ('time_from', '=', rec.time_from), ('time_to', '=', rec.time_to),
                        ('id', '!=', rec.id)]).filtered(lambda l: weekday in (l.week_day_ids))
                    if class_ids:
                        raise UserError(_("There is another class (%s) in same time for Class %s"
                                          % (class_ids[0].class_id.name, rec.class_id.name)))
                    elif class_ids2:
                        raise UserError(_("There is another class (%s) in same time for Class %s"
                                          % (class_ids2[0].class_id.name, rec.batch_id.name)))

    # onchange_override_max_limit of odoocms.course.registration
    # action_self_enroll_draft of odoocms.course.registration
    # action_submit of odoocms.course.registration
    # action_approve of odoocms.course.registration
    # student_enrollment_cart_add - student portal
    # student_enrollment_cart - student portal
    def _test_register_limit(self, new_course = None, new_credit= None, course=None, coupled_course=None):
        registered_courses = self.env['odoocms.student.course'].search([
            ('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id), ('grade', 'not in', ('W', 'F'))])

        sum_credits, sum_non, sum_repeat, sum_courses, reg_credits, reg_courses, req_credits, req_courses, drop_credits, drop_courses = self._register_limit(registered_courses, self.line_ids)
        if not course or 'limit_exclude' not in course.course_id.tag_ids.mapped('code'):
            if new_course and new_course > 0:
                sum_courses += new_course
                sum_credits += new_credit
                reg_courses += new_course
                reg_credits += new_credit
                if coupled_course:
                    sum_credits += coupled_course.credits
                    reg_credits += coupled_course.credits

            elif new_course and new_course < 0:
                sum_courses -= abs(new_course)
                sum_credits -= abs(new_credit)
                drop_courses += abs(new_course)
                drop_credits += abs(new_credit)
            
        register_limits = self._get_register_limit()
        if sum_non > register_limits['non_credits'] and not self.override_max_limit:
            self.limit_error = True
            self.limit_error_text = 'Registration of (%s) Non-Credit Hours is not Possible. Allowed limit: (%s) CH' % (sum_non, register_limits['non_credits'])
    
        elif sum_repeat > register_limits['repeat_credits'] and not self.override_max_limit:
            self.limit_error = True
            self.limit_error_text = 'Registration of (%s) Repeat-Credit Hours is not Possible. Allowed limit: (%s) CH' % (sum_repeat, register_limits['repeat_credits'])
    
        elif sum_credits > register_limits['max_credits'] and not self.override_max_limit:
            self.limit_error = True
            self.limit_error_text = 'Registration of (%s) Credit Hours is not Possible. Maximum Allowed limit: (%s) CH' % (sum_credits, register_limits['max_credits'])
        elif sum_courses > register_limits['max_courses'] and not self.override_max_limit:
            self.limit_error = True
            self.limit_error_text = 'Registration of (%s) Course is not Possible. Maximum Allowed limit: (%s) ' % (sum_courses, register_limits['max_courses'])
        else:
            self.limit_error = False
            self.limit_error_text = ''
            
        return sum_credits, sum_courses, reg_credits, reg_courses, req_credits, req_courses, drop_credits, drop_courses, register_limits
    
    def _get_register_limit(self):
        min_credits = max_credits = non_credits = repeat_credits = max_courses = 0
        # Allowed
        global_load = self.env['odoocms.student.registration.load'].search([
            ('type', '=', self.term_id.type), ('default_global', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)])
        if global_load:
            global_load = global_load[0]
            min_credits = global_load.min
            max_credits = global_load.max
            non_credits = global_load.non
            repeat_credits = global_load.repeat
            max_courses = global_load.max_courses
    
        career_load = self.student_id.career_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type and not l.tag_id)
        if career_load:
            career_load = career_load[0]
            min_credits = career_load.min if career_load.min > 0 else min_credits
            max_credits = career_load.max if career_load.max > 0 else max_credits
            non_credits = career_load.non if career_load.non > 0 else non_credits
            repeat_credits = career_load.repeat if career_load.repeat > 0 else repeat_credits
            max_courses = career_load.max_courses if career_load.max_courses > 0 else max_courses
    
        program_load = self.student_id.program_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type and not l.tag_id)
        if program_load:
            program_load = program_load[0]
            min_credits = program_load.min if program_load.min > 0 else min_credits
            max_credits = program_load.max if program_load.max > 0 else max_credits
            non_credits = program_load.non if program_load.non > 0 else non_credits
            repeat_credits = program_load.repeat if program_load.repeat > 0 else repeat_credits
            max_courses = program_load.max_courses if program_load.max_courses > 0 else max_courses
    
        batch_load = self.student_id.batch_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type and not l.tag_id)
        if batch_load:
            batch_load = batch_load[0]
            min_credits = batch_load.min if batch_load.min > 0 else min_credits
            max_credits = batch_load.max if batch_load.max > 0 else max_credits
            non_credits = batch_load.non if batch_load.non > 0 else non_credits
            repeat_credits = batch_load.repeat if batch_load.repeat > 0 else repeat_credits
            max_courses = batch_load.max_courses if batch_load.max_courses > 0 else max_courses
    
        # tag_load = self.student_id.tag_ids.mapped('registration_load_ids').filtered(lambda l: l.type == self.term_id.type)
        # if tag_load:
        #     tag_load = tag_load[0]
        #     min_credits = tag_load.min if tag_load.min > 0 else min_credits
        #     max_credits = tag_load.max if tag_load.max > 0 else max_credits
        #     non_credits = tag_load.non if tag_load.non > 0 else non_credits
        #     repeat_credits = tag_load.repeat if tag_load.repeat > 0 else repeat_credits
    
        domain_loads = self.env['odoocms.student.registration.load'].search([
            ('type', '=', self.term_id.type),'|',('company_id','=',self.env.company.id),('company_id','=',False)]).filtered(lambda l: l.domain and l.domain != '[]')
        for domain_load in domain_loads:
            domain = expression.AND([safe_eval(domain_load.domain), [('id', '=', self.student_id.id)]]) if domain_load.domain else []
            domain_student = self.env['odoocms.student'].search(domain)
            if domain_student:
                min_credits = domain_load.min if domain_load.min > 0 else min_credits
                max_credits = domain_load.max if domain_load.max > 0 else max_credits
                non_credits = domain_load.non if domain_load.non > 0 else non_credits
                repeat_credits = domain_load.repeat if domain_load.repeat > 0 else repeat_credits
                max_courses = domain_load.max_courses if domain_load.max_courses > 0 else max_courses
                break
    
        student_load = self.student_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type and not l.tag_id)
        if student_load:
            student_load = student_load[0]
            min_credits = student_load.min if student_load.min > 0 else min_credits
            max_credits = student_load.max if student_load.max > 0 else max_credits
            non_credits = student_load.non if student_load.non > 0 else non_credits
            repeat_credits = student_load.repeat if student_load.repeat > 0 else repeat_credits
            max_courses = student_load.max_courses if student_load.max_courses > 0 else max_courses
    
        return {
            'min_credits': min_credits,
            'max_credits': max_credits,
            'non_credits': non_credits,
            'repeat_credits': repeat_credits,
            'max_courses': max_courses,
        }
    
    def _register_limit(self, registered_courses, reg_line_ids):
        sum_credits = sum_non = sum_repeat = sum_courses = reg_credits = reg_courses = req_credits = req_courses = drop_credits = drop_courses = 0
        reg_lines = reg_line_ids.filtered(lambda l: not l.student_course_id)
        to_drop_classes = reg_lines.filtered(lambda l:l.action == 'drop').mapped('primary_class_id')
        to_add_classes = reg_lines.filtered(lambda l: l.action == 'add').mapped('primary_class_id')
        final_courses = registered_courses.mapped('course_id') - to_drop_classes.mapped('course_id') + to_add_classes.mapped('course_id')

        for course in registered_courses:
            if 'limit_exclude' not in course.course_id.tag_ids.mapped('code'):
                sum_credits += course.primary_class_id.credits
                reg_credits += course.primary_class_id.credits
            
                if course.course_type in ('additional', 'minor'):
                    sum_non += course.primary_class_id.credits
                if course.course_type == 'repeat':
                    sum_repeat += course.primary_class_id.credits

                cnt = 1
                ssl = self.student_id.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == (course.course_id and course.course_id.id or course.primary_class_id.course_id.id))
                if not ssl:
                    ssl = course.primary_class_id.study_scheme_line_id

                coreq_course = ssl.coreq_course
                if len(coreq_course.component_lines) == 1 and len(ssl.component_lines) == 1 and ssl.component_lines[0].component == 'lab':
                    if coreq_course.course_id in final_courses:
                        cnt = 0
                elif len(coreq_course.component_lines) == 1 and len(ssl.component_lines) == 1 and ssl.component_lines[0].component == 'lecture':
                    if course.course_id in to_drop_classes.mapped('course_id'):
                        cnt = 0

                    # for course2 in registered_courses:
                    #     if course2.primary_class_id.class_type in ('regular', 'elective') and course2.primary_class_id.study_scheme_line_id:
                    #         ssl2 = course2.primary_class_id.study_scheme_line_id
                    #     elif course2.primary_class_id.class_type in ('summer', 'winter', 'special'):
                    #         ssl2 = self.student_id.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == course2.primary_class_id.course_id.id)
                    #
                    #     if ssl2 == coreq_course:
                    #         cnt = 0

                sum_courses += cnt
                reg_courses += cnt
    
        # for course in (self.compulsory_course_ids + self.elective_course_ids + self.alternate_course_ids):
        #     sum_credits += course.credits
        #
        # for course in (self.additional_course_ids + self.minor_course_ids):
        #     sum_credits += course.credits
        #     sum_non += course.credits
        #
        # for course in (self.repeat_course_ids):
        #     sum_credits += course.credits
        #     sum_repeat += course.credits

        for reg_line in reg_lines:  # (self.compulsory_course_ids + self.elective_course_ids + self.alternate_course_ids):
            if 'limit_exclude' not in reg_line.primary_class_id.course_id.tag_ids.mapped('code'):
                if reg_line.action == 'add':
                    sum_credits += reg_line.credits
                    req_credits += reg_line.credits
                elif reg_line.action == 'drop':
                    sum_credits -= reg_line.credits
                    drop_credits += reg_line.credits
            
                if reg_line.course_type in ('additional', 'minor'):
                    sum_non += reg_line.credits
                elif reg_line.course_type == 'repeat':
                    sum_repeat += reg_line.credits

                # if reg_line.action == 'add':
                cnt = 1
                ssl = self.student_id.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == reg_line.primary_class_id.course_id.id)
                if not ssl:
                    ssl = reg_line.primary_class_id.study_scheme_line_id

                if ssl and len(ssl.coreq_course.component_lines) == 1 and len(ssl.component_lines) == 1 and ssl.component_lines[0].component == 'lab':
                    if ssl.coreq_course.course_id in final_courses:
                        cnt = 0
                elif ssl and len(ssl.coreq_course.component_lines) == 1 and len(ssl.component_lines) == 1 and ssl.component_lines[0].component == 'lecture':
                    if reg_line.course_id in to_drop_classes.mapped('course_id'):
                        cnt = 0

                    # for reg_line2 in self.line_ids:
                    #     if reg_line2.primary_class_id.class_type in ('regular', 'elective') and reg_line2.primary_class_id.study_scheme_line_id:
                    #         ssl2 = reg_line2.primary_class_id.study_scheme_line_id
                    #     elif reg_line2.primary_class_id.class_type in ('summer', 'winter', 'special'):
                    #         ssl2 = self.student_id.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == reg_line2.primary_class_id.course_id.id)
                    #
                    #     if ssl2 == coreq_course:
                    #         cnt = 0
                    # for course2 in registered_courses:
                    #     if course2.primary_class_id.class_type in ('regular', 'elective') and course2.primary_class_id.study_scheme_line_id:
                    #         ssl2 = course2.primary_class_id.study_scheme_line_id #reg_line2.primary_class_id.study_scheme_line_id
                    #     elif course2.primary_class_id.class_type in ('summer', 'winter', 'special'):
                    #         ssl2 = self.student_id.study_scheme_id.line_ids.filtered(lambda l: l.course_id.id == course2.primary_class_id.course_id.id)
                    #
                    #     if ssl2 == coreq_course:
                    #         cnt = 0

                if reg_line.action == 'add':
                    sum_courses += cnt
                    req_courses += cnt
                elif reg_line.action == 'drop':    # removed to test if it works otherwise enable it and remove the aboove if at line 968
                    sum_courses -= cnt
                    drop_courses += cnt

        return sum_credits, sum_non, sum_repeat, sum_courses, reg_credits, reg_courses, req_credits, req_courses, drop_credits, drop_courses


class OdooCMSCourseRegistrationLine(models.Model):
    _name = "odoocms.course.registration.line"
    _description = 'Enrollment Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'student_id'
    
    sequence = fields.Integer('sequence')
    registration_id = fields.Many2one('odoocms.course.registration','Registration ID')
    student_id = fields.Many2one('odoocms.student','Student',related='registration_id.student_id',store=True)
    term_id = fields.Many2one('odoocms.academic.term','Academic Term',related='registration_id.term_id',store=True)
    primary_class_id = fields.Many2one('odoocms.class.primary','Primary Class', ondelete='cascade')
    course_id = fields.Many2one('odoocms.course','Course', compute='_get_data', store=True, readonly=False, ondelete='cascade')
    course_code = fields.Char('Course Code', compute='_get_data', store=True)
    credits = fields.Float('Credit Hours', compute='_get_data' ,store=True)
    course_type = fields.Selection([
        ('compulsory','Core Course'),('elective','Elective'),
        ('repeat','Repeat'),('improve','Improve'),('additional','Additional'),
        ('alternate','Alternate'),('minor','Minor'),('project','Project')],'Course Type',default='compulsory'
    )
    scope = fields.Selection([
        ('batch','Batch'),('program','Program'),
        ('institute','Institute'),('cross','Cross')],'Scope',default='batch')
    
    batch_id = fields.Many2one('odoocms.batch','Student Batch', compute='_get_data', store=True)
    program_id = fields.Many2one('odoocms.program','Student Program', compute='_get_data', store=True)
    department_id = fields.Many2one('odoocms.department','Department/Center', compute='_get_data', store=True)
    
    course_batch_id = fields.Many2one('odoocms.batch', 'Course Batch')
    course_program_id = fields.Many2one('odoocms.program', 'Program')
    course_institute_id = fields.Many2one('odoocms.institute', 'Institute')

    student_course_id = fields.Many2one('odoocms.student.course','Student Course')
    cross_id = fields.Many2one('odoocms.course.registration.cross','Cross Request')
    error = fields.Text('Error')
    action = fields.Selection([('add','Add'),('drop','Drop')], 'Action', default='add')
    amount = fields.Float('Amount')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approval1', '1st Approval'),
        ('approval2', '2nd Approval'),
        ('error', 'Error'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('cancel','Cancel')], default='draft', string='Status', copy=False, tracking=True)
    strength = fields.Integer('Strength')
    company_id = fields.Many2one('res.company', string='Company', related='registration_id.company_id', store=True)

    @api.depends('primary_class_id','student_id')
    def _get_data(self):
        for rec in self:
            rec.write({
                'course_id': rec.primary_class_id.course_id.id,
                'course_code': rec.primary_class_id.course_code,
                'credits': rec.primary_class_id.credits,
                'batch_id': rec.student_id.batch_id.id,
                'program_id': rec.student_id.program_id.id,
                'department_id': rec.student_id.program_id.department_id.id,
            })

    def _get_reg_sequence(self):
        last_class = 0
        last_sequence = 0
        sql = """
            select id,primary_class_id from odoocms_course_registration_line where term_id = 194 order by primary_class_id,create_date
        """
        self.env.cr.execute(sql)
        recs = self.env.cr.fetchall()

        # recs = self.env['odoocms.course.registration.line'].search([('term_id','=',194)], order='primary_class_id, create_date')
        for rec in recs:
            row = self.env['odoocms.course.registration.line'].search([('id', '=', rec[0])])
            if rec[1] == last_class:
                last_sequence = last_sequence + 1
            else:
                last_sequence = 1
                last_class = row.primary_class_id.id

            row.sequence = last_sequence


class OdooCMSCourseRegistrationLineDrop(models.Model):
    _name = "odoocms.course.registration.line.drop"
    _description = 'Dropped Enrollment Lines'
    
    student_id = fields.Many2one('odoocms.student', 'Student')
    request_id = fields.Many2one('odoocms.course.registration','Registration Request')
    dropped_course_id = fields.Many2one('odoocms.class.primary', 'Dropped Course', ondelete='cascade')


class OdooCMSCourseRegistrationCross(models.Model):
    _name = "odoocms.course.registration.cross"
    _description = 'Cross Enrollment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'
    
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
        index=True, default=lambda self: _('New'))

    student_id = fields.Many2one('odoocms.student', 'Student')
    batch_id = fields.Many2one('odoocms.batch', 'Batch',related='student_id.batch_id',store=True)
    program_id = fields.Many2one('odoocms.program', 'Student Program',related='batch_id.program_id',store=True)
    department_id = fields.Many2one('odoocms.department', 'Department/Center', related='program_id.department_id', store=True)
    
    primary_class_id = fields.Many2one('odoocms.class.primary', 'Primary Class', ondelete='restrict')
    course_code = fields.Char('Course Code', related='primary_class_id.course_code', store=True)
    credits = fields.Float('Credit Hours', related='primary_class_id.credits', store=True)
    course_type = fields.Selection([
        ('compulsory', 'Core Course'), ('elective', 'Elective'),
        ('repeat', 'Repeat'), ('improve', 'Improve'),('additional', 'Additional'),
        ('alternate', 'Alternate'), ('minor', 'Minor')], 'Course Type', default='compulsory'
    )
    
    course_batch_id = fields.Many2one('odoocms.batch', 'Course Batch', related='primary_class_id.batch_id', store=True)
    course_program_id = fields.Many2one('odoocms.program', 'Program', related='course_batch_id.program_id', store=True)
    course_institute_id = fields.Many2one('odoocms.institute', 'Institute', related='course_program_id.institute_id', store=True)

    registration_line_id = fields.Many2one('odoocms.course.registration.line', 'Registration ID')
    student_course_id = fields.Many2one('odoocms.student.course', 'Student Course',related='registration_line_id.student_course_id',store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approval', 'Approval'),
        ('error', 'Error'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected')], default='draft', string='Status', copy=False, tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.course.registration.cross') or _('New')
            result = super().create(vals)
        return result

    def action_submit(self):
        activity = self.env.ref('odoocms_registration.mail_act_cross_registration')
        self.activity_schedule('odoocms_registration.mail_act_cross_registration', user_id=activity._get_role_users(self.sudo().program_id))
        self.registration_line_id.state = 'approval1'
        self.state = 'submit'

    def action_1st_approval(self):
        activity = self.env.ref('odoocms_registration.mail_act_cross_registration2')
        self.activity_schedule('odoocms_registration.mail_act_cross_registration2', user_id=activity._get_role_users(self.sudo().course_program_id))
        self.registration_line_id.state = 'approval2'
        self.state = 'approval'
        
    def action_approval(self):
        self = self.sudo()
        st_term = self.student_id.get_student_term(self.registration_line_id.registration_id.term_id)

        new_registration = self.student_id.register_new_course(
            self.registration_line_id, self.registration_line_id.registration_id.term_id, st_term, self.registration_line_id.registration_id.date_effective)
        if new_registration.get('reg', False):
            self.registration_line_id.state = 'approved'
            self.state = 'approved'
        
    def action_cancel(self):
        self.registration_line_id.state = 'rejected'
        self.state = 'rejected'


class OdooCMSCourseRegistrationCrossOffice(models.Model):
    _name = "odoocms.course.registration.cross.office"
    _description = 'Cross Enrollment - Office'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name desc'

    READONLY_STATES = {
        'submit': [('readonly', True)],
        'done': [('readonly', True)],
        'rejected': [('readonly', True)],
    }
    
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: _('New'))
    reg = fields.Char('Registration',required=True,states=READONLY_STATES)
    student_id = fields.Many2one('odoocms.student', 'Student',readonly=True, compute='_get_student',store=True)
    batch_id = fields.Many2one('odoocms.batch', 'Batch', related='student_id.batch_id', store=True)
    program_id = fields.Many2one('odoocms.program', 'Student Program', related='batch_id.program_id', store=True)
    department_id = fields.Many2one('odoocms.department', 'Department/Center', related='program_id.department_id', store=True)

    term_id = fields.Many2one('odoocms.academic.term', 'Term', required=True, states=READONLY_STATES)
    primary_class_id = fields.Many2one('odoocms.class.primary', 'Primary Class', ondelete='restrict',states=READONLY_STATES)
    course_code = fields.Char('Course Code', related='primary_class_id.course_code', store=True)
    credits = fields.Float('Credit Hours', related='primary_class_id.credits', store=True)
    course_type = fields.Selection([
        ('compulsory', 'Core Course'), ('elective', 'Elective'),
        ('repeat', 'Repeat'), ('improve', 'Improve'), ('additional', 'Additional'),
        ('alternate', 'Alternate'), ('minor', 'Minor')], 'Course Type', default='compulsory', states=READONLY_STATES)

    course_batch_id = fields.Many2one('odoocms.batch', 'Course Batch', related='primary_class_id.batch_id', store=True)
    course_program_id = fields.Many2one('odoocms.program', 'Program', related='course_batch_id.program_id', store=True)
    course_institute_id = fields.Many2one('odoocms.institute', 'Institute', related='course_program_id.institute_id', store=True)

    student_course_id = fields.Many2one('odoocms.student.course', 'Student Course',readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('error', 'Error'),
        ('done', 'Done'),
        ('rejected', 'Rejected')], default='draft', string='Status', copy=False, tracking=True)

    reg_date = fields.Date('Date', default=(fields.Date.today()), readonly=True)
    date_effective = fields.Date('Effective Date', default=(fields.Date.today()),states=READONLY_STATES)
    error = fields.Text('Error')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.course.registration.cross.office') or _('New')
            result = super().create(vals)
        return result

    @api.depends('reg')
    def _get_student(self):
        if self.reg:
            student = self.env['odoocms.student'].sudo().search([('code','=',self.reg)])
            no_reg_tags = self.env['odoocms.student.tag'].search(
                [('block_registration', '=', True)])  # ('graduate_line', '=', True),
            reg_student = self.env['odoocms.student'].sudo().search([
                ('code','=',self.reg), ('state', 'in', ('enroll', 'extra')), '!', ('tag_ids', 'in', no_reg_tags.ids)
            ])
            if not reg_student:
                raise UserError('Registration for this student is not Allowed')
            if student and len(student) == 1:
                self.student_id = student.id

    @api.onchange('term_id', 'student_id')
    def _can_register(self):
        if self.term_id and self.student_id and not self.student_id.batch_id.can_apply('enrollment', self.term_id, admin=True):
            self.error = 'Date Over'
        else:
            self.error = None
            
    def action_submit(self):
        self.state = 'submit'
        
    def action_register(self):
        student = self.student_id.sudo()
        st_term = student.get_student_term(self.term_id)

        new_registration = student.register_cross_course_office(self.primary_class_id, self.term_id, st_term, self.course_type, self.date_effective)
        if new_registration.get('reg', False):
            new_reg = new_registration.get('reg')
            self.student_course_id = new_reg.id
            self.state = 'done'
        elif new_registration.get('error', False):
            raise UserError(new_registration.get('error'))
        
    def action_cancel(self):
        self.state = 'rejected'
    
    # Remarked lines of Master table
    # @api.onchange('student_id','term_id')
    # def get_subjects(self):
    #     res = {}
    #     record = self
    #     if record.student_id and record.term_id:
    #         student = record.student_id
    #         new_semester = record.term_id
    #
    #         record.compulsory_course_ids = False
    #         record.elective_course_ids = False
    #         record.repeat_course_ids = False
    #
    #         # If Student does not have any academic semester
    #         if not student.term_id:
    #             semester_scheme = self.env['odoocms.semester.scheme'].search([
    #                 ('academic_session_id', '=', student.academic_session_id.id),
    #                 ('term_id', '=', new_semester.id)
    #             ])
    #             if not semester_scheme:
    #                 raise ValidationError("""Semester Scheme not defined for Session: %s \n Term: %s \n Student: %s """ % (
    #                     student.academic_session_id.name, new_semester.name, student.name))
    #             if semester_scheme.semester_id.number > 1:
    #                 raise ValidationError("""Direct Registration is not possible for Semester: %s \n Term: %s \n Student: %s """ % (
    #                     semester_scheme.semester_id.name, new_semester.name, student.name))
    #
    #             # student.term_id = semester_scheme.term_id.id
    #             # student.semester_id = semester_scheme.semester_id.id
    #
    #         # If Student Academic Semester and reistration semester are same
    #         elif student.term_id.id == new_semester.id:
    #             semester_scheme = self.env['odoocms.semester.scheme'].search([
    #                 ('academic_session_id', '=', student.academic_session_id.id),
    #                 ('term_id', '=', new_semester.id)
    #             ])
    #             if not semester_scheme:
    #                 raise ValidationError("""Semester Scheme not defined for Session: %s \n Term: %s \n Student: %s """ % (
    #                     student.academic_session_id.name, new_semester.name, student.name))
    #
    #             if not student.semester_id:
    #                 if semester_scheme.semester_id.number > 1:
    #                     raise ValidationError("""Direct Registration is not possible for Semester: %s \n Term: %s \n Student: %s """ % (
    #                         semester_scheme.semester_id.name, new_semester.name, student.name))
    #                 # student.semester_id = semester_scheme.semester_id.id
    #
    #         # If Student Academic Semester and reistration semester are not same
    #         elif student.term_id.id != new_semester.id:
    #             semester_scheme = self.env['odoocms.semester.scheme'].search([
    #                 ('academic_session_id', '=', student.academic_session_id.id),
    #                 ('term_id', '=', new_semester.id)
    #             ])
    #             if not semester_scheme:
    #                 raise ValidationError("""Semester Scheme not defined for Session: %s \n Term: %s \n Student: %s """ % (
    #                     student.academic_session_id.name, new_semester.name, student.name))
    #
    #             if not student.semester_id:
    #                 raise ValidationError("""Direct Promotion is not possible for Semester: %s \n Term: %s \n Student: %s """ % (
    #                     semester_scheme.semester_id.name, new_semester.name, student.name))
    #
    #             current_semester_number = student.semester_id.number
    #             next_semester_number = current_semester_number + 1
    #             next_semester = self.env['odoocms.semester'].search([('number', '=', next_semester_number)])
    #             if not next_semester:
    #                 return False
    #
    #             next_semester_scheme = self.env['odoocms.semester.scheme'].search([
    #                 ('academic_session_id', '=', student.academic_session_id.id),
    #                 ('semester_id', '=', next_semester.id)
    #             ])
    #
    #             if semester_scheme.semester_id.number != next_semester_scheme.semester_id.number:
    #                 raise ValidationError("""Promotion is not possible: \nFrom Semester: %s (%s) \nTo Semester: %s (%s) \nStudent: %s """ % (
    #                     student.term_id.name,student.semester_id.name,
    #                     semester_scheme.term_id.name, semester_scheme.semester_id.name, student.name))
    #
    #             # student.term_id = new_semester.id
    #             # student.semester_id = next_semester.id
    #
    #         classes = student.get_possible_classes(new_semester)[0]
    #         #record.registered_course_ids = [(6, 0, registered_class_ids.ids)]
    #
    #         res['domain'] = {
    #             'compulsory_course_ids': [('id', 'in', classes['comp_class_ids'] and len(classes['comp_class_ids']) > 0 and classes['comp_class_ids'].ids or [])],
    #             'elective_course_ids': [('id', 'in', classes['elec_class_ids'] and len(classes['elec_class_ids']) > 0 and classes['elec_class_ids'].ids or [])],
    #             'repeat_course_ids': [('id', 'in', classes['offered_f'] and len(classes['offered_f']) > 0 and classes['offered_f'].ids or [])],
    #             'additional_course_ids': [('id', 'in', classes['additional_class_ids'] and len(classes['additional_class_ids']) > 0 and classes['additional_class_ids'].ids or [])],
    #         }
    #     return res
    #
    #
    # def action_invoice(self):
    #     re_reg_receipt_type = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.re_reg_receipt_type')
    #     if not re_reg_receipt_type:
    #         raise UserError('Please configure the Re-Registration Receipt Type in Global Settings')
    #
    #     view_id = self.env.ref('odoocms_fee.view_odoocms_generate_invoice_form')
    #     return {
    #         'name': _('Subject Registration Invoice'),
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'odoocms.generate.invoice',
    #         'view_id': view_id.id,
    #         'views': [(view_id.id, 'form')],
    #         'context': {
    #             'default_fixed_type': True,
    #             'default_receipt_type_ids': [(4, eval(re_reg_receipt_type), None)]},
    #         'target': 'new',
    #         'type': 'ir.actions.act_window'
    #     }
    #
    #

    #
    # def write(self, vals):
    #     # old_compulsory_course_ids = ', '.join([k.name for k in self.compulsory_course_ids])
    #     # old_elective_course_ids = ', '.join([k.name for k in self.elective_course_ids])
    #     # old_repeat_course_ids = ', '.join([k.name for k in self.repeat_course_ids])
    #
    #     old_compulsory_course_ids = self.compulsory_course_ids
    #     old_elective_course_ids = self.elective_course_ids
    #     old_repeat_course_ids = self.repeat_course_ids
    #     old_additional_course_ids = self.additional_course_ids
    #
    #     super(OdooCMSCourseRegistration, self).write(vals)
    #
    #     # new_compulsory_course_ids = ', '.join([k.name for k in self.compulsory_course_ids])
    #     # new_elective_course_ids = ', '.join([k.name for k in self.elective_course_ids])
    #     # new_repeat_course_ids = ', '.join([k.name for k in self.repeat_course_ids])
    #
    #     # if old_compulsory_course_ids != new_compulsory_course_ids:
    #     #     self.message_post(body="<b>Core Courses:</b> %s &#8594; %s" % (old_compulsory_course_ids, new_compulsory_course_ids))
    #     # if old_elective_course_ids != new_elective_course_ids:
    #     #     self.message_post(body="<b>Core Courses:</b> %s &#8594; %s" % (old_elective_course_ids, new_elective_course_ids))
    #     # if old_repeat_course_ids != new_repeat_course_ids:
    #     #     self.message_post(body="<b>Core Courses:</b> %s &#8594; %s" % (old_repeat_course_ids, new_repeat_course_ids))
    #
    #     message = ''
    #     if self.compulsory_course_ids - old_compulsory_course_ids:
    #         message += "<b>Core Courses Added:</b> %s<br/>" % (
    #                 ', '.join([k.name for k in (self.compulsory_course_ids - old_compulsory_course_ids)]))
    #
    #     if old_compulsory_course_ids - self.compulsory_course_ids:
    #         message += "<b>Core Courses Removed:</b> %s\n" % (
    #                  ', '.join([k.name for k in (old_compulsory_course_ids - self.compulsory_course_ids)]))
    #
    #     if self.elective_course_ids - old_elective_course_ids:
    #         message += "<b>Elective Courses Added:</b> %s<br/>" % (
    #                 ', '.join([k.name for k in (self.elective_course_ids - old_elective_course_ids)]))
    #
    #
    #     if old_elective_course_ids - self.elective_course_ids:
    #         message += "<b>Elective Courses Removed:</b> %s<br/>" % (
    #                 ', '.join([k.name for k in (old_elective_course_ids - self.elective_course_ids)]))
    #
    #
    #     if self.repeat_course_ids - old_repeat_course_ids:
    #         message += "<b>Failed Courses Added:</b> %s<br/>" % (
    #                 ', '.join([k.name for k in (self.repeat_course_ids - old_repeat_course_ids)]))
    #
    #     if old_repeat_course_ids - self.repeat_course_ids:
    #         message += "<b>Failed Courses Removed:</b> %s<br/>" % (
    #                 ', '.join([k.name for k in (old_repeat_course_ids - self.repeat_course_ids)]))
    #
    #
    #     if self.additional_course_ids - old_additional_course_ids:
    #         message += "<b>Additional Courses Added:</b> %s<br/>" % (
    #             ', '.join([k.name for k in (self.additional_course_ids - old_additional_course_ids)]))
    #
    #     if old_additional_course_ids - self.additional_course_ids:
    #         message += "<b>Additional Courses Removed:</b> %s\n" % (
    #             ', '.join([k.name for k in (old_additional_course_ids - self.additional_course_ids)]))
    #
    #     if message:
    #         self.message_post(body=message)
    #
    #     return True


class OdooCMSCourseRegistrationMust(models.Model):
    _name = "odoocms.course.registration.must"
    _description = 'Course Registration - Must'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    # _order = 'name desc'
    
    term_id = fields.Many2one('odoocms.academic.term','Academic Term', required=1)
    batch_id = fields.Many2one('odoocms.batch','Batch')
    course_id = fields.Many2one('odoocms.study.scheme.line','Course')
    active = fields.Boolean(default=True)

    @api.onchange('batch_id')
    def onchagene_batch_id(self):
        domain = [('id', '=', 0)]
        if self.batch_id:
            ss = self.batch_id.study_scheme_id
            domain = [('id', 'in', ss.line_ids.ids)]
        return {
            'domain': {
                'course_id': domain
            },
        }
    
    
