# -*- coding: utf-8 -*-
import logging
import pdb

from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class OdoocmsFeeSyncPool(models.Model):
    _name = "odoocms.fee.sync.pool"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Fee Sync Pool"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    student_code = fields.Char(related='student_id.code', string='Registration', store=True)
    invoice_id = fields.Many2one('account.move', 'Challan', tracking=True, ondelete='cascade', index=True)
    invoice_state = fields.Selection(related='invoice_id.payment_state', string="Challan Status", store=True)
    challan_type = fields.Selection(related='invoice_id.challan_type', string="Challan Type", store=True)
    institute_id = fields.Many2one('odoocms.institute', related='invoice_id.institute_id', string="Faculty", store=True)
    date = fields.Date('SQL Create/Update Date')
    action = fields.Selection([('create', 'Create'),
                               ('update', 'Update'),
                               ], string='Action')
    sql_id = fields.Char('SQL ID')
    company_id = fields.Many2one('res.company', 'Company')
    to_be = fields.Boolean('To Be', default=True)
    status = fields.Selection([('new', 'New'),
                               ('success', 'Successfully Processed'),
                               ('error', 'Error'),
                               ('other', 'Other')], string='Status', default='new')
    skip_from_pushing = fields.Boolean('Skip From Pushing', default=False, tracking=True)
    description = fields.Char('Description')

    challan_term = fields.Many2one('odoocms.academic.term', 'Challan Term')
    tuition_fee = fields.Float('Tuition Fee')
    admission_fee = fields.Float('Admission Fee')
    prev_paid = fields.Float('Prev Paid')
    due_fee = fields.Float('Due Fee')
    payable = fields.Float('Payable')
    discount_types = fields.Char('Discounts')
    tuition_fee_discount = fields.Float('Tuition Fee Discount')
    admission_fee_discount = fields.Float('Admission Fee Discount')
    total_payable = fields.Float('Total Payable')
    hostel_fee = fields.Float('Hostel Fee')
    hostel_security = fields.Float('Hostel Security')
    total_fine = fields.Float('Total Fine')
    tax = fields.Float('Tax Amount')

    transport_fee = fields.Float('Transport Fee')
    misc_fee = fields.Float('Misc Fee')
    library_card_fee = fields.Float('Library Fee')
    graduation_fee = fields.Float('Graduation Fee')
    prospectus_fee = fields.Float('Prospectus Fee')
    entry_test_fee = fields.Float('Entry Test Fee')
    sports_fee = fields.Float('Sports Fee')
    degree_fee = fields.Float('Degree Fee')
    summary_id = fields.Many2one('odoocms.sync.challan.summary', 'Summary Detail')

    @api.model
    def create(self, vals):
        res = super().create(vals)
        if not res.name:
            res.name = self.env['ir.sequence'].next_by_code('odoocms.fee.sync.pool')
        return res

    def unlink(self):
        for rec in self:
            if len(rec.sql_id) > 0:
                raise ValidationError(_('Slip %s Already Pushed to Server') % rec.invoice_id.name)
        return super(OdoocmsFeeSyncPool, self).unlink()

    @api.model
    def cron_payslip_sync_pool(self, company_id=2, nlimit=500):
        # create connection
        connector_rec = self.env['odoo.fee.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            recs = self.env['odoocms.fee.sync.pool'].search([('company_id','=',company_id), ('to_be', '=', True)], limit=nlimit)
            for rec in recs:
                _logger.info('*** Challan %s-%s is being processed' % (rec.invoice_id.id, rec.invoice_id.old_challan_no))
                if rec.action == "create":
                    invoice_id = rec.invoice_id
                    bank_acc = ''
                    bank_ledger_code = ''
                    bank_name = ''
                    student_id = rec.invoice_id.student_id and rec.invoice_id.student_id or False
                    application_id = rec.invoice_id.application_id and rec.invoice_id.application_id or False
                    if invoice_id and invoice_id.payment_date:
                        # ref_no = student_id.application_id and student_id.application.name or ''
                        ref_no = ''
                        invoice_term = invoice_id and invoice_id.term_id or False
                        company = invoice_id.company_id and invoice_id.company_id or self.env.company
                        term_line = invoice_id.term_id.term_lines and invoice_id.term_id.term_lines[0] or False
                        payment_bank = rec.get_payment_bank()
                        if payment_bank:
                            bank_acc = payment_bank.journal_id.bank_account_id.bank_account_code and payment_bank.journal_id.bank_account_id.bank_account_code or ''
                            bank_ledger_code = payment_bank.journal_id.bank_account_id.bank_ledger_code and payment_bank.journal_id.bank_account_id.bank_ledger_code or ''
                            bank_name = payment_bank.journal_id.name
                            if payment_bank.journal_id.bank_id.street:
                                bank_name = bank_name + " " + payment_bank.journal_id.bank_id.street
                        tuition_fee2 = (rec.payable - rec.admission_fee - rec.hostel_fee - rec.hostel_security - rec.total_fine - rec.tax - rec.transport_fee - rec.misc_fee -
                                        rec.library_card_fee - rec.graduation_fee - rec.prospectus_fee - rec.entry_test_fee - rec.sports_fee - rec.degree_fee)

                        sql = """
                            insert into ucp_challans(
                              ucp_chalan_id, reg_no, reg_type, ref_no, program,
                              challan_no, name, cgpa, gpa, term,                                                
                              ax_billing_cycle, ax_sem_code, ax_session_code, ax_admin_year, legal_entity,
                              faculty, dept, frm_session, to_session, academic_year,                                                
                              city, cluster_code, tution_fee, due_fee, admission_fee,
                              perv_paid, payable_fee, discount_type, discount_tuitionfee, discount_adminfee,
                              total_payable, hostel_fee, hostel_security, installment_detail, installment_no,
                              remaining_fee, total_fine, payable_fine, tax, bank_name,                                                
                              due_date, expiry_date, paid_date, next_inst_ddate, print_date,
                              bank_account, bank_ledger_code, total_amt_wtax, ax_business_line, ax_business_unit,                                                
                              generationdate, transport_fee, misc_fee, librarycard_fee, graduation_fee,
                              prospectus_fee, entry_Test_fee, sports_fee, degree_fee, push_status,                                                
                              is_validated, prog, term_abbrev, faculty_txt, batchno,
                              err, recreational_trip) values(
                                    {},'{}',NULL,NULL,'{}',
                                    {},'{}',{},{},'{}',
                                    '{}','{}','{}','{}','{}',                                    
                                    NULL,NULL,NULL,NULL,'{}',                                    
                                    NULL,NULL,{},{},{},                                    
                                    {},{},NULL,{},{},                                    
                                    {},{},{},NULL,NULL,
                                    {},{},{},{},'{}',                                    
                                    '{}','{}','{}',NULL,NULL,                                    
                                    NULL,NULL,{},0,{},
                                    '{}',{},{},{},{},                                    
                                    {},{},{},{},'NEW',                                    
                                    NULL,'{}','{}','{}',{},
                                    NULL,0
                                )
                        """.format(
                            (float(rec.id + 2120000)),
                            (student_id and student_id.code) or (application_id and application_id.application_no) or '',
                            (student_id and student_id.program_id.integration_code) or (application_id.prefered_program_id and application_id.prefered_program_id.integration_code) or '',

                            float(invoice_id.old_challan_no),
                            (student_id and student_id.name) or (application_id and application_id.name) or '',
                             0,
                             0,
                             invoice_term and invoice_term.code,

                             invoice_term.ax_billing_cycle,
                             invoice_term.ax_sem_code,
                             invoice_term.ax_session_code,
                             invoice_term.ax_academic_year,
                             company.code,

                             invoice_term.ax_academic_year,

                             round((tuition_fee2 / (100 - rec.invoice_id.waiver_percentage or 1)) * 100),
                             rec.due_fee,
                             rec.admission_fee,

                             rec.prev_paid,
                             rec.payable,
                             rec.tuition_fee_discount,
                             rec.admission_fee_discount,

                             rec.total_payable,
                             rec.hostel_fee,
                             rec.hostel_security,


                             rec.get_remaining_fee(),
                             rec.total_fine,
                             rec.total_fine,
                             rec.tax,
                             bank_name,

                             invoice_id.invoice_date_due,
                             invoice_id.invoice_date_due,
                             invoice_id.payment_date,


                             rec.total_payable,
                             company.business_unit,

                             invoice_id.payment_date,
                             rec.transport_fee,
                             rec.misc_fee,
                             rec.library_card_fee,
                             rec.graduation_fee,

                             rec.prospectus_fee,
                             rec.entry_test_fee,
                             rec.sports_fee,
                             rec.degree_fee,

                             (student_id and student_id.program_id and student_id.program_id.code) or (application_id.prefered_program_id and application_id.prefered_program_id.code) or '',
                             invoice_term.code,
                             (student_id and student_id.institute_id.name) or (application_id and application_id.prefered_program_id.institute_id.name) or '',
                             fields.Date.today().strftime("%m%d%Y")
                        )

                        _logger.warning(sql)
                        cursor.execute(sql)
                        cursor.commit()

                        rec.sudo().write({
                            'sql_id': str(rec.id + 120000),
                            'status': 'success',
                            'date': fields.Date.today(),
                            'to_be': False
                        })

            cursor.close()
            cnxn.close()

    @api.model
    def cron_invoice_sync_unlink(self, challan_no):
        connector_rec = self.env['odoo.fee.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            cursor.execute("delete from ucp_challans where challan_no=?", challan_no)
            cursor.commit()
            cursor.close()
            cnxn.close()

    @api.model
    def cron_invoice_sync_unlink2(self, code):
        connector_rec = self.env['odoo.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            cursor.execute("delete from emp_salary where emp_code=?", float(code))
            cursor.commit()
            cursor.close()
            cnxn.close()

    @api.model
    def get_challan_by_reg_no(self, reg_no):
        connector_rec = self.env['odoo.fee.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            cursor.execute("SELECT *from ucp_challans where reg_no=?", reg_no)
            results = cursor.fetchall()
            print("Printing Result ....\n")
            for result in results:
                col_list = ['UCP_CHALAN_ID', 'Reg_No', 'Reg_Type', 'Ref_No', 'Program', 'Challan_no', 'Name', 'CGPA', 'GPA', 'Term',
                            'AX_BILLING_CYCLE', 'AX_SEM_CODE', 'AX_SESSION_CODE', 'AX_ADMIN_YEAR', 'Legal_Entity', 'Faculty', 'Dept', 'FRM_Session', 'TO_SESSION', 'Academic_Year',
                            'City', 'Cluster_Code', 'Tution_Fee', 'Due_Fee', 'Admission_Fee', 'Perv_Paid', 'Payable_Fee', 'Discount_Type', 'Discount_TuitionFee', 'Discount_AdminFee',
                            'Total_Payable', 'Hostel_Fee', 'Hostel_Security', 'Installment_Detail', 'Installment_No', 'Remaining_Fee', 'Total_Fine', 'Payable_Fine', 'Tax', 'Bank_Name',
                            'Due_Date', 'Expiry_Date', 'Paid_Date', 'Next_Inst_DDate', 'Print_Date', 'Bank_Account', 'Bank_Ledger_Code', 'Total_Amt_WTax', 'AX_BUSINESS_LINE', 'AX_BUSINESS_UNIT',
                            'GenerationDate', 'Transport_Fee', 'Misc_Fee', 'LibraryCard_Fee', 'Graduation_Fee', 'Prospectus_Fee', 'Entry_Test_Fee', 'Sports_Fee', 'Degree_Fee', 'PUSH_STATUS',
                            'IS_VALIDATED', 'PROG', 'term_abbrev', 'faculty_txt', 'BATCHNO', 'ERR', 'Recreational_Trip']

                for i in range(len(col_list)):
                    print(col_list[i], result[i], "\n")
                # print(results)
                print("Printing Result End....\n")
            cursor.close()
            cnxn.close()

    @api.model
    def get_challan_by_date(self, date):
        connector_rec = self.env['odoo.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            # cursor.execute("SELECT *from emp_salary where CAST(sal_month AS Date )>=?", date)
            # cursor.execute("SELECT *from emp_salary where CAST(sal_month AS Date )=?", date)
            cursor.execute("""SELECT sal_month,
                                emp_code,
                                payment_mode,
                                legal_entity,
                                ax_campus_code,
                                ax_legal_entity_code,
                                ax_business_unit,
                                dept_code,
                                ax_bank_code,
                                pay_rate,
                                adv,
                                pf_adv,
                                mob_bill,
                                tax_sal,
                                pol,
                                other_ded,
                                eobi,
                                emp_pf_amt,
                                emplyr_pf_amt,
                                gli,
                                arrears,
                                professional_tax,
                                trans_ref,
                                trans_nbr,
                                trans_type,
                                net_sal_amt,
                                add_dty_amt,
                                gross_sal_amt,
                                net_gross_salary,

                                teaching_staff_nme,
                                push_date,
                                push_status,
                                bnft1,
                                bnft2,
                                bnft3,
                                deduct1,
                                deduct2,
                                deduct3,
                                car_adv from emp_salary where CAST(sal_month AS Date )=?""", date)
            results = cursor.fetchall()
            print("Printing Result ....\n")
            for result in results:
                col_list = ['sal_month', 'emp_code', 'payment_mode', 'legal_entity', 'ax_campus_code', 'ax_legal_entity_code', 'ax_business_unit',
                            'dept_code', 'ax_bank_code', 'pay_rate', 'adv', 'pf_adv', 'mob_bill', 'tax_sal', 'pol', 'other_ded', 'eobi', 'emp_pf_amt', 'emplyr_pf_amt',
                            'gli', 'arrears', 'professional_tax', 'trans_ref', 'trans_nbr', 'trans_type', 'net_sal_amt', 'add_dty_amt', 'gross_sal_amt', 'net_gross_salary',
                            'teaching_staff_nme', 'push_date', 'push_status', 'bnft1', 'bnft2', 'bnft3', 'deduct1', 'deduct2', 'deduct3', 'car_adv']
                for i in range(len(col_list)):
                    print(col_list[i], "---->", result[i], "\n")
            print("Printing Result End....\n")
            cursor.close()
            cnxn.close()

    @api.model
    def get_challan_by_code(self, code):
        connector_rec = self.env['odoo.fee.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            cursor.execute("SELECT *from emp_salary where emp_code=?", float(code))
            result = cursor.fetchall()
            print("Printing Result ....\n")
            print(result)
            cursor.close()
            cnxn.close()

    @api.model
    def get_challan_by_field_values(self, reg_no):
        connector_rec = self.env['odoo.fee.sql.connector'].search([], order='id desc', limit=1)
        if connector_rec:
            cnxn, cursor = connector_rec.sudo().action_establish_connection()
            # cursor.execute("SELECT * from ucp_challans where reg_no=? ", reg_no)
            cursor.execute("SELECT *FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = N'ucp_challans'")
            result = cursor.fetchall()
            print("Printing Result ....\n")
            print(result)
            cursor.close()
            cnxn.close()

    def action_skip_from_pushing(self):
        for rec in self:
            flag = False
            if not flag and not rec.skip_from_pushing:
                rec.skip_from_pushing = True
                flag = True
            if not flag and rec.skip_from_pushing:
                rec.skip_from_pushing = False

    def get_installment_no(self):
        if self.invoice_id.challan_type == 'main_challan':
            return 'First Installment'
        if self.invoice_id.challan_type == '2nd_challan':
            return 'Second Installment'

    def get_remaining_fee(self):
        if self.invoice_id.forward_invoice and self.invoice_id.forward_invoice.payment_state not in ('paid', 'in_payment'):
            return self.invoice_id.forward_invoice.amount_total
        else:
            return 0

    def get_next_installment_date(self):
        if self.invoice_id.forward_invoice and self.invoice_id.forward_invoice.payment_state not in ('paid', 'in_payment'):
            return self.invoice_id.forward_invoice.invoice_date_due
        else:
            return ''

    def get_payment_bank(self):
        payment_rec = self.env['odoocms.fee.payment'].search([('invoice_id', '=', self.invoice_id.id)], limit=1)
        if payment_rec:
            return payment_rec
        return False
