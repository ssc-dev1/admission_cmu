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


class ReceiptReceivedDetailReportWiz(models.TransientModel):
    _inherit = 'receipt.received.detail.wiz'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)
    institute_ids = fields.Many2many('odoocms.institute', 'receipt_received_detail_institute_rel1', 'wiz_id', 'institute_id', 'Faculties')
    journal_ids = fields.Many2many('account.journal', 'receipt_received_detail_account_journal_rel1', 'wiz_id', 'journal_id', 'Banks')

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Invoice Received Detail Report")
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
            "font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
        style_table_totals2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour ivory;")
        style_table_totals3 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour ivory;")

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 25
        col2 = worksheet.col(2)
        col2.width = 256 * 40
        col3 = worksheet.col(3)
        col3.width = 256 * 20
        col4 = worksheet.col(4)
        col4.width = 256 * 20
        col5 = worksheet.col(5)
        col5.width = 256 * 20
        col6 = worksheet.col(6)
        col6.width = 256 * 20
        col7 = worksheet.col(7)
        col7.width = 256 * 30
        col8 = worksheet.col(8)
        col8.width = 256 * 20
        col9 = worksheet.col(9)
        col9.width = 256 * 20
        col10 = worksheet.col(10)
        col10.width = 256 * 20

        col_min = 0
        col_max = 8
        row = 0
        worksheet.write_merge(row, row + 1, col_min, col_max, 'Invoice Received Detail Report ' + self.date_from.strftime("%d-%m-%Y") + " To " + self.date_to.strftime("%d-%m-%Y"), style=style_table_header2)

        row += 2
        col = 0
        table_header = ['SR#', 'Reg #', 'Name', 'Invoice Date', 'Invoice No.', 'Invoice Type', 'Faculty', 'Bank', 'Rev Amount']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'receipt.received.detail.wiz',
            'form': data
        }
        dta = self.env['report.odoocms_fee.receipt_received_detail_report']._get_report_values(self, data=datas)
        if dta['invoice']:
            sr = 1
            for r in dta['invoice']:
                row += 1
                col = 0
                worksheet.write(row, col, sr, style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['student_code'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['student_name'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['inv_date'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['inv_barcode'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['inv_type'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['institute'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, r['bank'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(r['received_amount']), style=style_date_col)
                col += 1
                sr += 1

            row += 1
            col = 0
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(dta['total_amount']), style=style_table_totals2)
            col += 1

            row += 1
            col = 0
            ttime = fields.datetime.now() + relativedelta(hours=5)
            worksheet.write_merge(row, row, 0, 4, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
            col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Invoice Received Detail Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Received Detail Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
