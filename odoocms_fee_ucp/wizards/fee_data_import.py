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
from io import StringIO
import io
from odoo.exceptions import UserError, ValidationError
import pdb

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
    _inherit = "fee.data.import.wizard"

    import_type = fields.Selection([('paid_challan', 'Paid Challan'),
                                    ('unpaid_header', 'Unpaid Header'),
                                    ('unpaid_lines', 'Unpaid Lines'),
                                    ('primary_clas', 'Assign Primary Clas'),
                                    ('library', 'Library Fine'),
                                    ('paid_challan_update', 'Paid Challan Update'),
                                    ], string='Import Type')
    company_code = fields.Selection([('cms', 'UCP'),
                                     ('cust', 'CUST'),
                                     ('maju', 'MAJU'),
                                     ], string='Company')

    def action_import_fee_data(self):
        fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
        fp.write(binascii.a2b_base64(self.file))
        fp.seek(0)
        workbook = xlrd.open_workbook(fp.name)
        sheet = workbook.sheet_by_index(0)
        flag = 'Paid*****'
        move_id = self.env['account.move']

        for row_num in range(1, sheet.nrows):
            _logger.warning('Row---->of %s of %s' % (row_num, sheet.nrows))
            row = sheet.row_values(row_num)

            # ***** For PAID (Single Line Process) ******* #
            if self.import_type == 'paid_challan':
                # header_info = {'0':'student_id','1':'program_id','2':'session_id','3':'term_list','4':'semester_id','5':'old_challan_no',
                #                 '6':'invoice_date','7':'invoice_due_date','8':'paid_date','9':'APF Line','10':'Attendance Line',
                #                 '11':'misc_amt','12':'admission_line','13':'Tax Line','14':'Tuition Line','15':'installment_no',
                #                 '16':'Late Fee Fine Amount','17':'Other Fine Amt','18':'scholarship_list','19':'waiver_percentage','20':'receipts_ids',
                #                 '21':'payment_mode':'22':'paid_bank_name','23':'transaction_id','24':'online_vendor','25':'challan_type',
                #                 '26':'old_challan_type','27':'add_drop_no','28':'misc_fee_head','29':'reference','30':'filer_no_filer','31':'prev_challan_no','32':'hostel_security_amt'}
                # Old Challan ID
                old_challan_no = str(row[5]).split('.')
                old_challan_no = old_challan_no[0]
                record_already_exists = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if record_already_exists:
                    continue

                # Student ID
                student_list = str(row[0]).split('.')
                student_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.student'),
                                                                      ('module', '=', self.company_code),
                                                                      ('name', '=', student_list[1])
                                                                      ]).res_id
                student_id = self.env['odoocms.student'].browse(student_id)
                if not student_id:
                    raise UserError('Student ID REG No %s Not Found' % row[0])

                # Fee Structure
                fee_structure = self.env['odoocms.fee.structure'].search([('batch_id', '=', student_id.batch_id.id),
                                                                          ('session_id', '=', student_id.session_id.id),
                                                                          ('career_id', '=', student_id.career_id.id)
                                                                          ])
                # if not fee_structure:
                #     raise UserError('No Fee Structure Found For Student REG %s' % row[0])

                # Program ID
                program_list = str(row[1]).split('.')
                program_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.program'),
                                                                      ('module', '=', self.company_code),
                                                                      ('name', '=', program_list[1])
                                                                      ]).res_id

                # Session ID
                # session_list = str(row[2]).split('.')
                # session_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.session'),
                #                                                ('module', '=', self.company_code),
                #                                                ('name', '=', session_list[1])
                #                                                ]).res_id
                session_id = int(row[2])

                # Term ID
                # term_list = str(row[3]).split('.')
                # term_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.term'),
                #                                             ('module', '=', self.company_code),
                #                                             ('name', '=', term_list[1])]).res_id
                # term_id = 193
                term_id = int(row[3])

                # Semester ID
                semester_list = str(row[4]).split('.')
                semester_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.semester'),
                                                                       ('module', '=', self.company_code),
                                                                       ('name', '=', semester_list[1])
                                                                       ]).res_id

                # Scholarship ID
                scholarship_id = False
                scholarship_list = row[18] and str(row[18]).split('.') or False
                if scholarship_list:
                    scholarship_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.fee.waiver'),
                                                                              ('module', '=', self.company_code),
                                                                              ('name', '=', scholarship_list[1])
                                                                              ]).res_id

                # Invoice Date
                date_invoice = row[6]
                # Invoice Due Date
                date_due = row[7]
                # Invoice Paid Date
                paid_date = row[8]

                # Receipts
                receipts = [int(row[20])]
                registration_id = False
                lines = []

                # ***** APF Line *****#
                apf_amt = row[9] and float(row[9]) or 0.0
                if apf_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Prospectus Fee')])
                    if not fee_head:
                        raise UserError('Prospectus Fee Fee Head Not Found.')
                    apf_line = {
                        'sequence': 50,
                        'price_unit': apf_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': apf_amt,
                    }
                    lines.append((0, 0, apf_line))

                # ***** Attendance Fine Line *****#
                fine_amt = row[10] and float(row[10]) or 0.0
                if fine_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Attendance Fine')])
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

                # ***** Misc Line *****#
                misc_amt = row[11] and float(row[11]) or 0.0
                if misc_amt > 0:
                    fee_head_list = str(row[28]).split('.')
                    fee_head_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.fee.head'),
                                                                           ('module', '=', self.company_code),
                                                                           ('name', '=', fee_head_list[1])
                                                                           ]).res_id
                    if not fee_head_id:
                        raise UserError('Fee Head Not Found.')
                    fee_head = self.env['odoocms.fee.head'].browse(fee_head_id)
                    misc_line = {
                        'sequence': 50,
                        'price_unit': misc_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': misc_amt,
                    }
                    lines.append((0, 0, misc_line))

                # ***** Admission Line *****#
                admission_amt = row[12] and float(row[12]) or 0.0
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

                # ***** Tax Line *****#
                tax_amt = row[13] and float(row[13]) or 0.0
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

                # ***** Tuition Fee Line *****#
                tuition_amt = row[14] and float(row[14]) or 0.0
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

                # ***** Late Fee Fine Line *****#
                late_fee_fine_amt = row[16] and float(row[16]) or 0.0
                if late_fee_fine_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Late Fee Fine')])
                    fine_line = {
                        'sequence': 30,
                        'price_unit': late_fee_fine_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': late_fee_fine_amt,
                    }
                    lines.append((0, 0, fine_line))

                # ***** Other Fine Line *****#
                other_fine_amt = row[17] and float(row[17]) or 0.0
                if other_fine_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Other Fine')])
                    fine_line = {
                        'sequence': 30,
                        'price_unit': other_fine_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': other_fine_amt,
                    }
                    lines.append((0, 0, fine_line))

                # ***** Hostel Security Line *****#
                hostel_security_amt = row[32] and float(row[32]) or 0.0
                if hostel_security_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Hostel Security')])
                    fine_line = {
                        'sequence': 40,
                        'price_unit': hostel_security_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': hostel_security_amt,
                    }
                    lines.append((0, 0, fine_line))

                # ***** DATA DICT Of Fee Receipt *****#
                data = {
                    'student_id': student_id.id,
                    'student_name': student_id.partner_id.name,
                    'partner_id': student_id.partner_id.id,
                    'fee_structure_id': fee_structure and fee_structure.id or False,
                    'journal_id': self.env['account.journal'].search([('name', '=', 'Customer Invoices')], order='id', limit=1).id,
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
                    'program_id': program_id,
                    'term_id': term_id and term_id or False,
                    'semester_id': semester_id and semester_id or False,
                    'career_id': student_id.career_id and student_id.career_id.id or False,
                    'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                    'discipline_id': student_id.discipline_id and student_id.discipline_id.id or False,
                    'campus_id': student_id.campus_id and student_id.campus_id.id or False,
                    'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                    'session_id': student_id.session_id and student_id.session_id.id or False,
                    'validity_date': paid_date and paid_date or '',
                    'first_installment': True,
                    'second_installment': False,
                    'registration_id': registration_id and registration_id.id or False,
                    'old_challan_no': old_challan_no,
                    'installment_no': row[15] and float(row[15]) or 0.0,
                    'waiver_percentage': row[19] and float(row[19]) or 0.0,
                    'payment_mode': row[21] and row[21].lower() or '',
                    'transaction_id': row[23] and row[23] or '',
                    'online_vendor': row[24] and row[24] or '',
                    'challan_type': row[25] and row[25] or '',
                    'old_challan_type': row[26] and row[26] or '',
                    'add_drop_no': row[27] and row[27] or '',
                    'reference': row[29] and row[29] or '',
                    'payment_date': paid_date and paid_date or '',
                    'prev_challan_no': row[31] and row[31] or '',
                    'narration': 'NEW-PAID'
                }
                if row[30] and row[30] == 'Yes':
                    student_id.filer = True

                # Create Fee Receipt
                move_id = self.env['account.move'].sudo().create(data)
                self.invoice_ledger_entry(move_id)
                self.paid_leger_entry(move_id)
                move_id.payment_state = 'paid'
                self._cr.commit()

            ########################################################
            # ***** For Unpaid Challan (For Multiple Lines) ******#
            ############################if self.import_type == 'paid_challan':##########################
            mvl_lines = self.env['account.move.line']
            if self.import_type == 'unpaid_header':
                # header_info = {'0': 'student_id', '1': 'program_id', '2': 'session_id', '3': 'term_list', '4': 'semester_id', '5': 'old_challan_no',
                #                '6': 'invoice_date', '7': 'invoice_due_date', '8': 'paid_date', '9': '-', '10': '-',
                #                '11': 'installment_no', '12': 'waiver_percentage', '13': 'Scholarship', '14': '-', '15': 'receipts_ids',
                #                '16': 'challan_type', '17': 'old_challan_type', '18': 'add_drop_no', '19': 'reference', '20': 'filer_non_filer'
                #                }

                # Old Challan ID
                old_challan_no = str(row[5]).split('.')
                old_challan_no = old_challan_no[0]
                record_already_exists = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if record_already_exists:
                    continue

                # Student ID
                student_list = str(row[0]).split('.')
                student_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.student'),
                                                                      ('module', '=', self.company_code),
                                                                      ('name', '=', student_list[1])
                                                                      ]).res_id
                student_id = self.env['odoocms.student'].browse(student_id)
                if not student_id:
                    raise UserError('Student ID REG No %s Not Found' % row[0])

                # Fee Structure
                fee_structure = self.env['odoocms.fee.structure'].sudo().search([('batch_id', '=', student_id.batch_id.id),
                                                                                 ('session_id', '=', student_id.session_id.id),
                                                                                 ('career_id', '=', student_id.career_id.id)
                                                                                 ])
                # if not fee_structure:
                #     raise UserError('No Fee Structure Found For Student REG %s' % row[0])

                # Program ID
                program_list = str(row[1]).split('.')
                program_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.program'),
                                                                      ('module', '=', self.company_code),
                                                                      ('name', '=', program_list[1])
                                                                      ]).res_id

                # Session ID
                # if row[2]:
                #     session_list = str(row[2]).split('.')
                #     session_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.session'),
                #                                                    ('module', '=', self.company_code),
                #                                                    ('name', '=', session_list[1])
                #                                                    ]).res_id
                # else:
                #     session_id = False

                session_id = int(row[2])

                # Term ID
                # term_list = str(row[3]).split('.')
                # term_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.term'),
                #                                             ('module', '=', self.company_code),
                #                                             ('name', '=', term_list[1])
                #                                             ]).res_id

                term_id = int(row[3])
                # term_id = 193

                # Semester ID
                semester_id = False
                if row[4]:
                    semester_list = str(row[4]).split('.')
                    semester_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.semester'),
                                                                           ('module', '=', self.company_code),
                                                                           ('name', '=', semester_list[1])
                                                                           ]).res_id

                # Scholarship ID
                if row[13]:
                    scholarship_list = str(row[13]).split('.')
                    scholarship_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.fee.waiver'),
                                                                              ('module', '=', self.company_code),
                                                                              ('name', '=', scholarship_list[1])
                                                                              ]).res_id
                    if not scholarship_id:
                        scholarship_id = False
                else:
                    scholarship_id = False

                # Invoice Date
                date_invoice = row[6]

                # Invoice Due Date
                date_due = row[7]

                # Invoice Due Date
                paid_date = row[8]

                # Receipts
                receipts = [int(row[15])]
                registration_id = False
                lines = []

                # ***** DATA DICT Of Fee Receipt *****#
                data = {
                    'student_id': student_id.id,
                    'student_name': student_id.partner_id.name,
                    'partner_id': student_id.partner_id.id,
                    'fee_structure_id': fee_structure and fee_structure.id or False,
                    'journal_id': 1,
                    'invoice_date': (date_invoice and date_invoice) or (date_due and date_due) or (paid_date and paid_date) or '',
                    'invoice_date_due': (paid_date and paid_date) or (date_due and date_due) or '',
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipt, None) for receipt in receipts],
                    'waiver_ids': [(4, scholarship_id, None)],
                    'waiver_percentage': row[12] and float(row[12]) or 0.0,
                    'waiver_amount': 0.0,
                    'program_id': program_id,
                    'term_id': term_id and term_id or False,
                    'semester_id': semester_id and semester_id or False,
                    'career_id': student_id.career_id and student_id.career_id.id or False,
                    'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                    'discipline_id': student_id.discipline_id and student_id.discipline_id.id or False,
                    'campus_id': student_id.campus_id and student_id.campus_id.id or False,
                    'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                    'session_id': student_id.session_id and student_id.session_id.id or False,
                    'validity_date': date_due and date_due or '',
                    'first_installment': False,
                    'second_installment': True,
                    'registration_id': registration_id and registration_id.id or False,
                    'old_challan_no': old_challan_no,
                    'installment_no': row[11] and float(row[11]) or 0.0,
                    'challan_type': row[16] and row[16] or '',
                    'old_challan_type': row[17] and row[17].lower() or '',
                    'add_drop_no': row[18] and row[18] or '',
                    'reference': row[19] and row[19] or '',
                    'payment_date': paid_date and paid_date or '',
                    'narration': 'NEW-UNPAID'
                }
                if row[20] and row[20] == 'Yes':
                    student_id.filer = True

                # Create Fee Receipt
                move_id = self.env['account.move'].sudo().create(data)
                self._cr.commit()

            if self.import_type == 'unpaid_lines':
                # header_info = {'0': 'old_challan_no'}
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if move_id:
                    lines = []
                    mvl_lines = self.env['fee.lines.data.processing'].search([('name', '=', old_challan_no),
                                                                              ('processed', '!=', True)
                                                                              ], order="amount desc")
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
                                'course_gross_fee': (float(mvl_line.registration_type) * mvl_line.credit_hours),
                                'course_credit_hours': mvl_line.credit_hours,
                                'registration_type': 'main',
                                'section_name': mvl_line.add_drop_no,
                            }
                            lines.append((0, 0, fee_line))
                        mvl_lines.write({'processed': True})
                        move_id.write({'invoice_line_ids': lines})
                        move_id.payment_state = 'not_paid'

                    # *****assign Primary Class ****
                    fee_head_id = 47
                    if move_id.company_id.code == 'CUST':
                        fee_head_id = 25
                    for move_line in move_id.invoice_line_ids.filtered(lambda a: not a.course_id_new and a.fee_head_id.id == fee_head_id):
                        code_list = move_line.name.split("-")
                        course_code = code_list[0]
                        for line in move_id.student_id.course_ids:
                            if course_code == line.primary_class_id.course_id.code:
                                move_line['course_id_new'] = line.primary_class_id.id
                    self._cr.commit()

            if flag == 'OLD Status':
                moves = self.env['account.move'].search([('registration_id', '!=', False)])
                for move in moves:
                    reg_id = move.registration_id
                    for move_line in move.invoice_line_ids:
                        code_list = move_line.name.split("-")
                        course_code = code_list[0]
                        for reg_line in reg_id.line_ids:
                            if course_code == reg_line.primary_class_id.course_id.code:
                                # _logger.info("Course Code %r Found and REG Line ID %r", course_code,reg_line.id)
                                move_line.write({'registration_line_id': reg_line.id, 'course_id_new': reg_line.primary_class_id.id})

            if self.import_type == 'primary_clas':
                # Old Challan ID
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                move = self.env['account.move'].search([('old_challan_no', '=', old_challan_no)])

                move_line = move.line_ids.filtered(lambda a: a.name == row[1])
                p_class = str(row[2]).split('.')
                p_class_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.class.primary'),
                                                                      ('module', '=', self.company_code),
                                                                      ('name', '=', p_class[1])]).res_id
                move_line.with_context(check_move_validity=False).sudo().write({'course_id_new': p_class_id})

            if self.import_type == 'library':
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if move_id:
                    lines = []
                    seq = 10
                    amt = float(row[1])
                    fee_head_id = self.env['odoocms.fee.head'].search([('id', '=', 60)])
                    fee_line = {
                        'sequence': seq + 10,
                        'price_unit': amt,
                        'quantity': 1.00,
                        'product_id': fee_head_id.product_id and fee_head_id.product_id.id or False,
                        'name': "Library Fine",
                        'account_id': fee_head_id.property_account_income_id and fee_head_id.property_account_income_id.id or False,
                        'fee_head_id': fee_head_id and fee_head_id.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': float(row[1]),
                    }
                    lines.append((0, 0, fee_line))
                    move_id.write({'invoice_line_ids': lines})
                    move_id.payment_state = 'not_paid'

            # ***** Create or Update Account Move Line *****#
            if flag == 'Update':
                # ***** Create Account Move Line With Zero *****#
                # Student ID
                student = self.env['odoocms.student'].sudo().search([('code', '=', row[0])])
                if student:
                    move_id = self.env['account.move'].sudo().search([('student_id', '=', student.id),
                                                                      ('challan_type', '=', '2nd_challan')
                                                                      ], order='id desc', limit=1)
                if move_id:
                    old_payment_state = move_id.payment_state
                    course_id = student.course_ids.filtered(lambda a: a.term_id.id == 190 and a.course_id.code == row[1])
                    fee_head_id = self.env['odoocms.fee.head'].search([('id', '=', 47)])
                    name = ''
                    if course_id.course_id:
                        name = course_id.course_id.code + "-" + course_id.course_id.name
                    fee_line = {
                        'sequence': 90,
                        'price_unit': 0,
                        'quantity': 1.00,
                        'product_id': fee_head_id.product_id and fee_head_id.product_id.id or False,
                        'name': name,
                        'account_id': 21,
                        'fee_head_id': fee_head_id and fee_head_id.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': 0,
                        'course_credit_hours': course_id.credits,
                        'move_id': move_id.id,
                        'course_id_new': course_id and course_id.primary_class_id and course_id.primary_class_id.id or False,
                    }
                    self.env['account.move.line'].sudo().create(fee_line)
                    move_id.narration = '001'
                    move_id.payment_state = old_payment_state

                    # receivable_line = move_id.line_ids.filtered(lambda a: a.account_id.id == 6)
                    # if not receivable_line:
                    #     fee_line = {
                    #         'sequence': 100,
                    #         'price_unit': 0,
                    #         'quantity': 1.00,
                    #         'name': move_id.name,
                    #         'account_id': 6,
                    #         'fee_head_id': False,
                    #         'exclude_from_invoice_tab': True,
                    #         'course_gross_fee': 0,
                    #         'course_credit_hours': 0,
                    #         'move_id': move_id.id,
                    #         'partner_id': move_id.student_id.partner_id and move_id.student_id.partner_id.id or False,
                    #         'date_maturity': move_id.invoice_date_due,
                    #     }
                    #     receivable_line = self.env['account.move.line'].sudo().create(fee_line)

            # ***** Update Existing Account Move Line *****#
            if flag == 'Update1':
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                move_id = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if move_id:
                    fine_line = move_id.line_ids.filtered(lambda a: "Fine" in a.name)
                    receivable_line = move_id.line_ids.filtered(lambda a: a.account_id.id == 6)
                    amt = float(row[1])
                    if fine_line:
                        move_id.narration = 'Fine Line Added'
                        old_amt = fine_line.credit
                        credit_amt1 = fine_line.credit + amt
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

            if flag == 'Paid3':
                # Old Challan ID
                old_challan_no = str(row[5]).split('.')
                old_challan_no = old_challan_no[0]
                record_already_exists = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if record_already_exists:
                    continue

                # Student ID
                student_list = str(row[0]).split('.')
                student_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.student'), ('module', '=', 'cms'), ('name', '=', student_list[1])]).res_id
                student_id = self.env['odoocms.student'].browse(student_id)
                if not student_id:
                    raise UserError('Student ID REG No %s Not Found' % row[0])

                # Fee Structure
                fee_structure = self.env['odoocms.fee.structure'].search([('batch_id', '=', student_id.batch_id.id), ('session_id', '=', student_id.session_id.id), ('career_id', '=', student_id.career_id.id)])
                # if not fee_structure:
                #     raise UserError('No Fee Structure Found For Student REG %s' % row[0])

                # Program ID
                program_list = str(row[1]).split('.')
                program_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.program'), ('module', '=', 'cms'), ('name', '=', program_list[1])]).res_id

                # Session ID
                if row[2]:
                    session_list = str(row[2]).split('.')
                    session_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.session'), ('module', '=', 'cms'), ('name', '=', session_list[1])]).res_id
                else:
                    session_id = False

                # Term ID
                term_list = str(row[3]).split('.')
                term_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.term'), ('module', '=', 'cms'), ('name', '=', term_list[1])]).res_id

                # Semester ID
                semester_list = str(row[4]).split('.')
                semester_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.semester'), ('module', '=', 'cms'), ('name', '=', semester_list[1])]).res_id

                # Scholarship ID
                # scholarship_list = str(row[15]).split('.')
                # scholarship_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.fee.waiver'), ('module', '=', 'cms'), ('name', '=', scholarship_list[1])]).res_id
                # if not scholarship_id:
                #     scholarship_id = False

                # Invoice Date
                date_invoice = row[6]
                # Invoice Due Date
                date_due = row[7]
                # Invoice Paid Date
                paid_date = row[8]

                # Receipts
                receipts = [int(row[12])]
                registration_id = False
                lines = []

                # ***** Tuition Fee Line *****#
                tuition_amt = row[10] and float(row[10]) or 0.0
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
                admission_amt = row[9] and float(row[9]) or 0.0
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

                # ***** DATA DICT Of Fee Receipt *****#
                data = {
                    'student_id': student_id.id,
                    'student_name': student_id.partner_id.name,
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
                    'waiver_ids': [],
                    'waiver_amount': 0,
                    'program_id': program_id,
                    'term_id': term_id and term_id or False,
                    'semester_id': semester_id and semester_id or False,
                    'career_id': student_id.career_id and student_id.career_id.id or False,
                    'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                    'discipline_id': student_id.discipline_id and student_id.discipline_id.id or False,
                    'campus_id': student_id.campus_id and student_id.campus_id.id or False,
                    'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                    'session_id': student_id.session_id and student_id.session_id.id or False,
                    'validity_date': paid_date and paid_date or '',
                    'first_installment': True,
                    'second_installment': False,
                    'registration_id': registration_id and registration_id.id or False,
                    'old_challan_no': old_challan_no,
                    'installment_no': '',
                    'payment_mode': row[13] and row[13].lower() or '',
                    'transaction_id': row[15] and row[15] or '',
                    'online_vendor': row[16] and row[16] or '',
                    'challan_type': row[17] and row[17] or '',
                    'old_challan_type': row[18] and row[18] or '',
                    # 'add_drop_no': row[27] and row[27] or '',
                    'reference': row[19] and row[19] or '',
                    'payment_date': paid_date and paid_date or '',
                }
                # Create Fee Receipt
                move_id = self.env['account.move'].sudo().create(data)

            # ***** One Credit Hour Fee Issue ******* #
            if flag == 'Credit Hour':
                # Student ID
                student = self.env['odoocms.student'].sudo().search([('code', '=', row[0])])
                if student:
                    inv_rec = self.env['account.move'].sudo().search([('student_id', '=', student.id), ('challan_type', '=', '2nd_challan')], order='id desc', limit=1)
                    if inv_rec:
                        # Search Move Line
                        mvl_line = inv_rec.line_ids.filtered(lambda a: a.name == "BT3703-Immunology")
                        if mvl_line:
                            receivable_line = inv_rec.line_ids.filtered(lambda a: a.account_id.id == 6)
                            new_amt = mvl_line.price_subtotal + float(row[3])

                            self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,course_gross_fee=%s,course_credit_hours=%s where id=%s \n"
                                                , (new_amt, new_amt, -new_amt, -new_amt, new_amt, new_amt, float(row[2]), 3.00, mvl_line.id))

                            # Receivable Line, it will debit
                            debit_amt = receivable_line.debit + float(row[3])
                            self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s,amount_residual=%s, amount_residual_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                                , (-debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, receivable_line.id))

                            # Invoice Total Update
                            self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                                , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, inv_rec.id))
                            inv_rec.write({'semester_gross_fee': inv_rec.semester_gross_fee + float(row[5]), 'waiver_amount': inv_rec.waiver_amount + float(row[4])})
                            self._cr.commit()

            # ***** Update Balance Issue ******* #
            if flag == 'Update Balance':
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                invoice = self.env['account.move'].sudo().search([('id', '=', old_challan_no)])
                if invoice:
                    mvl_line = self.env['account.move.line'].search([('move_id', '=', invoice.id), ('fee_head_id', '=', 47), ('price_subtotal', '>', 0)], order='id desc', limit=1)
                    if mvl_line:
                        new_amt = mvl_line.price_subtotal + float(row[3])
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,course_gross_fee=%s,course_credit_hours=%s where id=%s \n"
                                            , (new_amt, new_amt, -new_amt, -new_amt, new_amt, new_amt, float(row[2]), 3.00, mvl_line.id))
                        self._cr.commit()

            # ***** Hostel******* #
            if flag == 'Hostel':
                # Old Challan ID
                old_challan_no = str(row[1]).split('.')
                old_challan_no = old_challan_no[0]
                record_already_exists = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if record_already_exists:
                    continue

                # Student ID
                student_list = str(row[0]).split('.')
                student_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.student'), ('module', '=', 'cms'), ('name', '=', student_list[1])]).res_id
                student_id = self.env['odoocms.student'].browse(student_id)
                if not student_id:
                    raise UserError('Student ID REG No %s Not Found' % row[0])

                # Fee Structure
                fee_structure = self.env['odoocms.fee.structure'].search([('batch_id', '=', student_id.batch_id.id), ('session_id', '=', student_id.session_id.id), ('career_id', '=', student_id.career_id.id)])

                # Invoice Date
                date_from = ''
                date_value = xlrd.xldate_as_tuple(float(row[7]), workbook.datemode)
                if date_value:
                    date_from = date(*date_value[:3]).strftime('%Y-%m-%d')

                # Receipts
                receipts = 4
                registration_id = False
                lines = []

                # ***** Tuition Fee Line *****#
                tuition_amt = row[3] and float(row[3]) or 0.0
                if tuition_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('id', '=', int(row[10]))])
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

                # *****Fine Line *****#
                fine_amt = row[5] and float(row[5]) or 0.0
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

                # ***** Security Line *****#
                apf_amt = row[4] and float(row[4]) or 0.0
                if apf_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('id', '=', 56)])
                    if not fee_head:
                        raise UserError('Fee Head Not Found.')
                    apf_line = {
                        'sequence': 50,
                        'price_unit': apf_amt,
                        'quantity': 1.00,
                        'product_id': fee_head.product_id and fee_head.product_id.id or False,
                        'name': fee_head.name,
                        'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                        'fee_head_id': fee_head and fee_head.id or False,
                        'exclude_from_invoice_tab': False,
                        'course_gross_fee': apf_amt,
                    }
                    lines.append((0, 0, apf_line))

                # ***** DATA DICT Of Fee Receipt *****#
                data = {
                    'student_id': student_id.id,
                    'student_name': student_id.partner_id.name,
                    'partner_id': student_id.partner_id.id,
                    'fee_structure_id': fee_structure and fee_structure.id or False,
                    'journal_id': 1,
                    'invoice_date': date_from or '',
                    'invoice_date_due': date_from or '',
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipts, None)],
                    'waiver_ids': [],
                    'waiver_amount': 0,
                    'program_id': student_id.program_id.id,
                    'term_id': 190,
                    'semester_id': False,
                    'career_id': student_id.career_id and student_id.career_id.id or False,
                    'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                    'discipline_id': student_id.discipline_id and student_id.discipline_id.id or False,
                    'campus_id': student_id.campus_id and student_id.campus_id.id or False,
                    'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                    'session_id': student_id.session_id and student_id.session_id.id or False,
                    'validity_date': date_from or '',
                    'first_installment': True,
                    'second_installment': False,
                    'registration_id': registration_id and registration_id.id or False,
                    'old_challan_no': old_challan_no,
                    'payment_date': date_from or '',
                    'narration': 'Hostel-19',
                    'challan_type': 'hostel_fee',
                }
                # Create Fee Receipt
                move_id = self.env['account.move'].sudo().create(data)

            if flag == 'Old_Fine':
                # Student ID
                student_list = str(row[0]).split('.')
                student_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.student'), ('module', '=', 'cms'), ('name', '=', student_list[1])]).res_id
                student_id = self.env['odoocms.student'].browse(student_id)
                if not student_id:
                    raise UserError('Student ID REG No %s Not Found' % row[0])

                # Fee Structure
                fee_structure = self.env['odoocms.fee.structure'].search([('batch_id', '=', student_id.batch_id.id), ('session_id', '=', student_id.session_id.id), ('career_id', '=', student_id.career_id.id)])

                # Term ID
                term_list = str(row[1]).split('.')
                term_id = self.env['ir.model.data'].sudo().search([('model', '=', 'odoocms.academic.term'), ('module', '=', 'cms'), ('name', '=', term_list[1])]).res_id

                # Invoice Date
                date_invoice = row[2]

                # Invoice Due Date
                date_due = row[3]

                paid_date = row[4]

                scholarship_id = False

                # Receipts
                receipts = [int(row[7])]
                registration_id = False
                lines = []

                fine_amt = row[5] and float(row[5]) or 0.0
                if fine_amt > 0:
                    fee_head = self.env['odoocms.fee.head'].search([('id', '=', int(row[8]))])
                    fine_line = {
                        'sequence': 10,
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

                # ***** DATA DICT Of Fee Receipt *****#
                data = {
                    'student_id': student_id.id,
                    'student_name': student_id.partner_id.name,
                    'partner_id': student_id.partner_id.id,
                    'fee_structure_id': fee_structure and fee_structure.id or False,
                    'journal_id': 1,
                    'invoice_date': (date_invoice and date_invoice) or (date_due and date_due) or (paid_date and paid_date) or '',
                    'invoice_date_due': (paid_date and paid_date) or (date_due and date_due) or '',
                    'payment_date': paid_date and paid_date or '',
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipt, None) for receipt in receipts],
                    'waiver_ids': [(4, scholarship_id, None)],
                    'waiver_percentage': 0.0,
                    'waiver_amount': 0.0,
                    'program_id': student_id.program_id,
                    'term_id': term_id and term_id or False,
                    'semester_id': False,
                    'career_id': student_id.career_id and student_id.career_id.id or False,
                    'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                    'discipline_id': student_id.discipline_id and student_id.discipline_id.id or False,
                    'campus_id': student_id.campus_id and student_id.campus_id.id or False,
                    'study_scheme_id': student_id.study_scheme_id and student_id.study_scheme_id.id or False,
                    'session_id': student_id.session_id and student_id.session_id.id or False,
                    'validity_date': date_due and date_due or '',
                    'first_installment': True,
                    'second_installment': False,
                    'narration': row[9] and row[9] or '',
                }
                # Create Fee Receipt
                move_id = self.env['account.move'].sudo().create(data)

            if self.import_type == 'paid_challan_update':
                lines = []
                amt = 0
                old_challan_no = str(row[0]).split('.')
                old_challan_no = old_challan_no[0]
                challan_rec = self.env['account.move'].sudo().search([('old_challan_no', '=', old_challan_no)])
                if challan_rec:
                    line = self.env['fee.lines.data.processing'].search([('name', '=', old_challan_no)])
                    if int(line.course_name) > 0:
                        amt += int(line.course_name)
                        fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Prospectus Fee')])
                        mvl_apf_line = challan_rec.line_ids.filtered(lambda a: a.fee_head_id.id == fee_head.id)
                        if mvl_apf_line:
                            mvl_apf_line.with_context(check_move_validity=False).sudo().write({'price_unit': int(line.course_name)})
                        else:
                            apf_line = {
                                'sequence': 50,
                                'price_unit': int(line.course_name),
                                'quantity': 1.00,
                                'product_id': fee_head.product_id and fee_head.product_id.id or False,
                                'name': fee_head.name,
                                'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                                'fee_head_id': fee_head and fee_head.id or False,
                                'exclude_from_invoice_tab': False,
                                'course_gross_fee': int(line.course_name),
                                'move_id': challan_rec.id,
                            }
                            self.env['account.move.line'].with_context(check_move_validity=False).sudo().create(apf_line)

                    # ***** Misc Line *****#
                    if int(line.registration_type) > 0:
                        amt += int(line.registration_type)
                        fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Hostel Fee')])
                        mvl_hostel_line = challan_rec.line_ids.filtered(lambda a: a.fee_head_id.id == fee_head.id)
                        if mvl_hostel_line:
                            mvl_hostel_line.with_context(check_move_validity=False).sudo().write({'price_unit': int(line.registration_type)})
                        else:
                            misc_line = {
                                'sequence': 50,
                                'price_unit': int(line.registration_type),
                                'quantity': 1.00,
                                'product_id': fee_head.product_id and fee_head.product_id.id or False,
                                'name': fee_head.name,
                                'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                                'fee_head_id': fee_head and fee_head.id or False,
                                'exclude_from_invoice_tab': False,
                                'course_gross_fee': int(line.registration_type),
                                'move_id': challan_rec.id,
                            }
                            self.env['account.move.line'].with_context(check_move_validity=False).sudo().create(misc_line)

                    # ***** Admission Line *****#
                    if int(line.fee_head_id) > 0:
                        amt += int(line.fee_head_id)
                        fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Admission Fee')])
                        mvl_adm_line = challan_rec.line_ids.filtered(lambda a: a.fee_head_id.id == fee_head.id)
                        if mvl_adm_line:
                            mvl_adm_line.with_context(check_move_validity=False).sudo().write({'price_unit': int(line.fee_head_id)})
                        else:
                            admission_line = {
                                'sequence': 20,
                                'name': fee_head.name,
                                'quantity': 1,
                                'course_gross_fee': int(line.fee_head_id),
                                'price_unit': int(line.fee_head_id),
                                'product_id': fee_head.product_id and fee_head.product_id.id or False,
                                'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                                'fee_head_id': fee_head and fee_head.id or False,
                                'exclude_from_invoice_tab': False,
                                'course_credit_hours': 0,
                                'move_id': challan_rec.id
                            }
                            self.env['account.move.line'].with_context(check_move_validity=False).sudo().create(admission_line)

                    # ***** Tuition Fee Line *****#
                    if int(line.credit_hours) > 0:
                        amt += int(line.credit_hours)
                        fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Tuition Fee')])
                        mvl_tutf_line = challan_rec.line_ids.filtered(lambda a: a.fee_head_id.id == fee_head.id)
                        if mvl_tutf_line:
                            mvl_tutf_line.with_context(check_move_validity=False).sudo().write({'price_unit': int(line.credit_hours)})
                        else:
                            tuition_line = {
                                'sequence': 10,
                                'price_unit': int(line.credit_hours),
                                'quantity': 1.00,
                                'product_id': fee_head.product_id and fee_head.product_id.id or False,
                                'name': fee_head.name,
                                'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                                'fee_head_id': fee_head and fee_head.id or False,
                                'exclude_from_invoice_tab': False,
                                'course_gross_fee': int(line.credit_hours),
                            }
                            self.env['account.move.line'].with_context(check_move_validity=False).sudo().create(tuition_line)
                    if line.amount > 0:
                        challan_rec.with_context(check_move_validity=False).sudo().write({'waiver_percentage': line.amount})
                    receivable_line = challan_rec.line_ids.filtered(lambda a: a.account_id.id == 6)
                    receivable_line.with_context(check_move_validity=False).sudo().write({'price_unit': -amt})
                self._cr.commit()

                challan_rec.payment_state = 'paid'
                if challan_rec.student_ledger_id:
                    challan_rec.student_ledger_id.credit = challan_rec.amount_total
                if challan_rec.payment_ledger_id:
                    challan_rec.payment_ledger_id.debit = challan_rec.amount_total

    def invoice_ledger_entry(self, invoice):
        if not invoice.student_ledger_id:
            ledger_data = {
                'student_id': invoice.student_id.id,
                'date': invoice.invoice_date and invoice.invoice_date or '',
                'credit': invoice.amount_total,
                'debit': 0,
                'invoice_id': invoice.id,
                'payment_id': False,
                'id_number': invoice.student_id.code,
                'session_id': invoice.student_id.session_id and invoice.student_id.session_id.id or False,
                'career_id': invoice.student_id.career_id and invoice.student_id.career_id.id or False,
                'program_id': invoice.student_id.program_id and invoice.student_id.program_id.id or False,
                'institute_id': invoice.student_id.institute_id and invoice.student_id.institute_id.id or False,
                'discipline_id': invoice.student_id.discipline_id and invoice.student_id.discipline_id.id or False,
                'campus_id': invoice.student_id.campus_id and invoice.student_id.campus_id.id or False,
                'term_id': invoice.student_id.term_id and invoice.student_id.term_id.id or False,
                'semester_id': invoice.student_id.campus_id and invoice.student_id.semester_id.id or False,
                'ledger_entry_type': 'semester',
                'description': 'Semester Fee',
            }
            ledger_id = self.env['odoocms.student.ledger'].create(ledger_data)
            invoice.student_ledger_id = ledger_id.id

    def paid_leger_entry(self, invoice):
        if not invoice.payment_ledger_id:
            if invoice.payment_date:
                p_ledger_data = {
                    'student_id': invoice.student_id.id,
                    'date': invoice.payment_date,
                    'credit': 0,
                    'debit': invoice.amount_total,
                    'invoice_id': invoice.id,
                    'payment_id': False,
                    'id_number': invoice.student_id.code,
                    'session_id': invoice.student_id.session_id and invoice.student_id.session_id.id or False,
                    'career_id': invoice.student_id.career_id and invoice.student_id.career_id.id or False,
                    'program_id': invoice.student_id.program_id and invoice.student_id.program_id.id or False,
                    'institute_id': invoice.student_id.institute_id and invoice.student_id.institute_id.id or False,
                    'discipline_id': invoice.student_id.discipline_id and invoice.student_id.discipline_id.id or False,
                    'campus_id': invoice.student_id.campus_id and invoice.student_id.campus_id.id or False,
                    'term_id': invoice.student_id.term_id and invoice.student_id.term_id.id or False,
                    'semester_id': invoice.student_id.campus_id and invoice.student_id.semester_id.id or False,
                    'ledger_entry_type': 'semester',
                    'description': 'Payment Received',
                }
                p_ledger_id = self.env['odoocms.student.ledger'].create(p_ledger_data)
                invoice.payment_ledger_id = p_ledger_id.id
