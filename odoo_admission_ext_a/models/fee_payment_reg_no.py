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
                            student = challan.student_id
                            program_sequence_number = student.program_id.sequence_number
                            company_code = getattr(invoice_id.company_id, 'code', False)
                            if company_code:
                                if invoice_id.company_id.code in ('CUST','UBAS'):
                                    reg_no = student.program_id.short_code + invoice_id.term_id.short_code + str(student.program_id.sequence_number).zfill(3)
                                elif invoice_id.company_id.code == 'MAJU':
                                     reg_no = invoice_id.term_id.code +"-"+ student.program_id.short_code +"-"+ str(student.program_id.sequence_number).zfill(4)
                                else:
                                    # last_student = self.env['odoocms.student'].search([('program_id', '=', invoice_id.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
                                    # if last_student:
                                    #     last_student_code = last_student.code[-4:]
                                    #     program_sequence_number = int(last_student_code) + 1
                                    reg_no = 'L1' + invoice_id.term_id.short_code + student.program_id.short_code + str(program_sequence_number).zfill(4)
                            else:
                                last_student = self.env['odoocms.student'].search([('program_id', '=', student.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
                                # if last_student:
                                #     last_student_code = last_student.code[-4:]
                                #     program_sequence_number = int(last_student_code) + 1
                                reg_no = 'L1' + invoice_id.term_id.short_code + student.program_id.short_code + str(program_sequence_number).zfill(4)

                            student.program_id.sequence_number = program_sequence_number + 1
                            notification_email= reg_no+'@'+student.company_id.code.lower()+'.edu.pk'
                            student.write({
                                'code': reg_no,
                                'id_number': reg_no,
                                'fee_paid':True,
                                'state':'enroll',
                                'notification_email':notification_email

                            })
                            self.create_applied_scholarship()
                            self.create_eligibility_scholarship()

                            # invoice_id.application_id.sudo().new_student_registration()
                            invoice_id.application_id.admission_link_invoice_to_student()

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



    