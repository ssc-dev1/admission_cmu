# -*- coding: utf-8 -*-
import pdb

from odoo import api, fields, models, tools, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


class OdooCMSFeeBarcode(models.Model):
    _inherit = 'odoocms.fee.barcode'

    sync_challan = fields.Boolean('Syncable to Dynamics')
    synced_challan = fields.Boolean('Synced to Dynamics')
    sql_id = fields.Char('SQL ID')
    date_sync = fields.Date('Sync Date')


    @api.model
    def cron_payslip_sync_pool(self, nlimit=500):
        try:
            # create connection
            connector_rec = self.env['odoo.fee.sql.connector'].search([], order='id desc', limit=1)
            if connector_rec:
                _logger.warning('*** Establishing Connection with Dynamics')
                cnxn, cursor = connector_rec.sudo().action_establish_connection()
                recs = self.env['odoocms.fee.barcode'].search([('sync_challan', '=', True)], limit=nlimit)
                for rec in recs:
                    _logger.warning('*** Challan %s is being processed', rec.name)
                    bank_acc = ''
                    bank_ledger_code = ''
                    bank_name = ''
                    student_id = rec.student_id

                    # ****** For Checking Duplicate *****#
                    # cursor.execute("SELECT challan_no from ucp_challans where challan_no=?", float(rec.name))
                    # already_exist_result = cursor.fetchall()
                    already_exist_result = False
                    if already_exist_result:
                        _logger.warning('*** Duplicate Challan %s was being processed', rec.name)
                        rec.sudo().write({
                            'sql_id': '0099',  # sql_id, #
                            'sync_challan': False,
                            'synced_challan': True,
                            # 'date_sync': fields.Date.today(),
                        })
                    else:

                        # ref_no = student_id.application_id and student_id.application.name or ''
                        ref_no = ''
                        invoice_term = rec.term_id or False
                        company = rec.company_id or self.env.company
                        term_line = invoice_term and invoice_term.term_lines and invoice_term.term_lines[0] or False

                        if rec.payment_id:
                            bank_acc = rec.payment_id.journal_id.bank_account_id.bank_account_code and rec.payment_id.journal_id.bank_account_id.bank_account_code or ''
                            bank_ledger_code = rec.payment_id.journal_id.bank_account_id.bank_ledger_code and rec.payment_id.journal_id.bank_account_id.bank_ledger_code or ''
                            bank_name = rec.payment_id.journal_id.name
                            if rec.payment_id.journal_id.bank_id.street:
                                bank_name = bank_name + " " + rec.payment_id.journal_id.bank_id.street

                        # tuition_fee2 = (rec.payable - rec.admission_fee - rec.hostel_fee - rec.hostel_security - rec.total_fine - rec.tax - rec.transport_fee - rec.misc_fee -
                        #                 rec.library_card_fee - rec.graduation_fee - rec.prospectus_fee - rec.entry_test_fee - rec.sports_fee - rec.degree_fee)
                        #
                        if rec.adjusted_gross and rec.adjusted_gross > 0 and rec.adjusted_gross != rec.gross_tuition_fee:
                            gross_tuition_fee = rec.adjusted_gross
                        else:
                            gross_tuition_fee = rec.gross_tuition_fee

                        if rec.adjusted_payable and rec.adjusted_payable > 0 and rec.adjusted_payable != rec.amount:
                            total_payable = rec.adjusted_payable
                        else:
                            total_payable = rec.amount

                        sql_id = cursor.execute(""" 
                            insert into ucp_challans(ucp_chalan_id, reg_no, reg_type, ref_no, program, challan_no, name, term,
                                ax_billing_cycle, ax_sem_code, ax_session_code, ax_admin_year, legal_entity, faculty, dept,
                                frm_session, to_session, academic_year, city, cluster_code,
                                tution_fee, due_fee, admission_fee, perv_paid, payable_fee, discount_type, discount_tuitionfee, discount_adminfee,
                                total_payable, hostel_fee, hostel_security, installment_detail, installment_no, remaining_fee, total_fine, payable_fine, tax,
                                bank_name, due_date, expiry_date, paid_date, next_inst_ddate, print_date, bank_account, bank_ledger_code, total_amt_wtax,
                                ax_business_line, ax_business_unit, generationdate, transport_fee, misc_fee, librarycard_fee, graduation_fee, prospectus_fee,
                                entry_Test_fee, sports_fee, degree_fee, push_status, is_validated, prog, term_abbrev, faculty_txt, batchno,
                                err, recreational_trip)
                                values(?,?,?,?,?,?,?,?,
                                    ?,?,?,?,?,?,?,?,?,?,
                                    ?,?,?,?,?,?,?,?,?,?,
                                    ?,?,?,?,?,?,?,?,?,?,
                                    ?,?,?,?,?,?,?,?,?,?,
                                    ?,?,?,?,?,?,?,?,?,?,
                                    ?,?,?,?,?,?,?
                                )  """, # RETURNING id
                                float(rec.id + 300000),  # ucp_challan_id,  # float(invoice_id.id),  # ucp_challan_id
                                student_id.code,  # reg_no
                                'NULL',  # reg_type
                                ref_no,  # ref_no
                                student_id.program_id and student_id.program_id.integration_code or '',  # program
                                float(rec.name),  # challan_no
                                student_id.name,  # name

                                invoice_term.code,  # term,

                                invoice_term.ax_billing_cycle,  # ax_billing_cycle
                                invoice_term.ax_sem_code,  # ax_sem_code
                                invoice_term.ax_session_code,  # ax_session_code
                                invoice_term.ax_academic_year,  # ax_admin_year
                                company.code,  # legal_entity
                                student_id.institute_id.integration_code,  # faculty
                                (student_id.department_id.integration_code and student_id.department_id.integration_code) or (student_id.institute_id.code and student_id.institute_id.code) or 'NULL',  # dept

                                term_line and term_line.date_start or '',  # frm_session
                                term_line and term_line.date_end or '',  # to_session
                                invoice_term.ax_academic_year,  # academic_year
                                'NULL',  # city
                                'NULL',  # cluster_code

                                round(gross_tuition_fee),  # tution_fee
                                # round((tuition_fee2 / (100 - rec.invoice_id.waiver_percentage or 1)) * 100),  # tution_fee
                                rec.gross_amount,   # due_fee   rec.due_fee
                                rec.admission_fee,  # admission_fee
                                rec.paid_amount,  # perv_paid rec.prev_paid
                                total_payable,  # payable_fee  rec.payable
                                rec.discount_types,  # discount_type
                                rec.waiver_percentage,  # discount_tuitionfee rec.tuition_fee_discount
                                0,  # discount_adminfee        rec.admission_fee_discount

                                total_payable, # total_payable  rec.total_payable
                                rec.hostel_fee,  # hostel_fee
                                rec.hostel_security,  # hostel_security
                                rec.label_id.name,   # installment_detail  rec.get_installment_no(),
                                'NULL',  # installment_no rec.invoice_id.installment_no and rec.invoice_id.installment_no or ,
                                rec.invoice_remaining_amount,  # remaining_fee  rec.get_remaining_fee(),
                                rec.fine_amount,  # total_fine
                                rec.fine_amount,  # payable_fine
                                rec.tax_amount,  # tax

                                bank_name,  # bank_name
                                rec.date_due,  # due_date
                                rec.date_expiry,  # expiry_date
                                rec.date_payment,  # paid_date
                                rec.invoice_remaining_due_date and rec.invoice_remaining_due_date.strftime('%d-%b-%Y') or '', # next_inst_ddate  rec.get_next_installment_date(),
                                rec.date_download,  # print_date
                                bank_acc,  # bank_account
                                bank_ledger_code,  # bank_ledger_code
                                total_payable,  # total_amt_wtax

                                0,  # ax_business_line
                                company.business_unit,  # ax_business_unit
                                rec.date_payment,  # generationdate
                                rec.transport_fee,  # transport_fee
                                rec.misc_fee,  # misc_fee
                                rec.library_card_fee,  # librarycard_fee
                                rec.graduation_fee,  # graduation_fee
                                rec.prospectus_fee,  # prospectus_fee

                                rec.entry_test_fee,  # entry_Test_fee
                                rec.sports_fee,  # sports_fee
                                rec.degree_fee,  # degree_fee
                                'NEW',  # push_status
                                'NULL',  # is_validated
                                student_id.program_id and student_id.program_id.code or '',  # prog
                                invoice_term.code,  # term_abbrev
                                student_id.institute_id.name,  # faculty_txt
                                fields.Date.today().strftime("%m%d%Y"),  # batchno

                                '',  # err
                                0  # recreational_trip
                            )


                        rec.sudo().write({
                            'sql_id': str(rec.id + 300000),  #sql_id, #
                            'sync_challan': False,
                            'synced_challan': True,
                            'date_sync': fields.Date.today(),
                        })
                        cursor.commit()
                        self.env.cr.commit()

                cursor.close()
                cnxn.close()

        except Exception as e:
            _logger.error(
                "*** Fee Sync Cron Job Failed: %s",
                str(e),
                exc_info=True   # this adds the full traceback
            )
        
            subject = f"{self.env.company.name} Fee Sync Cron Job Failed"
            main_content = {
                'subject': subject,
                'author_id': self.env.user.partner_id.id,
                'body_html': f"""
                    <p><b>{self.env.company.name} Fee Sync Cron Job Failed</b></p>
                    <p>Error: {str(e)}</p>
                """,
                'email_to': 'sarfraz@aarsol.com',
            }
            mail_id = self.env['mail.mail'].sudo().create(main_content)
            mail_id.send()

class OdooCMSFeePayment(models.Model):
    _inherit = 'odoocms.fee.payment'

    # This Method is used for Payment creation in the 1LINK
    @api.model
    def create_1link_payment(self, date, consumer_no, amount, journal_id):
        new_rec = False
        if date and consumer_no:
            register_id = self.env['odoocms.fee.payment.register'].sudo().search([('date', '=', date), ('journal_id', '=', journal_id)])
            if not register_id:
                register_values = {
                    'date': date,
                }
                register_id = self.env['odoocms.fee.payment.register'].sudo().create(register_values)

            if register_id.state == 'Draft':
                invoice_id = self.env['account.move'].search([('old_challan_no', '=', consumer_no), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
                already_exist = self.env['odoocms.fee.payment'].sudo().search([('receipt_number', '=', consumer_no), ('invoice_id.amount_residual', '=', 0.0)])
                if not already_exist:
                    already_exist = self.env['account.move'].search([('old_challan_no', '=', consumer_no), ('move_type', '=', 'out_invoice'), ('amount_residual', '=', 0.0)])
                if not already_exist:
                    fee_payment_rec_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', consumer_no)], order='id', limit=1)
                    if fee_payment_rec_exist:
                        if fee_payment_rec_exist.received_amount >= fee_payment_rec_exist.amount:
                            already_exist = fee_payment_rec_exist

                if not already_exist:
                    already_exist = self.env['odoocms.fee.payment'].search([('invoice_id', '=', invoice_id.id), ('payment_register_id', '=', register_id.id), ('invoice_id.amount_residual', '>', 0.0), ], order='id', limit=1)

                # Create the Record in the Fee Payment Receipts
                if invoice_id and not already_exist:
                    values = {
                        'invoice_id': invoice_id.id,
                        'receipt_number': consumer_no,
                        'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
                        'invoice_status': invoice_id.payment_state and invoice_id.payment_state or '',
                        'amount': invoice_id.amount_residual,
                        'id_number': invoice_id.student_id.code and invoice_id.student_id.code or '',
                        'term_id': invoice_id.term_id and invoice_id.term_id.id or False,
                        'journal_id': journal_id,
                        'date': date,
                        'payment_register_id': register_id.id,
                        'received_amount': invoice_id.amount_residual,
                    }
                    new_rec = self.env['odoocms.fee.payment'].sudo().create(values)

                # Already Exist But Payment Register is not Set
                if already_exist and already_exist._table == 'odoocms_fee_payment' and not already_exist.payment_register_id:
                    for already_exist_id in already_exist:
                        already_exist_id.payment_register_id = register_id._origin.id

                # Already Exit And Payment Register is also Set
                if already_exist and already_exist._table == 'odoocms_fee_payment' and already_exist.payment_register_id:
                    for already_exist_id in already_exist:
                        # Create Records in the Processed Receipts
                        notes = "Already Processed in " + (already_exist_id.payment_register_id.name and already_exist_id.payment_register_id.name or '') + " on " + already_exist_id.date.strftime("%d/%m/%Y")
                        processed_values = {
                            'barcode': consumer_no,
                            'name': consumer_no,
                            'payment_register_id': register_id.id,
                            'notes': notes,
                        }
                        self.env['odoocms.fee.processed.receipts'].create(processed_values)

                # If invoice_id is not found then create in the Non Barcode Receipts
                if not invoice_id and not already_exist:
                    non_barcode_exit = self.env['odoocms.fee.non.barcode.receipts'].search([('barcode', '=', self.barcode)])
                    if not non_barcode_exit:
                        non_barcode_vals = {
                            'barcode': consumer_no,
                            'name': consumer_no,
                            'payment_register_id': register_id.id,
                        }
                        self.env['odoocms.fee.non.barcode.receipts'].create(non_barcode_vals)
        return new_rec

    # def fee_payment_record(self, invoice_id, consumer_no, journal_id, date):
    #     # ***** Check if Any Previous Entry Not Post then Please Post it *****#
    #     prev_date_draft_payment_registers = self.env['odoocms.fee.payment.register'].sudo().search([('journal_id', '=', journal_id.id),
    #                                                                                                 ('state', '=', 'Draft'),
    #                                                                                                 ('date', '<', fields.Date.today())])
    #     if prev_date_draft_payment_registers:
    #         for prev_date_draft_payment_register in prev_date_draft_payment_registers:
    #             if all([line.state == 'done' for line in prev_date_draft_payment_register.fee_payment_ids]):
    #                 prev_date_draft_payment_register.state = 'Posted'
    #
    #     # ***** Payment Register *****#
    #     payment_register_id = self.env['odoocms.fee.payment.register']
    #     if journal_id:
    #         payment_register_id = self.env['odoocms.fee.payment.register'].search([('date', '=', date),
    #                                                                                ('journal_id', '=', journal_id.id),
    #                                                                                ('state', '=', 'Draft')])
    #         if not payment_register_id:
    #             register_values = {'date': date, 'journal_id': journal_id and journal_id.id or False}
    #             payment_register_id = self.env['odoocms.fee.payment.register'].create(register_values)
    #
    #     # ****** Create the Record in the Fee Payment Receipts *****#
    #     if invoice_id:
    #         values = {
    #             'invoice_id': invoice_id.id,
    #             'receipt_number': consumer_no,
    #             'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
    #             'invoice_status': invoice_id.payment_state and invoice_id.payment_state or '',
    #             'amount': invoice_id.amount_residual,
    #             'term_id': invoice_id.term_id and invoice_id.term_id.id or False,
    #             'journal_id': journal_id and journal_id.id or False,
    #             'date': date,
    #             'received_amount': invoice_id.amount_residual,
    #             'payment_register_id': payment_register_id and payment_register_id.id or False,
    #         }
    #         new_rec = self.env['odoocms.fee.payment'].create(values)
    #         return new_rec

    # def action_post_fee_payment(self):
    #     for rec in self:
    #         invoice = rec.invoice_id
    #         to_reconcile = invoice.line_ids._origin
    #         invoice_ids2 = invoice
    #         due_date = invoice.invoice_date_due
    #         date_invoice = rec.date
    #         payment_date = fields.Date.from_string(rec.date)
    #         invoice.payment_date = rec.date
    #         days = (payment_date - due_date).days
    #
    #         partner_id = invoice.student_id and invoice.student_id.partner_id or False
    #         destination_account_id = self.env['account.account'].search([('company_id','=',invoice.company_id.id),('user_type_id.name', '=', 'Receivable')], order='id asc', limit=1)
    #         data = {
    #             'payment_type': 'inbound',
    #             'payment_method_id': 1,
    #             'partner_type': 'customer',
    #             'company_id': invoice.company_id.id,
    #             'currency_id': invoice.journal_id.company_id.currency_id.id,
    #             'partner_id': partner_id and partner_id.id or False,
    #             'payment_date': rec.date,
    #             'date': rec.date,
    #             'ref': rec.receipt_number,
    #             'amount': rec.received_amount,
    #             'journal_id': rec.journal_id.id,
    #             'donor_id': invoice.donor_id and invoice.donor_id.id or False,
    #             'partner_bank_id': False,
    #             'destination_account_id': destination_account_id and destination_account_id.id or False,
    #         }
    #
    #         # _logger.warn("PAYMENT: %s" % (data,))
    #         payment_vals_list = [data]
    #         new_payment_recs = self.env['account.payment'].create(payment_vals_list)
    #         new_payment_recs.action_post()
    #         rec.name = new_payment_recs.name
    #         domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
    #         to_reconcile2 = to_reconcile.filtered_domain([('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)])
    #         for new_payment_rec, lines in zip(new_payment_recs, to_reconcile2):
    #             if new_payment_rec.state != 'posted':
    #                 continue
    #             payment_lines = new_payment_rec.line_ids.filtered_domain(domain)
    #             for account in payment_lines.account_id:
    #                 (payment_lines + lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()
    #
    #         # invoice.payment_id = new_payment_rec.id
    #         invoice_ids2.payment_date = rec.date
    #
    #         rec.state = 'done'
    #         rec.processed = True
    #         invoice.write({'confirmation_date': fields.Date.today(), 'paid_bank_name': rec.journal_id.bank_id.name})
    #
    #         # Approve Registration
    #         fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
    #         fee_charge_term_rec = self.env['odoocms.academic.term'].browse(fee_charge_term)
    #
    #         registration_id = invoice.registration_id
    #         if not registration_id:
    #             registration_id = self.env['odoocms.course.registration'].sudo().search([('student_id', '=', invoice.student_id.id),
    #                                                                                      ('term_id', '=', fee_charge_term_rec.id),
    #                                                                                      ('state', '!=', 'approved')], order='id desc', limit=1)
    #         if registration_id:
    #             registration_id.sudo().action_approve()
    #
    #         # ***** if it is prospectus challan *****#
    #         if invoice.application_id and invoice.challan_type == 'prospectus_challan' and not invoice.application_id.fee_voucher_state == 'verify':
    #             invoice.application_id.sudo().verify_voucher()
    #             # invoice.application_id.sudo().write({
    #             #     'voucher_date': invoice.payment_date or rec.date or fields.Date.today(),
    #             #     'voucher_verified_date': fields.Date.today(),
    #             #     'fee_voucher_state': 'verify'
    #             # })
    #
    #         # ***** For Admission Invoices/Vouchers *****#
    #         if invoice.is_admission_fee:
    #             student = invoice.application_id.sudo().create_student()
    #             # rec.sudo().send_fee_receive_sms()
    #             if student:
    #                 rec.write({'student_id': student.id})
    #                 if not invoice.student_id:
    #                     invoice.write({'student_id': student.id})
    #                 if invoice.batch_id:
    #                     company_code = getattr(invoice.company_id, 'code', False)
    #                     if company_code:
    #                         if invoice.company_id.code == 'CUST':
    #                             reg_no = student.program_id.short_code + invoice.term_id.short_code + str(student.program_id.sequence_number).zfill(3)
    #                         else:
    #                             last_student = self.env['odoocms.student'].search([('program_id', '=', invoice.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
    #                             if last_student:
    #                                 last_student_code = last_student.code[-4:]
    #                                 if not program_sequence_number == int(last_student_code) + 1:
    #                                     program_sequence_number = int(last_student_code) + 1
    #                             reg_no = 'L1' + invoice.term_id.short_code + student.program_id.short_code + str(program_sequence_number).zfill(4)
    #                     else:
    #                         last_student = self.env['odoocms.student'].search([('program_id', '=', invoice.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
    #                         if last_student:
    #                             last_student_code = last_student.code[-4:]
    #                             if not program_sequence_number == int(last_student_code) + 1:
    #                                 program_sequence_number = int(last_student_code) + 1
    #                         reg_no = 'L1' + invoice.term_id.short_code + student.program_id.short_code + str(program_sequence_number).zfill(4)
    #
    #                     student.write({'code': reg_no, 'id_number': reg_no})
    #                     student.program_id.sequence_number = program_sequence_number + 1
    #                     student.write({'code': reg_no, 'id_number': reg_no})
    #
    #                 invoice.application_id.sudo().new_student_registration()
    #                 payment_ledger_recs = self.env['odoocms.student.ledger'].search([('invoice_id', '=', invoice.id), ('debit', '>', 0)])
    #                 if payment_ledger_recs:
    #                     payment_ledger_recs.write({'student_id': student.id, 'id_number': student.code})
    #                 invoice.application_id.admission_link_invoice_to_student()
    #
    #                 # Email And SMS
    #                 rec.sudo().send_fee_receive_sms(reg_no)
    #                 if invoice.company_id.code == 'UCP':
    #                     rec.send_fee_receive_email(student, reg_no)

    def send_fee_receive_sms(self, reg_no):
        for rec in self:
            company_name = self.env.company.name
            company_code = self.env.company.code
            if company_code == 'UCP':
                msg_txt = f'Dear Student,\nWelcome to the {company_name}. Please note that your Registration No. is: "{reg_no}". For further details, please check your email.'
            else:
                msg_txt = f'Dear Student,\nYour payment of the 1st installment of the semester fee is confirmed. Welcome to the {company_name}. We wish you a very pleasant and rewarding academic stay at {company_code}.\nThank you'
            updated_mobile_no = rec.invoice_id.application_id.mobile.replace('-', '')
            updated_mobile_no = updated_mobile_no.replace(' ', '')
            updated_mobile_no = updated_mobile_no.lstrip('0')
            message = self.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.fee.payment', rec.id)
            gateway_id = self.env['gateway_setup'].sudo().search([], order='id desc', limit=1)
            if gateway_id:
                if company_code == 'UCP':
                    rec.prepare_sms_cron_values(rec, updated_mobile_no, msg_txt, gateway_id)
                else:
                    self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, rec.id, 'odoocms.fee.payment', gateway_id, rec.receipt_number, 'login', 'student', False, False, False)

    def prepare_sms_cron_values(self, fee_payment_rec, updated_mobile_no, message, gateway_id):
        sms_data_values = {
            'model_id': 'odoocms.fee.payment',
            'res_id': fee_payment_rec.id,
            'mobile_no': updated_mobile_no,
            'message_id': message,
            'gateway_id': gateway_id.id,
            'send_to': fee_payment_rec.invoice_id.student_id.name,
            'sms_nature': 'other',
            'type': 'student',
            'department_id': False,
            'institute_id': False,
            'mobile_network': '',
        }
        self.env['send_sms.cron'].sudo().create(sms_data_values)

    def send_fee_receive_email(self, student, reg_no):
        email_template = self.env.ref('odoocms_admission_fee_ucp.registered_student_email_template').sudo()
        for rec in self:
            email_value = {
                'mail_to': student.email,
                'admission_mail': 'ucpadmissions@ucp.edu.pk',
                'student_name': student.name,
                "company_name": self.env.company.name,
                "student_reg_no": reg_no,
            }
            email_template.with_context(email_value).sudo().send_mail(rec.id, force_send=True)
