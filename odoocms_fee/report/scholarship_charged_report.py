from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)

from io import StringIO
import io

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


class ScholarshipChargedReport(models.TransientModel):
    _name = 'scholarship.charged.report'
    _description = 'Student Scholarship Charged Report'

    institute_ids = fields.Many2many('odoocms.institute', 'scholarship_charged_rep_institute_rel', 'scholarship_charged_rep_id', 'institute_id', 'Institutes')
    campus_ids = fields.Many2many('odoocms.campus', 'scholarship_charged_rep_campus_rel', 'scholarship_charged_rep_id', 'campus_id', 'Campuses')
    term_id = fields.Many2one('odoocms.academic.term', 'Term')

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Scholarship Charged Report")
        style_title = xlwt.easyxf(
            "font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
        style_table_header3 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour ivory;alignment: wrap True;")

        style_table_totals = xlwt.easyxf(
            "font:height 150; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
        style_date_col = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
        style_date_col2 = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
        style_date_col3 = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")

        style_table_totals2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour ivory;")

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 8
        col1 = worksheet.col(1)
        col1.width = 256 * 25
        col2 = worksheet.col(2)
        col2.width = 256 * 35
        col3 = worksheet.col(3)
        col3.width = 256 * 25
        col4 = worksheet.col(4)
        col4.width = 256 * 25
        col5 = worksheet.col(5)
        col5.width = 256 * 25
        col6 = worksheet.col(6)
        col6.width = 256 * 35
        col7 = worksheet.col(7)
        col7.width = 256 * 15
        col8 = worksheet.col(8)
        col8.width = 256 * 15
        col9 = worksheet.col(9)
        col9.width = 256 * 15
        col10 = worksheet.col(10)
        col10.width = 256 * 15
        col11 = worksheet.col(11)
        col11.width = 256 * 15
        col12 = worksheet.col(12)
        col12.width = 256 * 15

        ttime = fields.datetime.now() + relativedelta(hours=5)
        worksheet.write_merge(0, 1, 0, 11, 'Scholarship Charged Report Of ' + self.term_id.name, style=style_table_header2)
        row = 2
        col = 0
        table_header = ['Sr No.', 'CMS ID', 'Student NAME', 'School', 'Career', 'Scholarship Group', 'Scholarship NAME',
                        'Student Invoice', 'Donor Invoice', 'Waiver', 'Hostel Invoice', 'Total']
        for i in range(12):
            worksheet.write(row, col, table_header[i], style=style_table_header2)
            col += 1

        dom = [('move_type', '=', 'out_invoice'),
               ('term_id', '>=', self.term_id.id),
               ('is_scholarship_fee', '=', True)]

        if self.institute_ids:
            dom.append(('institute_id', 'in', self.institute_ids.ids))
        if self.campus_ids:
            dom.append(('campus_id', 'in', self.campus_ids.ids))

        fee_receipts = self.env['account.move'].search(dom)
        sr = 1
        if fee_receipts:
            for fee_receipt in fee_receipts:
                student_receipt_amount = 0
                hostel_receipt_amount = 0
                waiver_amount = 0
                receipt_total = 0
                student_fee_receipts = self.env['account.move'].search([('student_id', '=', fee_receipt.student_id.id),
                                                                        ('term_id', '=', fee_receipt.term_id.id),
                                                                        ('is_scholarship_fee', '=', False),
                                                                        ('is_hostel_fee', '=', False),
                                                                        ])
                hostel_fee_receipts = self.env['account.move'].search([('student_id', '=', fee_receipt.student_id.id),
                                                                       ('term_id', '=', fee_receipt.term_id.id),
                                                                       ('is_hostel_fee', '=', True),
                                                                       ])

                if student_fee_receipts:
                    for student_fee_receipt in student_fee_receipts:
                        student_receipt_amount += student_fee_receipt.amount_total
                        waiver_amount += abs(student_fee_receipt.waiver_amount)
                if hostel_fee_receipts:
                    for hostel_fee_receipt in hostel_fee_receipts:
                        hostel_receipt_amount += hostel_fee_receipt.amount_total
                        waiver_amount += abs(hostel_fee_receipt.waiver_amount)

                receipt_total = fee_receipt.amount_total + student_receipt_amount + hostel_receipt_amount + waiver_amount
                row += 1
                col = 0

                student = fee_receipt.student_id
                worksheet.write(row, col, sr, style=style_date_col)
                col += 1
                worksheet.write(row, col, student.code and student.code or '', style=style_date_col2)
                col += 1
                worksheet.write(row, col, student.name and student.name or '', style=style_date_col2)
                col += 1
                worksheet.write(row, col, student.institute_id and student.institute_id.code or '', style=style_date_col2)
                col += 1
                worksheet.write(row, col, student.career_id and student.career_id.name or '', style=style_date_col2)
                col += 1
                worksheet.write(row, col, fee_receipt.donor_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, fee_receipt.donor_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, student_receipt_amount, style=style_date_col3)
                col += 1
                worksheet.write(row, col, fee_receipt.amount_total, style=style_date_col3)
                col += 1
                worksheet.write(row, col, waiver_amount, style=style_date_col3)
                col += 1
                worksheet.write(row, col, hostel_receipt_amount and hostel_receipt_amount or 0, style=style_date_col3)
                col += 1
                worksheet.write(row, col, receipt_total, style=style_date_col3)
                col += 1
                sr += 1

        col = 0
        row += 2
        worksheet.write(row, col, 'User Name', style=style_date_col2)
        col += 1
        worksheet.write(row, col, self.env.user.name, style=style_date_col2)

        col = 0
        row += 1
        worksheet.write(row, col, 'Report Print Date:-', style=style_date_col2)
        col += 1
        worksheet.write(row, col, str(ttime), style=style_date_col2)
        col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Scholarship Charged Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Scholarship Charged Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
