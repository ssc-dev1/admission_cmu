import pdb

from odoo import fields, models, _, api
from datetime import date
import random
import string
from odoo.exceptions import UserError, ValidationError, Warning


class ApplicantEntryTest(models.Model):
    _name = 'applicant.entry.test'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Applicant Entry Test'
    _rec_name = 'student_id'

    entry_test_schedule_details_id = fields.Many2one('odoocms.entry.schedule.details', string='Schedule', ondelete="cascade")
    program_id = fields.Many2one('odoocms.program', string='Program', related='entry_test_schedule_details_id.program_id', store=True)

    student_id = fields.Many2one('odoocms.application', string='Application')
    email = fields.Char('Applicant Email', related='student_id.email')
    mobile = fields.Char('Applicant Mobile', related='student_id.mobile')
    register_id = fields.Many2one('odoocms.admission.register', string='Register', related='student_id.register_id', store=True)
    applicant = fields.Char(related='student_id.name', string='Applicant')
    reference_no = fields.Char(
        related='student_id.application_no', string='Reference no')
    room = fields.Many2one(string='Room',related='entry_test_schedule_details_id.entry_schedule_id.entry_test_room_id', store=True)
    slots = fields.Many2one(string='Slots',
                            related='entry_test_schedule_details_id.entry_schedule_id.entry_test_slots_id', store=True)
    date = fields.Date(string='Date',related='entry_test_schedule_details_id.entry_schedule_id.date', store=True)
    entry_test_marks = fields.Float(' Test Total Marks', compute='_entry_test_marks', store=True)
    interview_total_marks = fields.Float(' Test Total Marks')
    cbt_marks = fields.Float(' Test Obtained Marks')
    interview_marks = fields.Float(' Interview Obtained Marks')
    cbt_id = fields.Integer(string='CBT ID')
    master_id = fields.Integer(string='Master ID')
    active = fields.Boolean('active', default=True)
    cbt_password = fields.Char(string='CBT Password')
    state = fields.Boolean(string='Active', default=True)
    applicant_line_ids = fields.One2many('applicant.entry.test.line', 'applicant_id')
    description = fields.Html(string='Description')
    passing_threshold = fields.Integer(string='Passing %age', default=0)
    # cbt_test_id = fields.Many2one('cbt.test.program', string='Cbt Test')
    # paper_conducted = fields.Char(' Test/Interview Conducted')
    paper_conducted = fields.Boolean('Paper Conducted')
    paper_status = fields.Selection(
        string=' Test/Interview Status', compute='_get_test_status',
        selection=[
            ('missed', 'Paper/Interview Missed'),
            ('pass', 'Pass'),
            ('failed', 'Failed')],store=True)
    attempts = fields.Integer("No. of attempts", compute='_get_no_of_attempts')

    company_id = fields.Many2one(related="student_id.company_id", string='Company', store="true")
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    def generate_retest(self):
        length = 8
        all = string.ascii_letters + string.digits + '$#'
        password = "".join(random.sample(all, length))

        for rec in self:
            # if rec.fee_voucher_state == 'verify':
            #     rec.voucher_verified_date = fields.Date.today()
            preference_program = rec.program_id

            test_schedule_details = self.env['odoocms.entry.schedule.details'].search(
                [('status', 'in', ('open', 'initialize')), ('program_id', '=', preference_program.id)]).filtered(
                lambda x: x.entry_schedule_id.register_id.id == rec.register_id.id and
                    x.entry_schedule_id.date >= date.today()  and x.entry_schedule_id.register_id.company_id == rec.company_id)

            # test_schedule_details_open = test_schedule_details.filtered(lambda x: x.status == 'open')
            #
            # test_schedule_details_init = test_schedule_details.filtered(lambda x: x.status == 'initialize').sorted(
            #     key=lambda s: s.entry_schedule_id.date, reverse=False)
            # First Case
            # and preference_program.interview == False
            if preference_program.entry_test:
                test_schedule_details_open = test_schedule_details.filtered(lambda x: x.entry_schedule_id.slot_type == 'test' and x.status == 'open')
                test_schedule_details_init = test_schedule_details.filtered(lambda x: x.status == 'initialize' and x.entry_schedule_id.slot_type == 'test').sorted(key=lambda s: s.entry_schedule_id.date, reverse=False)

                if not test_schedule_details_open and not test_schedule_details_init:
                    raise UserError(
                        f'No Test Schedule  Available For This Program {preference_program.name}')

                if test_schedule_details_open:
                    # test_schedule_details_opens = test_schedule_details_open
                    test_schedule_details_open = test_schedule_details_open[0]

                    applicant = self.env['applicant.entry.test'].sudo().search([('student_id', '=', rec.student_id.id),('entry_test_schedule_details_id', '=', test_schedule_details_open.id),('slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])

                    if applicant:
                        applicant = self.env['applicant.entry.test'].sudo().create({
                            'student_id': rec.student_id.id,
                            'entry_test_schedule_details_id': test_schedule_details_open.id,
                            'cbt_password': password,
                        })
                        test_schedule_details_open.count += 1
                        if applicant:
                            # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.applicant_id.company_id.id)])
                            template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'), ('mail_server_id', '=', mail_server_id.id)])
                            template.with_context().send_mail(applicant.id, force_send=True)
                        if test_schedule_details_open.capacity == test_schedule_details_open.count:
                            test_schedule_details_open.status = 'full'
                elif test_schedule_details_init:
                    test_schedule_details_inits = test_schedule_details_init
                    test_schedule_details_open = test_schedule_details_init[0]
                    # test_schedule_details_open.status = 'open'

                    applicant = self.env['applicant.entry.test'].sudo().search(
                        [('student_id', '=', rec.student_id.id),
                         ('entry_test_schedule_details_id', '=', test_schedule_details_open.id), (
                             'slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
                         ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
                    if applicant:
                        applicant = self.env['applicant.entry.test'].sudo().create({
                            'student_id': rec.student_id.id,
                            'entry_test_schedule_details_id': test_schedule_details_open.id,
                            'cbt_password': password,
                        })
                        test_schedule_details_open.status = 'open'
                        test_schedule_details_open.count += 1
                        if applicant:
                            template = self.env.ref(
                                'odoocms_admission_ucp.mail_template_test_email')
                            template.with_context().send_mail(applicant.id, force_send=True)
                        if test_schedule_details_open.capacity == test_schedule_details_open.count:
                            test_schedule_details_open.status = 'full'

            # # Second Case
            # if preference_program.interview == True and preference_program.entry_test == False:
            #     test_schedule_details_open = test_schedule_details.filtered(
            #         lambda x: x.entry_schedule_id.slot_type == 'interview' and x.status == 'open')
            #     test_schedule_details_init = test_schedule_details.filtered(
            #         lambda x: x.status == 'initialize' and x.entry_schedule_id.slot_type == 'interview').sorted(
            #         key=lambda s: s.entry_schedule_id.date, reverse=False)
            #     if not test_schedule_details_open and not test_schedule_details_init:
            #         raise UserError(
            #             f'No Interview Schedule Available For This Program {preference_program.name}')
            #     if test_schedule_details_open:
            #         test_schedule_details_opens = test_schedule_details_open
            #         test_schedule_details_open = test_schedule_details_open[0]
            #         applicant = self.env['applicant.entry.test'].sudo().search(
            #             [('student_id', '=', rec.student_id.id),
            #              ('entry_test_schedule_details_id', '=', test_schedule_details_open.id), (
            #                  'slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
            #              ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
            #         if applicant:
            #             applicant = self.env['applicant.entry.test'].sudo().create({
            #                 'student_id': rec.student_id.id,
            #                 'entry_test_schedule_details_id': test_schedule_details_open.id,
            #             })
            #             test_schedule_details_open.count += 1
            #             if applicant:
            #                 template = self.env.ref(
            #                     'odoocms_admission.mail_template_interview_email')
            #                 template.with_context().send_mail(applicant.id, force_send=True)
            #             if test_schedule_details_open.capacity == test_schedule_details_open.count:
            #                 test_schedule_details_open.status = 'full'
            #     elif test_schedule_details_init:
            #         test_schedule_details_inits = test_schedule_details_init
            #         test_schedule_details_open = test_schedule_details_init[0]
            #         # test_schedule_details_open.status = 'open'
            #         applicant = self.env['applicant.entry.test'].sudo().search(
            #             [('student_id', '=', rec.student_id.id),
            #              ('entry_test_schedule_details_id', '=', test_schedule_details_open.id), (
            #                  'slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
            #              ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
            #         if applicant:
            #             applicant = self.env['applicant.entry.test'].sudo().create({
            #                 'student_id': rec.student_id.id,
            #                 'entry_test_schedule_details_id': test_schedule_details_open.id,
            #                 # 'cbt_password': password,
            #             })
            #             test_schedule_details_open.status = 'open'
            #             test_schedule_details_open.count += 1

            #             # template = self.env.ref(
            #             #     'odoocms_admission.mail_template_voucher_verified')
            #             # post_message = rec.message_post_with_template(
            #             #     template.id, composition_mode='comment')  # , composition_mode='comment'
            #             if applicant:
            #                 template = self.env.ref(
            #                     'odoocms_admission.mail_template_interview_email')
            #                 template.with_context().send_mail(applicant.id, force_send=True)
            #             # test_schedule._get_applicant_record()
            #             if test_schedule_details_open.capacity == test_schedule_details_open.count:
            #                 test_schedule_details_open.status = 'full'

            # # Third Case
            # if preference_program.interview == True and preference_program.entry_test == True:
            #     test_schedule_details_open = test_schedule_details.filtered(
            #         lambda x: x.entry_schedule_id.slot_type in ('interview', 'test') and x.status == 'open')

            #     test_schedule_details_init = test_schedule_details.filtered(
            #         lambda x: x.status == 'initialize' and x.entry_schedule_id.slot_type in ('interview', 'test')).sorted(
            #         key=lambda s: s.entry_schedule_id.date, reverse=False)

            #     if not test_schedule_details_open and not test_schedule_details_init:
            #         raise UserError(
            #             f'No Interview/Test Schedule Available For This Program {preference_program.name}')
            #     if test_schedule_details_open:
            #         test_schedule_details_test_open = test_schedule_details_open.filtered(
            #             lambda x: x.entry_schedule_id.slot_type == 'test')
            #         test_schedule_details_interview_open = test_schedule_details_open.filtered(
            #             lambda x: x.entry_schedule_id.slot_type == 'interview')
            #         if test_schedule_details_test_open:
            #             test_schedule_details_test_opens = test_schedule_details_test_open
            #             test_schedule_details_test_open = test_schedule_details_test_open[0]

            #             for slot in test_schedule_details_test_open:

            #                 applicant = self.env['applicant.entry.test'].sudo().search([('student_id', '=', rec.student_id.id),
            #                                                                             ('entry_test_schedule_details_id', '=', slot.id),
            #                                                                             ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
            #                 if applicant:
            #                     applicant = self.env['applicant.entry.test'].sudo().create({
            #                         'student_id': rec.student_id.id,
            #                         'entry_test_schedule_details_id': slot.id,
            #                         # 'cbt_password': password,
            #                     })
            #                     slot.count += 1
            #                     # slot.status = 'open'

            #                     # template = self.env.ref(
            #                     #     'odoocms_admission.mail_template_voucher_verified')
            #                     # post_message = rec.message_post_with_template(
            #                     #     template.id, composition_mode='comment')  # , composition_mode='comment'
            #                     if applicant:
            #                         template = self.env.ref(
            #                             'odoocms_admission_ucp.mail_template_test_email')
            #                         template.with_context().send_mail(applicant.id, force_send=True)
            #                     if slot.capacity == slot.count:
            #                         slot.status = 'full'

            #             if test_schedule_details_interview_open:
            #                 test_schedule_details_interview_opens = test_schedule_details_interview_open
            #                 test_schedule_details_interview_open = test_schedule_details_interview_open[
            #                     0]
            #                 for slot in test_schedule_details_interview_open:

            #                     applicant = self.env['applicant.entry.test'].sudo().search(
            #                         [('student_id', '=', rec.student_id.id),
            #                          ('entry_test_schedule_details_id', '=', slot.id),
            #                          ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
            #                     if applicant:
            #                         applicant = self.env['applicant.entry.test'].sudo().create({
            #                             'student_id': rec.student_id.id,
            #                             'entry_test_schedule_details_id': slot.id,
            #                             # 'cbt_password': password,
            #                         })
            #                         slot.count += 1

            #                         # template = self.env.ref(
            #                         #     'odoocms_admission.mail_template_voucher_verified')
            #                         # post_message = rec.message_post_with_template(
            #                         #     template.id, composition_mode='comment')  # , composition_mode='comment'
            #                         if applicant:
            #                             template = self.env.ref(
            #                                 'odoocms_admission.mail_template_interview_email')
            #                             template.with_context().send_mail(applicant.id, force_send=True)
            #                         if slot.capacity == slot.count:
            #                             slot.status = 'full'
            #     elif test_schedule_details_init:
            #         test_schedule_details_test_init = test_schedule_details_init.filtered(
            #             lambda x: x.entry_schedule_id.slot_type == 'test')
            #         test_schedule_details_interview_init = test_schedule_details_init.filtered(
            #             lambda x: x.entry_schedule_id.slot_type == 'interview')
            #         if test_schedule_details_test_init:
            #             test_schedule_details_test_inits = test_schedule_details_test_init
            #             test_schedule_details_test_init = test_schedule_details_test_init[0]
            #             # test_schedule_details_test_init.status = 'open'
            #             for slot in test_schedule_details_test_init:

            #                 applicant = self.env['applicant.entry.test'].sudo().search(
            #                     [('student_id', '=', rec.student_id.id),
            #                      ('entry_test_schedule_details_id', '=', slot.id),
            #                      ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
            #                 if applicant:
            #                     applicant = self.env['applicant.entry.test'].sudo().create({
            #                         'student_id': rec.student_id.id,
            #                         'entry_test_schedule_details_id': slot.id,
            #                         # 'cbt_password': password,
            #                     })
            #                     slot.status = 'open'
            #                     slot.count += 1

            #                 # template = self.env.ref(
            #                 #     'odoocms_admission.mail_template_voucher_verified')
            #                 # post_message = rec.message_post_with_template(
            #                 #     template.id, composition_mode='comment')  # , composition_mode='comment'
            #                 if applicant:
            #                     template = self.env.ref(
            #                         'odoocms_admission_ucp.mail_template_test_email')
            #                     template.with_context().send_mail(applicant.id, force_send=True)
            #                 if slot.capacity == slot.count:
            #                     slot.status = 'full'
            #         if test_schedule_details_interview_init:
            #             test_schedule_details_interview_inits = test_schedule_details_interview_init
            #             test_schedule_details_interview_init = test_schedule_details_interview_init[
            #                 0]
            #             # test_schedule_details_interview_init.status = 'open'
            #             for slot in test_schedule_details_interview_init:

            #                 applicant = self.env['applicant.entry.test'].sudo().search(
            #                     [('student_id', '=', rec.student_id.id),
            #                      ('entry_test_schedule_details_id', '=', slot.id),
            #                      ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True), ('paper_status', 'in', ('missed', 'failed'))])
            #                 if applicant:
            #                     applicant = self.env['applicant.entry.test'].sudo().create({
            #                         'student_id': rec.student_id.id,
            #                         'entry_test_schedule_details_id': slot.id,
            #                         # 'cbt_password': password,
            #                     })
            #                     slot.status = 'open'
            #                     slot.count += 1

            #                 # template = self.env.ref(
            #                 #     'odoocms_admission.mail_template_voucher_verified')
            #                 # post_message = rec.message_post_with_template(
            #                 #     template.id, composition_mode='comment')  # , composition_mode='comment'
            #                 if applicant:
            #                     template = self.env.ref(
            #                         'odoocms_admission.mail_template_interview_email')
            #                     template.with_context().send_mail(applicant.id, force_send=True)
            #                 if slot.capacity == slot.count:
            #                     slot.status = 'full'

    @api.depends('paper_conducted', 'passing_threshold', 'cbt_marks','applicant_line_ids')
    def _get_test_status(self):
        for rec in self:
            cbt_percentage = ((rec.cbt_marks/rec.entry_test_marks)*100) if rec.entry_test_marks >0 else 0
            if not rec.paper_conducted and (rec.date and rec.date < date.today()) and rec.state:
                rec.paper_status = 'missed'
            elif rec.paper_conducted and rec.passing_threshold <= cbt_percentage:
                rec.paper_status = 'pass'
            elif rec.paper_conducted and rec.passing_threshold > cbt_percentage:
                rec.paper_status = 'failed'
            else:
                rec.paper_status = False

    @api.depends('entry_test_schedule_details_id', 'paper_conducted')
    def _get_no_of_attempts(self):
        for rec in self:
            all_recs = self.env['applicant.entry.test'].search([('student_id', '=', rec.student_id.id),
                                                                ('entry_test_schedule_details_id','=',rec.entry_test_schedule_details_id.id),
                                                                ('paper_conducted',
                                                                 '!=', False),
                                                                ('paper_status', 'in', ('missed', 'pass', 'failed'))])
            if all_recs:
                rec.attempts = len(all_recs)
            else:
                rec.attempts = 0

    slot_type = fields.Selection(
        string='Slot Type',
        selection=[('interview', 'interview'),
                   ('test', 'Test'), ],
        required=False, related='entry_test_schedule_details_id.entry_schedule_id.slot_type', store=True)

    @api.depends('applicant_line_ids', 'applicant_line_ids.total_marks', 'applicant_line_ids.obtained_marks')
    def _entry_test_marks(self):
        for rec in self:
            unique_section = []
            tests = rec.applicant_line_ids.sorted(
                lambda x: x.obtained_marks, reverse=True)
            for rec2 in tests:
                if rec2.name not in unique_section:
                    unique_section.append(rec2.name)
                else:
                    tests -= rec2
            test_total_marks = sum(tests.mapped('total_marks'))
            test_obtained_marks = sum(tests.mapped('obtained_marks'))
            rec.entry_test_marks = test_total_marks or 0
            rec.cbt_marks = test_obtained_marks or 0

    def section_wise_marks(self):

        merit_application = self.env['odoocms.merit.register.line'].search(
            [('applicant_id', '=', self.student_id.id)])

        if merit_application:
            for rec in self.applicant_line_ids:
                merit_application.write({
                    'cbt_section_ids': [(0, 0, {'name': rec.name, 'marks': rec.obtained_marks})]
                })

    def unlink(self):
        for rec in self:
            rec.entry_test_schedule_details_id.count = rec.entry_test_schedule_details_id.count - 1
            if rec.entry_test_schedule_details_id.status == 'full':
                rec.entry_test_schedule_details_id.status = 'initialize'

        return super(ApplicantEntryTest, self).unlink()


class ApplicantEntryTestLine(models.Model):
    _name = 'applicant.entry.test.line'
    _description = 'Applicant Entry Test Line'

    name = fields.Char(string='Name')
    obtained_marks = fields.Integer(string='Obtained Marks')
    total_marks = fields.Integer(string='Total Marks')
    applicant_id = fields.Many2one('applicant.entry.test')
