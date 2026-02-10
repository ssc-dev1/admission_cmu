# -*- coding: utf-8 -*-
from odoo import fields, models, _, api
from datetime import date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError
import pdb


class OdooCmsRegisterInherit(models.Model):
    _inherit = 'odoocms.admission.register'

    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', tracking=True)
    journal_id = fields.Many2one('account.journal', 'Journal')


class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    fee_payer_name = fields.Char(string='Fee Payer Name')
    fee_payer_cnic = fields.Char(string='Fee Payer Cnic')

    # Voucher Details
    # voucher_image = fields.Binary(string='Fee Voucher', attachment=True)
    # voucher_number = fields.Char(string='Voucher Number')
    # voucher_date = fields.Date(string='Fee Submit Date')
    # amount = fields.Integer(string='Amount')
    # voucher_verified_date = fields.Date(string='Voucher Verified Date')
    # voucher_issued_date = fields.Date(string='Voucher Issue Date')
    # fee_voucher_state = fields.Selection([('no', 'Not Downloaded Yet'), ('download', 'Not Uploaded Yet'),
    #                                       ('upload0', 'Only Image Uploaded'), ('upload', 'Not Verified Yet'),
    #                                       ('verify', 'Verified'), ('unverify', 'Un-Verified')
    #                                       ], default='no')
    #
    prospectus_inv_id = fields.Many2one('account.move', string='Prospectus Fee')
    admission_inv_id = fields.Many2one('account.move', string='Admission Fee')

    admission_challan_ids = fields.One2many('account.move', 'application_id', 'Admission Challans')

    # ****** Create Prospectus Challan *****#
    def action_create_prospectus_invoice(self):
        lines = []
        user = self.user_id
        if not user:
            user = self.env['res.users'].sudo().search(
                [('login', '=', self.application_no)])
        partner_id = user.partner_id
        if partner_id:
            amount = 0
            due_date = fields.Date.today()
            preference_id = self.preference_ids and \
                            self.preference_ids.sorted(key=lambda a: a.preference, reverse=False)[0] or False
            program_id = False
            if preference_id:
                program_id = preference_id.program_id
                # Prospectus Fee
                if program_id.prospectus_registration_fee > 0:
                    amount = program_id.prospectus_registration_fee
                else:
                    prospectus_fee = float(self.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.registration_fee') or '2000')
                    amount = prospectus_fee

                # Prospectus Fee Due Date
                if program_id.prospectus_program_fee_date:
                    due_date = program_id.prospectus_program_fee_date
                else:
                    due_date = self.register_id.prospectus_fee_due_date
            else:
                prospectus_fee = float(self.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.registration_fee') or '2000')
                amount = prospectus_fee
                due_date = self.register_id.prospectus_fee_due_date

            # fee_structure = self.env['odoocms.fee.structure'].sudo().search([('company_id' , '=' , self.register_id.company_id.id)], order='id desc', limit=1)
            receipts = self.env['odoocms.receipt.type'].sudo().search([('name', 'in', ('Registration Fee', 'Prospectus Fee')) , ('company_id' , '=' , self.register_id.company_id.id)])
            fee_head_id = self.env['odoocms.fee.head'].sudo().search([('name', 'in', ('Prospectus Fee', 'Prospectus')) , ('company_id' , '=' , self.register_id.company_id.id) ])

            # program = self.preference_ids[0].program_id
            # batch_domain = [('program_id', '=', program_id.id), ('session_id', '=', self.register_id.academic_session_id.id),
            #                 ('career_id', '=', self.register_id.career_id.id)]
            # program_batch = self.env['odoocms.batch'].search(batch_domain)

            # if not self.student_id:
            #     student_data = {
            #         'program_id': program and program.id or False,
            #         'term_id': self.register_id.term_id and self.register_id.term_id.id or False,
            #         'institute_id': False,
            #         'batch_id': program_batch and program_batch.id or False,
            #         'study_scheme_id': program_batch and program_batch.study_scheme_id.id or False,
            #     }
            #     student = self.sudo().create_student(student_data)
            #     self.student_id = student.id

            fee_lines = {
                'sequence': 10,
                'name': "Prospectus Fee",
                'quantity': 1,
                'price_unit': amount,
                'product_id': fee_head_id.product_id.id,
                'account_id': fee_head_id.property_account_income_id.id,
                'fee_head_id': fee_head_id.id,
                'exclude_from_invoice_tab': False,
                'course_gross_fee': amount,
            }
            lines.append((0, 0, fee_lines))

            data = {
                'application_id': self.id,
                'student_id': self.student_id.id,
                'partner_id': partner_id.id,
                # 'fee_structure_id': fee_structure and fee_structure.id or False,
                'journal_id': self.register_id.journal_id.id,
                'invoice_date': fields.Date.today(),
                'invoice_date_due': due_date,
                'state': 'draft',
                'is_fee': True,
                'is_cms': True,
                'is_hostel_fee': False,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'term_id': self.register_id.term_id and self.register_id.term_id.id or False,
                'validity_date': due_date,
                'narration': 'Prospectus Fee',
                'is_prospectus_fee': True,
                'challan_type': 'prospectus_challan',
            }
            invoice_id = self.env['account.move'].sudo().create(data)
            self.prospectus_inv_id = invoice_id.id
            invoice_id.sudo().action_post()
            # invoice_id.sudo().action_invoice_send()

    def check_applicant_doc(self):
        for rec in self:
            # doc_check = False
            doc_check = rec.applicant_academic_ids.filtered(lambda x: x.doc_state not in ('yes', 'reg_verified'))
            if doc_check:
                raise UserError(_("Applicant Doc not verified"))
            else:
                rec.action_create_admission_invoice()

    # ***** Admission Challan *****#
    def action_create_admission_invoice(self):
        lines = []
        new_invoice_id = self.env['account.move']
        invoice_id = self.env['account.move']
        fee_structure = False
        receipts = False
        program_id = False
        invoice_waiver_amount = 0

        merit_line = self.env['odoocms.merit.register.line'].search([('applicant_id', '=', self.id), ('selected', '=', True),
                                                                     ('program_id', '=', self.preference_ids[0].program_id.id)
                                                                     ])

        if not merit_line:
            raise UserError(_("Record Not Found in Merit List"))

        # if  all documents are verified and scholarship is applied
        if all(x.doc_state == 'yes' for x in merit_line.applicant_id.applicant_academic_ids) and merit_line.applicant_id.scholarship_id:
            user = self.user_id
            if not user:
                user = self.env['res.users'].sudo().search([('login', '=', self.application_no)])
            partner_id = user.partner_id
            first_semester_courses = self.env['odoocms.applicant.first.semester.courses']

            if partner_id:
                adm_amount = 0
                program_batch = False
                study_scheme_id = False
                program_id = self.prefered_program_id if  self.prefered_program_id  else merit_line.program_id 

                if not program_id:
                    raise UserError(_('No Program in Merit For this Application'))
                # due_date = program_id.admission_due_date

                due_date, second_due_date = self.get_challan_due_date(program_id, merit_line.merit_reg_id.register_id)
                program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id),
                                                                  ('session_id', '=', self.register_id.academic_session_id.id),
                                                                  ('term_id', '=', self.register_id.term_id.id),
                                                                  ('career_id', '=', self.register_id.career_id.id)])
                if program_batch:
                    study_scheme_id = program_batch.study_scheme_id
                    if self.first_semester_courses:
                        first_semester_courses = self.first_semester_courses.mapped('study_scheme_line_id')
                    if not first_semester_courses:
                        first_semester_courses = study_scheme_id.line_ids.filtered(lambda a: a.semester_id.number == 1)
                if not self.student_id:
                    student_data = {
                        'program_id': program_id and program_id.id or False,
                        'term_id': self.register_id.term_id and self.register_id.term_id.id or False,
                        'batch_id': program_batch and program_batch.id or False,
                        'study_scheme_id': program_batch and program_batch.study_scheme_id.id or False,
                    }
                    student = self.sudo().create_student(view=False, student_data=student_data)
                else:
                    student_data = {
                        'program_id': program_id and program_id.id or False,
                        'term_id': self.register_id.term_id and self.register_id.term_id.id or False,
                        'batch_id': program_batch and program_batch.id or False,
                        'study_scheme_id': program_batch and program_batch.study_scheme_id.id or False,
                    }
                    student = self.student_id.sudo().write(student_data)
                # ***** Get Fee Structure + Fee Receipts ***** #
                fee_structure = program_batch.fee_structure_id
                if fee_structure:
                    fee_structure = self.env['odoocms.fee.structure'].search([('session_id', '=', self.register_id.academic_session_id.id),
                                                                              ('batch_id', '=', program_batch.id),
                                                                              ('career_id', '=', self.register_id.career_id.id)
                                                                              ], order='id desc', limit=1)
                if not fee_structure:
                    raise UserError(_("Please define Fee Structure For Batch %s of Career %s") % (program_batch.name, self.register_id.career_id.name))

                receipts = self.env['odoocms.receipt.type'].sudo().search([('name', 'in', ('Admission Fee', 'Admission'))])
                if not receipts:
                    UserError(_("Please define the Receipt Type named Admission Fee"))

                # ***** Admission and Tuition Fee Head ***** #
                tut_fee_head_id = program_batch.batch_tuition_structure_head.fee_head_id
                adm_fee_head_id = program_batch.admission_tuition_structure_head.fee_head_id
                if not tut_fee_head_id:
                    tut_fee_head_id = self.env['odoocms.fee.head'].search([('name', 'in', ('Tuition', 'Tuition Fee'))
                                                                           ], order='id desc', limit=1)
                if not adm_fee_head_id:
                    adm_fee_head_id = self.env['odoocms.fee.head'].search([('name', 'in', ('Admission Fee', 'Admission'))
                                                                           ], order='id desc', limit=1)
                if not tut_fee_head_id:
                    raise UserError(_('Tuition Fee Head Not Found.'))
                if not adm_fee_head_id:
                    raise UserError(_('Admission Fee Head Not Found.'))

                waivers = []
                line_discount = 0
                if self.scholarship_id:
                    waiver_fee_line = self.env['odoocms.fee.waiver.line'].search(
                        [('waiver_id', '=', self.scholarship_id.id),
                         ('fee_head_id', '=',
                          adm_fee_head_id.id)
                         ], order='id desc', limit=1)

                    if waiver_fee_line:
                        waivers.append(self.scholarship_id)
                        line_discount = self.scholarship_id.amount if (self.scholarship_id and self.scholarship_id.amount > 0) else self.scholarship_id.line_ids[0].percentage
                        invoice_waiver_amount += program_batch.admission_fee * (line_discount / 100)

                # ***** Admission Line ***** #
                adm_line = {
                    'sequence': 10,
                    'name': "Admission Fee",
                    'quantity': 1,
                    'price_unit': program_batch.admission_fee,
                    'product_id': adm_fee_head_id.product_id.id,
                    'account_id': adm_fee_head_id.property_account_income_id.id,
                    'fee_head_id': adm_fee_head_id.id,
                    'exclude_from_invoice_tab': False,
                    'discount': line_discount,
                    'course_id_new': False,
                    'registration_id': False,
                    'registration_line_id': False,
                    'course_credit_hours': 0,
                    'course_gross_fee': program_batch.admission_fee,
                    'registration_type': 'main',
                }
                lines.append((0, 0, adm_line))

                # ***** Courses Fee ***** #
                jj = 0
                if first_semester_courses:
                    for course in first_semester_courses:
                        line_discount = 0
                        primary_class_id = self.env['odoocms.class.primary'].search([('study_scheme_line_id', '=', course.id)])
                        amount = program_batch.per_credit_hour_fee * course.credits
                        if self.scholarship_id:
                            waiver_fee_line = self.env['odoocms.fee.waiver.line'].search([('waiver_id', '=', self.scholarship_id.id),
                                                                                          ('fee_head_id', '=', tut_fee_head_id.id)
                                                                                          ], order='id desc', limit=1)
                            if waiver_fee_line:
                                waivers.append(self.scholarship_id)
                                line_discount = self.scholarship_id.line_ids and self.scholarship_id.line_ids[0].percentage
                                invoice_waiver_amount += amount * (line_discount / 100)

                        fee_line = {
                            'sequence': 20 + jj,
                            'name': course.course_name,
                            'quantity': 1,
                            'price_unit': amount,
                            'product_id': tut_fee_head_id.product_id.id,
                            'account_id': tut_fee_head_id.property_account_income_id.id,
                            'fee_head_id': tut_fee_head_id.id,
                            'course_id_new': primary_class_id and primary_class_id.id or False,  # Sarfraz, i will check it later
                            'exclude_from_invoice_tab': False,
                            'registration_id': False,
                            'registration_line_id': False,
                            'course_credit_hours': course.credits,
                            'discount': line_discount,
                            'course_gross_fee': amount,
                            'registration_type': 'main',
                            'study_scheme_line': course.id,
                        }
                        lines.append((0, 0, fee_line))
                        jj += 1

                # ***** Move Record Dict ***** #
                data = {
                    'application_id': self.id,
                    'partner_id': partner_id.id,
                    'fee_structure_id': fee_structure.id,
                    'journal_id': fee_structure.journal_id.id,
                    'invoice_date': fields.Date.today(),
                    'invoice_date_due': due_date,
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                    'term_id': self.register_id.term_id and self.register_id.term_id.id or False,
                    'validity_date': due_date,
                    'challan_type': 'admission',
                    'is_admission_fee': True,
                    'waiver_ids': [(6, 0, self.scholarship_id.ids)],
                    'waiver_percentage': self.scholarship_id.amount,
                    'waiver_amount': invoice_waiver_amount,

                }
                invoice_id = self.env['account.move'].sudo().create(data)
                self.admission_inv_id = invoice_id and invoice_id.id or False

                if invoice_id.payment_state == 'not_paid':
                    invoice_id.sudo().action_post()
                # if invoice_id.payment_state == 'open':
                #     invoice_id.sudo().action_invoice_send()

                # ***** Split Invoice ***** But Admission Line Should not be Split ***** #
                faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].search([('term_id', '=', self.register_id.term_id.id)], order='id desc', limit=1)
                if faculty_wise_fee_rec:
                    new_invoice_id = invoice_id.action_split_invoice(date_due2=faculty_wise_fee_rec.second_challan_due_date)
                    new_invoice_id.challan_type = '2nd_challan'
                    new_invoice_id.second_installment = True

                if not faculty_wise_fee_rec:
                    new_invoice_id = invoice_id.action_split_invoice(date_due2=second_due_date)
                    new_invoice_id.challan_type = '2nd_challan'
                    new_invoice_id.second_installment = True

        return invoice_id, new_invoice_id

    def admission_link_invoice_to_student(self):
        if self.student_id:
            invoices = self.env['account.move'].search(
                [('application_id', '=', self.id)], order='id asc')
            if invoices:
                invoices.write({'student_id': self.student_id.id})

    # def verify_voucher(self):
    #     for rec in self:
    #         if rec.fee_voucher_state == 'upload':
    #             data = {
    #                 'fee_voucher_state': 'verify',
    #                 'voucher_date': date.today(),
    #             }
    #             rec.sudo().write(data)
    #             if rec.is_dual_nationality or rec.overseas or rec.nationality.id != 177:
    #                 template = self.env.ref('odoocms_admission.mail_template_voucher_verified2')
    #             else:
    #                 template = self.env.ref('odoocms_admission.mail_template_voucher_verified')
    #             post_message = rec.message_post_with_template(template.id)  # , composition_mode='comment'

    # def univerify_voucher(self):
    #     for rec in self:
    #         rec.fee_voucher_state = 'unverify'
    #         template = self.env.ref(
    #             'odoocms_admission.mail_template_voucher_un_verified')
    #         post_message = rec.message_post_with_template(
    #             template.id)  # , composition_mode='comment'

    def get_challan_due_date(self, program_id, admission_register):
        first_challan_due_date = None
        second_challan_due_date = None

        if program_id:
            first_challan_due_date = getattr(program_id, 'admission_due_date', first_challan_due_date)
            second_challan_due_date = getattr(program_id, 'second_challan_due_date', second_challan_due_date)

        if admission_register:
            if not first_challan_due_date:
                first_challan_due_date = getattr(admission_register, 'first_challan_due_date', '')
            if not second_challan_due_date:
                second_challan_due_date = getattr(admission_register, 'second_challan_due_date', '')
        return first_challan_due_date, second_challan_due_date
