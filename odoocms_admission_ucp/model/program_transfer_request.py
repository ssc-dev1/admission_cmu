import pdb
from odoo.exceptions import UserError
from odoo import fields, models, _, api
from datetime import date


class ProgramTransferRequest(models.Model):
    _name = 'odoocms.program.transfer.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Program Transfer Request'
    _rec_name = 'applicant_id'

    applicant_id = fields.Many2one(
        'odoocms.application', string='Application', required=True)
    term=fields.Many2one('odoocms.academic.term', string='Term', related='applicant_id.term_id', readonly=True)
    transfer_date = fields.Date('Transfer Date', readonly=True)
    current_program = fields.Many2one(
        'odoocms.program', string='Requested Program')
    previous_program = fields.Many2one(
        'odoocms.program', string='Prev Program')
    program_previous= fields.Many2one(
        'odoocms.program', string='Previous Program',compute='_compute_program_previous', store=True)    
    # prog_req = fields.Boolean(string='Program', default=False)
    pre_test_marks = fields.Integer(string='Pre Test Marks')
    pretest_id = fields.Many2one('odoocms.pre.test', string='pretest')
    ssc_approval = fields.Boolean('Ssc Approval')
    pretest_card = fields.Binary('Pretest Card')
    entry_test_id = fields.Many2one(
        'applicant.entry.test', string='Entry Test', compute='_applicant_entry_test')
    merit_id = fields.Many2one(
        'odoocms.merit.register.line', string='Merit', compute='_applicant_merit')
    # re_test = fields.Boolean('Re Test', default=False)
    # re_test = fields.Selection('Re Test',[("no","Eligibile(No Test)"),("yes","Not Eligibile(Re Test)")])
    re_test = fields.Selection([
        ('no', 'No Test(Eligibile For Merit)'),
        ('yes', 'Re Test(Not Eligibile For Merit)')
    ], string='Re Test')

    # invoice_partner_id = fields.Many2one('res.partner', related='invoice_id.partner_id', string='Nama')
    state = fields.Selection(
        string='State',
        selection=[('draft', 'Draft'),
                   ('process', 'Processing'), ('approve', 'Approve'), ('reject', 'Reject'), ],
        required=False, default='draft')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
    shift = fields.Selection([
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('weekend', 'Weekend'),
    ], string='Shift', help='Choose shift if program provides shifts')

    # related helper to check program flag in view
    program_enable_shifts = fields.Boolean(
        string='Program Enable Shifts',
        related='current_program.enable_shifts',
        readonly=True,
        store=False
    )

    # @api.onchange('current_program')
    # def _onchange_current_program_clear_shift(self):
    #     """If program changed and it does not allow shifts, clear the selected shift."""
    #     for rec in self:
    #         if rec.current_program and not rec.current_program.enable_shifts:
    #             rec.shift = False

    def _get_program_allowed_shifts(self, program):
        """
        Return allowed shift keys for given program record.
        Expected result: ['morning', 'evening'] etc.
        """
        if not program:
            return []
        # use program.get_enabled_shifts() if implemented (returns list of tuples)
        if hasattr(program, 'get_enabled_shifts'):
            return [v for v, l in program.get_enabled_shifts()]
        # fallback: check fields directly
        allowed = []
        if getattr(program, 'morning', False):
            allowed.append('morning')
        if getattr(program, 'evening', False):
            allowed.append('evening')
        if getattr(program, 'weekend', False):
            allowed.append('weekend')
        return allowed

    @api.onchange('applicant_id')
    def _onchange_applicant_id(self):
        if self.applicant_id:
            pr_pr=self.applicant_id.prefered_program_id
            if pr_pr:
                self.program_previous = pr_pr

    @api.onchange('current_program','shift')
    def _onchange_shift_dynamic(self):
        for rec in self:
            if rec.current_program and not rec.current_program.enable_shifts:
                rec.shift = False

        allowed = self._get_program_allowed_shifts(self.current_program)
        if self.shift and self.shift not in allowed:
            self.shift = False
            return {
                'warning': {
                    'title': "Shift not allowed",
                    'message': "Selected shift is not allowed for this program."
                }
            }


    # @api.depends('applicant_id')
    # def _compute_program_previous(self):
    #     for record in self:
    #         if record.applicant_id:
    #             record.program_previous = record.applicant_id.prefered_program_id

    def approve(self):
        # self.prog_req = True

        for rec in self:
            application_preference = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)], limit=1).preference_ids

            previous_preference = application_preference.filtered(
                lambda x: x.program_id == rec.applicant_id.prefered_program_id)
            new_preference = application_preference.filtered(
                lambda x: x.program_id == rec.current_program)

            if not new_preference:
                new_preference=new_preference.sudo().create({
                    'application_id': rec.applicant_id.id,
                    'preference': 4,
                    'program_id': rec.current_program.id,
                })
                # raise UserError('Requested Program Must be In Preference')

            check_merit = self.env['odoocms.merit.register.line'].search(
                [('applicant_id', '=', rec.applicant_id.id)], limit=1, order='id desc').filtered(lambda x: x.selected)
            admission_inv_id = rec.applicant_id.admission_inv_id
            if rec.current_program and rec.current_program.enable_shifts:
                allowed = rec._get_program_allowed_shifts(rec.current_program)  # uses helper above
                if not rec.shift:
                    raise UserError(_("This program requires selecting a shift. Please choose a shift."))
                if rec.shift not in allowed:
                    raise UserError(_("Selected shift '%s' is not available for the requested program.") % rec.shift)
                else:
                    rec.applicant_id.shift=rec.shift

            else:
                # if program doesn't allow shifts, ensure shift is empty
                if rec.shift:
                    # clear it or raise: better to clear automatically
                    rec.shift = False
            if not check_merit and (not admission_inv_id or (admission_inv_id and (admission_inv_id.payment_state == 'not_paid' or admission_inv_id.state == 'cancel'))):

                new_preference.preference = 1
                conflict = rec.applicant_id.preference_ids.filtered(lambda x: x.preference == 1 and x.id != new_preference.id)
                conflict.preference = 3
                rec.applicant_id.prefered_program_id = False
                # for course in rec.applicant_id.first_semester_courses:
                #     course.sudo().unlink()

                if rec.re_test == 'yes':
                    entry_test = self.env['applicant.entry.test'].sudo().search([('student_id', '=', rec.applicant_id.id), ('active', '=', True), ('register_id', '=', rec.applicant_id.register_id.id)])
                    entry_test.active = False
                    rec.applicant_id.assign_test_date()
                scholarship = rec.applicant_id.scholarship_ids
                if scholarship:
                    # scholarship.unlink()
                    rec.applicant_id.scholarship_ids = [(3,s.id) for s in scholarship]

                rec.applicant_id._prefered_program()
                rec.state = 'approve'

            if check_merit and (not admission_inv_id or (admission_inv_id.payment_state == 'not_paid' or admission_inv_id.state == 'cancel')):
                # change preference
                new_preference.preference = 1
                conflict = rec.applicant_id.preference_ids.filtered(lambda x:x.preference == 1 and x.id != new_preference.id)
                conflict.preference = 3

                rec.applicant_id.prefered_program_id = False
                # rec.applicant_id.first_semester_courses = [()]
                for course in rec.applicant_id.first_semester_courses:
                    course.sudo().unlink()

                # application_preference.filtered(lambda x: x.program_id.id == rec.previous_program.id)[-1].preference = current_pref.preference
                # current_pref.preference = 1
                # if pre test given upate with new one
                if rec.pre_test_marks and isinstance(rec.pre_test_marks, int) and rec.pre_test_marks > 0:
                    rec.applicant_id.pre_test_marks = rec.pre_test_marks
                    rec.applicant_id.pre_test_attachment = rec.pretest_card
                    rec.applicant_id.pre_test_id = rec.pretest_id

                # Re take test

                if rec.re_test == 'yes':
                    entry_test = self.env['applicant.entry.test'].sudo().search(
                        [('student_id', '=', rec.applicant_id.id), ('active', '=', True),
                         ('register_id', '=', rec.applicant_id.register_id.id)])
                    entry_test.active = False
                    rec.applicant_id.assign_test_date()
                offer_letter = self.env['ucp.offer.letter'].sudo().search([('applicant_id', '=', rec.applicant_id.id)])
                if offer_letter:
                    offer_letter.sudo().unlink()
                if check_merit:
                    check_merit.sudo().unlink()

                # remove scholarship
                scholarship = rec.applicant_id.scholarship_ids
                if scholarship:
                    # scholarship.unlink()
                    rec.applicant_id.scholarship_ids = [(3,s.id) for s in scholarship]


                # cancel admission invoice
                if admission_inv_id:
                    admission_inv_id.button_cancel()
                    admission_inv_id.sudo().unlink()

                domain = [('student_id', '=',  rec.applicant_id.student_id.id),('label_id.type','in',('admission','installment'))]
                fee_challan = self.env['odoocms.fee.barcode'].sudo().search(domain, limit=1,order='id desc')
                if fee_challan:
                    for chalan in fee_challan:
                        chalan.unlink()
                

                # added in merit register if eligible not user requirements so its commented it will add to merit register automate
                '''if rec.re_test == 'no':
                    first_preference_program = rec.applicant_id.preference_ids.filtered(
                        lambda x: x.preference == 1).program_id[0]
                    merit_register_program = self.env['odoocms.merit.program'].search(
                        [('program_id', '=', current_pref.program_id.id)])
                    merit_register = merit_register_program.merit_register_id.filtered(
                        lambda x: x.state == 'open').filtered(lambda x: x.register_id.id == rec.applicant_id.register_id.id)
                    if not merit_register_program or not merit_register:
                        raise UserError(
                            f'Currently No Merit register Open For This Program {current_pref.program_id.name}')
                    merit_register.calculate_merit()'''
                rec.applicant_id._prefered_program()
                rec.applicant_id._compute_first_semester_courses()
                student = self.env['odoocms.student'].search([('id', '=', rec.applicant_id.student_id.id)], limit=1)
                if student:
                   student.sudo().unlink()
                if rec.applicant_id.prefered_program_id and rec.applicant_id.register_id.academic_session_id and rec.applicant_id.register_id.career_id:
                    batch_domain = [('program_id', '=', rec.applicant_id.prefered_program_id.id), ('session_id', '=', rec.applicant_id.register_id.academic_session_id.id),('career_id', '=', rec.applicant_id.register_id.career_id.id)]
                program_batch = self.env['odoocms.batch'].search(batch_domain)
                if program_batch:
                    study_scheme_id = program_batch.study_scheme_id
                if not study_scheme_id:
                    study_scheme_id =self.env['odoocms.study.scheme'].search([('session_id','=',rec.applicant_id.register_id.academic_session_id.id),('program_id','=',rec.applicant_id.prefered_program_id.id)])
                student_data = {
                     'program_id':rec.applicant_id.prefered_program_id.id or False,
                     'term_id':  rec.applicant_id.register_id.term_id.id or False,
                     'batch_id': program_batch and program_batch.id or False,
                     'study_scheme_id': program_batch and program_batch.study_scheme_id.id or False,
                 }
                student = rec.applicant_id.sudo().create_student(view=False, student_data=student_data)
                rec.state = 'approve'


            # if admission_inv_id.payment_state in ['in_payment', 'paid', 'partial']:
            #
            #     pass
                # check_merit.unlink()

    def reject(self):
        for rec in self:
            rec.state = 'reject'

    def _applicant_entry_test(self):
        for rec in self:
            entry_test = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id)], limit=1, order='id desc')
            rec.entry_test_id = entry_test.id

    @api.model
    def create(self, values):
        result = super().create(values)
        result.program_previous= result.applicant_id.prefered_program_id
        entry_test = self.env['applicant.entry.test'].search(
            [('student_id', '=', int(values.get('applicant_id')))])
        if entry_test and entry_test.paper_conducted is not False:
            cbt_conducted = self.env['cbt.test.program'].search(
                [('name', '=', entry_test.paper_conducted)])
            if cbt_conducted:
                program_eligible = cbt_conducted.test_program_ids.ids
                if int(values.get('current_program')) in program_eligible:
                    result.re_test = 'no'
                    return result
                result.re_test = 'yes'
        return result
