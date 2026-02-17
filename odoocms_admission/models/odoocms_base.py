from odoo import fields, models, api


class OdooCMSDegree(models.Model):
    _name = 'odoocms.degree'
    _description = 'Degree'

    name = fields.Char('Degree Name', required=True)
    code = fields.Char('Code', required=True)
    career_id = fields.Many2one('odoocms.career', string="Admission Career")
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    # offering = fields.Boolean(string='Offering', default=True)
    program_ids = fields.Many2many('odoocms.program', 'program_degree_rel', 'degree_id', 'program_id', 'Programs')
    degree_id = fields.Many2one('odoocms.admission.degree', string='Degree', required=True)
    degree_name = fields.Char('Degree Name',related='degree_id.name' ,readonly=True)
    specialization_id = fields.Many2one('applicant.academic.group', string='Specialization/Group')
    eligibilty_percentage = fields.Float(string='Eligibility Percentage >=', )
    eligibilty_per = fields.Float(string='Eligibility Percentage <=', )
    eligibilty_cgpa = fields.Float(string='Eligibility CGPA >=', )
    eligibilty_cgp = fields.Float(string='Eligibility CGPA <=', )

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    @api.onchange('degree_id')
    def onchange_institute_id(self):
        for rec in self:
            return {'domain': {'specialization_id': [('degree_id', '=', rec.degree_id.id)]}}


class OdooCMSProgram(models.Model):
    _inherit = "odoocms.program"

    degree_ids = fields.Many2many('odoocms.degree', 'program_degree_rel', 'program_id', 'degree_id', 'Degrees')
    # prospectus_fee_due_date = fields.Date(string='Prospectus Fee Due Date')
    prospectus_registration_fee = fields.Integer(string='Application Processing Fee', default=0)
    prospectus_program_fee_date = fields.Date(string='Application Processing Fee Due Date')
    admission_due_date = fields.Date(string='Admission Fee Due Date')
    second_challan_due_date = fields.Date(string='Second Challan Due Date')
    signup_end_date = fields.Date(string='Sign up End Date')
    signin_end_date = fields.Date(string='Sign in End Date')
    commencement_class_date = fields.Date(string='Commencement of class date')
    pre_test = fields.Many2one('odoocms.pre.test', string='Pre Test')
    pre_test_ids = fields.Many2many('odoocms.pre.test','odoocms_pretest_application_rel','pretest_id','application_id', string='Pre Tests')


class OdoocmsApplicationBoard(models.Model):
    _name = 'odoocms.application.board'
    _description = 'Education Board'

    name = fields.Char(string='Name', required=True)
    sh_name = fields.Char(string='Short Name')
    code = fields.Char('Code')
    city_id = fields.Many2one('odoocms.city', 'City')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


class OdoocmsApplicationPassingYear(models.Model):
    _name = 'odoocms.application.passing.year'
    _description = 'Application Passing Year'
    _order ='name desc'

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='code')
    matric = fields.Boolean('Matric', default=True)
    inter = fields.Boolean('Intermediate', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


class ResUsers(models.Model):
    _inherit = 'res.users'

    @api.model
    def _signup_create_user(self, values):
        """ signup a new user using the template user """

        # check that uninvited users may sign up
        # if 'partner_id' not in values:
        #     if self._get_signup_invitation_scope() != 'b2c':
        #         raise SignupError(_('Signup is not allowed for uninvited users'))
        return self._create_user_from_template(values)


    @api.model
    def _get_login_domain(self, login):
        return [('login', '=', login)]


class ResCompany(models.Model):
    _inherit = 'res.company'

    short_name = fields.Char('Short Name')
    social_twitter = fields.Char('Twitter Account')
    social_facebook = fields.Char('Facebook Account')
    social_github = fields.Char('GitHub Account')
    social_linkedin = fields.Char('LinkedIn Account')
    social_youtube = fields.Char('Youtube Account')
    social_instagram = fields.Char('Instagram Account')

    admission_mail = fields.Char(string='Admission office Email')
    admission_phone = fields.Char(string='Admission office Phone')
    fax = fields.Char('Fax')
    admission_invoice = fields.Integer('Admission Invoice', default=4)
    admission_banner = fields.Image("Banner", help="Select banner image here")


class MailServer(models.Model):
    _inherit = "ir.mail_server"

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


class MailTemplate(models.Model):
    _inherit = "mail.template"

    event = fields.Selection([
        ('admission_signup', 'Admission Signup'),
        ('image_reject', 'Application Profile Image Reject'),
        ('voucher_verified', 'Admission Application Fee Verified'),
        ('voucher_un_verified', 'Admission Voucher UnVerified'),
        ('reminder_only_signup', 'Reminder Email Only Signup'),
        ('reminder_verified_only','Reminder Email Form Verified Only'),
        ('reminder_submitted_only', 'Reminder Email Form Submitted Only'),
        ('reminder_email', 'Reminder Email'),
        ('reminder_email2', 'Reminder Email2'),

    ],'Event')

    def find_template(self, company_id=None, event=None, name=None):
        domain = []
        template = False
        if company_id and self.env['ir.mail_server'].sudo().search_count([]) > 1:
            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', company_id.id)])
            domain.append(('mail_server_id', '=', mail_server_id.id))
        if event:
            domain.append(('event', '=', event))
            template = self.env['mail.template'].sudo().search(domain)
        if not template and name:
            domain.append(('event', '=', event))
            template = self.env['mail.template'].sudo().search(domain)

        return template
