# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)
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


class StudentFineHistoryRepWiz(models.TransientModel):
    _name = 'student.fine.history.rep.wiz'
    _description = "Student Fine History Report Wizard"

    student_id = fields.Many2one('odoocms.student', 'Student')
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    show_all_history = fields.Boolean('Show All History', default=False)
    registered_courses = fields.Many2many('odoocms.student.course', 'student_fine_history_rep_wiz_course_rel1', 'wiz_id', 'student_course_id', 'Courses')

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'student.fine.history.rep.wiz',
            'form': data
        }
        return self.env.ref('odoocms_fee_ucp.action_student_fine_history_report').with_context(landscape=False).report_action(self, data=datas, config=False)

    # def make_excel(self):
    #     workbook = xlwt.Workbook(encoding="utf-8")
    #     worksheet = workbook.add_sheet("Program Wise Financial Report")
    #     style_title = xlwt.easyxf(
    #         "font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
    #     style_table_header = xlwt.easyxf(
    #         "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
    #     style_table_header2 = xlwt.easyxf(
    #         "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center,vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
    #     style_table_header3 = xlwt.easyxf(
    #         "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour ivory;alignment: wrap True;")
    #
    #     style_table_totals = xlwt.easyxf(
    #         "font:height 150; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
    #     style_date_col = xlwt.easyxf(
    #         "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
    #     style_date_col2 = xlwt.easyxf(
    #         "font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
    #     style_table_totals2 = xlwt.easyxf(
    #         "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz right,vert center;borders: left thin, right thin, top thin, bottom thin;")
    #     style_table_totals3 = xlwt.easyxf(
    #         "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz left,vert center;borders: left thin, right thin, top thin, bottom thin;")
    #
    #     # col width
    #     col0 = worksheet.col(0)
    #     col0.width = 256 * 10
    #     col1 = worksheet.col(1)
    #     col1.width = 256 * 20
    #     col2 = worksheet.col(2)
    #     col2.width = 256 * 40
    #     col3 = worksheet.col(3)
    #     col3.width = 256 * 20
    #     col4 = worksheet.col(4)
    #     col4.width = 256 * 20
    #     col5 = worksheet.col(5)
    #     col5.width = 256 * 20
    #     col6 = worksheet.col(6)
    #     col6.width = 256 * 20
    #     col7 = worksheet.col(7)
    #     col7.width = 256 * 20
    #     col8 = worksheet.col(8)
    #     col8.width = 256 * 20
    #     col9 = worksheet.col(9)
    #     col9.width = 256 * 20
    #
    #     col_min = 0
    #     col_max = 13
    #     col = 0
    #     row = 0
    #
    #     [data] = self.read()
    #     datas = {
    #         'ids': [],
    #         'model': 'program.wise.fin.summary.wiz',
    #         'form': data
    #     }
    #     dta = self.env['report.odoocms_fee.program_wise_fin_summary_report']._get_report_values(self, data=datas)
    #
    #     # Header
    #     worksheet.write_merge(row, row + 1, col_min, col_max, 'Program Wise Financial Report', style=style_table_header2)
    #     row += 2
    #
    #     table_header = ['SR#', 'Student ID', 'Student Name', 'Faculty', 'Program', 'Term', 'Type', 'Admission', 'Tuition', 'Misc', 'Hostel', 'Fine', 'Tax', 'Amount']
    #     for i in range(col_min, col_max + 1):
    #         worksheet.write(row, col, table_header[i], style=style_table_header)
    #         col += 1
    #
    #     if dta['invoice']:
    #         invoices = dta['invoice']
    #         admission = 0
    #         tuition = 0
    #         misc = 0
    #         hostel = 0
    #         fine = 0
    #         tax = 0
    #         total_amount = 0
    #
    #         sr = 1
    #         for inv in invoices:
    #             row += 1
    #             col = 0
    #
    #             worksheet.write(row, col, sr, style=style_date_col2)
    #             col += 1
    #             worksheet.write(row, col, inv.student_id.code, style=style_date_col2)
    #             col += 1
    #             worksheet.write(row, col, inv.student_id.name, style=style_date_col2)
    #             col += 1
    #             worksheet.write(row, col, inv.student_id.institute_id.code, style=style_date_col2)
    #             col += 1
    #             worksheet.write(row, col, inv.student_id.program_id.code, style=style_date_col2)
    #             col += 1
    #             worksheet.write(row, col, inv.term_id.code, style=style_date_col2)
    #             col += 1
    #             worksheet.write(row, col, dict(inv.fields_get(allfields=['challan_type'])['challan_type']['selection'])[inv.challan_type], style=style_date_col2)
    #             col += 1
    #
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.admission_fee), style=style_date_col)
    #             admission += inv.admission_fee
    #             col += 1
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.tuition_fee), style=style_date_col)
    #             tuition += inv.tuition_fee
    #             col += 1
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.misc_fee), style=style_date_col)
    #             misc += inv.misc_fee
    #             col += 1
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.hostel_fee), style=style_date_col)
    #             hostel += inv.hostel_fee
    #             col += 1
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.fine_amount), style=style_date_col)
    #             fine += inv.fine_amount
    #             col += 1
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.tax_amount), style=style_date_col)
    #             tax += inv.tax_amount
    #             col += 1
    #             worksheet.write(row, col, '{0:,.2f}'.format(inv.amount_residual), style=style_date_col)
    #             total_amount += inv.amount_residual
    #             col += 1
    #             sr += 1
    #
    #         # ***** Totals *****#
    #         row += 1
    #         col = 0
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '', style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(admission), style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(tuition), style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(misc), style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(hostel), style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(fine), style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(tax), style=style_table_totals2)
    #         col += 1
    #         worksheet.write(row, col, '{0:,.2f}'.format(total_amount), style=style_table_totals2)
    #         col += 1
    #
    #         # Print Date and Time Display
    #         row += 1
    #         col = 0
    #         ttime = fields.datetime.now() + relativedelta(hours=5)
    #         worksheet.write_merge(row, row, 0, 5, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
    #         col += 1
    #
    #     file_data = io.BytesIO()
    #     workbook.save(file_data)
    #     wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
    #         'data': base64.encodebytes(file_data.getvalue()),
    #         'name': 'Program Wise Financial Report.xls'
    #     })
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'name': 'Program Wise Financial Report',
    #         'res_model': 'odoocms.fee.report.save.wizard',
    #         'view_mode': 'form',
    #         'view_type': 'form',
    #         'res_id': wiz_id.id,
    #         'target': 'new'
    #     }
