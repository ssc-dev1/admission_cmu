from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime,timedelta


class OdooCMSAdmissionRegister(models.Model):
    _name = 'odoocms.admission.register'
    _description = "Admission Register"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, readonly=True, states={'draft': [('readonly', False)]})
    academic_session_id = fields.Many2one('odoocms.academic.session', 'Academic Session', required=True)
    campus_id = fields.Many2one('odoocms.campus', 'Campus')
    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term', required=False)
    career_id = fields.Many2one('odoocms.career', 'Career', required=True)
    date_start = fields.Date('Start Date', readonly=False, default=fields.Date.today(),
                             states={'draft': [('readonly', False)]})
    date_end = fields.Date('End Date', readonly=False, default=(fields.Date.today() + relativedelta(days=30)),
                           tracking=True, states={'draft': [('readonly', False)]})
    dob_min = fields.Date(string='DOB Minimum')
    dob_max = fields.Date(string='DOB Maximum')
    preferences_allowed = fields.Integer(string='Preferences Allowed')

    eligibility_criteria_image = fields.Binary('Eligibility criteria Image', states={'draft': [('readonly', False)]})
    program_ids = fields.Many2many('odoocms.program', 'register_program_rel', 'register_id', 'program_id', 'Offered Programs')
    min_edu_year = fields.Integer(string='Minimum Education Year', default=12,required=True, )

    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirmed'),
         ('cancel', 'Cancelled'), ('application', 'Application Gathering'), ('sort', 'Application Stoped'),
         ('admission', 'Merit Process'), ('merit', 'Merit'), ('done', 'Done')],
        'Status', default='draft', tracking=True)

    application_ids = fields.One2many('odoocms.application', 'register_id', 'Admissions')

    # Test Series
    undertaking = fields.Html(string='Undertaking')
    test_series_ids = fields.One2many('odoocms.admission.test.series', 'register_id', 'Test Series')
    offer_letter = fields.Html('Offer Letter')
    admit_card_letter = fields.Html('Admit Card Setup')
    merit_list_line = fields.Html('Merit List Line')
    important_notes_line = fields.Html('Important Notes Line')
    class_commencement = fields.Date('Class Commencement Date',required=True)
    enable_admission_challan = fields.Boolean('Enable Admission Challan',default=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    registration_fee = fields.Float(string='Fee for admission Registration')
    registration_fee_international = fields.Float(string='Fee for admission Registration')
    additional_fee = fields.Float(string='Fee for Additional Registration')

    account_payable = fields.Char(string='Account Title admission Registration')
    account_title = fields.Char(string='Account for admission Registration')
    account_no = fields.Char(string='Account Number admission Registration')

    def sort_applications(self):
        i = 1
        for application in self.application_ids.filtered(lambda l: l.state in ('approve', 'open', 'submit')).sorted(
                key=lambda r: r.merit_score, reverse=True):
            # for application in self.application_ids.filtered(lambda l: l.state in ('approve', 'open', 'submit')).sorted(key=lambda r: r.manual_score, reverse=True):

            if not application.preference_ids:
                raise UserError('Program Preference not set for %s - %s not Set.' % (application.entry_registration, application.name))

            # if self.information_gathering:
            #     application.write({
            #         'program_id': application.preference_ids and application.preference_ids[0].program_id.id,
            #         'locked': True,
            #         'state': 'open',
            #         'preference': 1,
            #     })

            if application.cnic and len(application.cnic) == 13:
                application.cnic = application.cnic[:5] + '-' + application.cnic[5:12] + '-' + application.cnic[12:]

            application.merit_number = i
            i += 1

    @api.constrains('dob_max', 'dob_min')
    def date_constrains(self):
        for rec in self:
            if rec.dob_max > rec.dob_min:
                raise ValidationError(_('Sorry, DOB Max Date Must be Less Than DOB Min Date...'))

    @api.constrains('date_start', 'date_end')
    def check_dates(self):
        for record in self:
            start_date = fields.Date.from_string(record.date_start)
            end_date = fields.Date.from_string(record.date_end)
            if start_date > end_date:
                raise ValidationError(_("End Date cannot be set before Start Date."))

    def confirm_register(self):
        self.state = 'confirm'

    def set_to_draft(self):
        self.state = 'draft'

    def cancel_register(self):
        self.state = 'cancel'

    def start_application(self):
        self.state = 'application'

    def stop_application(self):
        self.state = 'sort'

    def start_admission(self):
        self.sort_applications()
        self.state = 'admission'
    
    # @api.model
    def followup_email(self):
        application = self.env['odoocms.application'].sudo().search([('register_id','=',self.id)])

        def send_followup_sms(application):
            msg_txt = f'Dear {application.name},\n Please complete the UCP Admission Form to ensure timely completion of the admission process. If you need assistance, please contact us at 080-000-827 (9:00 AM to 5:00 PM) or email us at admissions@ucp.edu.pk.'
            updated_mobile_no = application.mobile.replace('-', '').replace(' ', '').lstrip('0')
            message = self.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.application', application.id)
            gateway_id = self.env['gateway_setup'].sudo().search([], order='id desc', limit=1)
            if gateway_id:
                self.prepare_sms_cron_values(application, updated_mobile_no, message, gateway_id)

                # self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, application.id,'odoocms.application', gateway_id, application.name,'other','student',False,False,False)

        for register in self:
            only_signup = application.filtered(lambda x:x.state == 'draft' and x.fee_voucher_state != 'verify' and  x.create_date < datetime.now() - timedelta(hours=3)).sudo()
            fee_verified_not_submitted = application.filtered(lambda x:x.fee_voucher_state == 'verify' and x.state == 'draft').sudo()
            only_submitted = application.filtered(lambda x:x.fee_voucher_state != 'verify' and x.state == 'submit').sudo()

            if only_signup:
                only_signup_template = self.env['mail.template'].sudo().find_template(company_id=self.company_id, event='reminder_only_signup', name='Reminder Email Only Signup')
                if only_signup_template:
                    for application in only_signup:
                        valid_application = False

                        if application.mail_count == 0:
                            valid_application = True

                        if application.mail_count == 1 and ( datetime.now() - timedelta(days=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if application.mail_count == 2 and ( datetime.now() - timedelta(days=9) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True


                        if valid_application and application.mail_count < 3:
                            email_value = {
                                'mail_to':application.email,
                                'admission_mail':'ucpadmissions@ucp.edu.pk',
                                'applicant_name':application.name,
                                "company_name":self.env.company.name,
                                "company_website":self.env.company.website,
                                "admission_phone":self.env.company.admission_phone,
                                "street":self.env.company.street,
                                "street2":self.env.company.street2,
                                }
                            send_followup_sms(application)
                            only_signup_template.with_context(email_value).sudo().send_mail(register.id, force_send=True)
                            application.mail_count += 1
                            application.last_mail_time = datetime.now()
                            self.env.cr.commit()

            if fee_verified_not_submitted:
                fee_verified_not_submitted_template = self.env['mail.template'].sudo().find_template(company_id=self.company_id, event='reminder_verified_only', name='Reminder Email Form Verified Only')
                if fee_verified_not_submitted_template:
                    for application in fee_verified_not_submitted:
                        valid_application = False

                        if application.mail_count == 0 and ( datetime.now() - timedelta(hours=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if application.mail_count == 1 and ( datetime.now() - timedelta(days=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if application.mail_count == 2 and ( datetime.now() - timedelta(days=9) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if valid_application and application.mail_count < 3:
                            email_value = {
                                'mail_to':application.email,
                                'admission_mail':'ucpadmissions@ucp.edu.pk',
                                'applicant_name':application.name,
                                "company_name":self.env.company.name,
                                "company_website":self.env.company.website,
                                "admission_phone":self.env.company.admission_phone,
                                "street":self.env.company.street,
                                "street2":self.env.company.street2,
                                }
                            send_followup_sms(application)
                            fee_verified_not_submitted_template.with_context(email_value).sudo().send_mail(register.id, force_send=True)
                            application.mail_count += 1
                            application.last_mail_time = datetime.now()
                            self.env.cr.commit()


            if only_submitted:
                only_submitted_template = self.env['mail.template'].sudo().find_template(company_id=self.company_id, event='reminder_submitted_only', name='Reminder Email Form Submitted Only')
                if only_submitted_template:
                    for application in only_submitted:
                        valid_application = False

                        if application.mail_count == 0 and ( datetime.now() - timedelta(hours=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if application.mail_count == 1 and ( datetime.now() - timedelta(days=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if application.mail_count == 2 and ( datetime.now() - timedelta(days=9) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                            valid_application = True

                        if valid_application and application.mail_count < 3:
                            email_value = {
                                'mail_to':application.email,
                                'admission_mail':'ucpadmissions@ucp.edu.pk',
                                'applicant_name':application.name,
                                "company_name":self.env.company.name,
                                "company_website":self.env.company.website,
                                "admission_phone":self.env.company.admission_phone,
                                "city":self.env.company.city,
                                "street":self.env.company.street,
                                "street2":self.env.company.street2,
                                }
                            send_followup_sms(application)
                            only_submitted_template.with_context(email_value).sudo().send_mail(register.id, force_send=True)
                            application.mail_count += 1
                            application.last_mail_time = datetime.now()
                            self.env.cr.commit()


    def prepare_sms_cron_values(self, application, updated_mobile_no, message, gateway_id):
        sms_data_values = {
            'model_id': 'odoocms.application',
            'res_id': application.id,
            'mobile_no': updated_mobile_no,
            'message_id': message,
            'gateway_id': gateway_id.id,
            'send_to': application.name,
            'sms_nature': 'other',
            'type': 'student',
            'department_id': False,
            'institute_id': False,
            'mobile_network': '',
        }
        self.env['send_sms.cron'].sudo().create(sms_data_values)
        # self.prepare_sms_cron_values(application, updated_mobile_no, message, gateway_id)

    @api.model
    def followup_email2(self):
        admission_register = self.search([('state','=','application')])
        today = datetime.now()
        is_sunday = today.weekday() == 6
        is_monday = today.weekday() == 0
        if is_sunday or is_monday:  
            for register in admission_register:
                applications = register.application_ids.filtered(lambda x:x.state in ['draft','submit'] and x.fee_voucher_state in ['no','download'])
                if is_sunday:
                    draft_applications = applications.filtered(lambda x:x.state =='draft')
                    draft_applications = draft_applications.filtered(lambda x: x.create_date < datetime.now() - timedelta(days=3) )
                    # saturday reminder email
                    if draft_applications:
                        template = self.env['mail.template'].sudo().find_template(company_id=self.company_id, event='reminder_email', name='Reminder Email')
                        if template:
                            for applicant in draft_applications.filtered(lambda x:x.followup_mail_draft_date != datetime.today().date()):
                                email_value = {
                                    'mail_to':applicant.email,
                                    'admission_mail':self.env.company.admission_mail,
                                    'applicant_name':applicant.name,
                                    }
                                template.with_context(email_value).send_mail(register.id, force_send=True)
                                applicant.write({
                                    'followup_mail_draft':True,
                                    'followup_mail_draft_date':datetime.today(),
                                    })
                    
                
                # monday reminder email
                if is_monday:
                    submit_applications = applications.filtered(lambda x:x.state =='submit')
                    submit_applications = submit_applications.filtered(lambda x: x.create_date < datetime.now() - timedelta(days=3) )
                    if submit_applications:
                        template = self.env['mail.template'].sudo().find_template(company_id=self.company_id, event='reminder_email2', name='Reminder Email2')
                        if template:
                            for applicant in submit_applications.filtered(lambda x:x.followup_mail_submit_date != datetime.today().date()):
                                email_value = {
                                    'mail_to':applicant.email,
                                    'admission_mail':self.env.company.admission_mail,
                                    'applicant_name':applicant.name,

                                    }
                                template.with_context(email_value).send_mail(register.id, force_send=True)
                                applicant.write({
                                    'followup_mail_submit':True,
                                    'followup_mail_submit_date':datetime.today(),
                                })


class OdooCMSAdmissionMerit(models.Model):
    _name = "odoocms.admission.merit.criteria"
    _description = "Admission Merit Criteria"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    register_id = fields.Many2one('odoocms.admission.register', 'Admission Register', required=True)
    program_ids = fields.Many2many('odoocms.program', string='Program', required=True)
    matric_percentage = fields.Float('Matric Percentage', default=60,
                                     help='If this is not eligible for any program, Add percentage > 100')


class ResCompany(models.Model):
    _inherit = 'res.company'

    admission_phone = fields.Char()
