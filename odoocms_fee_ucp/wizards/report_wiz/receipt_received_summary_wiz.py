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


class ReceiptReceivedReportWiz(models.TransientModel):
    _inherit = 'receipt.received.summary.wiz'

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)
    institute_ids = fields.Many2many('odoocms.institute', 'receipt_received_sum_institute_rel1', 'wiz_id', 'institute_id', 'Faculties')
    journal_ids = fields.Many2many('account.journal', 'receipt_received_sum_account_journal_rel1', 'wiz_id', 'journal_id', 'Banks')

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Invoice Received Summary Report")
        style_title = xlwt.easyxf(
            "font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center,vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
        style_table_header3 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour ivory;alignment: wrap True;")

        style_table_totals = xlwt.easyxf(
            "font:height 150; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
        style_date_col = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
        style_date_col2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
        style_table_totals2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz right,vert center;borders: left thin, right thin, top thin, bottom thin;")
        style_table_totals3 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz left,vert center;borders: left thin, right thin, top thin, bottom thin;")

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 20
        col2 = worksheet.col(2)
        col2.width = 256 * 20
        col3 = worksheet.col(3)
        col3.width = 256 * 20
        col4 = worksheet.col(4)
        col4.width = 256 * 20
        col5 = worksheet.col(5)
        col5.width = 256 * 20

        col_min = 0
        col_max = 19
        col = 0
        row = 0

        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'receipt.received.summary.wiz',
            'form': data
        }
        dta = self.env['report.odoocms_fee.receipt_received_summary_report']._get_report_values(self, data=datas)

        # Header
        worksheet.write_merge(row, row + 1, col_min, col_max, 'Invoice Received Summary Report', style=style_table_header2)
        row += 2

        # Header-1
        worksheet.write_merge(row, row + 1, 0, 0, "SR#", style=style_table_header)
        worksheet.write_merge(row, row + 1, 1, 1, "Transaction Date", style=style_table_header)
        worksheet.write_merge(row, row, 2, 3, "ABB", style=style_table_header)
        worksheet.write_merge(row, row, 4, 5, "BAL", style=style_table_header)
        worksheet.write_merge(row, row, 6, 7, "BIPL", style=style_table_header)
        worksheet.write_merge(row, row, 8, 9, "DIB", style=style_table_header)
        worksheet.write_merge(row, row, 10, 11, "FBL", style=style_table_header)
        worksheet.write_merge(row, row, 12, 13, "HBL", style=style_table_header)
        worksheet.write_merge(row, row, 14, 15, "TMF", style=style_table_header)
        worksheet.write_merge(row, row, 16, 17, "BOP", style=style_table_header)
        worksheet.write_merge(row, row + 1, 18, 19, "Total", style=style_table_header)
        row += 1

        # Header-2
        col = 2
        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        worksheet.write(row, col, 'Inv', style=style_table_header)
        col += 1
        worksheet.write(row, col, 'Amt', style=style_table_header)
        col += 1

        if dta['date_wise_amount']:
            invoices = dta['date_wise_amount']
            totals = dta['totals']

            sr = 1
            for inv in invoices:
                row += 1
                col = 0

                worksheet.write(row, col, sr, style=style_date_col2)
                col += 1
                worksheet.write(row, col, inv['date'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['abb_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['abb_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['bal_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['bal_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['bipl_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['bipl_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['dib_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['dib_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['fbl_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['fbl_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['hbl_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['hbl_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['tmf_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['tmf_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['bop_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['bop_amt']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['received_inv']), style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(inv['received_amount']), style=style_date_col)
                col += 1
                sr += 1

            # ***** Totals *****#
            row += 1
            col = 0
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_abb_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_abb_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_bal_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_bal_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_bipl_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_bipl_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_dib_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_dib_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_fbl_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_fbl_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_hbl_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_hbl_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_tmf_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_tmf_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_bop_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_bop_amt']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_received_inv']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['total_received_amount']), style=style_table_totals2)
            col += 1

            # Print Date and Time Display
            row += 1
            col = 0
            ttime = fields.datetime.now() + relativedelta(hours=5)
            worksheet.write_merge(row, row, 0, 5, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
            col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Invoice Received Summary Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Invoice Received Summary Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
