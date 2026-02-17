import pdb

from odoo import fields, models, api
from odoo.exceptions import UserError


class AllocateSlotRetestWizard(models.TransientModel):

    _name = 'allocate.slot.retest.wizard'

    def _allocate_retest_slot_ids(self):

        if self.env.context and self.env.context.get('active_ids'):
            return self.env.context.get('active_ids')
        return []

    applicant_admit_ids = fields.Many2many(
        'applicant.entry.test', string='Applicant/Admit Card', default=_allocate_retest_slot_ids)
    # register_id = fields.Many2one(
    #     'odoocms.admission.register', string='Register')

    def allocate_retest_slot(self):

        for rec in self.applicant_admit_ids:
                # .filtered(lambda x: x.student_id.state not in ['done', 'reject']):
            # preference_program = rec.preference_ids.filtered(
            #     lambda x: x.preference == 1).program_id
            # test_schedule_details = self.env['odoocms.entry.schedule.details'].search(
            #     [('status', '=', 'open'), ('program_id', '=', preference_program.id)])
            # test_schedule_register = test_schedule_details.filtered(
            #     lambda x: x.entry_schedule_id.register_id.id == rec.register_id.id)
            # if not test_schedule_register:
            #     raise UserError(
            #         f'No Schedule Open For This Program {preference_program.name} For This Register!')

            rec.generate_retest()

    # @api.onchange('register_id')
    # def onchange_register_id(self):
    #     if self.register_id:
    #         applicant = self.register_id.application_ids.filtered(
    #             lambda x: x.fee_voucher_state == 'verify').filtered(lambda x: x.state not in ['done', 'reject'])
    #         entry_test = self.env['applicant.entry.test'].search(
    #             [('student_id', 'in', applicant.ids)]).student_id
    #         non_allocated_candidates = applicant.filtered(
    #             lambda x: x.id not in entry_test.ids)
    #         self.applicant_ids = non_allocated_candidates
