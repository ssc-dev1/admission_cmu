from datetime import date, datetime, timedelta
from odoo import models, fields, api, _
import pdb


class OdooCMS_Admission_Reg_ubas_Ext(models.Model):
    _inherit = "odoocms.admission.register"

    @api.model
    def followup_email(self):
        admission_register = self.search([('state', '=', 'application')])
        today = datetime.now()
        is_sunday = today.weekday() == 6
        is_monday = today.weekday() == 0
        if is_sunday or is_monday:
            for register in admission_register:
                applications = register.application_ids.filtered(
                    lambda x: x.state in ['draft', 'submit'] and x.fee_voucher_state in ['no', 'download'])
                if is_sunday:
                    draft_applications = applications.filtered(lambda x: x.state == 'draft')
                    draft_applications = draft_applications.filtered(
                        lambda x: x.create_date < datetime.now() - timedelta(days=3))
                    # saturday reminder email
                    if draft_applications:
                        # template = self.env.ref('odoocms_admission.mail_template_reminder_email').sudo()
                        mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', register.company_id.id)])
                        template = self.env['mail.template'].sudo().search([('name', '=', 'Reminder Email'), ('mail_server_id', '=', mail_server_id.id)])
                        for applicant in draft_applications.filtered(lambda x: x.followup_mail_draft_date != datetime.today().date()):
                            email_value = {
                                'mail_to': applicant.email,
                                # 'admission_mail': self.env.company.admission_mail,
                                'admission_mail': register.company_id.admission_mail,
                                'applicant_name': applicant.name,
                            }
                            template.with_context(email_value).send_mail(register.id, force_send=True)
                            applicant.write({
                                'followup_mail_draft': True,
                                'followup_mail_draft_date': datetime.today(),
                            })

                # monday reminder email
                if is_monday:
                    submit_applications = applications.filtered(lambda x: x.state == 'submit')
                    submit_applications = submit_applications.filtered(lambda x: x.create_date < datetime.now() - timedelta(days=3))
                    if submit_applications:
                        for applicant in submit_applications.filtered(lambda x: x.followup_mail_submit_date != datetime.today().date()):
                            # template = self.env.ref('odoocms_admission.mail_template_reminder_email2').sudo()
                            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', register.company_id.id)])
                            template = self.env['mail.template'].sudo().search([('name', '=', 'Reminder Email 2'), ('mail_server_id', '=', mail_server_id.id)])
                            email_value = {
                                'mail_to': applicant.email,
                                'admission_mail': register.company_id.admission_mail,
                                'applicant_name': applicant.name,
                            }
                            template.with_context(email_value).send_mail(register.id, force_send=True)
                            applicant.write({
                                'followup_mail_submit': True,
                                'followup_mail_submit_date': datetime.today(),
                            })

