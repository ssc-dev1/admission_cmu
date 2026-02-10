import pdb
from odoo import api, fields, models, tools, _
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
                            'date_sync': fields.Date.today(),
                        })
                    if not rec.payment_id and rec.amount_residual == 0:
                        rec.sudo().write({
                            'sql_id': '0098',  # sql_id, #
                            'sync_challan': False,
                            'synced_challan': True,
                            'date_sync': fields.Date.today(),
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
                            insert into ucp_challans(ucp_chalan_id, reg_no, reg_type, ref_no, program, challan_no, name, cgpa, gpa, term,
                                ax_billing_cycle, ax_sem_code, ax_session_code, ax_admin_year, legal_entity, faculty, dept,
                                frm_session, to_session, academic_year, city, cluster_code,
                                tution_fee, due_fee, admission_fee, perv_paid, payable_fee, discount_type, discount_tuitionfee, discount_adminfee,
                                total_payable, hostel_fee, hostel_security, installment_detail, installment_no, remaining_fee, total_fine, payable_fine, tax,
                                bank_name, due_date, expiry_date, paid_date, next_inst_ddate, print_date, bank_account, bank_ledger_code, total_amt_wtax,
                                ax_business_line, ax_business_unit, generationdate, transport_fee, misc_fee, librarycard_fee, graduation_fee, prospectus_fee,
                                entry_Test_fee, sports_fee, degree_fee, push_status, is_validated, prog, term_abbrev, faculty_txt, batchno,
                                err, recreational_trip)
                                values(?,?,?,?,?,?,?,?,?,?,
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
                                student_id.cgpa,  # cgpa,
                                student_id.get_student_sgpa(),  # sgpa,
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


