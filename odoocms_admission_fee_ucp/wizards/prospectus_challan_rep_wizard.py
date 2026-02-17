# -*- coding: utf-8 -*-
import io
import logging

from odoo import models, fields
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

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


class ProspectusChallanDetailRepWiz(models.TransientModel):
    _name = 'prospectus.challan.rep.wiz'
    _description = 'Prospectus Challans Report '

    date_from = fields.Date('From Date', default=fields.Date.today() + relativedelta(day=1))
    date_to = fields.Date('To Date', default=fields.Date.today())
    source = fields.Selection([('admission', 'Admission Department'),
                               ('finance', 'Finance Department'),
                               ('auto', 'Bank'),
                               ('all', 'All'),
                               ], string='Voucher Verify Source')
    program_id = fields.Many2one('odoocms.program', 'Program')

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'prospectus.challan.rep.wiz',
            'form': data
        }
        return self.env.ref('odoocms_admission_fee_ucp.action_prospectus_challan_rep').with_context(landscape=True).report_action(self, data=datas)

    def make_excel(self):
        row = 0
        col_min = 0
        col_max = 12
        workbook, worksheet = self.setup_workbook()
        self.write_header(worksheet, row=row, col_min=col_min, col_max=col_max)
        row += 2
        self.write_data(worksheet, row=row)
        return self.save_workbook(workbook)

    def setup_workbook(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Prospectus Challan Detail Report")

        # Set column widths
        col_widths = [15, 45, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25, 25]
        for i, width in enumerate(col_widths):
            worksheet.col(i).width = 256 * width
        return workbook, worksheet

    def write_header(self, worksheet, row, col_min, col_max):
        style_title = xlwt.easyxf("font:height 300; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;")
        worksheet.write_merge(row, row + 1, col_min, col_max, self.env.company.name, style=style_title)

    def write_data(self, worksheet, row):
        style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin;")
        table_header = ["Sr No", "Candidate Name", "Reference No", "Program Applied For", "Faculty", "Date Enter By",
                        'Payment Verify By', "Payment Sub Type", "Prospectus Fee", "References", "Paid Date", "Payment Confirmation",
                        "Challan#"]
        for i, header in enumerate(table_header):
            worksheet.write(row, i, header, style=style_table_header)

        # Process and write data
        self.process_data(worksheet, row=row)

    def save_workbook(self, workbook):
        file_data = io.BytesIO()
        workbook.save(file_data)

        wiz_id = self.env['excel.reports.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Prospectus Challan Report.xls'
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Prospectus Challan Report',
            'res_model': 'excel.reports.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'views': [[False, 'form']],
            'res_id': wiz_id.id,
            'target': 'new',
            'context': self._context,
        }

    def process_data(self, worksheet, row):
        style_title = xlwt.easyxf("font:height 300; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;")
        style_table_header = xlwt.easyxf("font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour silver_ega;")
        style_date_col = xlwt.easyxf("font:height 180; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;")
        style_date_col2 = xlwt.easyxf("font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;")
        style_col_totals = xlwt.easyxf("font:height 200; font: name Liberation Sans,color black,bold on; align: horiz right;borders: left thin, right thin, top thin, bottom thin;")

        # ***** Called Report *****#
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'prospectus.challan.rep.wiz',
            'form': data
        }

        dta = self.env['report.odoocms_admission_fee_ucp.prospectus_challan_report']._get_report_values(self, data=datas)
        lines = dta['lines']
        faculty_summary_lines = dta['faculty_summary_lines']
        deo_summary_lines = dta['deo_summary_lines']

        sr = 1
        total_amount = 0
        for line in lines:
            candidate = 'Candidate'
            if not line.create_uid.login == 'public':
                candidate = line.create_uid.login.split('@')[0]

            source = ''
            if line.fee_voucher_verify_source == 'auto':
                source = 'Auto Bank'
            if not line.fee_voucher_verify_source == 'auto' and line.fee_voucher_verify_by:
                source = line.fee_voucher_verify_by.login.split('@')[0]

            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col)
            col += 1
            worksheet.write(row, col, line.name, style=style_date_col)
            col += 1
            worksheet.write(row, col, line.application_no and line.application_no or '', style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.program_id.code and line.prospectus_inv_id.program_id.code or '', style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.program_id.institute_id.code and line.prospectus_inv_id.program_id.institute_id.code or '', style=style_date_col)
            col += 1
            worksheet.write(row, col, candidate, style=style_date_col)
            col += 1
            worksheet.write(row, col, source, style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.sudo().get_paid_bank_name(), style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.amount_total, style=style_date_col2)
            col += 1
            worksheet.write(row, col, len(line.preference_ids), style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.payment_date and line.prospectus_inv_id.payment_date.strftime('%d-%m-%Y') or '', style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.confirmation_date and line.prospectus_inv_id.confirmation_date.strftime("%d-%m-%Y") or '', style=style_date_col)
            col += 1
            worksheet.write(row, col, line.prospectus_inv_id.old_challan_no and line.prospectus_inv_id.old_challan_no or '', style=style_date_col)
            col += 1
            sr += 1
            total_amount += line.prospectus_inv_id.amount_total

        row += 1
        col = 0
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, total_amount, style=style_col_totals)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1
        worksheet.write(row, col, '', style=style_date_col)
        col += 1

        # ***** Summary  *****#
        row += 2
        worksheet.write_merge(row, row, 6, 8, 'Summary', style=style_title)

        # *****Faculty Summary *****#
        col = 4
        row += 1
        deo_row = row
        f_total_amount = 0
        worksheet.write(row, col, "Faculty", style=style_table_header)
        col += 1
        worksheet.write(row, col, "Count", style=style_table_header)
        col += 1
        worksheet.write(row, col, "Amount", style=style_table_header)
        col += 1

        for f_line in faculty_summary_lines:
            row += 1
            col = 4
            worksheet.write(row, col, f_line['faculty'], style=style_date_col)
            col += 1
            worksheet.write(row, col, f_line['cnt'], style=style_date_col2)
            col += 1
            worksheet.write(row, col, f_line['amount'], style=style_date_col2)
            col += 1
            f_total_amount += f_line['amount']

        row += 1
        col = 4
        worksheet.write(row, col, "", style=style_date_col)
        col += 1
        worksheet.write(row, col, "Total", style=style_col_totals)
        col += 1
        worksheet.write(row, col, f_total_amount, style=style_col_totals)
        col += 1

        # ***** DEO Summary *****#
        col = 8
        deo_total_amount = 0
        worksheet.write(deo_row, col, "Deo", style=style_table_header)
        col += 1
        worksheet.write(deo_row, col, "Count", style=style_table_header)
        col += 1
        worksheet.write(deo_row, col, "Amount", style=style_table_header)
        col += 1

        for deo_line in deo_summary_lines:
            deo_row += 1
            col = 8
            worksheet.write(deo_row, col, deo_line['deo'], style=style_date_col)
            col += 1
            worksheet.write(deo_row, col, deo_line['cnt'], style=style_date_col2)
            col += 1
            worksheet.write(deo_row, col, deo_line['amount'], style=style_date_col2)
            col += 1
            f_total_amount += deo_line['amount']

        deo_row += 1
        col = 8
        worksheet.write(deo_row, col, "", style=style_date_col)
        col += 1
        worksheet.write(deo_row, col, "Total", style=style_col_totals)
        col += 1
        worksheet.write(deo_row, col, f_total_amount, style=style_col_totals)
        col += 1
