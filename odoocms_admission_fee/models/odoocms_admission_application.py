from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import datetime, date
import pdb


import logging
_logger = logging.getLogger(__name__)

class OdooCmsRegisterInherit(models.Model):
    _inherit = 'odoocms.admission.register'

    invoice_payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', tracking=True)
    full_invoice_payment_term_id = fields.Many2one('account.payment.term', string='Full Payment Terms', tracking=True)
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
            receipts = self.env['odoocms.receipt.type'].sudo().search([('name', 'in', ('Registration Fee', 'Prospectus Fee','Application Processing Fee')) , ('company_id' , '=' , self.register_id.company_id.id)])
            fee_head_id = self.env['odoocms.fee.head'].sudo().search([('name', 'in', ('Prospectus Fee', 'Prospectus')) , ('company_id' , '=' , self.register_id.company_id.id) ])

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

            journal_id = None
            if not journal_id:
                journal_id = self.env['account.journal'].search([('company_id','=',self.env.company.id),('type','=','sale')])

            data = {
                'application_id': self.id,
                'student_id': self.student_id.id,
                'partner_id': partner_id.id,
                # 'fee_structure_id': fee_structure and fee_structure.id or False,
                'journal_id': journal_id[0].id,
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
            # Get company configuration for challan checksx
            company = self.env.company
            
            # Document Verification Check (only if enabled in company config)
            if company.challan_check_document_verification:
                doc_check = rec.applicant_academic_ids.filtered(lambda x: x.doc_state not in ('yes', 'reg_verified'))
                if doc_check:
                    raise UserError(_("Applicant Doc not verified"))
            
            # Scholarship Check (only if enabled in company config)
            if company.challan_check_scholarship:
                if not rec.scholarship_id:
                    raise UserError('Scholarship not Assigned to Student')
            
            # If all enabled checks pass, generate the invoice
            rec.action_create_admission_invoice()

    # ***** Admission Challan *****#
    def action_create_admission_invoice(self,bypass_check=False):
        lines = []
        invoice_id = self.env['account.move']
        invoice_waiver_amount = 0

        # Get company configuration for challan checks
        company = self.env.company
        
        # Merit List Check (only if enabled in company config)
        merit_line = self.env['odoocms.merit.register.line']
        if company.challan_check_merit_list:
            merit_list = self.meritlist_id
            # First try strict match: selected in this specific merit register
            domain = [('applicant_id', '=', self.id), ('selected', '=', True)]
            if merit_list:
                domain.append(('merit_reg_id', '=', merit_list.id))
            merit_line = self.env['odoocms.merit.register.line'].search(domain, limit=1)
            # Fallback: any selected merit line for this applicant (in case UI/db mismatch)
            if not merit_line:
                merit_line = self.env['odoocms.merit.register.line'].search([
                    ('applicant_id', '=', self.id), ('selected', '=', True)
                ], limit=1)
            if not merit_line:
                raise UserError(_("Record Not Found in Merit List"))
        else:
            # If merit check is disabled, still get one merit_line for program inference if available
            merit_list = self.meritlist_id
            domain = [('applicant_id', '=', self.id), ('selected', '=', True)]
            if merit_list:
                domain.append(('merit_reg_id', '=', merit_list.id))
            merit_line = self.env['odoocms.merit.register.line'].search(domain, limit=1)

        # Document Verification Check (only if enabled in company config)
        doc_verified = True
        if company.challan_check_document_verification:
            doc_verified = all(x.doc_state == 'yes' for x in self.applicant_academic_ids)
        
        # Scholarship Check (only if enabled in company config)
        scholarship_assigned = True
        if company.challan_check_scholarship:
            scholarship_assigned = bool(self.scholarship_id)
        if company and company.challan_check_offer_letter:
                exists = self.env['ucp.offer.letter'].sudo().search_count([
                    ('applicant_id', '=', self.id)
                ])
                if not exists:
                    raise UserError(_("The offer letter must be sent to the applicant before proceeding."))



        # if all enabled checks pass
        if bypass_check or (doc_verified and scholarship_assigned):
            user = self.user_id
            if not user:
                user = self.env['res.users'].sudo().search([('login', '=', self.application_no)])

            program_id =  self.prefered_program_id if  self.prefered_program_id  else merit_line.program_id 
            if not program_id:
                raise UserError(_('No Program in Merit For this Application'))

            first_semester_courses = self.env['odoocms.applicant.first.semester.courses']
            partner_id = user.partner_id

            if partner_id:
                due_date, second_due_date = self.get_challan_due_date(program_id, merit_line.merit_reg_id.register_id)
                batch_domain = [('program_id', '=', program_id.id), ('session_id', '=', self.register_id.academic_session_id.id),
                                ('career_id', '=', self.register_id.career_id.id)]
                program_batch = self.env['odoocms.batch'].search(batch_domain)
                if program_batch:
                    study_scheme_id = program_batch.study_scheme_id
                    if self.first_semester_courses:
                        first_semester_courses = self.first_semester_courses.mapped('study_scheme_line_id')
                    if not first_semester_courses:
                        raise UserError(_("Please define courses for candidate %s") % (self.application_no))
                        # first_semester_courses = study_scheme_id.line_ids.filtered(lambda a: a.semester_id.number == 1)


    
                    # self.student_id = student.id
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
                if not fee_structure:
                    fee_domain = [
                        ('company_id','=',self.company_id.id),
                        ('session_id', '=', self.register_id.academic_session_id.id),
                        ('batch_id', '=', program_batch.id),
                        ('career_id', '=', self.register_id.career_id.id)
                    ]
                    fee_structure = self.env['odoocms.fee.structure'].search(fee_domain, order='id desc', limit=1)
                if not fee_structure:
                    fee_domain = [
                        ('company_id', '=', self.company_id.id),
                        ('session_id', '=', self.register_id.academic_session_id.id),
                        ('career_id', '=', self.register_id.career_id.id)
                    ]
                    fee_structure = self.env['odoocms.fee.structure'].search(fee_domain, order='id desc', limit=1)
                if not fee_structure:
                    raise UserError(_("Please define Fee Structure For Batch %s of Career %s") % (program_batch.name, self.register_id.career_id.name))

                receipts = self.env['odoocms.receipt.type'].sudo().search([('company_id','=',self.company_id.id), ('name', 'in', ('Admission Fee', 'Admission'))])
                if not receipts:
                    raise UserError("Please define the Receipt Type named Admission Fee")

                # ***** Admission and Tuition Fee Head ***** #
                tut_fee_head_id = program_batch.batch_tuition_structure_head.fee_head_id
                adm_fee_head_id = program_batch.admission_tuition_structure_head.fee_head_id
                if not tut_fee_head_id:
                    tut_fee_head_id = self.env['odoocms.fee.head'].search([('company_id','=',self.company_id.id),('name', 'in', ('Tuition', 'Tuition Fee'))], order='id desc', limit=1)
                if not adm_fee_head_id:
                    adm_fee_head_id = self.env['odoocms.fee.head'].search([('company_id','=',self.company_id.id),('name', 'in', ('Admission Fee', 'Admission'))], order='id desc', limit=1)

                if not tut_fee_head_id:
                    raise UserError(_('Tuition Fee Head Not Found.'))
                if not adm_fee_head_id:
                    raise UserError(_('Admission Fee Head Not Found.'))

                waivers = []
                line_discount = 0
                if self.scholarship_id:
                    waiver_domain = [('waiver_id', '=', self.scholarship_id.id), ('fee_head_id', '=', adm_fee_head_id.id)]
                    waiver_fee_line = self.env['odoocms.fee.waiver.line'].search(waiver_domain, order='id desc', limit=1)
                    if waiver_fee_line:
                        waivers.append(self.scholarship_id)
                        line_discount =waiver_fee_line.amount if (waiver_fee_line and waiver_fee_line.amount > 0) else waiver_fee_line.percentage #added by abubakar
                        # line_discount = self.scholarship_id.amount if (self.scholarship_id and self.scholarship_id.amount > 0) else self.scholarship_id.line_ids[0].percentage
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
                    'partner_id': partner_id.id,
                    'no_split': True,
                    # 'no_split': adm_fee_head_id.no_split,
                }
                lines.append((0, 0, adm_line))

                # ***** Courses Fee ***** #
                jj = 0
                if first_semester_courses:
                    for course in first_semester_courses:
                        line_discount = 0
                        primary_class_id = self.env['odoocms.class.primary'].search([('study_scheme_line_id', '=', course.id)])
                        qty = course.credits
                        price_unit = program_batch.per_credit_hour_fee
                        gross = qty * price_unit

                        if self.scholarship_id:
                            waiver_line_domain = [('waiver_id', '=', self.scholarship_id.id), ('fee_head_id', '=', tut_fee_head_id.id)]
                            waiver_fee_line = self.env['odoocms.fee.waiver.line'].search(waiver_line_domain, order='id desc', limit=1)
                            if waiver_fee_line:
                                waivers.append(self.scholarship_id)
                                line_discount =waiver_fee_line.amount if (waiver_fee_line and waiver_fee_line.amount > 0) else waiver_fee_line.percentage   #added by abubakar
                                # line_discount = self.scholarship_id.line_ids and self.scholarship_id.line_ids[0].percentage
                                invoice_waiver_amount += gross * (line_discount / 100)

                        fee_line = {
                            'sequence': 20 + jj,
                            'name': course.course_name,
                            'quantity': qty,
                            'price_unit': price_unit,
                            'product_id': tut_fee_head_id.product_id.id,
                            'account_id': tut_fee_head_id.property_account_income_id.id,
                            'fee_head_id': tut_fee_head_id.id,
                            'course_id_new': primary_class_id and primary_class_id.id or False,  # Sarfraz, i will check it later
                            'exclude_from_invoice_tab': False,
                            'registration_id': False,
                            'registration_line_id': False,
                            'course_credit_hours': qty,
                            'discount': line_discount,
                            'course_gross_fee': gross,
                            'registration_type': 'main',
                            'study_scheme_line': course.id,
                            'partner_id': partner_id.id,
                            'no_split': False,
                            # 'no_split': tut_fee_head_id.no_split,
                        }
                        lines.append((0, 0, fee_line))
                        jj += 1

                # ***** Move Record Dict ***** #
                if self.scholarship_id.amount == 100:
                    payment_term = self.register_id.full_invoice_payment_term_id
                else:
                    payment_term = self.register_id.invoice_payment_term_id

                data = {
                    'application_id': self.id,
                    'student_id': self.student_id.id,
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
                    'invoice_payment_term_id': payment_term and payment_term.id or False,

                }
                invoice_id = self.env['account.move'].sudo().create(data)
                self.admission_inv_id = invoice_id and invoice_id.id or False

                if invoice_id.payment_state == 'not_paid':
                    invoice_id.sudo().action_post()

        return invoice_id
    
    def admission_link_invoice_to_student(self):
        if self.student_id:
            invoices = self.env['account.move'].search([('application_id', '=', self.id)], order='id asc')
            if invoices:
                invoices.write({'student_id': self.student_id.id})

    def verify_voucher(self, manual=True):
        for rec in self:
            data = {
                'fee_voucher_state': 'verify',
                'voucher_date': date.today(),
                'voucher_verified_date': fields.Date.today(),
            }

            if manual and rec.prospectus_inv_id and rec.prospectus_inv_id.payment_state not in ('paid', 'in_payment'):
                update_data = {
                    'payment_date': fields.Date.today(),
                    'paid_time': datetime.now().strftime("%H:%M:%S"),
                    'paid_bank_name': 'Admission Department',
                }

                journal_id = self.env['account.journal'].sudo().search([('name', '=', 'Admission Department'),('company_id','=',self.company_id.id)])
                payment_obj = self.env['odoocms.fee.payment'].sudo()
                payment_rec = payment_obj.sudo().fee_payment_record(fields.Date.today(), rec.prospectus_inv_id.old_challan_no, rec.prospectus_inv_id.amount_total, journal_id, invoice_id=rec.prospectus_inv_id)
                payment_rec.sudo().action_post_fee_payment()
                rec.prospectus_inv_id.sudo().write(update_data)

                verify_source = 'auto'
                if self.env.user.department_id_new:
                    if 'Admission' in self.env.user.department_id_new.name:
                        verify_source = 'admission'
                    elif 'Finance' in self.env.user.department_id_new.name:
                        verify_source = 'finance'
                data['fee_voucher_verify_by'] = self.env.user.id
                data['fee_voucher_verify_source'] = verify_source

            rec.sudo().write(data)

            # mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', rec.company_id.id)])
            # template = self.env['mail.template'].sudo().search(
            #     [('name', '=', 'Admission Application Fee Verified'), ('mail_server_id', '=', mail_server_id.id)])

            # try:
            #     rec.message_post_with_template(template.id)  # , composition_mode='comment'
            # except Exception as e:
            #     print(e)

            if rec.state == 'submit' and rec.prefered_program_id.entry_test and not rec.prefered_program_id.calculate_merit_with_exemption:
                rec.assign_test_date()

    def univerify_voucher(self):
        for rec in self:
            rec.fee_voucher_state = 'unverify'
            rec.voucher_verified_date = False
            # template = self.env.ref('odoocms_admission.mail_template_voucher_un_verified')
            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', rec.company_id.id)])
            template = self.env['mail.template'].sudo().search(
                [('name', '=', 'Admission Voucher UnVerified'), ('mail_server_id', '=', mail_server_id.id)])
            try:
                post_message = rec.message_post_with_template(template.id)  # , composition_mode='comment'
            except ValueError:
                continue
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
