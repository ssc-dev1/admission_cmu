from odoo import fields, models, _, api
from datetime import datetime
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from odoo import tools
from odoo.osv import expression
import pdb
import logging

_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning(
        "The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class IrSequence(models.Model):
    _inherit = 'ir.sequence'

    @api.model
    def next_by_code(self, sequence_code, sequence_date=None):
        self.check_access_rights('read')
        company_id = self.env.context.get('company_id', False)
        if not company_id:
            company_id = self.env.company.id

        seq_ids = self.search([('code', '=', sequence_code), ('company_id', 'in', [company_id, False])], order='company_id')
        if not seq_ids:
            _logger.debug("No ir.sequence has been found for code '%s'. Please make sure a sequence is set for current company." % sequence_code)
            return False
        seq_id = seq_ids[0]
        return seq_id._next(sequence_date=sequence_date)


class OdooCMSAdmissionApplication(models.Model):
    _name = 'odoocms.application'
    _description = 'Applications for the admission'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    READONLY_STATES = {
        'approve': [('readonly', True)],
        'open': [('readonly', True)],
        'done': [('readonly', True)],
        'reject': [('readonly', True)],
    }

    @api.depends('first_name', 'middle_name', 'last_name')
    def _get_applicant_name(self):
        for applicant in self:
            name = applicant.first_name or ''
            if applicant.middle_name:
                name = name + ' ' + applicant.middle_name
            if applicant.last_name:
                name = name + ' ' + applicant.last_name
            applicant.name = name

    first_name = fields.Char(string='First Name', help="First name of Applicant", states=READONLY_STATES)
    middle_name = fields.Char(string='Middle Name', help="Middle name of Applicant", states=READONLY_STATES)
    last_name = fields.Char(string='Last Name', help="Last name of Applicant", states=READONLY_STATES)
    name = fields.Char('Applicant Name', compute='_get_applicant_name', store=True)

    cnic = fields.Char(string='CNIC')
    cnic_front = fields.Binary('Cnic Front', attachment=True)
    cnic_back = fields.Binary('Cnic Back', attachment=True)
    domicile = fields.Binary('Domicile', attachment=True)

    pass_port = fields.Binary('Passport', attachment=True)
    applicant_type = fields.Selection([
        ('national', 'National'),
        ('international', 'International'),
    ], string='Applicant Type')
    passport = fields.Char(string='Passport')
    date_of_birth = fields.Date(string="Date Of Birth")
    gender = fields.Selection([('m', 'Male'), ('f', 'Female'), ('o', 'Other')],
                              string='Gender', tracking=True)
    religion_id = fields.Many2one('odoocms.religion', string="Religion")
    blood_group = fields.Selection(
        [('A+', 'A+ve'), ('B+', 'B+ve'), ('O+', 'O+ve'), ('AB+', 'AB+ve'),
         ('A-', 'A-ve'), ('B-', 'B-ve'), ('O-',
                                          'O-ve'), ('AB-', 'AB-ve'), ('N', 'Not Known')
         ], 'Blood Group', tracking=True)

    brothers = fields.Integer(string='Brothers')
    sisters = fields.Integer(string='Sisters')
    step_no = fields.Integer(string='Step No')

    nationality = fields.Many2one('res.country', string='Nationality', ondelete='restrict', )
    province_id = fields.Many2one('odoocms.province', string='Province')
    province2 = fields.Char(string='Other Province')
    domicile_id = fields.Many2one('odoocms.domicile', string='Domicile', states=READONLY_STATES)

    image = fields.Binary(string='Image', attachment=True, help="Provide the image of the Student")

    father_name = fields.Char(string="Father Name")
    father_cnic = fields.Char(string='Father CNIC')
    father_status = fields.Selection([('alive', 'Alive'), ('deceased', 'Deceased')], 'Father Status')
    father_cell = fields.Char('Father Cell')
    father_education = fields.Selection([
        ('matric', 'Matric'),
        ('intermediate', 'FA/ Fsc or Equivalent'),
        ('bachelor', 'BA/ BS or Equivalent'),
        ('postgraduate', 'M-PHIL/ MS or Equivalent'),
        ('doctorate', 'PhD or Equivalent'),
        ('illiterate', 'Illiterate'),
    ], 'Father Education')
    father_profession = fields.Many2one('odoocms.profession', 'Father Profession', domain=[('apply_on', 'in', ('b', 'm'))])

    mother_name = fields.Char(string="Mother Name")
    mother_cnic = fields.Char(string='Mother CNIC')
    mother_status = fields.Selection([('alive', 'Alive'), ('deceased', 'Deceased')], 'Mother Status')
    mother_cell = fields.Char('Mother Cell')
    mother_education = fields.Selection([
        ('matric', 'Matric'),
        ('intermediate', 'FA/ Fsc or Equivalent'),
        ('bachelor', 'BA/ BS or Equivalent'),
        ('postgraduate', 'M-PHIL/ MS or Equivalent'),
        ('doctorate', 'PhD or Equivalent'),
        ('illiterate', 'Illiterate'),
    ], 'Mother Education')
    mother_profession = fields.Many2one('odoocms.profession', 'Mother Profession', domain=[('apply_on', 'in', ('b', 'f'))])

    degree = fields.Many2one('odoocms.admission.degree', 'Last Degree',compute='_last_degree')
    # degree_code = fields.Char('Degree Code', related='degree.code')

    # For Nutech
    family_in_university = fields.Text('How many Brothers & Sister you have in University level Education or Completed their University Level Education?')

    # Scholarship
    single_parent = fields.Boolean('Single Parent', default=False)
    # Indicates whether the applicant opted to apply for Need-Based Scholarship
    need_based_scholarship_applied = fields.Boolean(
        string='Applied for Need Based Scholarship',
        default=False,
        help='Set when applicant chooses to apply for need-based scholarship',
    )

    # Contact
    email = fields.Char(string='Email')
    phone = fields.Char(string='Phone')
    mobile = fields.Char(string='Mobile')

    street = fields.Char(string='Street', help="Enter the First Part of Address")
    street2 = fields.Char(string='Street2', help="Enter the Second Part of Address")
    city = fields.Char(string='City', help="Enter the City Name")
    zip = fields.Char(change_default=True)
    state_id = fields.Many2one("res.country.state", string='Country State', ondelete='restrict',
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one('res.country', string='Country', ondelete='restrict', help="Select the Country")

    is_same_address = fields.Boolean(string="Permanent Address same as above", default=False,
                                     help="Tick the field if the Present and permanent address is same")
    per_street = fields.Char(string='Per. Street', help="Enter the First Part of Permanent Address")
    per_street2 = fields.Char(string='Per. Street2', help="Enter the First Part of Permanent Address")
    per_city = fields.Char(string='Per. City', help="Enter the City Name of Permanent Address")
    per_zip = fields.Char(change_default=True)
    per_state_id = fields.Many2one("res.country.state", string='Per State', ondelete='restrict',
                                   domain="[('country_id', '=?', per_country_id)]")
    per_country_id = fields.Many2one('res.country', string='Per. Country', ondelete='restrict', help="Select the Country")

    # Guardian
    guardian_name = fields.Char('Guardian Name')
    guardian_cnic = fields.Char('Guardian CNIC')
    guardian_cell = fields.Char('Guardian Cell')
    guardian_education = fields.Selection([
        ('matric', 'Matric'),
        ('intermediate', 'FA/Fsc or Equivalent'),
        ('bachelor', 'BA / BS or Equivalent'),
        ('postgraduate', 'M-PHIL / MS or Equivalent'),
        ('doctorate', 'PhD or Equivalent'),
        ('illiterate', 'Illiterate'),
    ], 'Mother Education')
    guardian_profession = fields.Many2one('odoocms.profession', 'Guardian Profession', domain=[('apply_on', 'in', ('b', 'm'))])
    guardian_relation = fields.Char('Relation with Guardian')
    guardian_income = fields.Integer('Guardian Income')
    guardian_address = fields.Char('Guardian Address')
    fee_payer_name = fields.Char(string='Fee Payer Name')
    fee_payer_cnic = fields.Char(string='Fee Payer Cnic')

    entry_registration = fields.Char('Entry Registration', states=READONLY_STATES)
    entry_total_marks = fields.Integer('Entry Total Marks', states=READONLY_STATES)
    # entry_obtained_marks = fields.Integer(
    #     'Entry Obtained Marks', states=READONLY_STATES)
    entry_percentage = fields.Float('Entry Percentage', compute='_get_entry_percentage', store=True)

    # Preferences
    preference_ids = fields.One2many('odoocms.application.preference', 'application_id', 'Preferences', states=READONLY_STATES)
    preference_cnt = fields.Integer('Preference Count', compute='_get_preference_count', store=True)
    first_preference = fields.Char('First Preference', compute='_get_preference_count', store=True)

    # Misc
    register_id = fields.Many2one('odoocms.admission.register', 'Admission Register', states=READONLY_STATES)
    academic_session_id = fields.Many2one(
        'odoocms.academic.session', 'Academic Session', related='register_id.academic_session_id', store=True)
    career_id = fields.Many2one('odoocms.career', 'Career', related='register_id.career_id', store=True)

    application_no = fields.Char(string='Reference No', copy=False, readonly=True, index=True,
                                 default=lambda self: _('New'))
    application_date = fields.Datetime('Application Date', copy=False, states=READONLY_STATES,
                                       default=lambda self: fields.Datetime.now())
    application_submit_date = fields.Datetime('Application Submit Date', copy=False, states=READONLY_STATES)

    active = fields.Boolean(string='Active', default=True)
    overseas = fields.Boolean(string='Overseas Pakistani?', default=False)
    description = fields.Text(string="Note")
    # class_id = fields.Many2one('odoocms.class', string="Class")

    verified_by = fields.Many2one('res.users', string='Verified by', help="The Document is Verified By")
    reject_reason = fields.Many2one('odoocms.application.reject.reason',
                                    string='Reject Reason', help="Reason of Application rejection")

    user_id = fields.Many2one('res.users', 'Login User')

    is_dual_nationality = fields.Boolean(string='Dual Nationality', default=False)
    # Merit
    merit_score = fields.Float('Merit Score', compute='_get_merit_score', store=True)
    merit_number = fields.Integer('Merit Number')
    manual_score = fields.Float()
    pre_test_id = fields.Many2one('odoocms.pre.test', string='Test Name')
    pre_test_marks = fields.Integer(string='Pre Test Marks')
    # pre_test_total_marks = fields.Integer(string='Total Marks')
    pre_test_total_marks = fields.Integer(string='Pre Test Total Marks', related='pre_test_id.pre_test_total_marks', store=True)
    pre_test_attachment = fields.Binary(string='Pre Test Attachment')

    fee_voucher_download_date = fields.Date('Fee Voucher Download Date',
                                            help="This field is defined for the Fee Voucher Downloaded Dashboard. Required in the Tree View")
    test_series_id = fields.Many2one('odoocms.admission.test.series', 'Time')
    # slot_ids = fields.Many2many('odoocms.admission.test.time','test_slot_applicant_rel', 'slot_id', 'student_id', 'Test Timings')
    applicant_academic_ids = fields.One2many('applicant.academic.detail', 'application_id')
    confirm_test_center = fields.Boolean('Confirm Test Slot', default=False)
    schedule_second_test = fields.Boolean('Is Schedule Second Test', default=False)

    # locked = fields.Boolean('Locked', default=False)
    state = fields.Selection([
        ('draft', 'Draft'), ('confirm', 'Confirm'), ('submit', 'Submit'), ('verified', 'Verified'),
        ('verification', 'Sent for Verification'),
        ('approve', 'Approve'), ('open', 'Open'),
        ('reject', 'Reject'), ('done', 'Done'), ], string='Status',
        default='draft', tracking=True)

    #migrations
    program_migration = fields.Boolean('Program Transfer/Migration')
    last_institute_other = fields.Char('Last Institute Other')
    migration_type = fields.Selection(
        [('inter_university', 'UCP Inter-faculty Transfer'), ('other_university', 'Migration From Other University')], string='Migration Type',
       )
    backend_sale = fields.Boolean('Backend Sale',default=False)
    fee_voucher_verify_by = fields.Many2one('res.users', 'Voucher Verify By')
    fee_voucher_verify_source = fields.Selection([('admission', 'Admission Department'),
                                                  ('finance', 'Finance Department'),
                                                  ('auto', 'Auto'),
                                                  ('other', 'Other'),
                                                  ], string='Voucher Verify Source')
    migration_university = fields.Char('Migration University Name')
    last_studied_semester = fields.Char('Last Studied Semester')
    last_obtained_cgpa = fields.Char('Last Obtained CGPA')
    current_registration_no = fields.Char('Current Registration Number')
    migration_state = fields.Selection([
        ('draft', 'Draft'),
        ('approve', 'Approve'),
        ('reject', 'Reject')], string='Status', tracking=True)
    reject_reason_des = fields.Text('Reject Reason Description')
    inter_result_status = fields.Char('Result Status', default="Complete")
    voucher_image = fields.Binary(string='Fee Voucher', attachment=True)
    voucher_number = fields.Char(string='Voucher Number')
    voucher_date = fields.Date(string='Fee Submit Date')
    amount = fields.Integer(string='Amount')
    voucher_verified_date = fields.Date(string='Voucher Verified Date')
    voucher_issued_date = fields.Date(string='Voucher Issue Date')
    fee_voucher_state = fields.Selection([
        ('no', 'Not Downloaded Yet'), ('download', 'Not Uploaded Yet'),
        ('upload0', 'Only Image Uploaded'), ('upload', 'Not Verified Yet'),
        ('verify', 'Verified'), ('unverify', 'Un-Verified')
    ], default='no',tracking=True)

    statement_purpose = fields.Binary('Statement Of Purpose')
    followup_mail_draft = fields.Boolean('Followup Mail Draft',default=False)
    followup_mail_submit = fields.Boolean('Followup Mail submit',default=False)
    followup_mail_draft_date = fields.Date()
    followup_mail_submit_date = fields.Date()
    reset_password = fields.Char('Reset Password',tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', string='Admission Term')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    # Voucher Details
    # voucher_image = fields.Binary(string='Fee Voucher', attachment=True)
    # voucher_number = fields.Char(string='Voucher Number')
    # voucher_date = fields.Date(string='Fee Submit Date')
    # amount = fields.Integer(string='Amount')
    # voucher_verified_date = fields.Date(
    #     string='Voucher Verified Date', compute='_voucher_verified_date', store=True)
    # voucher_issued_date = fields.Date(string='Voucher Issue Date')
    # # send_mail = fields.Boolean(string='Send Email', default=False)
    # fee_voucher_state = fields.Selection([
    #     ('no', 'Not Downloaded Yet'),
    #     ('download', 'Not Uploaded Yet'),
    #     ('upload0', 'Only Image Uploaded'),
    #     ('upload', 'Not Verified Yet'),
    #     ('verify', 'Verified'),
    #     ('unverify', 'Un-Verified')
    # ], default='no')
    #
    # prospectus_inv_id = fields.Many2one(
    #     string='Application Processing Fee',
    #     comodel_name='account.move',
    # )
    # admission_inv_id = fields.Many2one(
    #     string='Admission Fee',
    #     comodel_name='account.move',
    # )

    student_id = fields.Many2one('odoocms.student', string='Applicant Student')
    doc_count = fields.Integer('Count')
    prefered_program = fields.Char('Program Applied', compute='_prefered_program')
    prefered_program_id = fields.Many2one('odoocms.program',string='Program Applied')
    transfer_program_id = fields.Many2one('odoocms.program',string='Program Transfered From')

    first_semester_courses = fields.One2many('odoocms.applicant.first.semester.courses', 'application_id', 'First Semester Courses')
    extra_var = fields.Boolean('Extra Var', compute='_compute_first_semester_courses', store=True)
    reset_password = fields.Char('Reset Password',tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', string='Admission Term')
    mail_count = fields.Integer('Mail Count',default=0)
    last_mail_time = fields.Datetime('Last MAil Time')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('application_no', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def write(self, vals):
        if vals.get('state',False) or vals.get('fee_voucher_state',False):
            vals.update({
                'mail_count':0,
                'last_mail_time':datetime.now(),
            })

        return super(OdooCMSAdmissionApplication, self).write(vals)

    def approve_migration_request(self):
        for rec in self:
            rec.migration_state = 'approve'

    def reject_migration_request(self):
        for rec in self:
            rec.migration_state = 'reject'
            rec.state = 'reject'

    @api.depends('preference_ids')
    def _prefered_program(self):
        for rec in self:
            rec.prefered_program = ''
            if len(rec.preference_ids) > 0:
                rec.prefered_program = rec.preference_ids[0].program_id.name
                rec.prefered_program_id = rec.preference_ids.filtered(lambda x: x.preference == 1).program_id.id
        for rec in self:
                prospectus_challan  = self.env['account.move'].sudo().search([('application_id','=',rec.id),('challan_type','=','prospectus_challan')])
                if prospectus_challan:
                    for pc in prospectus_challan:
                        if rec.preference_ids:
                            pc.program_id = rec.preference_ids[0].program_id.id
                        else:
                            pc.program_id = False

    def reject_profile_image(self):
        if self.image:
            self.image = False
            # template = self.env.ref('odoocms_admission.mail_template_image_reject').sudo()
            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', self.company_id.id)])
            template = self.env['mail.template'].sudo().search(
                [('name', '=', 'Application Profile Image Reject '), ('mail_server_id', '=', mail_server_id.id)])
            template.send_mail(self.id, force_send=True)
    
    # @api.depends('preference_ids')
    # def _prefered_program_id(self):
    #     for rec in self:
    #         rec.prefered_program = ''
    #         if len(rec.preference_ids) > 0:
    #             pdb.set_trace()


    # def action_create_prospectus_invoice(self):
    #     lines = []
    #     user = self.user_id
    #     if not user:
    #         user = self.env['res.users'].sudo().search(
    #             [('login', '=', self.application_no)])
    #     partner_id = user.partner_id
    #     if partner_id:
    #         amount = 0
    #         due_date = fields.Date.today()
    #         preference_id = self.preference_ids and \
    #                         self.preference_ids.sorted(key=lambda a: a.preference, reverse=False)[
    #                             0] or False
    #         program_id = False
    #         if preference_id:
    #             program_id = preference_id.program_id
    #             # Prospectus Fee
    #             if program_id.prospectus_registration_fee > 0:
    #                 amount = program_id.prospectus_registration_fee
    #             else:
    #                 prospectus_fee = float(self.env['ir.config_parameter'].sudo().get_param(
    #                     'odoocms_admission_portal.registration_fee') or '2000')
    #                 amount = prospectus_fee
    #
    #             # Prospectus Fee Due Date
    #             if program_id.prospectus_program_fee_date:
    #                 due_date = program_id.prospectus_program_fee_date
    #             else:
    #                 due_date = self.register_id.prospectus_fee_due_date
    #         else:
    #             prospectus_fee = float(self.env['ir.config_parameter'].sudo().get_param(
    #                 'odoocms_admission_portal.registration_fee') or '2000')
    #             amount = prospectus_fee
    #             due_date = self.register_id.prospectus_fee_due_date
    #         fee_structure = self.env['odoocms.fee.structure'].search(
    #             [], order='id desc', limit=1)
    #         receipts = self.env['odoocms.receipt.type'].search(
    #             [('name', 'in', ('Registration Fee', 'Prospectus Fee'))])
    #         fee_head_id = self.env['odoocms.fee.head'].search(
    #             [('name', 'in', ('Prospectus Fee', 'Prospectus'))])
    #         fee_lines = {
    #             'sequence': 10,
    #             'name': "Prospectus Fee",
    #             'quantity': 1,
    #             'price_unit': amount,
    #             'product_id': fee_head_id.product_id.id,
    #             'account_id': fee_head_id.property_account_income_id.id,
    #             'fee_head_id': fee_head_id.id,
    #             'exclude_from_invoice_tab': False,
    #             'course_gross_fee': amount,
    #         }
    #         lines.append((0, 0, fee_lines))
    #
    #         data = {
    #             'application_id': self.id,
    #             'student_name': self.name,
    #             'partner_id': partner_id.id,
    #             'fee_structure_id': fee_structure.id,
    #             'journal_id': fee_structure.journal_id.id,
    #             'invoice_date': fields.Date.today(),
    #             'invoice_date_due': due_date,
    #             'state': 'draft',
    #             'is_fee': True,
    #             'is_cms': True,
    #             'is_hostel_fee': False,
    #             'move_type': 'out_invoice',
    #             'invoice_line_ids': lines,
    #             'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
    #             'program_id': program_id and program_id.id or False,
    #             'term_id': self.register_id.term_id and self.register_id.term_id.id or False,
    #             'career_id': self.register_id.career_id and self.register_id.career_id.id or False,
    #             'institute_id': False,
    #             'discipline_id': False,
    #             'campus_id': False,
    #             'session_id': self.academic_session_id and self.academic_session_id.id or False,
    #             'validity_date': due_date,
    #             'first_installment': False,
    #             'second_installment': False,
    #             'narration': 'Prospectus Fee',
    #             'is_prospectus_fee': True,
    #         }
    #         invoice_id = self.env['account.move'].sudo().create(data)
    #         self.prospectus_inv_id = invoice_id.id
    #         invoice_id.sudo().action_post()
    #         invoice_id.sudo().action_invoice_send()
    #

    # def admission_link_invoice_to_student(self):
    #     if self.student_id:
    #         invoices = self.env['account.move'].search(
    #             [('application_id', '=', self.id)], order='id asc')
    #         if invoices:
    #             invoices.write({'student_id': self.student_id.id})
    #             for invoice in invoices.filtered(lambda a: not a.student_ledger_id):

    @api.depends('name', 'application_no')
    def name_get(self):
        result = []
        for applicant in self:
            name = applicant.name
            if applicant.application_no:
                name = applicant.application_no + '-' + name
            result.append((applicant.id, name))
        return result

    @api.depends('doc_count', 'applicant_academic_ids')
    def action_view_documents(self):
        # documents = self.env['applicant.academic.detail']
        for rec in self:
            app_docs = self.env['applicant.academic.detail'].search(
                [('application_id', '=', rec.id)])
            rec.doc_count = 0
            if app_docs:
                app_docs = app_docs.mapped('id')
                rec.doc_count = len(app_docs)

                return {
                    'domain': [('id', 'in', app_docs)],
                    'name': _('Classes'),
                    'view_type': 'form',
                    'view_mode': 'tree,form',
                    'res_model': 'applicant.academic.detail',
                    'view_id': False,
                    'type': 'ir.actions.act_window'
                }

    @api.model
    def create(self, vals):
        if vals.get('application_no', _('New')) == _('New') or '':
            vals['application_no'] = self.env['ir.sequence'].with_context({'company_id': vals.get('company_id',self.env.company.id)}).next_by_code('odoocms.application') or _('New')
        res = super(OdooCMSAdmissionApplication, self).create(vals)
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'reject':
                raise ValidationError(
                    _("Application can only be deleted after Rejecting it"))

    @api.depends('preference_ids')
    def _get_preference_count(self):
        for rec in self:
            rec.preference_cnt = len(rec.preference_ids)
            rec.first_preference = rec.preference_ids and rec.preference_ids[
                0].program_id.code or False

    def cron_get_adjustments(self):
        recs = self.env['odoocms.application'].search(
            [('register_id.state', '=', 'application')])
        for rec in recs:
            rec._get_adjustments()

    def send_to_verify(self):
        for rec in self:
            rec.write({'state': 'verification'})

    def reject_application(self):
        for rec in self:
            rec.write({
                'state': 'reject'
            })

    def _last_degree(self):
        for rec in self:
            rec.degree = False
            if rec.applicant_academic_ids:
                rec.degree = rec.applicant_academic_ids[-1].degree_name.id

    def is_zero(self, amount):
        return tools.float_is_zero(amount, precision_rounding=2)

    def amount_to_text(self, amount):
        self.ensure_one()

        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()

        if num2words is None:
            logging.getLogger(__name__).warning(
                "The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(2) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)])
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
            amt_value=_num2words(integer_value, lang=lang.iso_code),
            amt_word='.',
        )
        if not self.is_zero(amount - integer_value):
            amount_words += ' ' + 'and' + tools.ustr(' {amt_value} {amt_word}').format(
                amt_value=_num2words(fractional_value, lang=lang.iso_code),
                amt_word='.',
            )
        return amount_words

    def signup_mail(self):
        author = self.env['res.partner'].sudo().search(
            [('email', '=', self.email)], limit=1)
        subject = f"Welcome to {self.env.company.name}"
        signup_user = self.env['mail.mail'].search(
            [('subject', '=', subject), ('email_to', '=', self.email)], limit=1, order='id desc')

        if signup_user:
            return {
                'name': _('Signup Mail'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'view_type': 'form',
                'res_model': 'mail.mail',
                'res_id': signup_user.id,
            }

    def create_student(self, view=False, student_data={}):
        semester = self.env['odoocms.semester'].search([('number', '=', 1)], limit=1)
        user = self.user_id
        blood_group = self.blood_group
        if blood_group == 'N':
            blood_group = False

        values = {
            'state': 'draft',
            'name': self.name,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'father_name': self.father_name,

            'cnic': self.cnic,
            'gender': self.gender,
            'date_of_birth': self.date_of_birth,
            'religion_id': self.religion_id.id,
            'nationality': self.nationality.id,

            'email': self.email,
            'mobile': self.mobile,
            'phone': self.phone,
            'image_1920': self.image,

            'street': self.street,
            'street2': self.street2,
            'city': self.city,
            'zip': self.zip,
            'state_id': self.state_id.id,
            'country_id': self.country_id.id,

            'is_same_address': self.is_same_address,
            'per_street': self.per_street,
            'per_street2': self.per_street2,
            'per_city': self.per_city,
            'per_zip': self.per_zip,
            'per_state_id': self.per_state_id.id,
            'per_country_id': self.per_country_id.id,

            'career_id': self.career_id.id,
            'session_id': self.academic_session_id.id,
            'company_id': self.company_id.id,
            'domicile_id': self.domicile_id and self.domicile_id.id or False,
            'blood_group': blood_group,
            'user_id': self.user_id and self.user_id.id or False,

            'mother_name': self.mother_name,
            # 'father_profession': self.father_profession and self.father_profession.id or False,
            # 'mother_profession': self.mother_profession and self.mother_profession.id or False,
            'father_cell': self.father_cell,
            'mother_cell': self.mother_cell,
            'guardian_name': self.guardian_name,
            'guardian_mobile': self.guardian_cell,
            'notification_email': self.email,
            'sms_mobile': self.mobile,
            'admission_no': self.application_no,

            'program_id': student_data.get('program_id',False),
            'term_id': student_data.get('term_id',False),
            'semester_id': semester.id,
            'batch_id': student_data.get('batch_id',False),
            'study_scheme_id': student_data.get('study_scheme_id',False),
            'shift': student_data.get('shift',False)
        }
        if user:
            values['partner_id'] = user.partner_id.id
        if not self.is_same_address:
            pass
        else:
            values.update({
                'per_street': self.street,
                'per_street2': self.street2,
                'per_city': self.city,
                'per_zip': self.zip,
                'per_state_id': self.state_id.id,
                'per_country_id': self.country_id.id,
            })
        student = self.env['odoocms.student'].sudo().create(values)
        if student:
            self.write({'student_id': student.id})
            self.admission_inv_id.write({'student_id': student.id})

        if view:
            return {
                'name': _('Student'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'odoocms.student',
                'type': 'ir.actions.act_window',
                'res_id': student.id,
                'context': self.env.context
            }
        else:
            return student

    def new_student_registration(self):
        batch_id = self.admission_inv_id.batch_id
        if batch_id:
            sections = self.env['odoocms.batch.term.section'].search(
                [('batch_id', '=', batch_id.id)], order='sequence,name')
            selected_section = False
            flag = False
            for section in sections:
                for primary_class in section.primary_class_ids:
                    if primary_class.student_count >= primary_class.strength:
                        flag = True
                        break
                if not flag:
                    selected_section = section
                    break
            # if not selected_section:
            #     raise UserError("Please Define Batch Term Section")
            # Remarked by Sarfraz, For initial Testing as sections are not opened yet now
            if selected_section:
                for primary_class in selected_section.primary_class_ids:
                    course = primary_class.course_id
                    student_course_data = {
                        'student_id': self.student_id and self.student_id.id or False,
                        'semester_id': primary_class.batch_id.semester_id and primary_class.batch_id.semester_id.id or False,
                        'term_id': primary_class.term_id and primary_class.term_id.id or False,
                        'course_id': course.id,
                        'course_code': course.code,
                        'course_name': course.name,
                        # 'course_type': course.type,
                        'primary_class_id': primary_class.id
                    }
                    self.env['odoocms.student.course'].sudo().create(
                        student_course_data)
                    inv_line = self.admission_inv_id.invoice_line_ids.filtered(
                        lambda ln: ln.name == primary_class.course_code + "-" + primary_class.course_name + " Tuition Fee")
                    if inv_line:
                        inv_line.write({'course_id_new': primary_class.id})



    @api.depends('preference_ids', 'preference_ids.preference', 'preference_ids.program_id')
    def _compute_first_semester_courses(self):
        for rec in self:
            if rec.preference_ids and len(rec.preference_ids)>0:
                if rec.first_semester_courses:
                    rec.first_semester_courses.sudo().unlink()
                program_id = rec.prefered_program_id
                if not program_id:
                    program_id = rec.preference_ids[0].program_id
                if not program_id:
                    return
                program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id), ('session_id', '=',  rec.register_id.academic_session_id.id), ('term_id', '=', rec.register_id.term_id.id), ('career_id', '=', rec.register_id.career_id.id)])
                if program_batch:
                    study_scheme_id = program_batch.study_scheme_id
                    study_scheme_lines = study_scheme_id.line_ids.filtered(lambda a: a.semester_id.number == 1)
                    for line in study_scheme_lines:
                        course_already_exist = self.env['odoocms.applicant.first.semester.courses'].search([('application_id', '=', rec.id),('course_id', '=', line.course_id.id)])
                        if not course_already_exist and line.course_type != 'deficiency':
                            data_values = {
                                'course_id': line.course_id.id,
                                'study_scheme_id': study_scheme_id.id,
                                'study_scheme_line_id': line.id,
                                'credit_hours': line.credits,
                                'per_credit_hour_fee': program_batch.per_credit_hour_fee,
                                'application_id': rec.id,
                            }
                            self.env['odoocms.applicant.first.semester.courses'].sudo().create(data_values)
                    applicant_last_education_detail = rec.applicant_academic_ids.sorted(key=lambda r: r.degree_name.year_age, reverse=True)[:1]
                    # applicant_last_education_detail = rec.applicant_academic_ids.filtered(lambda r: r.year_age == max(rec.applicant_academic_ids.mapped('year_age')))
                    if applicant_last_education_detail.group_specialization in program_id.def_courses_group:
                        deficiency_course = study_scheme_id.line_ids.filtered(lambda a: a.course_type == 'deficiency')
                        if deficiency_course:
                            for def_course in deficiency_course:
                                course_already_exist = self.env['odoocms.applicant.first.semester.courses'].search([('application_id', '=', rec.id),('course_id', '=', def_course.course_id.id)])
                                if not course_already_exist:
                                    def_course_values = {
                                        'course_id': def_course.course_id.id,
                                        'study_scheme_id': study_scheme_id.id,
                                        'study_scheme_line_id': def_course.id,
                                        'credit_hours': def_course.credits,
                                        'per_credit_hour_fee': program_batch.per_credit_hour_fee,
                                        'application_id': rec.id,
                                    }
                                    self.env['odoocms.applicant.first.semester.courses'].sudo().create(def_course_values)
                    rec.extra_var = True

    # GET First Semester Courses
    # @api.depends('preference_ids', 'preference_ids.preference', 'preference_ids.program_id')
    # def _compute_first_semester_courses(self):
    #     for rec in self:
    #         if rec.preference_ids and len(rec.preference_ids)>0:
    #             if rec.first_semester_courses:
    #                 rec.first_semester_courses.sudo().unlink()
    #             program_id = rec.prefered_program_id
    #             if not program_id:
    #                 program_id = rec.preference_ids[0].program_id
    #             if not program_id:
    #                 return
    #             program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id), ('session_id', '=',  rec.register_id.academic_session_id.id), ('term_id', '=', rec.register_id.term_id.id), ('career_id', '=', rec.register_id.career_id.id)])
    #             if program_batch:
    #                 study_scheme_id = program_batch.study_scheme_id
    #                 study_scheme_lines = study_scheme_id.line_ids.filtered(lambda a: a.semester_id.number == 1)
    #                 for line in study_scheme_lines:
    #                     course_already_exist = self.env['odoocms.applicant.first.semester.courses'].search([('application_id', '=', rec.id),('course_id', '=', line.course_id.id)])
    #                     if not course_already_exist:
    #                         data_values = {
    #                             'course_id': line.course_id.id,
    #                             'study_scheme_id': study_scheme_id.id,
    #                             'study_scheme_line_id': line.id,
    #                             'credit_hours': line.credits,
    #                             'per_credit_hour_fee': program_batch.per_credit_hour_fee,
    #                             'application_id': rec.id,
    #                         }
    #                         self.env['odoocms.applicant.first.semester.courses'].sudo().create(data_values)
    #                 rec.extra_var = True


class OdoocmsApplicationPreference(models.Model):
    _name = 'odoocms.application.preference'
    _description = 'Application Preference'
    _order = 'application_id desc, preference'
    _rec_name = 'application_id'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    application_id = fields.Many2one(
        'odoocms.application', string='Applicant', tracking=True, ondelete='cascade')
    application_status = fields.Selection(
        string='Application Status', related='application_id.state', store=True)
    cnic = fields.Char(related='application_id.cnic',
                       string='CNIC', store=True)
    program_id = fields.Many2one(
        'odoocms.program', string='Program', tracking=True)
    preference = fields.Integer(string='Preference', tracking=True)
    discipline_preference = fields.Integer(
        string='Discipline Preference', tracking=True, default=1)
    discipline_id = fields.Many2one(
        string='Discipline ID', related='program_id.discipline_id', store=True)
    discipline_name = fields.Char(related='discipline_id.name', store=True)
    # discipline_name = fields.Char( 'Discipline', compute='_discipline_name', store=True)
    type = fields.Selection([('Armed Forces', 'Armed Forces'),
                             ('Regular', 'Regular')], 'Type', default='Regular', tracking=True)
    sequence = fields.Integer()

    @api.depends('preference')
    def _discipline_name(self):
        for each in self:
            each.discipline_name = each.program_id.discipline_id.name

    _sql_constraints = [
        ('application_program', 'unique(application_id,program_id,preference,type)',
         "Another Preference already exists with this Application and Program!"), ]


class OdooCMSAdmissionApplicationDocuments(models.Model):
    _name = 'odoocms.application.documents'
    _description = 'Applications Documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'student_id'

    student_id = fields.Many2one('odoocms.student', string='Student')
    application_id = fields.Many2one(
        'odoocms.application', string='Applicant', ondelete='cascade')
    matric_scaned_copy = fields.Binary(
        'Scanned Copy of Matric', attachment=True)
    matric_scaned_copy_name = fields.Text('Scanned Copy of Matric Name')
    matric_scaned_copy_size = fields.Text('Scanned Copy of Matric Size')

    inter_scaned_copy = fields.Binary('Scanned Copy of Inter', attachment=True)
    inter_scaned_copy_name = fields.Text('Scanned Copy Inter Name')
    inter_scaned_copy_size = fields.Text('Scanned Copy Inter Size')

    domicile_scaned_copy = fields.Binary(
        'Scanned Copy of Domicile', attachment=True)
    domicile_scaned_copy_name = fields.Text('Scanned Copy Domicile Name')
    domicile_scaned_copy_size = fields.Text('Scanned Copy Domicile Size')

    salary_slip_scaned_copy = fields.Binary(
        'Scanned Copy of Salary Slip', attachment=True)
    salary_slip_scaned_copy_name = fields.Text('Scanned Copy Salary Slip Name')
    salary_slip_scaned_copy_size = fields.Text('Scanned Copy Salary Slip Size')

    prc_scaned_copy = fields.Binary('Scanned Copy of PRC', attachment=True)
    prc_scaned_copy_name = fields.Text('Scanned Copy PRC Name')
    prc_scaned_copy_size = fields.Text('Scanned Copy PRC Size')

    test_certificate = fields.Binary('Scanned Copy of Test', attachment=True)
    test_certificate_name = fields.Text('Scanned Copy Test Name')
    test_certificate_size = fields.Text('Scanned Copy Test Size')

    cnic_scanned_copy = fields.Binary('Scanned Copy of CNIC', attachment=True)
    cnic_scanned_copy_name = fields.Text('Scanned Copy CNIC Name')
    cnic_scanned_copy_size = fields.Text('Scanned Copy CNIC Size')

    hafiz_scaned_copy = fields.Binary(
        'Scanned Copy of Hafiz-e-Quran', attachment=True)
    hafiz_scaned_copy_name = fields.Text('Scanned Copy Hafiz-e-Quran Name')
    hafiz_scaned_copy_size = fields.Text('Scanned Copy Hafiz-e-Quran Size')




