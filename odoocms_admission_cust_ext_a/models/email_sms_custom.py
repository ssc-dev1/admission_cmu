from odoo import models, fields, api


class CustomEmailSmsSend(models.Model):
    _name = 'custom.email.sms.send'
    _description = 'Custom Email and SMS Send Interface'


    READONLY_STATES = {
        'done': [('readonly', True)]
    }

    selection_type = fields.Selection( [('email', 'Email'), ('sms', 'SMS')], string="Select Type", required=True)
    cus_mobile_email = fields.Boolean('Custom Email/Number', info ='Formate')
    applicant_ids = fields.Many2many('odoocms.application',  string="Applicants")
    email_subject = fields.Char(string="Email Subject")
    email_body = fields.Html(string="Email Body")
    sms_body = fields.Text(string="SMS Body")
    custom_text =fields.Char(string="Custom Email/Number")
    company =  fields.Many2one(comodel_name="res.company", string="Company", required=True)
    company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)


    state = fields.Selection([('draft', 'Draft'), ('done', 'Done')],
        string="State",
        default='draft'
    )


    @api.onchange('company')
    def _onchange_company(self):
        if self.env.user:
            return {'domain': {'company': [('id', 'in', self.env.user.company_ids.ids)]}}
    @api.onchange('selection_type')
    def _onchange_selection_type(self):
        """Show or hide fields based on the selection."""
        if self.selection_type == 'email':
            self.email_subject = ''
            self.email_body = ''
        elif self.selection_type == 'sms':
            self.sms_body = ''

    def send_selected_action(self):
        """Call respective methods based on the selection type."""
        if self.selection_type == 'email':
            self.send_email_to_applicants()
        elif self.selection_type == 'sms':
            self.send_sms_to_applicants()
        # Set the state to 'done' after sending
        self.state = 'done'

    def send_email_to_applicants(self):
        """Invoke the email sending logic."""
        if not self.cus_mobile_email:
            for applicant in self.applicant_ids:
                wizard = self.env['student.email.wizard'].create({
                    'subject': self.email_subject,
                    'body': self.email_body
                })
                wizard.with_context(active_ids=[applicant.id]).send_email()
        else:
            wizard = self.env['student.email.wizard'].create({
                    'subject': self.email_subject,
                    'body': self.email_body
                })
            wizard.with_context(custom_text=self.custom_text, company =self.company).send_email()
    def send_sms_to_applicants(self):
        """Invoke the SMS sending logic."""
        if not self.cus_mobile_email:
            for applicant in self.applicant_ids:
                wizard = self.env['student.sms.wizard'].create({
                    'sms': self.sms_body
                })
                wizard.with_context(active_ids=[applicant.id]).send_sms()
        else:

                wizard = self.env['student.sms.wizard'].create({
                    'sms': self.sms_body
                })
                wizard.with_context(custom_text=self.custom_text,company=self.company).send_sms()
        

class StudentEmailWizard(models.TransientModel):
    _name = 'student.email.wizard'
    _description = 'Send Email to Students'

    subject = fields.Char(string="Subject", required=True)
    body = fields.Html(string="Email Body", required=True) 
    # company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
 

    def send_email(self):
        active_ids = self.env.context.get('active_ids')
        custom_text=self.env.context.get('custom_text')
        company=self.env.context.get('company')


        if not custom_text:
            template = self.env.ref('odoocms_admission_cust_ext_a.email_template_custom')
            if not active_ids:
                return  
            applicants = self.env['odoocms.application'].browse(active_ids)
            for applicant in applicants:
                try:
                    if template:
                        template.with_context(
                            subject=self.subject,
                            body_html=self.body,
                            email_from=applicant.company_id.admission_mail,
                            email_to=applicant.email
                        ).send_mail(applicant.id, force_send=True)
                except Exception as e :
                        continue
        else :
            if not custom_text or not company :
                return 
            custom_email_list =self.split_by_comma(custom_text)
            template = self.env.ref('odoocms_admission_cust_ext_a.email_template_custom_user')
            for email in custom_email_list:
                try:
                    if template:
                        template.with_context(
                            subject=self.subject,
                            body_html=self.body,
                            email_from=company.admission_mail,
                            email_to=email
                        ).send_mail(self.env.user.id,force_send=True)
                except Exception as e :
                        continue

    def split_by_comma(self,custom_string):
        if ',' in custom_string:
            return [item.strip() for item in custom_string.split(',')]
        return [custom_string.strip()]

class StudentSmsWizard(models.TransientModel):
    _name = 'student.sms.wizard'
    _description = 'Send SMS to Students'


    sms = fields.Text(string="SMS Body", required=True)
    # company_id = fields.Many2one('res.company', required=True, readonly=True, default=lambda self: self.env.company)
  



    def send_sms(self):
        active_ids = self.env.context.get('active_ids')
        custom_text=self.env.context.get('custom_text')
        company=self.env.context.get('company')

        if not custom_text:
            if not active_ids:
                return  
            applicants = self.env['odoocms.application'].browse(active_ids)

            for applicant in applicants:
                company = applicant.company_id
                msg_txt = self.sms
                updated_mobile_no = applicant.mobile.replace('-', '')
                updated_mobile_no = updated_mobile_no.replace(' ', '')
                updated_mobile_no = updated_mobile_no.lstrip('0')
                message = self.env['send_sms'].sudo().render_template(msg_txt, 'student.sms.wizard', applicant.id)
                gateway_id = self.env['gateway_setup'].sudo().search([('company_id','=',applicant.company_id.id)], order='id desc', limit=1)
                if gateway_id:
                    try:
                        # self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, applicant.id,'student.sms.wizard', gateway_id, applicant.application_no,'login','student',False,False,False)
                        self.prepare_sms_cron_values(applicant,updated_mobile_no,message,gateway_id)
                    except Exception as e:
                        continue
        else:
            if not custom_text or not company :
                return 
            custom_numbers_list =self.split_by_comma(custom_text)
            for number in custom_numbers_list:
                msg_txt = self.sms
                updated_mobile_no = number.replace('-', '')
                updated_mobile_no = number.replace(' ', '')
                updated_mobile_no = number.lstrip('0')
                message = self.env['send_sms'].sudo().render_template(msg_txt, 'student.sms.wizard', 2)
                gateway_id = self.env['gateway_setup'].sudo().search([('company_id','=',company.id)], order='id desc', limit=1)
                if gateway_id:
                    try:
                        # self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, applicant.id,'student.sms.wizard', gateway_id, applicant.application_no,'login','student',False,False,False)
                        self.prepare_sms_cron_values_custom(number,updated_mobile_no,message,gateway_id)
                    except Exception as e:
                        continue

    def split_by_comma(self,custom_string):
        if ',' in custom_string:
            return [item.strip() for item in custom_string.split(',')]
        return [custom_string.strip()]
    def prepare_sms_cron_values(self, application, updated_mobile_no, message,gateway_id):
        sms_data_values = {
            'model_id': 'student.sms.wizard',
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

    def prepare_sms_cron_values_custom(self, number, updated_mobile_no, message,gateway_id):
        sms_data_values = {
            'model_id': 'student.sms.wizard',
            'res_id': 2,
            'mobile_no': updated_mobile_no,
            'message_id': message,
            'gateway_id': gateway_id.id,
            'send_to': number,
            'sms_nature': 'other',
            'type': 'student',
            'department_id': False,
            'institute_id': False,
            'mobile_network': '',
        }
        self.env['send_sms.cron'].sudo().create(sms_data_values)