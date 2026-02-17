from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)


def _has_registration_number(applicant):
    """
    Returns True only if a REAL registration number is present.
    """
    code = (applicant.student_id and applicant.student_id.code) or ''
    code_up = code.upper().strip()
    if not code_up:
        return False
    # Treat any code starting with 'UCP' as a Ref No
    if code_up.startswith('UCP'):
        return False
    return True


class UcpWelcomeLetter(models.Model):
    _name = 'ucp.welcome.letter'
    _description = 'UCP Welcome Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'applicant_id'

    applicant_id = fields.Many2one('odoocms.application', string='Name', required=True)
    program_id = fields.Many2one('odoocms.program', string='Program', required=True)
    reference_no = fields.Char(string='Reference No', related='applicant_id.application_no', store=False)
    is_blacklisted = fields.Boolean('Is Blacklisted', default=False)
    date = fields.Datetime(string='Date')
    letter_body = fields.Html(string='Letter Body', compute='_compute_letter_body', store=True)

    @api.depends('applicant_id.register_id.class_commencement', 'program_id')
    def _compute_letter_body(self):
        for record in self:
            company = record.env.company
            applicant = record.applicant_id
            program = record.program_id

            date_now = datetime.now().strftime('%Y-%m-%d')
            class_start = (applicant.register_id.class_commencement and
                           applicant.register_id.class_commencement.strftime('%B %d, %Y')) or 'TBD'
            phone = applicant.mobile or applicant.phone or company.admission_phone or 'N/A'

            reg_or_ref = (applicant.student_id and applicant.student_id.code) or ''

            letter = f"""
            <div style="font-family: Arial, Helvetica, sans-serif; font-size: 13px;">
                <div style="text-align: left;"><strong>Ref/Reg No:</strong> {reg_or_ref}</div>
                <div style="text-align: right;"><strong>Date:</strong> {date_now}</div>
                <div style="text-align: left;"><strong>Program:</strong> {program.name or ''}</div>
                <div style="text-align: left;"><strong>Class Start Date:</strong> {class_start}</div>

                <div class="row mt-2">
                    <div style="width:100%; text-align:justify; text-justify:inter-word;" class="col-12">
                        <p>{applicant.register_id.welcome_letter or ''}</p>
                    </div>
                </div>
                <div>Phone: {phone}</div>
                <div>{company.admission_mail or ''}</div>
                <div>{company.street or ''}</div>
            </div>
            """
            record.letter_body = letter

    # Send Mail button on the Welcome Letter form
    def send_mail(self):
        self.ensure_one()
        app = self.applicant_id

        # Block if still a Ref No (starts with UCP) or no code at all
        if not _has_registration_number(app):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Registration number not assigned'),
                    'message': _('Welcome Letter can be sent only after a registration number is issued.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }

        # only use applicant email now
        return self._send_welcome_mail(email_to=(app.email or ''))

    def _send_welcome_mail(self, email_to):
        self.ensure_one()

        if self.is_blacklisted:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Mail not sent'),
                    'message': _('This applicant is blacklisted.'),
                    'sticky': False,
                    'type': 'danger',
                }
            }

        if not email_to:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Missing email address'),
                    'message': _('No email address found for this applicant.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }

        template = self.env.ref('odoocms_admission_mis.mail_template_welcome_letter').sudo()
        sender = 'ucpadmissions@ucp.edu.pk'
        receiver = email_to.strip()

        _logger.info("EMAIL DEBUG (WELCOME): Sender: %s | Receiver: %s", sender, receiver)
        template.with_context({'mail_to': receiver, 'admission_mail': sender}).send_mail(self.id, force_send=True)

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Welcome Letter sent'),
                'message': _('Email has been sent successfully.'),
                'sticky': False,
                'type': 'success',
            }
        }

    def action_print_welcome_letter(self):
        # Logic to call the report action defined in data/report.xml
        return self.env.ref('odoocms_admission_mis.action_report_welcome_letter').report_action(self)


class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    # @api.constrains('need_based_scholarship_applied', 'meritlist_id', 'ref_meritlist')
    # def _check_need_based_scholarship_merit(self):
    #     for rec in self:
    #         if not rec.need_based_scholarship_applied:
    #             continue
    #         meritlist_id = getattr(rec, 'meritlist_id', False)
    #         ref_meritlist = getattr(rec, 'ref_meritlist', False)
    #         if not (meritlist_id or ref_meritlist):
    #             raise ValidationError(_("Need-based scholarship can only be applied to applicants in the merit list."))

    def generate_welcome_letter_from_application(self):
        self.ensure_one()
        applicant = self

        # Block if still a Ref No or no code
        if not _has_registration_number(applicant):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Registration number not assigned'),
                    'message': _('Welcome Letter will be available after a registration number is issued for this applicant.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }

        if not applicant.prefered_program_id:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Missing preferred program'),
                    'message': _('Please set Preferred Program on the application before generating the Welcome Letter.'),
                    'sticky': False,
                    'type': 'warning',
                }
            }

        program = applicant.prefered_program_id
        welcome_letter_rec = self.env['ucp.welcome.letter'].search([
            ('applicant_id', '=', applicant.id),
            ('program_id', '=', program.id),
        ], limit=1)

        if not welcome_letter_rec:
            check_black_list = applicant.cnic or applicant.passport
            blacklist_applicant = self.env['admission.blacklist.application'].sudo().search(
                [('cnic', '=', check_black_list)], limit=1)
            welcome_letter_rec = self.env['ucp.welcome.letter'].create({
                'applicant_id': applicant.id,
                'program_id': program.id,
                'is_blacklisted': bool(blacklist_applicant),
                'date': datetime.now(),
            })

        # Send mail only to applicant.email
        email_to = applicant.email or ''
        welcome_letter_rec._send_welcome_mail(email_to=email_to)

        # Open the record form view
        view_id = self.env.ref('odoocms_admission_mis.ucp_welcome_letter_view_form').id
        return {
            'name': _('Welcome Letter'),
            'view_mode': 'form',
            'res_model': 'ucp.welcome.letter',
            'res_id': welcome_letter_rec.id,
            'view_id': view_id,
            'type': 'ir.actions.act_window',
            'target': 'current',
        }


class OdooCmsMeritRegister(models.Model):
    _inherit = 'odoocms.merit.registers'

    def generate_welcome_letter(self):
        return {'type': 'ir.actions.act_window_close'}
