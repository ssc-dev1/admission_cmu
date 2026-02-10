# -*- coding: utf-8 -*-
import time
import tempfile
import binascii
import xlrd
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, DEFAULT_SERVER_DATE_FORMAT
from datetime import date, datetime
from odoo.exceptions import Warning
from odoo import models, fields, exceptions, api, _

import logging

_logger = logging.getLogger(__name__)
from odoo.exceptions import UserError, ValidationError

try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


# if row[7].ctype == 3:  # Date
# if row[7]:
#     date_value = xlrd.xldate_as_tuple(row[7], workbook.datemode)
#     grade_date = date(*date_value[:3]).strftime('%Y-%m-%d')
#     registration.grade_date = grade_date


class FeeDataImportWizard(models.TransientModel):
    _name = "fee.data.import.wizard"
    _description = 'Fee Data Import Wizard'

    file = fields.Binary('File')

    def action_import_fee_data(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        flag = 'Update'
        move_id = self.env['account.move']

        for row_num in range(1, sheet.nrows):
            _logger.info('Row---->of %s of %s' % (row_num, sheet.nrows))
            row = sheet.row_values(row_num)

            # ***** For PAID (Single Line Process) ******* #
            if flag == 'Paid':
                # Old Challan ID
                old_challan_no = str(row[8]).split('.')
                old_challan_no = old_challan_no[0]
                record_already_exists = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if record_already_exists:
                    continue

                # Student ID
                student_list = str(row[0]).split('.')
                student_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.student'), ('module', '=', 'cms'), ('name', '=', student_list[1])]).res_id
                student_id = self.env['odoocms.student'].browse(student_id)
                if not student_id:
                    raise UserError('Student ID REG No %s Not Found' % row[0])

                # Fee Structure
                fee_structure = self.env['odoocms.fee.structure'].search([('batch_id', '=', student_id.batch_id.id), ('session_id', '=', student_id.session_id.id), ('career_id', '=', student_id.career_id.id)])
                # if not fee_structure:
                #     raise UserError('No Fee Structure Found For Student REG %s' % row[0])

                # Program ID
                program_list = str(row[1]).split('.')
                program_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.program'), ('module', '=', 'cms'), ('name', '=', program_list[1])]).res_id

                # Session ID
                session_list = str(row[2]).split('.')
                session_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.academic.session'), ('module', '=', 'cms'), ('name', '=', session_list[1])]).res_id

                # Term ID
                term_list = str(row[3]).split('.')
                term_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.academic.term'), ('module', '=', 'cms'), ('name', '=', term_list[1])]).res_id

                # Semester ID
                semester_list = str(row[4]).split('.')
                semester_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.semester'), ('module', '=', 'cms'), ('name', '=', semester_list[1])]).res_id

                # Scholarship ID
                scholarship_list = str(row[5]).split('.')
                scholarship_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.fee.waiver'), ('module', '=', 'cms'), ('name', '=', scholarship_list[1])]).res_id
                if not scholarship_id:
                    scholarship_id = False

                # Invoice Date
                date_invoice = row[9]
                # Invoice Due Date
                date_due = row[10]
                # Invoice Paid Date
                paid_date = row[11]

                # Receipts
                receipts = [int(row[20])]
                registration_id = False
                lines = []

                # ***** Tuition Fee Line *****#
                tuition_amt = row[17] and float(row[17]) or 0.0
                if tuition_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', "Tuition Fee")])
                    tuition_line = {
                        'sequence': 10,
                        'price_unit': tuition_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': tuition_amt,
                    }
                    lines.append((0, 0, tuition_line))

                # ***** Admission Line *****#
                admission_amt = row[14] and float(row[14]) or 0.0
                if admission_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Admission Fee')])
                    admission_line = {
                        'sequence': 20,
                        'price_unit': admission_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': admission_amt,
                    }
                    lines.append((0, 0, admission_line))

                # *****Fine Line *****#
                fine_amt = row[13] and float(row[13]) or 0.0
                if fine_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Late Fine')])
                    fine_line = {
                        'sequence': 30,
                        'price_unit': fine_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': fine_amt,
                    }
                    lines.append((0, 0, fine_line))

                # ***** Tax Line *****#
                tax_amt = row[15] and float(row[15]) or 0.0
                if tax_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Withholding Tax')])
                    tax_line = {
                        'sequence': 40,
                        'price_unit': tax_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': tax_amt,
                    }
                    lines.append((0, 0, tax_line))

                # ***** DATA DICT Of Fee Receipt *****#
                data = {
                    'student_id': student_id.id,
                    'partner_id': student_id.partner_id.id,
                    'fee_structure_id': fee_structure and fee_structure.id or False,
                    'journal_id': 1,
                    'invoice_date': (date_invoice and date_invoice) or (date_due and date_due) or (paid_date and paid_date) or '',
                    'invoice_date_due': (date_due and date_due) or (paid_date and paid_date) or '',
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipt, None) for receipt in receipts],
                    'waiver_ids': [(4, scholarship_id, None)] if scholarship_id else [],
                    'waiver_amount': 0,
                    'term_id': term_id and term_id or False,
                    'semester_id': semester_id and semester_id or False,
                    'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                    'validity_date': paid_date and paid_date or '',
                    'registration_id': registration_id and registration_id.id or False,
                    'old_challan_no': old_challan_no,
                    'installment_no': row[18] and row[18] or '',
                    'payment_mode': row[21] and row[21].lower() or '',
                    'transaction_id': row[23] and row[23] or '',
                    'online_vendor': row[24] and row[24] or '',
                    'challan_type': row[25] and row[25] or '',
                    'old_challan_type': row[26] and row[26] or '',
                    # 'add_drop_no': row[27] and row[27] or '',
                    'reference': row[28] and row[28] or '',
                    'payment_date': paid_date and paid_date or '',
                    'narration': 'PAID',
                }
                if row[29] and row[29] == 'Y':
                    student_id.filer = True

                # Create Fee Receipt
                move_id = self.env['account.move'].sudo().create(data)

            ########################################################
            # ***** For Unpaid Challan (For Multiple Lines) ******#
            ######################################################
            mvl_lines = self.env['account.move.line']
            if flag == 'Unpaid':
                # To Create Main Record For Unpaid Invoices
                if not flag == 'Unpaid':
                    # Old Challan ID
                    old_challan_no = str(row[5]).split('.')
                    old_challan_no = old_challan_no[0]
                    # record_already_exists = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                    # if record_already_exists:
                    #     continue

                    # Student ID
                    student_list = str(row[0]).split('.')
                    student_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.student'), ('module', '=', 'cms'), ('name', '=', student_list[1])]).res_id
                    student_id = self.env['odoocms.student'].browse(student_id)
                    if not student_id:
                        raise UserError('Student ID REG No %s Not Found' % row[0])

                    # Fee Structure
                    fee_structure = self.env['odoocms.fee.structure'].search([('batch_id', '=', student_id.batch_id.id), ('session_id', '=', student_id.session_id.id), ('career_id', '=', student_id.career_id.id)])
                    # if not fee_structure:
                    #     raise UserError('No Fee Structure Found For Student REG %s' % row[0])

                    # Program ID
                    program_list = str(row[1]).split('.')
                    program_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.program'), ('module', '=', 'cms'), ('name', '=', program_list[1])]).res_id

                    # Session ID
                    session_list = str(row[2]).split('.')
                    session_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.academic.session'), ('module', '=', 'cms'), ('name', '=', session_list[1])]).res_id

                    # Term ID
                    term_list = str(row[3]).split('.')
                    term_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.academic.term'), ('module', '=', 'cms'), ('name', '=', term_list[1])]).res_id

                    # Semester ID
                    semester_id = False
                    if row[4]:
                        semester_list = str(row[4]).split('.')
                        semester_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.semester'), ('module', '=', 'cms'), ('name', '=', semester_list[1])]).res_id

                    # Scholarship ID
                    # scholarship_list = str(row[5]).split('.')
                    # scholarship_id = self.env['ir.model.data'].search([('model', '=', 'odoocms.fee.waiver'), ('module', '=', 'cms'), ('name', '=', scholarship_list[1])]).res_id
                    # if not scholarship_id:
                    #     scholarship_id = False

                    # Invoice Date
                    date_invoice = row[6]
                    # Invoice Due Date
                    date_due = row[7]

                    # Receipts
                    receipts = [int(row[9])]
                    registration_id = False
                    lines = []

                    # ***** DATA DICT Of Fee Receipt *****#
                    data = {
                        'student_id': student_id.id,
                        'partner_id': student_id.partner_id.id,
                        'fee_structure_id': fee_structure and fee_structure.id or False,
                        'journal_id': 1,
                        'invoice_date': (date_invoice and date_invoice) or (date_due and date_due) or '',
                        'invoice_date_due': (date_due and date_due) or '',
                        'state': 'draft',
                        'is_fee': True,
                        'is_cms': True,
                        'is_hostel_fee': False,
                        'move_type': 'out_invoice',
                        'invoice_line_ids': lines,
                        'receipt_type_ids': [(4, receipt, None) for receipt in receipts],
                        'waiver_ids': [],
                        'waiver_amount': 0,
                        'term_id': term_id and term_id or False,
                        'semester_id': semester_id and semester_id or False,
                        'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                        'validity_date': date_due and date_due or '',
                        'registration_id': registration_id and registration_id.id or False,
                        'old_challan_no': old_challan_no,
                        'installment_no': row[8] and row[8] or '',
                        'challan_type': row[10] and row[10] or '',
                        'old_challan_type': row[11] and row[11] or '',
                        'reference': row[12] and row[12] or '',
                        'narration': '2nd-Installment UNPAID',
                    }
                    if row[14] and row[14] == 'Y':
                        student_id.filer = True

                    # Create Fee Receipt
                    move_id = self.env['account.move'].sudo().create(data)
                    main_challan_old_no_list = str(row[13]).split('.')
                    main_challan_old_no = main_challan_old_no_list[0]
                    main_challan = self.env['account.move'].sudo().search([('old_challan_no', '=', main_challan_old_no)])
                    if main_challan:
                        move_id.write({'back_invoice': main_challan.id})
                        main_challan.write({'forward_invoice': move_id.id})

                if flag == 'Unpaid':
                    old_challan_no = str(row[0]).split('.')
                    old_challan_no = old_challan_no[0]
                    move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                    if move_id:
                        lines = []
                        mvl_lines = self.env['fee.lines.data.processing'].search([('name', '=', old_challan_no)], order="amount desc")
                        if mvl_lines:
                            seq = 10
                            for mvl_line in mvl_lines:
                                amt = mvl_line.amount
                                fee_head_id = self.env['odoocms.fee.head'].search([('id', '=', mvl_line.fee_head_id)])
                                fee_line = {
                                    'sequence': seq + 10,
                                    'price_unit': amt,
                                    'quantity': 1.00,
                                    'product_id': fee_head_id.product_id and fee_head_id.product_id.id or False,
                                    'name': mvl_line.course_name,
                                    'account_id': fee_head_id.property_account_income_id and fee_head_id.property_account_income_id.id or False,
                                    'fee_head_id': fee_head_id and fee_head_id.id or False,
                                    'exclude_from_invoice_tab': False,
                                    'course_gross_fee': amt,
                                    'course_credit_hours': mvl_line.credit_hours,
                                    'registration_type': mvl_line.registration_type,
                                    'add_drop_no': mvl_line.add_drop_no,
                                }
                                lines.append((0, 0, fee_line))
                            mvl_lines.write({'processed': True})
                            move_id.write({'invoice_line_ids': lines})
                            move_id.payment_state = 'not_paid'

            if flag == 'Status':
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if move_id:
                    lines = []
                    seq = 10
                    amt = float(row[1])
                    fee_head_id = self.env['odoocms.fee.head'].search([('id', '=', 49)])
                    fee_line = {
                        'sequence': seq + 10,
                        'price_unit': amt,
                        'quantity': 1.00,
                        'product_id': fee_head_id.product_id and fee_head_id.product_id.id or False,
                        'name': fee_head_id.name,
                        'account_id': fee_head_id.property_account_income_id and fee_head_id.property_account_income_id.id or False,
                        'fee_head_id': fee_head_id and fee_head_id.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': amt,
                        'course_credit_hours': 0,
                    }
                    lines.append((0, 0, fee_line))
                    move_id.write({'invoice_line_ids': lines, 'narration': 'UCP-2'})

            # ***** Create or Update Account Move Line *****#
            if flag == 'Update':
                # ***** Create Account Move Line With Zero *****#
                if not flag == 'Update':
                    old_challan_no = str(row[0]).split('.')
                    old_challan_no = old_challan_no[0]
                    move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                    if move_id:
                        fine_line = move_id.line_ids.filtered(lambda a: "Fine" in a.name)
                        if not fine_line:
                            fee_head_id = self.env['odoocms.fee.head'].search([('id', '=', 52)])
                            fee_line = {
                                'sequence': 100,
                                'price_unit': 0,
                                'quantity': 1.00,
                                'product_id': fee_head_id.product_id and fee_head_id.product_id.id or False,
                                'name': fee_head_id.name,
                                'account_id': 21,
                                'fee_head_id': fee_head_id and fee_head_id.id or False,
                                'exclude_from_invoice_tab': False,
                                'course_gross_fee': 0,
                                'course_credit_hours': 0,
                                'move_id': move_id.id,
                            }
                            self.env['account.move.line'].sudo().create(fee_line)

                        receivable_line = move_id.line_ids.filtered(lambda a: a.account_id.user_type_id.name == 'Receivable')
                        if not receivable_line:
                            fee_line = {
                                'sequence': 100,
                                'price_unit': 0,
                                'quantity': 1.00,
                                'name': move_id.name,
                                'account_id': 6,
                                'fee_head_id': False,
                                'exclude_from_invoice_tab': True,
                                'course_gross_fee': 0,
                                'course_credit_hours': 0,
                                'move_id': move_id.id,
                                'partner_id': move_id.student_id.partner_id and move_id.student_id.partner_id.id or False,
                                'date_maturity': move_id.invoice_date_due,
                            }
                            receivable_line = self.env['account.move.line'].sudo().create(fee_line)

                # ***** Update Existing Account Move Line *****#
                if flag == 'Update':
                    old_challan_no = str(row[0]).split('.')
                    old_challan_no = old_challan_no[0]
                    move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                    if move_id and move_id.line_ids:
                        fine_line = move_id.line_ids.filtered(lambda a: "Fine" in a.name)
                        receivable_line = move_id.line_ids.filtered(lambda a: a.account_id.id == 6)
                        amt = float(row[1])
                        if fine_line:
                            old_amt = fine_line.credit
                            credit_amt1 = amt
                            debit_amt = receivable_line.debit + amt - old_amt
                            self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s, course_gross_fee=%s where id=%s \n"
                                                , (credit_amt1, credit_amt1, -credit_amt1, -credit_amt1, credit_amt1, credit_amt1, credit_amt1, fine_line.id))

                            # ***** Receivable Line, it will Debit ***** #
                            self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                                , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                            # ***** Invoice Total Update *****#
                            self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                                , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, move_id.id))
                            self._cr.commit()


class FeeLinesDataProcessing(models.Model):
    _name = "fee.lines.data.processing"
    _description = "Fee Lines Data Processing"

    name = fields.Char('Old Challan No')
    course_name = fields.Char('Course Name')
    registration_type = fields.Char('Registration')
    add_drop_no = fields.Char('Add Drop No')
    fee_head_id = fields.Integer('Fee Head ID')
    credit_hours = fields.Integer('Credit Hours')
    amount = fields.Float('Amount')
    processed = fields.Boolean('Processed', default=False)
