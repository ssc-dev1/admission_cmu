from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime,timedelta,date
import logging


_logger = logging.getLogger(__name__)


class OdooCMSAdmissionRegister(models.Model):
    _inherit = "odoocms.admission.register"


    semester_start_date  = fields.Date(string="Semester Start Date")


    def followup_email_cron(self):
        sms_queue_count =0
        today_date = date.today().strftime('%Y-%m-%d')
        sms_count = self.env['sms_track'].sudo().search_count([('create_date', '>=', today_date + ' 00:00:00'),('create_date', '<=', today_date + ' 23:59:59')])
        companies = self.env['res.company'].search([])
        if companies:
            for company in companies:
                registers = self.env['odoocms.admission.register'].sudo().search([('state','=','application'),('company_id','=',company.id)])
                if len(registers) > 0:
                    for record in registers:
                        sms_to_send_count = record.followup_email_c()
                        sms_queue_count += sms_to_send_count
                    if sms_queue_count is not None:
                        template = self.env.ref('odoo_admission_ext_a.mail_template_daily_outgoing_sms').sudo()
                        pass_val = {
                            'company':company,
                            'sms_sent': sms_count if sms_count else 0,
                            'sms_queue': sms_queue_count
                        }
                        template.with_context(pass_val).send_mail(self.env.user.id,force_send=True)

    def followup_email_c(self):
        sms_to_send_count=0
        admission_register = self
        application = self.env['odoocms.application'].sudo().search([('register_id','=',self.id)])

        def send_followup_sms(application):
            msg_txt = f'Dear {application.name},\n Please complete the {application.company_id.code} Admission Form to ensure timely completion of the admission process. If you need assistance, please contact us at {application.company_id.admission_phone}(9:00 AM to 5:00 PM) or email us at {application.company_id.admission_mail}.'
            updated_mobile_no = application.mobile.replace('-', '').replace(' ', '').lstrip('0')
            message = self.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.application', application.id)
            gateway_id = self.env['gateway_setup'].sudo().search([('company_id','=',application.company_id.id)], order='id desc', limit=1)
            if gateway_id:
                self.prepare_sms_cron_values(application, updated_mobile_no, message, gateway_id)

                # self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, application.id,'odoocms.application', gateway_id, application.name,'other','student',False,False,False)

        for register in admission_register:

            only_signup = application.filtered(lambda x:x.state == 'draft' and x.fee_voucher_state != 'verify' and  x.create_date < datetime.now() - timedelta(hours=3)).sudo()
            fee_verified_not_submitted = application.filtered(lambda x:x.fee_voucher_state == 'verify' and x.state == 'draft').sudo()
            only_submitted = application.filtered(lambda x:x.fee_voucher_state != 'verify' and x.state == 'submit').sudo()

            if only_signup:
                only_signup_template = self.env['mail.template'].sudo().search([('company_id','=',self.company_id.id),  ('name','=','Reminder Email')])

                for application in only_signup:
                    valid_application = False

                    if application.mail_count == 0:
                        valid_application = True

                    if application.mail_count == 1 and ( datetime.now() - timedelta(days=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if application.mail_count == 2 and ( datetime.now() - timedelta(days=9) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True


                    if valid_application and application.mail_count < 3:
                        
                        try:
                            sms_to_send_count +=1
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
                            
                            application.mail_count += 1
                            application.last_mail_time = datetime.now()
                            only_signup_template.with_context(email_value).sudo().send_mail(register.id, force_send=True)
                            send_followup_sms(application)
                            self.env.cr.commit()
                        except Exception as e:
                            _logger.error(f"Failed to send follow-up sms for application ID {application.id}: {e}")
                            self.env.cr.rollback()
                            application.mail_count += 1

            if fee_verified_not_submitted:
                fee_verified_not_submitted_template = self.env['mail.template'].sudo().search([('company_id','=',self.company_id.id),  ('name','=','Reminder Email')])
                for application in fee_verified_not_submitted:
                    valid_application = False

                    if application.mail_count == 0 and ( datetime.now() - timedelta(hours=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if application.mail_count == 1 and ( datetime.now() - timedelta(days=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if application.mail_count == 2 and ( datetime.now() - timedelta(days=9) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if valid_application and application.mail_count < 3:
                        
                        try:
                            sms_to_send_count +=1
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
                            
                            application.mail_count += 1
                            application.last_mail_time = datetime.now()
                            only_signup_template.with_context(email_value).sudo().send_mail(register.id, force_send=True)
                            send_followup_sms(application)
                            self.env.cr.commit()
                        except Exception as e:
                            _logger.error(f"Failed to send follow-up sms for application ID {application.id}: {e}")
                            self.env.cr.rollback()
                            application.mail_count += 1


            if only_submitted:
                only_submitted_template = self.env['mail.template'].sudo().search([('company_id','=',self.company_id.id),  ('name','=','Remider Email 2')])
                for application in only_submitted:
                    valid_application = False

                    if application.mail_count == 0 and ( datetime.now() - timedelta(hours=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if application.mail_count == 1 and ( datetime.now() - timedelta(days=3) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if application.mail_count == 2 and ( datetime.now() - timedelta(days=9) > application.last_mail_time if application.last_mail_time else  datetime.now()):
                        valid_application = True

                    if valid_application and application.mail_count < 3:
                        
                        try:
                            sms_to_send_count +=1
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
                            
                            application.mail_count += 1
                            application.last_mail_time = datetime.now()
                            only_signup_template.with_context(email_value).sudo().send_mail(register.id, force_send=True)
                            send_followup_sms(application)
                            self.env.cr.commit()
                        except Exception as e:
                            _logger.error(f"Failed to send follow-up sms for application ID {application.id}: {e}")
                            self.env.cr.rollback()
                            application.mail_count += 1
        return sms_to_send_count
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