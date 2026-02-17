import pdb

from odoo import fields, models, _, api
from datetime import date
import random
import string
from odoo.exceptions import UserError, ValidationError, Warning


class ApplicantInterview(models.Model):
    _name = 'applicant.interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Applicant Interview'
    _rec_name = 'student_id'

    entry_test_schedule_details_id = fields.Many2one(
        'odoocms.entry.schedule.details', string='Schedule')
    program_id = fields.Many2one(
        'odoocms.program', string='Program', related='entry_test_schedule_details_id.program_id', store=True)

    applicant_id = fields.Many2one('odoocms.application', string='Application')
    email = fields.Char('Applicant Email',related='applicant_id.email')
    mobile = fields.Char('Applicant Mobile',related='applicant_id.mobile')
    register_id = fields.Many2one(
        'odoocms.admission.register', string='Register', related='applicant_id.register_id', store=True)
    applicant = fields.Char(related='applicant_id.name', string='Applicant')
    reference_no = fields.Char(
        related='applicant_id.application_no', string='Reference no')
    room = fields.Many2one(string='Room',
                           related='entry_test_schedule_details_id.entry_schedule_id.entry_test_room_id', store=True)
    slots = fields.Many2one(string='Slots',
                            related='entry_test_schedule_details_id.entry_schedule_id.entry_test_slots_id', store=True)
    date = fields.Date(string='Date',
                       related='entry_test_schedule_details_id.entry_schedule_id.date', store=True)
    entry_test_marks = fields.Float(
        ' Test Total Marks', compute='_entry_test_marks', store=True)
    cbt_marks = fields.Float('UCP Test Obtained Marks')
    cbt_id = fields.Integer(string='CBT ID')
    master_id = fields.Integer(string='Master ID')
    active = fields.Boolean('active', default=True)
    cbt_password = fields.Char(string='CBT Password')
    state = fields.Boolean(string='Active', default=True)
    applicant_line_ids = fields.One2many(
        'applicant.entry.test.line', 'applicant_id')
    description = fields.Html(string='Description')
    passing_threshold = fields.Integer(string='Passing %age', default=50)
    # cbt_test_id = fields.Many2one('cbt.test.program', string='Cbt Test')
    paper_conducted = fields.Char('UCP Test Conducted')
    paper_status = fields.Selection(
        string='UCP Test Status', compute='_get_test_status',
        selection=[
            ('missed', 'Interview Missed'),
                   ('pass', 'Pass'),
                   ('failed', 'Failed') ])
    # attempts = fields.Integer("No. of attempts", compute='_get_no_of_attempts')

    # def generate_retest(self):
    #
    #     length = 8
    #     all = string.ascii_letters + string.digits + '$#'
    #     password = "".join(random.sample(all, length))
    #
    #
    #     for app in self:
    #
    #         rec = app.student_id
    #         preference_program = rec.preference_ids.filtered(
    #             lambda x: x.preference == 1).program_id
    #         test_schedule_details = self.env['odoocms.entry.schedule.details'].search(
    #             [('status', 'in', ('open','initialize')), ('program_id', '=', preference_program.id)])
    #         if not test_schedule_details:
    #             raise UserError(_("Test Schedule is not available"))
    #         test_schedule_details_open = test_schedule_details.filtered(lambda x: x.status == 'open')
    #         test_schedule_details_init = test_schedule_details.filtered(lambda x: x.status == 'initialize').sorted(key=lambda s: s.entry_schedule_id.date, reverse=False)
    #         if test_schedule_details_open:
    #             test_schedule_details_open = test_schedule_details_open[0]
    #             test_schedule_register = self.env['odoocms.entry.test.schedule'].search(
    #                 [('register_id', '=', rec.register_id.id), ('entry_test_schedule_ids', 'in', test_schedule_details_open.ids)], limit=1)
    #             test_schedule = test_schedule_register.entry_test_schedule_ids.filtered(
    #                 lambda x: x.program_id.id == preference_program.id)
    #
    #             # if not test_schedule_register and not test_schedule:
    #             #     raise UserError(f'No Schedule Open For This Program {preference_program.name}')
    #
    #             if preference_program.offering == True and preference_program.entry_test == True and test_schedule_register.slot_type != 'interview':
    #                 # if rec.fee_voucher_state == 'verify':
    #                 #     previous_card = self.env['applicant.entry.test'].sudo().search([
    #                 #         ('student_id','=', rec.id),('paper_conducted','!=',False),('paper_status','=','failed'),
    #                 #         ('entry_test_schedule_details_id','=',test_schedule_details_open.id)
    #                 #     ])
    #                 #     if previous_card:
    #                         applicant = self.env['applicant.entry.test'].sudo().create({
    #                             'student_id': rec._origin.id,
    #                             'entry_test_schedule_details_id': test_schedule_details_open.id,
    #                             'cbt_password': password,
    #                         })
    #
    #                         template = self.env.ref(
    #                             'odoocms_admission.mail_template_voucher_verified')
    #                         post_message = rec.message_post_with_template(
    #                             template.id, composition_mode='comment')  # , composition_mode='comment'
    #                         if applicant:
    #                             template = self.env.ref(
    #                                 'odoocms_admission_ucp.mail_template_test_email')
    #                             template.with_context().send_mail(applicant.id, force_send=True)
    #                         if test_schedule.capacity == test_schedule.count:
    #                             test_schedule.status = 'full'
    #
    #         if not test_schedule_details_open and test_schedule_details_init:
    #             test_schedule_details_init = test_schedule_details_init[0]
    #             test_schedule_details_init.status = 'open'
    #             test_schedule_details_open = test_schedule_details_init
    #             test_schedule_register = self.env['odoocms.entry.test.schedule'].search(
    #                 [('register_id', '=', rec.register_id.id), ('entry_test_schedule_ids', 'in', test_schedule_details_open.ids)], limit=1)
    #             test_schedule = test_schedule_register.entry_test_schedule_ids.filtered(
    #                 lambda x: x.program_id.id == preference_program.id)
    #
    #             # if not test_schedule_register and not test_schedule:
    #             #     raise UserError(f'No Schedule Open For This Program {preference_program.name}')
    #
    #             if preference_program.offering == True and preference_program.entry_test == True and test_schedule_register.slot_type != 'interview':
    #                 # if rec.fee_voucher_state == 'verify':
    #                 #     previous_card = self.env['applicant.entry.test'].sudo().search([('student_id', '=', rec.id), ('paper_conducted', '!=', False),('paper_status', '=', 'failed'),
    #                 #         ('entry_test_schedule_details_id', '=', test_schedule_details_open.id)
    #                 #     ])
    #                 #     if previous_card:
    #                         applicant = self.env['applicant.entry.test'].sudo().create({
    #                             'student_id': rec._origin.id,
    #                             'entry_test_schedule_details_id': test_schedule_details_open.id,
    #                             'cbt_password': password,
    #                         })
    #
    #                         template = self.env.ref(
    #                             'odoocms_admission.mail_template_voucher_verified')
    #                         post_message = rec.message_post_with_template(
    #                             template.id, composition_mode='comment')  # , composition_mode='comment'
    #                         if applicant:
    #                             template = self.env.ref(
    #                                 'odoocms_admission_ucp.mail_template_test_email')
    #                             template.with_context().send_mail(applicant.id, force_send=True)
    #                         if test_schedule.capacity == test_schedule.count:
    #                             test_schedule.status = 'full'

    def _get_interview_status(self):
        for rec in self:
            if not rec.paper_conducted and rec.date < date.today() and rec.state == True:
                rec.paper_status = 'missed'
            elif rec.paper_conducted and rec.passing_threshold <= rec.cbt_marks:
                rec.paper_status = 'pass'
            elif rec.paper_conducted and rec.passing_threshold > rec.cbt_marks:
                rec.paper_status = 'failed'
            else:
                rec.paper_status = False

    @api.depends('entry_test_schedule_details_id','interview_conducted')
    def _get_no_of_attempts(self):
        for rec in self:
            all_recs = self.env['applicant.entry.test'].search([('student_id','=', rec.student_id.id),
                                                                # ('entry_test_schedule_details_id','=',rec.entry_test_schedule_details_id.id),
                                                                ('interview_conducted','!=',False),
                                                                ('paper_status','in',('missed','pass','failed'))])
            if all_recs:
                rec.attempts = len(all_recs)
            else:
                rec.attempts = 0

    slot_type = fields.Selection(
        string='Slot Type',
        selection=[('interview', 'interview'),
                   ('test', 'Test'), ],
        required=False, related='entry_test_schedule_details_id.entry_schedule_id.slot_type', store=True)

    @api.depends('applicant_line_ids')
    def _entry_test_marks(self):
        test_marks = 0
        test_total_marks = 0
        for rec in self:
            for entry in rec.applicant_line_ids:
                test_marks = test_marks + entry.obtained_marks
                test_total_marks = test_total_marks + entry.total_marks
            rec.entry_test_marks = test_total_marks
            rec.cbt_marks = test_marks

    def section_wise_marks(self):

        merit_application = self.env['odoocms.merit.register.line'].search(
            [('applicant_id', '=', self.student_id.id)])

        if merit_application:
            for rec in self.applicant_line_ids:
                merit_application.write({
                    'cbt_section_ids': [(0, 0, {'name': rec.name, 'marks': rec.obtained_marks})]
                })


class ApplicantEntryTestLine(models.Model):
    _name = 'applicant.entry.test.line'
    _description = 'Applicant Entry Test Line'

    name = fields.Char(string='Name')
    obtained_marks = fields.Integer(string='Obtained Marks')
    total_marks = fields.Integer(string='Total Marks')
    applicant_id = fields.Many2one('applicant.entry.test')
