from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class OdooCMSFeeBarcode(models.Model):
    _inherit = 'odoocms.fee.barcode'

    confirmation_mail = fields.Boolean(string="Confirmation Mail", default=False)

    def cron_fee_confirmation_mail(self):
        try:
            companies = self.env['res.company'].search([])
            for company in companies:
                current_admisison_register = self.env["odoocms.admission.register"].sudo().search(
                    [('state', '=', 'application'),('company_id','=',company.id)], limit=1)
                chalans = self.env["odoocms.fee.barcode"].sudo().search(
                    [('state', '=', 'paid'), ('term_id', '=', current_admisison_register.term_id.id),
                    ('confirmation_mail', '=', False), ('label_id.type', '=', 'admission'),('company_id','=',company.id )])

                for challan in chalans:
                    try:
                        challan.confirmation_mail = True
                        self.env.cr.commit()
                        application = self.env["odoocms.application"].sudo().search(
                            [('application_no', '=', challan.admission_no),('company_id','=',company.id)])
                        mail_values = {
                            'registration_no': challan.student_id.code or '',
                            'semester_start_date': application.register_id.semester_start_date.strftime('%d %b %Y'),
                            'term': current_admisison_register.term_id.name or '',
                            'email': application.email,
                            'company':application.company_id,
                            'logo':application.company_id.logo,

                        }
                        try:
                            if application.company_id.id ==2:
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Admission Fee Verification cust')])
                                template.with_context(mail_values).send_mail(self.id, force_send=True)
                            elif application.company_id.id ==4:
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Admission Fee Verification ubas')])
                                template.with_context(mail_values).send_mail(self.id, force_send=True)

                        except Exception as e:
                            _logger.exception(f'Error while posting fee confirmation email: {e}')
                            challan.confirmation_mail = True

                        if application:
                            msg_txt = f'Dear Student,\nHeartiest congratulations! You have been admitted to the {application.company_id.name}. For further details, please check your email. Thank you'
                            updated_mobile_no = application.mobile.replace('-', '')
                            updated_mobile_no = updated_mobile_no.replace(' ', '')
                            updated_mobile_no = updated_mobile_no.lstrip('0')
                            message = self.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.fee.barcode', challan.id)
                            gateway_id = self.env['gateway_setup'].sudo().search([('company_id','=',application.company_id.id)], order='id desc', limit=1)
                            # if gateway_id:
                            #     try:
                            #         self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, challan.id,'odoocms.fee.barcode', gateway_id, challan.admission_no, 'login', 'student', False,False, False)
                            #     except Exception as e:
                            #         challan.sudo().write({'confirmation_mail': True})
                            #         _logger.exception(f'Error while posting fee confirmation sms: {e}')
                    except Exception as e:
                        _logger.error('Error occurred: %s', str(e))
                        challan.sudo().write({'confirmation_mail': True})
                        continue
        except Exception as e:
            _logger.exception(f'Error while posting fee confirmation email or sms: {e}')
