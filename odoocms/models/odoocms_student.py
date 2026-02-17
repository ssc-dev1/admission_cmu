from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.osv import expression
from dateutil.relativedelta import relativedelta
import logging

import pdb
import sys
import ftplib
import os
import time
import codecs
from datetime import datetime, date

_logger = logging.getLogger(__name__)


class OdooCMSStudentTagCategory(models.Model):
    _name = 'odoocms.student.tag.category'
    _description = 'Student Tag Category'

    name = fields.Char(string="Category Tag", required=True)
    code = fields.Char('Category Code')
    multiple = fields.Boolean(string='Is multiple?')
    
    group_ids = fields.Many2many('res.groups', 'student_tag_category_group_rel', 'tag_category_id', 'group_id', 'Groups')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Tag Category already exists !"),
        ('code_uniq', 'unique(code)', "Tag Category Code already exists !"),
    ]

    @api.model
    def get_serving_groups(self):
        groups = []
        for group in self.group_ids:
            domain = [('model', '=', 'res.groups'), ('res_id', '=', group.id)]
            model_data = self.env['ir.model.data'].sudo().search(domain, limit=1)
            xml_id = "%s.%s" % (model_data.module, model_data.name)
            groups.append(xml_id)
        return groups
       

class OdooCMSStudentTag(models.Model):
    _name = 'odoocms.student.tag'
    _description = 'Student Tag'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Student Tag", required=True)
    code = fields.Char('Tag Code')
    color = fields.Integer(string='Color Index')
    category_id = fields.Many2one('odoocms.student.tag.category', string='Category')
    category_code = fields.Char(related='category_id.code', store=True)
    
    exclude_fee = fields.Boolean('Exclude Fee', default=False)
    block = fields.Boolean('Block Student', default=False)
    block_registration = fields.Boolean('Block Registration', default=False, help='Student cannot Register any Course')
    no_new_registration = fields.Boolean('No New Registration', default=False, help='Students can register only Failed and/or Improvement Courses')
    time_lapsed = fields.Boolean('Time Lapsed',default=False, help='Expired Time Period')
    graduate_line = fields.Boolean('Graduate Tag',default=False, help='Graduate Line')
    vis_line = fields.Boolean('VIS Tag',default=False, help='Graduate Line')

    student_ids = fields.Many2many('odoocms.student', 'student_tag_rel', 'tag_id', 'student_id', string='Group/Tag')
    group_ids = fields.Many2many('res.groups', 'student_tag_group_rel', 'tag_id', 'group_id', 'Groups')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "Tag name already exists !"),
        ('code_uniq', 'unique(code)', "Tag code already exists !"),
    ]

    @api.model
    def get_serving_groups(self):
        groups = []
        for group in self.group_ids:
            domain = [('model', '=', 'res.groups'), ('res_id', '=', group.id)]
            model_data = self.env['ir.model.data'].sudo().search(domain, limit=1)
            xml_id = "%s.%s" % (model_data.module, model_data.name)
            groups.append(xml_id)
        return groups

    
class OdooCMSStudent(models.Model):
    _name = 'odoocms.student'
    _description = 'Student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'res.partner': 'partner_id'}
    _order = 'code, id_number'

    # @api.depends('first_name', 'last_name')
    # def _get_student_name(self):
    #     for student in self:
    #         student.name = (student.first_name or '') + ' ' + (student.last_name or '')
    @api.depends('first_name', 'middle_name', 'last_name')
    def _get_student_name(self):
        for student in self:
            name = student.first_name or ''
            if student.middle_name:
                name = name + ' ' + student.middle_name
            if student.last_name:
                name = name + ' ' + student.last_name
            student.name = name
    def _valid_field_parameter(self, field, name):
        # I can't even
        return name == 'tracking' or super()._valid_field_parameter(field, name)
    
    # added father/guardian CNIC
    fee_enable = fields.Boolean()  # compute='_compute_fee_enable',store=True
    father_guardian_cnic = fields.Char(string="Father/Guardian CNIC", size=15)
    
    first_name = fields.Char('First Name', required=True, tracking=True)
    last_name = fields.Char('Last Name', tracking=True)

    father_name = fields.Char(string="Father Name", tracking=True)
    father_status = fields.Selection([('alive', 'Alive'), ('deceased', 'Deceased'), ('shaheed', 'Shaheed'), ('other', 'Other')], 'Father Status', default='alive')
    father_profession = fields.Many2one('odoocms.profession', 'Father Profession')
    father_income = fields.Integer('Father Income')
    father_cell = fields.Char('Father Cell')

    mother_name = fields.Char(string="Mother Name", tracking=True)
    mother_status = fields.Selection([('alive', 'Alive'), ('deceased', 'Deceased'), ('shaheed', 'Shaheed'), ('other', 'Other')], 'Mother Status', default='alive')
    mother_profession = fields.Many2one('odoocms.profession', 'Mother Profession')
    mother_income = fields.Integer('Mother Income')
    mother_cell = fields.Char('Mother Cell')

    first_generation_studying = fields.Boolean('First Generation Studying', default=False)
    cnic = fields.Char('CNIC', size=15, tracking=True)
    cnic_expiry_date = fields.Date('CNIC Expiry Date')

    disability = fields.Boolean('Disability', default=False)
    disability_detail = fields.Char('Disability Detail')

    passport_no = fields.Char('Passport Number', tracking=True)
    passport_issue_date = fields.Date("Passport Issue Date")
    passport_expiry_date = fields.Date('Passport Expiry Date', tracking=True)
    
    u_id_no = fields.Char("U.I.D")   # Recheck
    
    visa_info = fields.Char('Visa Info')
    visa_issue_date = fields.Date("Visa Issue Date")
    visa_expiry_date = fields.Date('Visa Expiry Date', tracking=True)
    domicile_id = fields.Many2one('odoocms.domicile', 'Domicile', tracking=True)

    date_of_birth = fields.Date('Birth Date', required=True, tracking=True,
        default=lambda self: self.compute_previous_year_date(fields.Date.context_today(self)))
    gender = fields.Selection([('m', 'Male'), ('f', 'Female'), ('o', 'Other')], 'Gender', required=True, tracking=True)
    marital_status = fields.Many2one('odoocms.marital.status', 'Marital Status', tracking=True)
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-', 'O-ve'), ('AB-', 'AB-ve'),('N', 'Not Known')],
        'Blood Group', tracking=True)
    religion_id = fields.Many2one('odoocms.religion', string="Religion", tracking=True)
    nationality = fields.Many2one('res.country', string='Nationality', ondelete='restrict', tracking=True)
    nationality_name = fields.Char(related='nationality.name', store=True)

    net_stream = fields.Selection([('open', 'Open'), ('SATN', 'SATN'), ('SATI', 'SATI')], 'NET Stream')
    inter_stream = fields.Selection([('OA', 'A Level'), ('FSC', 'FSC'), ('diploma', 'Diploma'), ('bachelor', 'Bachelor'), ('masters', 'Masters'), ('doctoral', 'Doctoral')], 'Intermediate Stream')
    pbnet_cbnet = fields.Selection([('pbnet', 'PBNET'), ('cbnet', 'CBNET')], 'PBNET/CBNET')

    admission_no = fields.Char(string="Admission Number")
    id_number = fields.Char('Student ID', size=64, tracking=True)
    entryID = fields.Char('Entry ID', size=64, tracking=True)
    entry_date = fields.Date('Entry Date')
    
    code = fields.Char(compute='_get_code', store=True, tracking=True)
    merit_no = fields.Char('Merit No.')
    urban_rural = fields.Selection([('urban', 'Urban'), ('rural', 'Rural')], 'Urban/Rural')
    pc_cadet = fields.Boolean('PC Cadet', default=False)

    emergency_contact = fields.Char('Emergency Contact', tracking=True)
    emergency_mobile = fields.Char('Emergency Mobile', tracking=True)
    emergency_email = fields.Char('Emergency Email', tracking=True)
    emergency_address = fields.Char('Em. Address', tracking=True)
    emergency_city = fields.Char('Em. Street', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', related='campus_id.company_id', store=True)

    is_same_address = fields.Boolean(string="Is same Address?", tracking=True)
    per_street = fields.Char()
    per_street2 = fields.Char()
    per_city = fields.Char()
    per_zip = fields.Char(change_default=True)
    per_state_id = fields.Many2one("res.country.state", string='Per State', ondelete='restrict',
        domain="[('country_id', '=?', per_country_id)]")
    per_country_id = fields.Many2one('res.country', string='Per. Country', ondelete='restrict')

    guardian_name = fields.Char('Guardian Name')
    guardian_mobile = fields.Char('Guardian Mobile')
    guardian_cnic = fields.Char(string="Guardian CNIC", size=15)

    tag_ids = fields.Many2many('odoocms.student.tag', 'student_tag_rel', 'student_id', 'tag_id', string='Group/Tag')

    partner_id = fields.Many2one('res.partner', 'Partner', required=True, ondelete="cascade")

    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    career_id = fields.Many2one('odoocms.career', 'Career/Degree Level', readonly=True, states={'draft': [('readonly', False)]})
    program_id = fields.Many2one('odoocms.program', 'Academic Program', tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    department_id = fields.Many2one('odoocms.department', string="Department/Center", related='program_id.department_id', store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute/Faculty', related='program_id.institute_id', store=True)
    discipline_id = fields.Many2one('odoocms.discipline', 'Discipline')
    campus_id = fields.Many2one('odoocms.campus', 'Campus', related='institute_id.campus_id', store=True)
    specialization_id = fields.Many2one('odoocms.specialization', string='Specialization')
    
    campus_code = fields.Char(string='Campus Code', related='campus_id.code', store=True)
    institute_code = fields.Char(string='Institute/Faculty Code', related='institute_id.code', store=True)
    department_code = fields.Char(string='Department/Center Code', related='department_id.code', store=True)
    program_code = fields.Char(string='Program Code', related='program_id.code', store=True)
    career_code = fields.Char(string='Caeeer Code', related='career_id.code', store=True)

    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', tracking=True, readonly=True, states={'draft': [('readonly', False)]}, ondelete='restrict')
    study_scheme_id = fields.Many2one('odoocms.study.scheme', 'Study Scheme', compute='_get_study_scheme', store=True, ondelete='restrict')
    minor_scheme_id = fields.Many2one('odoocms.study.scheme', 'Minor Scheme', tracking=True, readonly=True, states={'draft': [('readonly', False)]})

    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term', readonly=True, states={'draft': [('readonly', False)]}, ondelete='restrict')
    semester_id = fields.Many2one('odoocms.semester', 'Semester')

    academic_ids = fields.One2many('odoocms.student.academic', 'student_id', 'Academics')
    stream_id = fields.Many2one('odoocms.program.stream', 'Stream')

    new_id_number = fields.Char('New Student ID', size=64)

    award_ids = fields.One2many('odoocms.award', 'student_id', 'Honor/Awards')
    publication_ids = fields.One2many('odoocms.publication', 'student_id', 'Publications')

    language_ids = fields.Many2many('odoocms.language', string='Languages')
    extra_activity_ids = fields.One2many('odoocms.extra.activity', 'student_id', 'Extra Activities')

    state = fields.Selection(lambda self: self.env['odoocms.selections'].get_selection_field('Student States'),
                             string='Student Status', tracking=True, store=True, default='draft')

    state2 = fields.Selection([
        ('draft', 'Draft'), ('enroll', 'Admitted'), ('alumni', 'Alumni'), ('suspend', 'Suspend'), ('struck', 'Struck Off'),
        ('defer', 'Deferred'), ('withdrawn', 'WithDrawn'), ('cancel', 'Cancel'),
    ], 'Status - Temp', default='draft', tracking=True)
    old_state = fields.Selection([
        ('draft', 'Draft'), ('enroll', 'Admitted'), ('alumni', 'Alumni'), ('suspend', 'Suspend'), ('struck', 'Struck Off'),
        ('defer', 'Deferred'), ('withdrawn', 'WithDrawn'), ('cancel', 'Cancel'),
    ], 'Old Status', default='draft')
    notification_email = fields.Char('Email For Notification')
    official_email = fields.Char()
    sms_mobile = fields.Char('Mobile For SMS')
    warning_message = fields.Char()

    mobile_notify = fields.Char(string='Mobile Number For Notifications')
    email_notify = fields.Char(string='Email for Notifications')
    filer = fields.Boolean('Filer Status')
    ntn = fields.Char('NTN no.')
    cgpa = fields.Float('CGPA')

    # import_identifier = fields.Many2one('ir.model.data', 'Import Identifier', compute='_get_import_identifier',
    #     store=True)

    _sql_constraints = [
        ('admission_no', 'unique(session_id,admission_no)', "Another Student already exists with this Admission number and Session!"),
        ('code', 'unique(code,career_id)', "Another Student already exists with this Student ID and Career/Degree Level!"),
    ]

    def write(self, vals):
        auto = vals.get('auto', False)
        if auto:
            del vals['auto']

        graduate_line_tags = self.env['odoocms.student.tag'].search([('graduate_line', '=', True)])

        graduate_tag = (self.tag_ids and graduate_line_tags and any(
            tag in graduate_line_tags for tag in self.tag_ids) or False)

        if graduate_tag and not self.env.context.get('bypass_graduate_tag', False) and not vals.get('tag_ids',False):
            raise UserError('Change in Student Profile after Graduate Tag is not possible %s' % (self.code,))

        # Capitalize First and Last name
        if vals.get('first_name', False) or vals.get('last_name', False):
            first_name = vals.get('first_name', self.first_name).title()
            last_name = vals.get('last_name', self.last_name)
            name = first_name
            if last_name:
                last_name = last_name.title()
                name = first_name + ' ' + last_name

            vals['first_name'] = first_name
            vals['last_name'] = last_name
            vals['name'] = name

        if vals.get('state',False):
            field_state_id = self.env['ir.model.fields'].search([('model', '=', self._name), ('name', '=', 'state')])
            history_data = {
                'student_id': self.id,
                'field_name_id': field_state_id and field_state_id.id or False,
                'field_name': 'State',
                'changed_from': self.state,
                'changed_to': vals.get('state'),
                'changed_by': self.env.user.id,
                'date': datetime.now(),
                'date_effective': self._context.get('date_effective', False),
                'description': self._context.get('description', False),
                'method': self._context.get('method', False),
            }
            self.env['odoocms.student.history'].create(history_data)

        if vals.get('tag_ids',False):
            to_be_removed = self.env['odoocms.student.tag']
            updated_tags = self.env['odoocms.student.tag'].search([('id', 'in', vals.get('tag_ids')[0][2])])
            added_tags = updated_tags - self.tag_ids
            for added_tag in added_tags:
                if added_tag.category_id and not added_tag.category_id.multiple:
                    if len(added_tags.filtered(lambda l: l.category_id == added_tag.category_id)) == 1:
                        to_be_removed += (updated_tags - added_tags).filtered(lambda l: l.category_id == added_tag.category_id)
                    else:
                        raise UserError('The following tags can not be used simultaneously %s' % (', '.join([k.name for k in added_tags.filtered(lambda l: l.category_id == added_tag.category_id)])))
            updated_tags -= to_be_removed
            to_be_removed2 = self.tag_ids - updated_tags

            alist = list(vals.get('tag_ids'))
            my_list = [i for i in alist[0]]
            my_list[2] = updated_tags.ids
            vals.update({'tag_ids': [my_list]})

            # alist[0][2] = updated_tags.ids
            # vals.update({'tag_ids': alist})

            if any(added_tags.mapped('block')):
                self.warning_message = self._context.get('description', False)
            if any(to_be_removed2.mapped('block')):
                self.warning_message = False

        method = 'Manual'
        if vals.get('tag_apply_method'):
            method = vals.get('tag_apply_method')
            vals.pop('tag_apply_method')
        old_tags = self.tag_ids.mapped('name')
        res = super(OdooCMSStudent, self).write(vals)

        new_tags = self.tag_ids.mapped('name')
        if vals.get('tag_ids'):  # old_tags != new_tags
            history_data = {
                'student_id': self.id,
                'field_name': 'Tags',
                'changed_from': old_tags,
                'changed_to': new_tags,
                'changed_by': self.env.user.id,
                'date': datetime.now(),
                'date_effective': self._context.get('date_effective', False),
                'description': self._context.get('description', False),
                'method': self._context.get('method', method),
            }
            self.env['odoocms.student.history'].create(history_data)

        if vals.get('user_id', False) and not auto:
            self.user_id.write({
                'user_type': 'student',
                'student_id': self.id,
                'auto': True,
            })
        # if not self.partner_id.code:
        #     self.partner_id.code = self.code

        return res

    @api.depends('tag_ids', 'tag_ids.exclude_fee')
    def _compute_fee_enable(self):
        i = 1
        for rec in self:
            _logger.info('%s of %s' % (i, len(self)))
            fee_enable = True
            for tag in self.tag_ids:
                if tag.exclude_fee:
                    fee_enable = False
                    break
            rec.fee_enable = fee_enable
            i = i + 1

    # @api.constrains('father_guardian_cnic')
    # def check_fcnic(self):
    #     for rec in self:
    #         if self.father_guardian_cnic and not re.match("\d{5}-\d{7}-\d{1}", rec.father_guardian_cnic):
    #             raise ValidationError(_('CNIC should be written as 99999-9999999-9"'))

    def name_get(self):
        res = []
        for record in self:
            name = record.code + ' - ' + record.name
            res.append((record.id, name))
        return res

    @api.depends('id_number', 'entryID','admission_no')
    def _get_code(self):
        for rec in self:
            rec.code = rec.id_number or rec.entryID or rec.admission_no or ('ST.' + str(rec.id))

    def get_student_id(self):
        if self.batch_id and self.batch_id.sequence_id:
            self.id_number = self.batch_id.sequence_id.next_by_id()

    @api.depends('program_id', 'session_id', 'batch_id')
    def _get_study_scheme(self):
        for rec in self:
            if rec.program_id and rec.session_id and rec.batch_id:
                rec.study_scheme_id = rec.batch_id.study_scheme_id.id

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    @api.model
    def create(self, vals):
        if vals.get('first_name', False) or vals.get('last_name', False):
            first_name = vals.get('first_name', '')
            if first_name:
                first_name = first_name.title()  # capitalize
                vals['first_name'] = first_name

            name = first_name

            last_name = vals.get('last_name', '')
            if last_name:
                last_name = last_name.title()  # capitalize
                vals['last_name'] = last_name
                name = name + ' ' + last_name

            vals['name'] = name

        student = super().create(vals)
        if not student.batch_section_id:
            if student.batch_id and len(student.batch_id.section_ids)==1:
                student.batch_section_id = student.batch_id.section_ids[0].id
        return student

    

    # @api.constrains('cnic')
    # def _check_cnic(self):
    #     for rec in self:
    #         if rec.cnic:
    #             cnic_com = re.compile('^[0-9+]{5}-[0-9+]{7}-[0-9]{1}$')
    #             a = cnic_com.search(rec.cnic)
    #             if a:
    #                 return True
    #             else:
    #                 raise UserError(_("CNIC Format is Incorrect. Format Should like this 00000-0000000-0"))
    #     return True

    @api.constrains('date_of_birth')
    def _check_birthdate(self):
        for record in self:
            if record.date_of_birth > fields.Date.today():
                raise ValidationError(_("Birth Date can't be greater than Current Date!"))

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Students'),
            'template': '/odoocms/static/xls/odoocms_student.xlsx'
        }]

    def create_user(self):
        group_portal = self.env.ref('base.group_portal')
        for student in self:
            if not student.user_id:
                data = {
                    # 'name': record.name + ' ' + (record.last_name or ''),
                    'partner_id': student.partner_id.id,
                    'student_id': student.id,
                    'user_type': 'student',
                    'login': student.id_number or student.entryID or student.email,
                    'password': student.mobile or '123456',
                    'groups_id': group_portal,
                }
                user = self.env['res.users'].create(data)
                student.user_id = user.id

    def compute_previous_year_date(self, strdate):
        tenyears = relativedelta(years=16)
        start_date = fields.Date.from_string(strdate)
        return fields.Date.to_string(start_date - tenyears)

    # @api.depends('code')
    # def _get_import_identifier(self):
    #     for rec in self:
    #         identifier = self.env['ir.model.data'].search(
    #             [('model', '=', 'odoocms.student'), ('res_id', '=', rec.id)])
    #         if identifier:
    #             identifier.module = 'ST'
    #             identifier.name = rec.code or rec.id
    #         else:
    #             data = {
    #                 'name': rec.code or rec.id,
    #                 'module': 'ST',
    #                 'model': 'odoocms.student',
    #                 'res_id': rec.id,
    #             }
    #             identifier = self.env['ir.model.data'].create(data)
    #
    #         rec.import_identifier = identifier.id

    def lock(self):
        for rec in self:
            if rec.batch_id:
                rec.state = 'enroll'
                if not rec.term_id:
                    rec.term_id = rec.batch_id.term_id.id
                if not rec.semester_id:
                    rec.semester_id = rec.batch_id.semester_id.id
            else:
                raise UserError('Please Assign Batch to Student.')

    def cron_account(self):
        recs = self.env['res.partner'].search(['|', ('property_account_receivable_id', '=', False), ('property_account_payable_id', '=', False)])
        for rec in recs:
            rec.property_account_receivable_id = 3
            rec.property_account_payable_id = 229

    def cron_pass(self):
        for rec in self:
            if rec.mobile:
                rec.mobile = rec.mobile.replace('-', '')
                if rec.user_id:
                    rec.user_id.password = rec.mobile

    def cron_reg(self):
        for rec in self.env['odoocms.assesment.obe.summary'].search([('registration_id', '=', False)]):
            reg = self.env['odoocms.student.course'].search([('student_id', '=', rec.student_id.id), ('class_id', '=', rec.class_id.id)])
            rec.registration_id = rec.id

    def _get_report_base_filename(self):
        self.ensure_one()
        return '%s-%s' % (self.code, self.name)
    
    def process_images(self):
        # source = "ftp/files/"
        source = self.env['ir.config_parameter'].sudo().get_param('odoocms.ftp_server_source')
        destination = "/tmp/"
        self.downloadFiles(source, destination)
        os.chdir(destination + source)
        image_list = os.listdir()
        students = self.env['odoocms.student'].search([])
        for img in image_list:
            for rec in students:
                if rec.id_number and rec.id_number==os.path.splitext(img)[0]:
                    pic = open(destination + source + img, 'rb')
                    pic_binary = pic.read()
                    pic_binary2 = bytearray(pic_binary)
                    if pic_binary:
                        rec.image = codecs.encode(pic_binary, 'base64')
                        # pic_binary2 = base64.b64encode(pic.read())
                        # pic_binary2 = pic_binary.decode('base64')

    def downloadFiles(self, path, destination):
        # server = "127.0.0.1"
        # user = "testftp"
        # password = "123"

        server = self.env['ir.config_parameter'].sudo().get_param('odoocms.ftp_server_address')
        user = self.env['ir.config_parameter'].sudo().get_param('odoocms.ftp_server_user')
        password = self.env['ir.config_parameter'].sudo().get_param('odoocms.ftp_server_password')

        interval = 0.05

        ftp = ftplib.FTP(server)
        ftp.login(user, password)

        try:
            ftp.cwd(path)
            os.chdir(destination)
            self.mkdir_p(destination[0:len(destination)] + path)
            print("Created: " + destination[0:len(destination)] + path)
        except OSError:
            pass
        except ftplib.error_perm:
            print("Error: could not change to " + path)
            sys.exit("Ending Application")

        filelist = ftp.nlst()

        for file in filelist:
            time.sleep(interval)
            try:
                ftp.cwd(path + file + "/")
                self.downloadFiles(path + file + "/", destination[0:len(destination)] + path)
            except ftplib.error_perm:
                os.chdir(destination[0:len(destination)])

                try:
                    ftp.retrbinary("RETR " + file, open(os.path.join(destination[0:len(destination)] + path, file), "wb").write)
                    print("Downloaded: " + file)
                except:
                    print("Error: File could not be downloaded " + file)
        return

    def mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:
            if os.path.isdir(path):
                pass
            else:
                raise


class ResPartner(models.Model):
    _inherit = 'res.partner'

    code = fields.Char('Code')

    def _get_name(self):
        partner = self
        res = super()._get_name()
        return (partner.code or '') + res


class OdooCMSStudentPublic(models.Model):
    _name = 'odoocms.student.public'
    _description = 'Student Public'
    _rec_name = 'student_id'

    student_id = fields.Many2one('odoocms.student', 'Student', required=True)
    campus_id = fields.Many2one('odoocms.campus', 'Campus')
    career_id = fields.Many2one('odoocms.career', 'Career')
    session_id = fields.Many2one('odoocms.academic.session', 'Academic Session')
    institute_id = fields.Many2one('odoocms.institute', 'Institute')
    program_id = fields.Many2one('odoocms.program', 'Program')
    batch_id = fields.Many2one('odoocms.batch','Batch')
    discipline_id = fields.Many2one('odoocms.discipline', 'Discipline')


class OdooCMSStudentAcademic(models.Model):
    _name = 'odoocms.student.academic'
    _description = 'Student Academics'

    degree_level = fields.Selection([
        ('matric', 'Matric'), ('o-level', 'O-Level'), ('dae', 'DAE'), ('dba', 'DBA'),('inter', 'Intermediate'),
        ('a-level', 'A-Level'),('grad_14','Bachelors(14 Years)'),('grad_hon','Bachelors(Honors)'),('msc','M.Sc.(16 Years)'),
        ('ma','MA(16 Years)'),('ms','MS(18 Years)'), ('mcs','MCS'), ('mcom','MCOM'),('others','Others')
    ], 'Degree Level', required=1)

    degree = fields.Char('Degree', required=1)
    year = fields.Char('Passing Year')
    board = fields.Char('Board Name')
    subjects = fields.Char('Subjects')
    total_marks = fields.Integer('Total Marks')
    obtained_marks = fields.Integer('Obtained Marks')
    cgpa = fields.Float('CGPA')
    student_id = fields.Many2one('odoocms.student', 'Student')

    attachment = fields.Binary(string='Attachment', attachment=True, tracking=True)
    # degree_attachment = fields.Binary('Degree Attachment Download', related='attachment')
    state = fields.Selection([('draft','Draft'),('verified','Verified'),('reject','Rejected')],'Status',default='draft')


class OdooCmsStChangeStateRule(models.Model):
    _name = 'odoocms.student.change.state.rule'
    _description = "Reason for Changing Student State"
    _order = 'sequence'

    name = fields.Text(string='Reason', help='Define the Reason To Change the State of Student')
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string='Sequence')
    color = fields.Integer('Color')


class OdooCmsStudentProfileAttribute(models.Model):
    _name = 'odoocms.student.profilechange.attribute'
    _description = "Attributes Allowed for Student Profile Change"

    name = fields.Char('Name')
    field_name_id = fields.Many2one('ir.model.fields', 'Change Allowed In')


class OdooCMSStudentComment(models.Model):
    _name = 'odoocms.student.comment'
    _description = 'Student Comment'
    # _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'student_id'

    student_id = fields.Many2one('odoocms.student', 'Student', required=True)
    name = fields.Char(string='Student Name', related='student_id.name', readonly=True, store=True)
    message_from = fields.Char(string='Message From', readonly=True)
    program_id = fields.Many2one('odoocms.program', string='Program', related='student_id.program_id', readonly=True, store=True)
    comment = fields.Html(string="Comment", required=True)

    date = fields.Date('Comment Date', default=date.today(), readonly=1)
    notfication_date = fields.Date('Notification Date', default=date.today())
    message_ref = fields.Char(string="Reference Number", required=True)

    cms_ref = fields.Char(string="CMS Reference Number", required=True)


class OdooCMSStudentHistory(models.Model):
    _name = 'odoocms.student.history'
    _description = 'Student History'
    _order = 'student_id'
    _rec_name = 'student_id'
    
    student_id = fields.Many2one('odoocms.student', 'Student', required=True)
    field_name_id = fields.Many2one('ir.model.fields', 'Change In Attribute')
    field_name = fields.Char('Change In')
    changed_from = fields.Text('Changed From')
    changed_to = fields.Text('Changed To')
    changed_by = fields.Many2one('res.users', 'Changed By')
    date = fields.Datetime('Changed At')
    method = fields.Char('By Method')
    date_effective = fields.Date('Date Effective')
    description = fields.Text('Description')
    company_id = fields.Many2one('res.company', string='Company', related='student_id.company_id', store=True)
