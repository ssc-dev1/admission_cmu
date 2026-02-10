# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError
import pdb

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


class SelectedCandidateChallanReportWiz(models.TransientModel):
    _name = 'selected.candidate.challan.report.wiz'
    _description = 'Selected Candidate Challan Report Wizard'

    @api.model
    def _get_generate_invoice_id(self):
        if self.env.context.get('active_model', False) == 'generate.invoice' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    bulk_challan_id = fields.Many2one('generate.invoice', 'Register', default=_get_generate_invoice_id)

    def print_report(self):
        lines = []
        totals = {'fee_amount': 0, 'admission_amount': 0, 'scholarship_amount': 0, 'net_amount': 0}
        fee_amt = 0
        adm_amt = 0
        scholarship_amt = 0
        net_amt = 0
        if self.bulk_challan_id.lines:
            for rec in self.bulk_challan_id.lines:
                fee_amt += rec.fee_amount
                adm_amt += rec.admission_amount
                scholarship_amt += rec.scholarship_amount
                net_amt += rec.net_amount
                line = ({
                    'application_no': rec.application_id.application_no,
                    'applicant_name': rec.applicant_name,
                    'credit_hrs': rec.credit_hrs,
                    'credit_hrs_fee': rec.credit_hrs_fee,
                    'fee_amount': rec.fee_amount,
                    'admission_amount': rec.admission_amount,
                    'scholarship_name': rec.scholarship_id.name,
                    'scholarship_percentage': rec.scholarship_percentage,
                    'scholarship_amount': rec.scholarship_amount,
                    'net_amount': rec.net_amount,
                })
                lines.append(line)
            totals['fee_amount'] = fee_amt
            totals['admission_amount'] = adm_amt
            totals['scholarship_amount'] = scholarship_amt
            totals['net_amount'] = net_amt

        data = {
            'company_name': self.bulk_challan_id.company_id.name,
            'merit_list': self.bulk_challan_id.merit_id.name,
            'program': self.bulk_challan_id.program_id.name,
            'totals': totals,
            'lines': lines,
        }
        return self.env.ref('odoocms_admission_fee.action_selected_candidate_challan_report').with_context(landscape=True).report_action(self, data=data)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Selected Candidate Challan Report")
        style_title = xlwt.easyxf("font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;")
        style_table_header = xlwt.easyxf("font:height 150; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin;")
        style_table_header2 = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin;alignment: wrap True;")
        style_table_header3 = xlwt.easyxf("font:height 150; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; alignment: wrap True;")

        style_date_col = xlwt.easyxf("font:height 180; font: name Liberation Sans,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin;")
        style_date_col2 = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;")
        style_table_totals2 = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin;")
        style_table_totals3 = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;")

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 20
        col2 = worksheet.col(2)
        col2.width = 256 * 35
        col3 = worksheet.col(3)
        col3.width = 256 * 25
        col4 = worksheet.col(4)
        col4.width = 256 * 25
        col5 = worksheet.col(5)
        col5.width = 256 * 25
        col6 = worksheet.col(6)
        col6.width = 256 * 25
        col7 = worksheet.col(7)
        col7.width = 256 * 25
        col8 = worksheet.col(8)
        col8.width = 256 * 25
        col9 = worksheet.col(9)
        col9.width = 256 * 25
        col10 = worksheet.col(10)
        col10.width = 256 * 25

        col_min = 0
        col_max = 10
        row = 0

        worksheet.write_merge(row, row + 1, col_min, col_max, self.bulk_challan_id.company_id.name, style=style_table_header2)
        row += 2
        worksheet.write_merge(row, row, col_min, col_max, 'Selected Candidate Challan Report', style=style_table_header2)
        row += 1
        col = 0

        tb_headers = ["Sr#", "Application# ", "Applicant Name", "Per Credit Hour Fee", "Total Credit Hours", "Fee Amount",
                      "Admission Fee", "Scholarship", "Scholarship %", "Scholarship Amount", "Net Receivable"]
        col = 0
        for i in range(0, col_max + 1):
            worksheet.write(row, col, tb_headers[i], style=style_table_header)
            col += 1

        dta = self.print_report()
        if dta:
            sr = 1
            lines = dta['data']['lines']
            totals = dta['data']['totals']
            for line in lines:
                row += 1
                col = 0
                worksheet.write(row, col, sr, style=style_date_col2)
                col += 1
                worksheet.write(row, col, line['application_no'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, line['applicant_name'], style=style_date_col2)
                col += 1
                worksheet.write(row, col, line['credit_hrs_fee'], style=style_date_col)
                col += 1
                worksheet.write(row, col, line['credit_hrs'], style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(line['fee_amount']), style=style_date_col)
                col += 1
                worksheet.write(row, col, line['admission_amount'] and '{0:,.0f}'.format(line['admission_amount']) or '', style=style_date_col)
                col += 1
                worksheet.write(row, col, line['scholarship_name'] and line['scholarship_name'] or '', style=style_date_col2)
                col += 1
                worksheet.write(row, col, line['scholarship_percentage'] and '{0:,.0f}'.format(line['scholarship_percentage']) or '', style=style_date_col)
                col += 1
                worksheet.write(row, col, line['scholarship_amount'] and '{0:,.0f}'.format(line['scholarship_amount']) or '', style=style_date_col)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(line['net_amount']), style=style_date_col)
                col += 1
                sr += 1

            row += 1
            col = 0
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['fee_amount']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['admission_amount']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['scholarship_amount']), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(totals['net_amount']), style=style_table_totals2)
            col += 1

        row += 2
        ttime = fields.datetime.now() + relativedelta(hours=5)
        worksheet.write_merge(row, row, 0, 2, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
        col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['excel.reports.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Selected Candidate Challan Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Selected Candidate Challan ',
            'res_model': 'excel.reports.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }


class ExcelReportsSaveWizard(models.TransientModel):
    _name = "excel.reports.save.wizard"
    _description = 'Excel Reports Save Wizard'

    name = fields.Char('filename', readonly=True)
    data = fields.Binary('file', readonly=True)
