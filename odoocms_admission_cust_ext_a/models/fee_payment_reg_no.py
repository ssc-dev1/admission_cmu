# -*- coding: utf-8 -*-
import pdb
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import decimal
import logging

_logger = logging.getLogger(__name__)


class OdooCMSFeePayment(models.Model):
    _inherit = 'odoocms.fee.payment'
    _description = 'Fee Payment'
 
 
 
    def action_post_fee_payment(self, fee_term_id=False, student_ledger=True):
            if not fee_term_id:
                fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
                fee_term_id = self.env['odoocms.academic.term'].browse(fee_charge_term).id

            for rec in self:
                if rec.payment_id:
                    continue

                if rec.challan_id:
                    flag = True
                    challan = rec.challan_id
                    if abs(rec.received_amount - challan.amount_residual) > 2:
                        if (challan.late_fine + challan.amount_residual) == rec.received_amount:
                            rec.late_fee_invoice()
                        else:
                            flag = False
                    if flag:
                        to_reconcile = challan.line_ids
                        partner_id = rec.student_id and rec.student_id.partner_id or False
                        destination_account_id = self.env['account.account'].search([('company_id','=',challan.company_id.id),('user_type_id.name', '=', 'Receivable')], order='id asc', limit=1)
                        invoice_id = challan.line_ids[0].move_id
                        _logger.warning("POSTING Fee: Challan:%s, Invoice:%s" % (challan.name, invoice_id.name,))

                        if invoice_id.state != 'posted':
                            invoice_id.action_post()

                        data = {
                            'payment_type': 'inbound',
                            'payment_method_id': 1,
                            'partner_type': 'customer',
                            'currency_id': rec.journal_id.company_id.currency_id.id,
                            'partner_id': partner_id and partner_id.id or False,
                            'payment_date': rec.date,
                            'date': rec.date,
                            'ref': rec.receipt_number,
                            'amount': rec.received_amount,
                            'journal_id': rec.journal_id.id,
                            # 'donor_id': invoice.donor_id and invoice.donor_id.id or False,
                            'partner_bank_id': False,
                            'destination_account_id': destination_account_id and destination_account_id.id or False,
                        }
                        payment_id = self.env['account.payment'].create(data)
                        payment_id.action_post()
                        domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                        payment_lines = payment_id.line_ids.filtered_domain(domain)
                        for account in payment_lines.account_id:
                            (payment_lines + to_reconcile).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()

                        rec.write({
                            'name': payment_id.name,
                            'invoice_id': invoice_id.id,
                            'payment_id': payment_id.id,
                            'state': 'done',
                            'post_date': fields.Date.today(),
                            'processed': True,
                        })

                        # ***** Approve Registration *****
                        registration_id = self.env['odoocms.course.registration'].sudo().search([('invoice_id', '=', invoice_id.id),('state','=','submit')], order='id desc', limit=1)
                        registration_confirm_at_fee_paid = self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.registration_confirm_at_fee_paid', False)
                        if registration_confirm_at_fee_paid:
                            registration_id.write({
                                'date_effective': rec.date
                            })
                        registration_id.sudo().action_approve()

                        # if not registration_id:
                        #     registration_id = self.env['odoocms.course.registration'].sudo().search([('student_id', '=', invoice.student_id.id),
                        #                                                                              ('term_id', '=', fee_term_id),
                        #                                                                              ('state', '!=', 'approved')
                        #                                                                              ], order='id desc', limit=1)
                        # if registration_id and invoice.challan_type in ('main_challan', 'add_drop', 'admission'):
                        #     registration_id.sudo().action_approve()

                        if challan.label_id.type == 'admission':
                            try:
                                student = challan.student_id
                                if not student or not student.program_id:
                                    _logger.error("POSTING Fee: Student or Program missing for Challan:%s, Invoice:%s", challan.name, invoice_id.name)
                                    continue
                            
                                # Determine which program to use for registration number generation
                                # ONLY manual assignment - NO auto-detection
                                # If program has parent_program_id set (manually set in Admission Register) → use parent's sequence_number
                                # Otherwise → use program's own sequence_number
                                reg_program = student.program_id  # Default: use program's own sequence_number
                                
                                # Check if program has parent_program_id set (explicitly linked in Admission Register)
                                # This is the ONLY way to determine parent-child relationship - manual assignment only
                                if student.program_id.parent_program_id:
                                    reg_program = student.program_id.parent_program_id
                                    _logger.info("POSTING Fee: Using program's parent_program_id for registration. Student Program:%s, Parent Program:%s",
                                               student.program_id.code, reg_program.code)
                                else:
                                    # No parent_program_id set - use program's own sequence_number
                                    # This handles:
                                    # - Parent programs (e.g., BBA with is_parent = true) → use BBA's own sequence_number
                                    # - Standalone programs (no parent relationship) → use program's own sequence_number
                                    _logger.info("POSTING Fee: Using program's own sequence_number. Student Program:%s (no parent_program_id set)",
                                               student.program_id.code)
                                
                                program_sequence_number = reg_program.sequence_number
                                if program_sequence_number is None:
                                    _logger.error("POSTING Fee: Program sequence_number is None for Student:%s, Reg Program:%s", 
                                                student.id, reg_program.id)
                                    continue

                                # Validate short_code fields before generating reg_no
                                program_short_code = getattr(reg_program, 'short_code', None) or ''
                                term_short_code = getattr(invoice_id.term_id, 'short_code', None) or ''
                                term_code = getattr(invoice_id.term_id, 'code', None) or ''
                                
                                if not program_short_code:
                                    _logger.error("POSTING Fee: Program short_code is None/Empty for Student:%s, Program:%s, Challan:%s", 
                                                student.id, reg_program.id, challan.name)
                                    continue
                                
                                company_code = getattr(invoice_id.company_id, 'code', False)
                                reg_no = None
                                
                                if company_code:
                                    if invoice_id.company_id.code in ('CUST','UBAS'):
                                        if not term_short_code:
                                            _logger.error("POSTING Fee: Term short_code is None/Empty for Invoice:%s, Term:%s", 
                                                        invoice_id.name, invoice_id.term_id.id)
                                            continue
                                        reg_no = program_short_code + term_short_code + str(program_sequence_number).zfill(3)
                                    elif invoice_id.company_id.code == 'MAJU':
                                        if not term_code:
                                            _logger.error("POSTING Fee: Term code is None/Empty for Invoice:%s, Term:%s", 
                                                        invoice_id.name, invoice_id.term_id.id)
                                            continue
                                        reg_no = term_code + "-" + program_short_code + "-" + str(program_sequence_number).zfill(4)
                                    else:
                                        if not term_short_code:
                                            _logger.error("POSTING Fee: Term short_code is None/Empty for Invoice:%s, Term:%s", 
                                                        invoice_id.name, invoice_id.term_id.id)
                                            continue
                                        reg_no = 'L1' + term_short_code + program_short_code + str(program_sequence_number).zfill(4)
                                else:
                                    if not term_short_code:
                                        _logger.error("POSTING Fee: Term short_code is None/Empty for Invoice:%s, Term:%s", 
                                                    invoice_id.name, invoice_id.term_id.id)
                                        continue
                                    reg_no = 'L1' + term_short_code + program_short_code + str(program_sequence_number).zfill(4)

                                if not reg_no:
                                    _logger.error("POSTING Fee: Failed to generate reg_no for Student:%s, Challan:%s, Invoice:%s", 
                                                student.id, challan.name, invoice_id.name)
                                    continue

                                # Check if registration number already exists for this career_id
                                # Unique constraint is on (code, career_id), so we need to ensure uniqueness
                                student_career_id = student.career_id.id if student.career_id else None
                                max_retries = 10  # Prevent infinite loop
                                retry_count = 0
                                
                                while retry_count < max_retries:
                                    # Check if this reg_no already exists for the same career_id
                                    existing_student = self.env['odoocms.student'].search([
                                        ('code', '=', reg_no),
                                        ('career_id', '=', student_career_id),
                                        ('id', '!=', student.id)
                                    ], limit=1)
                                    
                                    if existing_student:
                                        # Registration number already exists for this career_id
                                        # Increment sequence and try again
                                        program_sequence_number += 1
                                        retry_count += 1
                                        _logger.warning("POSTING Fee: Registration number %s already exists for career_id %s. Incrementing sequence to %s (retry %s/%s)", 
                                                       reg_no, student_career_id, program_sequence_number, retry_count, max_retries)
                                        
                                        # Regenerate registration number with new sequence
                                        if company_code:
                                            if invoice_id.company_id.code in ('CUST','UBAS'):
                                                reg_no = program_short_code + term_short_code + str(program_sequence_number).zfill(3)
                                            else:
                                                reg_no = 'L1' + term_short_code + program_short_code + str(program_sequence_number).zfill(4)
                                        else:
                                            reg_no = 'L1' + term_short_code + program_short_code + str(program_sequence_number).zfill(4)
                                    else:
                                        # Registration number is unique, break the loop
                                        break
                                
                                if retry_count >= max_retries:
                                    _logger.error("POSTING Fee: Failed to generate unique reg_no after %s retries for Student:%s, Challan:%s", 
                                                max_retries, student.id, challan.name)
                                    continue

                                # Update sequence number on the program used for registration (parent if child, self if parent)
                                # Use the final sequence_number (may have been incremented if duplicates found)
                                reg_program.sequence_number = program_sequence_number + 1
                                _logger.info("POSTING Fee: Updated sequence_number for Reg Program:%s (ID:%s) to %s", 
                                           reg_program.code, reg_program.id, reg_program.sequence_number)
                                
                                # Generate notification email
                                company_code_lower = getattr(student.company_id, 'code', 'cust') or 'cust'
                                notification_email = reg_no + '@' + company_code_lower.lower() + '.edu.pk'
                                
                                # Write student data
                                student.write({
                                    'code': reg_no,
                                    'id_number': reg_no,
                                    'fee_paid': True,
                                    'state': 'enroll',
                                    'notification_email': notification_email
                                })
                                _logger.info("POSTING Fee: Successfully assigned reg_no %s to Student:%s, Challan:%s", 
                                           reg_no, student.id, challan.name)

                                # Generate welcome letter
                                try:
                                    reg = invoice_id.application_id and invoice_id.application_id.register_id
                                    if reg and reg.enable_welcome_letter:
                                        invoice_id.application_id.sudo().generate_welcome_letter_from_application()
                                except Exception as e:
                                    _logger.error("POSTING Fee: Failed to send Welcome Letter for student %s: %s", student.id, e)

                                # Create scholarships
                                try:
                                    self.create_applied_scholarship()
                                    self.create_eligibility_scholarship()
                                except Exception as e:
                                    _logger.error("POSTING Fee: Failed to create scholarships for student %s: %s", student.id, e)

                                # Link invoice to student
                                try:
                                    invoice_id.application_id.admission_link_invoice_to_student()
                                except Exception as e:
                                    _logger.error("POSTING Fee: Failed to link invoice to student for student %s: %s", student.id, e)

                            except Exception as e:
                                _logger.error("POSTING Fee: Critical error in admission registration for Challan:%s, Invoice:%s, Student:%s, Error: %s", 
                                            challan.name, invoice_id.name, challan.student_id.id if challan.student_id else 'N/A', str(e))
                                # Continue processing - don't fail the entire payment posting
                                continue

                            # Email And SMS
                            # rec.sudo().send_fee_receive_sms(reg_no)
                            # if invoice_id.company_id.code == 'UCP':
                            #     rec.send_fee_receive_email(student, reg_no)

                        # ***** Reinstate Drap Courses due to Fee *****#
                        # ***** Search Out Withdraw Courses *****#

                        if challan.label_id.type != 'other':
                            reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
                            if reason_id:
                                withdraw_courses = challan.student_id.course_ids.filtered(lambda a: a.state == 'withdraw' and a.withdraw_reason == reason_id)
                                if withdraw_courses:
                                    withdraw_courses.write({
                                        'state': 'current',
                                        'withdraw_date': False,
                                        'withdraw_reason': False,
                                        'grade': False,
                                    })


                else:
                    invoice = rec.invoice_id
                    _logger.warning("POSTING Fee: Invoice:%s" % (invoice.name,))
                    if invoice.state != 'posted':
                        rec.write({
                            'state': 'error',
                        })
                        continue
                    to_reconcile = invoice.line_ids._origin
                    invoice_ids2 = invoice
                    due_date = invoice.invoice_date_due
                    date_invoice = rec.date
                    payment_date = fields.Date.from_string(rec.date)
                    invoice.payment_date = rec.date
                    # days = (payment_date - due_date).days

                    partner_id = invoice.student_id and invoice.student_id.partner_id or False
                    destination_account_id = self.env['account.account'].search([('company_id','=',invoice.company_id.id),('user_type_id.name', '=', 'Receivable')], order='id asc', limit=1)
                    data = {
                        'payment_type': 'inbound',
                        'payment_method_id': 1,
                        'partner_type': 'customer',
                        'currency_id': invoice.journal_id.company_id.currency_id.id,
                        'partner_id': partner_id and partner_id.id or False,
                        'payment_date': rec.date,
                        'date': rec.date,
                        'ref': rec.receipt_number,
                        'amount': rec.received_amount,
                        'journal_id': rec.journal_id.id,
                        'donor_id': invoice.donor_id and invoice.donor_id.id or False,
                        'partner_bank_id': False,
                        'destination_account_id': destination_account_id and destination_account_id.id or False,
                    }

                    payment_vals_list = [data]
                    new_payment_recs = self.env['account.payment'].create(payment_vals_list)
                    new_payment_recs.action_post()
                    rec.name = new_payment_recs.name
                    domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                    to_reconcile2 = to_reconcile.filtered_domain([('account_internal_type', 'in', ('receivable', 'payable')),
                                                                ('reconciled', '=', False)])
                    for new_payment_rec, lines in zip(new_payment_recs, to_reconcile2):
                        if new_payment_rec.state != 'posted':
                            continue
                        payment_lines = new_payment_rec.line_ids.filtered_domain(domain)
                        for account in payment_lines.account_id:
                            (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                                    ('reconciled', '=', False)
                                                                    ]).reconcile()

                    # invoice.payment_id = new_payment_rec.id
                    invoice_ids2.payment_date = rec.date
                    rec.write({
                        'state': 'done',
                        'processed': True,
                    })
                    invoice.write({
                        'confirmation_date': fields.Date.today(),
                        'paid_bank_name':rec.journal_id.name
                    })

                    # ***** Approve Registration *****#
                    registration_id = invoice.registration_id
                    if not registration_id:
                        reg_domain = [('student_id', '=', invoice.student_id.id), ('term_id', '=', fee_term_id), ('state', '!=', 'approved')]
                        registration_id = self.env['odoocms.course.registration'].sudo().search(reg_domain, order='id desc', limit=1)
                    if registration_id and invoice.challan_type in ('main_challan', 'add_drop', 'admission'):
                        registration_id.sudo().action_approve()

                    # Prospectus Fee
                    if invoice.application_id and invoice.challan_type == 'prospectus_challan' and not invoice.application_id.fee_voucher_state == 'verify':
                        invoice.application_id.sudo().verify_voucher(manual=False)
                        invoice.application_id.sudo().write({
                            'voucher_date': invoice.payment_date or rec.date or fields.Date.today(),
                            'voucher_verified_date': fields.Date.today(),
                            'fee_voucher_state': 'verify'
                        })

                    # ***** Reinstate Drap Courses due to fee *****#
                    # ***** Search Out Withdraw Courses *****#
                    if invoice.challan_type in ('2nd_challan', 'installment'):
                        reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
                        if reason_id:
                            withdraw_courses = invoice.student_id.course_ids.filtered(lambda a: a.state == 'withdraw' and a.withdraw_reason == reason_id)
                            if withdraw_courses:
                                withdraw_courses.write({
                                    'state': 'current',
                                    'withdraw_date': False,
                                    'withdraw_reason': False,
                                    'grade': False,
                                })



    def create_applied_scholarship(self):
        for rec in self:
            if rec.challan_id:
                applied_scholarship=rec.challan_id.waiver_ids
                if applied_scholarship:
                    for app_scholarship in applied_scholarship:
                        rec.student_id.scholarship_id =app_scholarship
                        data_values = {
                        'student_id': rec.student_id and rec.student_id.id or False,
                        'student_code': rec.challan_id.student_id and rec.challan_id.student_id.code or '',
                        'student_name': rec.challan_id.student_id and rec.challan_id.student_id.name,
                        'program_id': rec.challan_id.student_id.program_id and rec.challan_id.student_id.program_id.id or False,
                        'term_id': rec.challan_id.term_id and rec.challan_id.term_id.id or False,
                        'scholarship_id': app_scholarship and app_scholarship.id or False,
                        'scholarship_percentage': app_scholarship.amount,
                        'current': True,
                        'state': 'lock',
                        }
                        self.env['odoocms.student.applied.scholarships'].sudo().create(data_values)
    def create_eligibility_scholarship(self):
        for rec in self:
            if rec.challan_id and rec.challan_id.student_id:
                student =rec.challan_id.student_id
                applicant_scholarship_ids = self.env['odoocms.application'].search([('application_no','=',rec.challan_id.student_id.admission_no)]).scholarship_ids
                if applicant_scholarship_ids:
                    for eligibility_scholarship in applicant_scholarship_ids:
                        program_term_scholarship_id = self.env['odoocms.program.term.scholarship'].search([('program_id', '=', student.program_id.id),
                                                                                                           ('term_id', '=', rec.challan_id.term_id.id),
                                                                                                           ('scholarship_ids', 'in', eligibility_scholarship.id)])
                        data_values = {
                            'student_id': student and student.id or False,
                            'student_code': student.code,
                            'student_name': student.name,
                            'program_id': student.program_id and student.program_id.id or False,
                            'applied_term_id': rec.challan_id.term_id and rec.challan_id.term_id.id or False,
                            'program_term_scholarship_id': program_term_scholarship_id and program_term_scholarship_id.id or False,
                            'scholarship_id': eligibility_scholarship.id,
                            'scholarship_value': eligibility_scholarship and eligibility_scholarship.amount or 0,
                            'state': 'lock',
                        }
                        self.env['odoocms.student.scholarship.eligibility'].create(data_values)

    @api.model
    def missing_scholarship_allocation_for_student(self, company_id=None, term_id=None ):
        paid_receipts = self.env['account.move'].search([('payment_state','in',['paid','partial']),('term_id','=',term_id),('challan_type','=','admission'),('company_id','=',company_id)])
        for inv in paid_receipts:
            fee_payment_record = self.env['odoocms.fee.payment'].search([('state','=','done'),('term_id','=',term_id),('invoice_id','=',inv.id),('company_id','=',company_id)])
            for fpr in fee_payment_record:
                try:
                    if not inv.student_id.applied_scholarship_ids:
                        fpr.create_applied_scholarship()
                    if not inv.student_id.scholarship_eligibility_ids:
                        fpr.create_eligibility_scholarship()
                except Exception as e :
                    continue



    
