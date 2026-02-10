import pdb

from odoo import fields, models, api
from odoo.exceptions import UserError


class CustomSlotAllocationWizard(models.TransientModel):

    _name = 'custom.slot.allocation.wizard'

    def _allocate_slot_ids(self):

        if self.env.context and self.env.context.get('active_ids'):
            return self.env.context.get('active_ids')
        return []

    applicant_admit_ids = fields.Many2many('applicant.entry.test', string='Applicant/Admit Card', default=_allocate_slot_ids)
    slot = fields.Many2one('odoocms.entry.test.schedule', string='Slot',domain="[('company_id', 'in', company_ids)]")
    company_ids = fields.Many2many(
        'res.company',
        string='Allowed Companies',
        default=lambda self: self.env.user.company_ids
    )

    def allocate_slot(self):

        for rec in self.applicant_admit_ids:
            test_schedule_details = self.env['odoocms.entry.schedule.details'].search([('entry_schedule_id', '=', self.slot.id), ('program_id', '=', rec.program_id.id)])
            if not test_schedule_details:
                raise UserError(f'No Schedule Found For This Program {rec.program_id.name} For This Entry Test Schedule {self.slot.entry_test_room_id.name} on date {self.slot.date}, slot {self.slot.entry_test_slots_id.display_name}!')
            else:
                for etd in test_schedule_details:
                    rec.entry_test_schedule_details_id =etd.id
                    if rec.student_id:
                        mail_value = {
                        'applicant_name': rec.student_id.name,
                        'company_name': self.env.company.name,
                        'admission_mail': self.env.company.admission_mail,
                        'mail_to':rec.student_id.email,
                        'admission_phone': self.env.company.admission_phone,
                        'password':rec.cbt_password,
                        'username':rec.student_id.application_no,
                        'venue':self.slot.entry_test_room_id.name,
                        'time': self.slot.date.strftime('%Y-%m-%d') + ' ' + self.slot.entry_test_slots_id.display_name,
                        }
                        # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                        try:
                            if rec.student_id:
                                mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', rec.student_id.company_id.id)])
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'), ('mail_server_id', '=', mail_server_id.id)])
                                template.with_context(mail_value).send_mail(rec.student_id.id, force_send=True)
                        except Exception as e :
                            continue
