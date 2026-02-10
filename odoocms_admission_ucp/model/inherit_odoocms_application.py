import pdb
from datetime import date
import random
import string
from odoo.exceptions import UserError
from odoo import fields, models, _, api


class InheritDocument(models.Model):
    _inherit = 'applicant.academic.detail'

    pgc = fields.Boolean('Is PGC',related='application_id.pgc',store=True)
    pgc_institute_id = fields.Many2one('pgc.institute',related='application_id.pgc_institute_id', string='PGC Institute',store=True,)
    

class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    # Need Base Scholarship
    guardian_occupation = fields.Char(string='Father/Guardian Occupation')
    guardian_job_status = fields.Selection(
        string='Guardian Job Status',
        selection=[('serving', 'Serving'),
                   ('retired', 'Retired'), ],
        required=False, default='serving')
    guardian_monthly_income = fields.Char(
        string='Father/Guardians Monthly Income')
    residential_status = fields.Selection(
        string='Residential Status',
        selection=[('r', 'Resident'),
                   ('nr', 'Non Resident'), ],
        required=False, default='r')
    family_member = fields.Char(string='Family Member')
    previous_school_attend = fields.Char(string='Previous Institute Attend')


    pgc = fields.Boolean('PGC',compute='_is_pgc',store=True)
    pgc_registration_no = fields.Char(string='Previous Registration No')
    pgc_institute_id = fields.Many2one('pgc.institute', string='PGC Institute')
    last_school_attend = fields.Many2one(
        'last.institute.attend', string='Last Institute Attend')
    advertisement = fields.Many2one(
        'odoocms.advertisement', string='How do You Know about US')

    invoice_visibility = fields.Boolean('Invoice Visibility')
    password = fields.Char('Password')
    voucher_verify_flag = fields.Boolean('Verify Flag')
    merit_rejected = fields.Boolean('Merit Rejected')

    # Indicates whether the applicant opted to apply for Need-Based Scholarship
    need_based_scholarship_applied = fields.Boolean(
        string='Applied for Need Based Scholarship',
        default=False,
        help='Set when applicant chooses to apply for need-based scholarship',
    )

    @api.depends('fee_voucher_state')
    @api.onchange('fee_voucher_state')
    def assign_test_date(self):
        # length = 8
        # all = string.ascii_letters + string.digits + '$#'
        digits = string.digits
        password_length = 5
        password = "".join(random.sample(digits, password_length))
        
        for rec in self:
            if rec.fee_voucher_state == 'verify' and rec.state == 'submit':
                rec.voucher_verified_date = fields.Date.today()
                preference_program = rec.preference_ids.filtered(lambda x: x.preference == 1).program_id

                test_schedule_details = self.env['odoocms.entry.schedule.details'].search(
                    [('status', '=', 'open'), ('program_id', '=', preference_program.id)]).filtered(
                    lambda x: x.entry_schedule_id.register_id.id == rec.register_id.id and x.entry_schedule_id.date >= date.today() and x.entry_schedule_id.register_id.company_id == rec.company_id)
                # test_schedule_details_open = test_schedule_details.filtered(lambda x: x.status == 'open')
                #
                # test_schedule_details_init = test_schedule_details.filtered(lambda x: x.status == 'initialize').sorted(
                #     key=lambda s: s.entry_schedule_id.date, reverse=False)
                #First Case
                if preference_program.entry_test == True and preference_program.interview == False:
                    test_schedule_details_open = test_schedule_details.filtered(lambda x: x.entry_schedule_id.slot_type == 'test' and x.status == 'open')
                    test_schedule_details_init = test_schedule_details.filtered(
                        lambda x: x.status == 'initialize' and x.entry_schedule_id.slot_type == 'test').sorted(
                        key=lambda s: s.entry_schedule_id.date, reverse=False)
                    if not test_schedule_details_open and not test_schedule_details_init:
                        msg_txt = f'Dear Concerned,\nEntry test capacity for program { preference_program.name} become full now.'
                        message = self.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.entry.test.schedule', self.id)
                        gateway_id = self.env['gateway_setup'].sudo().search([('company_id','=',rec.company_id.id)], order='id desc', limit=1)
                        if gateway_id:
                            mobile_nos =['3030000993','3214269125']
                            if rec.company_id.id ==2:
                                mobile_nos.append('3335696364')
                            elif rec.company_id.id ==4:
                                mobile_nos.extend(['3224271127','3334805835'])
                            elif rec.company_id.id ==5:
                                mobile_nos.extend(['3008244228','3462417114','3136726044'])
                            for mobile_no in mobile_nos:
                                try:
                                    self.env['send_sms'].sudo().send_sms_link(message,mobile_no, self.id,'odoocms.application', gateway_id, preference_program.name,'other','staff',False,False,False)
                                except Exception as e:
                                    break
                        raise UserError(f'No Test Schedule Available For This Program {preference_program.name}')


                    if test_schedule_details_open:
                        test_schedule_details_opens = test_schedule_details_open
                        test_schedule_details_open = test_schedule_details_open[0]
                        applicant = self.env['applicant.entry.test'].sudo().search(
                            [('student_id', '=', rec._origin.id),
                             ('entry_test_schedule_details_id', '=', test_schedule_details_open.id),
                             ('slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
                             ('active', '=', True)])
                        if not applicant:
                            applicant = self.env['applicant.entry.test'].sudo().create({
                                'student_id': rec._origin.id,
                                'entry_test_schedule_details_id': test_schedule_details_open.id,
                                'cbt_password': password,
                            })
                            test_schedule_details_open.count += 1
                            # if applicant:
                            #     mail_value = {
                            #         'applicant_name': rec.name,
                            #         'company_name': self.env.company.name,
                            #         'admission_mail': self.env.company.admission_mail,
                            #         'mail_to': rec.email,
                            #         'admission_phone': self.env.company.admission_phone,
                            #     }
                            #     # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                            #     mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                            #     template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'), ('mail_server_id', '=', mail_server_id.id)])
                            #     template.with_context(mail_value).send_mail(applicant.id, force_send=True)
                            if test_schedule_details_open.capacity == test_schedule_details_open.count:
                                test_schedule_details_open.status = 'full'
                    elif test_schedule_details_init:
                        test_schedule_details_inits = test_schedule_details_init
                        test_schedule_details_open = test_schedule_details_init[0]
                        test_schedule_details_open.status = 'open'

                        applicant = self.env['applicant.entry.test'].sudo().search(
                            [('student_id', '=', rec._origin.id),
                             ('entry_test_schedule_details_id', '=', test_schedule_details_open.id), ('slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
                             ('active', '=', True)])
                        if not applicant:
                            applicant = self.env['applicant.entry.test'].sudo().create({
                                'student_id': rec._origin.id,
                                'entry_test_schedule_details_id': test_schedule_details_open.id,
                                'cbt_password': password,
                            })
                            test_schedule_details_open.status = 'open'
                            test_schedule_details_open.count += 1
                            if applicant:
                                # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                                mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'), ('mail_server_id', '=', mail_server_id.id)])
                                template.with_context().send_mail(applicant.id, force_send=True)
                            if test_schedule_details_open.capacity == test_schedule_details_open.count:
                                test_schedule_details_open.status = 'full'

                #Second Case
                if preference_program.interview == True and preference_program.entry_test == False:
                    test_schedule_details_open = test_schedule_details.filtered(lambda x: x.entry_schedule_id.slot_type == 'interview' and x.status == 'open')
                    test_schedule_details_init = test_schedule_details.filtered(
                        lambda x: x.status == 'initialize' and x.entry_schedule_id.slot_type == 'interview').sorted(
                        key=lambda s: s.entry_schedule_id.date, reverse=False)
                    if not test_schedule_details_open and not test_schedule_details_init:
                        raise UserError(f'No Interview Schedule Available For This Program {preference_program.name}')
                    if test_schedule_details_open:
                        test_schedule_details_opens = test_schedule_details_open
                        test_schedule_details_open = test_schedule_details_open[0]
                        applicant = self.env['applicant.entry.test'].sudo().search([
                            ('student_id', '=', rec._origin.id),
                            ('entry_test_schedule_details_id', '=', test_schedule_details_open.id),
                            ('slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
                            ('active', '=', True)
                        ])
                        if not applicant:
                            applicant = self.env['applicant.entry.test'].sudo().create({
                                'student_id': rec._origin.id,
                                'entry_test_schedule_details_id': test_schedule_details_open.id,
                            })
                            test_schedule_details_open.count += 1
                            if applicant:
                                # template = self.env.ref('odoocms_admission.mail_template_interview_email')
                                mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Interview'), ('mail_server_id', '=', mail_server_id.id)])
                                template.with_context().send_mail(applicant.id, force_send=True)
                            if test_schedule_details_open.capacity == test_schedule_details_open.count:
                                test_schedule_details_open.status = 'full'
                    elif test_schedule_details_init:
                        test_schedule_details_inits = test_schedule_details_init
                        test_schedule_details_open = test_schedule_details_init[0]
                        # test_schedule_details_open.status = 'open'
                        applicant = self.env['applicant.entry.test'].sudo().search(
                            [('student_id', '=', rec._origin.id),
                             ('entry_test_schedule_details_id', '=', test_schedule_details_open.id), ('slot_type', '=', test_schedule_details_open.entry_schedule_id.slot_type),
                             ('active', '=', True)])
                        if not applicant:
                            applicant = self.env['applicant.entry.test'].sudo().create({
                                'student_id': rec._origin.id,
                                'entry_test_schedule_details_id': test_schedule_details_open.id,
                                # 'cbt_password': password,
                            })
                            test_schedule_details_open.status = 'open'
                            test_schedule_details_open.count += 1

                            # template = self.env.ref(
                            #     'odoocms_admission.mail_template_voucher_verified')
                            # post_message = rec.message_post_with_template(
                            #     template.id, composition_mode='comment')  # , composition_mode='comment'
                            if applicant:
                                # template = self.env.ref('odoocms_admission.mail_template_interview_email')
                                mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Interview'), ('mail_server_id', '=', mail_server_id.id)])
                                template.with_context().send_mail(applicant.id, force_send=True)
                            # test_schedule._get_applicant_record()
                            if test_schedule_details_open.capacity == test_schedule_details_open.count:
                                test_schedule_details_open.status = 'full'

                #Third Case
                if preference_program.interview == True and preference_program.entry_test == True:
                    test_schedule_details_open = test_schedule_details.filtered(lambda x: x.entry_schedule_id.slot_type in ('interview','test') and x.status == 'open')

                    test_schedule_details_init = test_schedule_details.filtered(
                        lambda x: x.status == 'initialize' and x.entry_schedule_id.slot_type in ('interview','test')).sorted(
                        key=lambda s: s.entry_schedule_id.date, reverse=False)

                    if not test_schedule_details_open and not test_schedule_details_init:
                        raise UserError(f'No Interview/Test Schedule Available For This Program {preference_program.name}')
                    if test_schedule_details_open:
                        test_schedule_details_test_open = test_schedule_details_open.filtered(lambda x: x.entry_schedule_id.slot_type == 'test')
                        test_schedule_details_interview_open = test_schedule_details_open.filtered(lambda x: x.entry_schedule_id.slot_type == 'interview')
                        if test_schedule_details_test_open:
                            test_schedule_details_test_opens = test_schedule_details_test_open
                            test_schedule_details_test_open = test_schedule_details_test_open[0]

                            for slot in test_schedule_details_test_open:
                                applicant = self.env['applicant.entry.test'].sudo().search(
                                    [('student_id', '=', rec._origin.id),
                                     ('entry_test_schedule_details_id', '=', slot.id),
                                     ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True)])
                                if not applicant:
                                    applicant = self.env['applicant.entry.test'].sudo().create({
                                        'student_id': rec._origin.id,
                                        'entry_test_schedule_details_id': slot.id,
                                        'cbt_password': password,
                                    })
                                    slot.count += 1
                                    # slot.status = 'open'

                                    # template = self.env.ref(
                                    #     'odoocms_admission.mail_template_voucher_verified')
                                    # post_message = rec.message_post_with_template(
                                    #     template.id, composition_mode='comment')  # , composition_mode='comment'
                                    if applicant:
                                        # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                                        mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                                        template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'), ('mail_server_id', '=', mail_server_id.id)])
                                        template.with_context().send_mail(applicant.id, force_send=True)
                                    if slot.capacity == slot.count:
                                        slot.status = 'full'

                            if test_schedule_details_interview_open:
                                test_schedule_details_interview_opens = test_schedule_details_interview_open
                                test_schedule_details_interview_open = test_schedule_details_interview_open[0]
                                for slot in test_schedule_details_interview_open:

                                    applicant = self.env['applicant.entry.test'].sudo().search(
                                            [('student_id', '=', rec._origin.id),
                                             ('entry_test_schedule_details_id', '=', slot.id),
                                             ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True)])
                                    if not applicant:
                                            applicant = self.env['applicant.entry.test'].sudo().create({
                                                'student_id': rec._origin.id,
                                                'entry_test_schedule_details_id': slot.id,
                                                # 'cbt_password': password,
                                            })
                                            slot.count += 1

                                            # template = self.env.ref(
                                            #     'odoocms_admission.mail_template_voucher_verified')
                                            # post_message = rec.message_post_with_template(
                                            #     template.id, composition_mode='comment')  # , composition_mode='comment'
                                            if applicant:
                                                template = self.env.ref(
                                                    'odoocms_admission.mail_template_interview_email')
                                                template.with_context().send_mail(applicant.id, force_send=True)
                                            if slot.capacity == slot.count:
                                                slot.status = 'full'
                    elif test_schedule_details_init:
                        test_schedule_details_test_init = test_schedule_details_init.filtered(lambda x: x.entry_schedule_id.slot_type == 'test')
                        test_schedule_details_interview_init = test_schedule_details_init.filtered(lambda x: x.entry_schedule_id.slot_type == 'interview')
                        if test_schedule_details_test_init:
                            test_schedule_details_test_inits = test_schedule_details_test_init
                            test_schedule_details_test_init = test_schedule_details_test_init[0]
                            # test_schedule_details_test_init.status = 'open'
                            for slot in test_schedule_details_test_init:
                                applicant = self.env['applicant.entry.test'].sudo().search(
                                    [('student_id', '=', rec._origin.id),
                                     ('entry_test_schedule_details_id', '=', slot.id),
                                     ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True)])
                                if not applicant:
                                    applicant = self.env['applicant.entry.test'].sudo().create({
                                        'student_id': rec._origin.id,
                                        'entry_test_schedule_details_id': slot.id,
                                        'cbt_password': password,
                                    })
                                    slot.status = 'open'
                                    slot.count += 1

                                # template = self.env.ref(
                                #     'odoocms_admission.mail_template_voucher_verified')
                                # post_message = rec.message_post_with_template(
                                #     template.id, composition_mode='comment')  # , composition_mode='comment'
                                if applicant:
                                    # template = self.env.ref('odoocms_admission_ucp.mail_template_test_email')
                                    mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                                    template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Entry Test'), ('mail_server_id', '=', mail_server_id.id)])
                                    template.with_context().send_mail(applicant.id, force_send=True)
                                if slot.capacity == slot.count:
                                    slot.status = 'full'
                        if test_schedule_details_interview_init:
                            test_schedule_details_interview_inits = test_schedule_details_interview_init
                            test_schedule_details_interview_init = test_schedule_details_interview_init[0]
                            # test_schedule_details_interview_init.status = 'open'
                            for slot in test_schedule_details_interview_init:
                                applicant = self.env['applicant.entry.test'].sudo().search(
                                    [('student_id', '=', rec._origin.id),
                                     ('entry_test_schedule_details_id', '=', slot.id),
                                     ('slot_type', '=', slot.entry_schedule_id.slot_type), ('active', '=', True)])
                                if not applicant:
                                    applicant = self.env['applicant.entry.test'].sudo().create({
                                        'student_id': rec._origin.id,
                                        'entry_test_schedule_details_id': slot.id,
                                        # 'cbt_password': password,
                                    })
                                    slot.status = 'open'
                                    slot.count += 1

                                # template = self.env.ref(
                                #     'odoocms_admission.mail_template_voucher_verified')
                                # post_message = rec.message_post_with_template(
                                #     template.id, composition_mode='comment')  # , composition_mode='comment'
                                if applicant:
                                    # template = self.env.ref('odoocms_admission.mail_template_interview_email')
                                    mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', applicant.company_id.id)])
                                    template = self.env['mail.template'].sudo().search([('name', '=', 'Call For Interview'), ('mail_server_id', '=', mail_server_id.id)])
                                    template.with_context().send_mail(applicant.id, force_send=True)
                                if slot.capacity == slot.count:
                                    slot.status = 'full'

    @api.depends('pgc_institute_id')
    def _is_pgc(self):
        for rec in self:
            rec.pgc = False
            if rec.pgc_institute_id:
                rec.pgc = True
            

        

class OdooCMSProgramInherit(models.Model):
    _inherit = 'odoocms.program'
    _description = 'Odoo CMS Program Inherit'

    offering = fields.Boolean(string='Offering', default=True)
    payment = fields.Selection(
        string='Payment',
        selection=[('online', 'Online'),
                   ('voucher', 'Through Voucher'), ],
        required=False, )
    entry_test = fields.Boolean(string='Entry Test')
    interview = fields.Boolean(string='Interview')
    offer_letter = fields.Boolean(string='Offer Letter')
    date = fields.Date(string='Classes Start Date')
    description = fields.Html(string='Offer Letter Set Up')
    test_admit_card = fields.Html()
    interview_card_setup = fields.Html()


class OdooCmsRegisterInherit(models.Model):
    _inherit = 'odoocms.admission.register'
    _description = 'Odoo CMS Register Inherit'

    prospectus_fee_due_date = fields.Date(string='Application Fee Due Date')
    first_challan_due_date = fields.Date(string='First Challan Due Date')
    second_challan_due_date = fields.Date(string='Second Challan Due Date')
