from odoo import fields, models, _, api
import random
import string
import pytz
import pdb
from odoo.exceptions import UserError


class AdmitCard(models.Model):
    _name = 'generate.admit.card'
    _description = 'Generate Admit Card'
    _rec_name = 'register_id'

    register_id = fields.Many2one('odoocms.admission.register', string='Register', required=True)

    def generate_admit_card(self):
        length = 8
        all = string.ascii_letters + string.digits + '$#'
        password = "".join(random.sample(all, length))

        for rec in self:
            program_check = self.env['odoocms.program'].search([])
            student = rec.register_id.application_ids.filtered(lambda x: x.fee_voucher_state != 'verify')
            for rec2 in student:
                rec2.fee_voucher_state = 'verify'
                if rec2.fee_voucher_state == 'verify':
                    for check_program in program_check:
                        preference = rec2.preference_ids[0]
                        if preference:
                            schedule = self.env['odoocms.entry.test.schedule'].search(
                                [('register_id', '=', rec.register_id.id)]).entry_test_schedule_ids.filtered(
                                lambda x: x.status == 'open').filtered(
                                lambda x: x.program_id.id == preference.program_id.id)

                            capacity = schedule.capacity
                            count = schedule.count
                            if schedule and count < capacity:
                                if preference.program_id.id == check_program.id:
                                    if check_program.offering == True and check_program.entry_test == True and check_program.interview == True:
                                        applicant = self.env['applicant.entry.test'].search([('student_id', '=', rec2.id)])
                                        if not applicant:
                                            applicant = self.env['applicant.entry.test'].create({
                                                'student_id': rec2.id,
                                                'entry_test_schedule_details_id': schedule.id,
                                                'cbt_password': password,
                                            })
                                        schedule.count = schedule.count + 1
                                        self.env.cr.commit()

                                        # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                                        mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.applicant_id.company_id.id)])
                                        template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'),
                                             ('mail_server_id', '=', mail_server_id.id)])
                                        template.with_context().send_mail(applicant.id, force_send=True)
                                    else:
                                        raise UserError(_('Admit Card Interview and Offering are not Checked!'))
                        else:
                            raise UserError(_('Please Add Program Reference!'))
