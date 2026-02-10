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


class FeeDefaulterRepWiz(models.TransientModel):
    _name = 'fee.defaulter.rep.wiz'
    _description = 'Fee Defaulter Report'

    @api.model
    def get_default_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        if term_id:
            return term_id.id
        else:
            return False

    faculty_ids = fields.Many2many('odoocms.institute', 'fee_defaulter_faculty_rep_rel', 'wiz_id', 'faculty_id', 'Faculties')
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_default_term)
    exclude_due_date = fields.Boolean('Exclude Due Date', default=False)
    exclude_withdraw_students = fields.Boolean('Exclude Withdraw Students', default=False)
    label_id = fields.Many2one('account.payment.term.label', 'Label')

    def print_report(self):
        self.ensure_one()
        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'fee.defaulter.rep.wiz',
            'form': data
        }
        return self.env.ref('odoocms_fee_ucp.action_fee_defaulter_report').with_context(landscape=True).report_action(self, data=datas, config=False)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Fee Defaulter Report")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center,vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
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
        col7.width = 256 * 20
        col8 = worksheet.col(8)
        col8.width = 256 * 20
        col9 = worksheet.col(9)
        col9.width = 256 * 20

        col_min = 0
        col_max = 9
        col = 0
        row = 0

        [data] = self.read()
        datas = {
            'ids': [],
            'model': 'fee.defaulter.rep.wiz',
            'form': data
        }
        dta = self.env['report.odoocms_fee_ucp.fee_defaulter_report']._get_report_values(self, data=datas)

        # Header
        worksheet.write_merge(row, row + 1, col_min, col_max, 'Fee Defaulter Report', style=style_table_header2)
        row += 2
        worksheet.write_merge(row, row, col_min, col_max, dta['term'].name + "-" + dta['label'], style=style_table_header2)
        row += 1

        table_header = ['SR#', 'Reg No', 'Name', 'Amount', 'Fine Amount', 'Due Date', 'Fee Type', 'Invoice Status', 'Registration Status', 'Remarks']
        for i in range(col_min, col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        if dta['data_lines']:
            total_amount = 0
            fine_amount = 0
            data_lines = dta['data_lines']
            for data_line in data_lines:
                row += 1
                col = 0
                worksheet.write_merge(row, row, col, col + 2, data_line['faculty_name'] + "-" + data_line['faculty_code'], style=style_table_totals3)

                sr = 1
                faculty_total_amount = 0
                faculty_fine_amount = 0
                for line in data_line['lines']:
                    move = line.line_ids.mapped('move_id')
                    inv = move[0]

                    row += 1
                    col = 0
                    worksheet.write(row, col, sr, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, line.student_id.code, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, line.student_id.name, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, '{0:,.2f}'.format(line.amount_residual), style=style_date_col)
                    col += 1
                    worksheet.write(row, col, '', style=style_date_col)
                    col += 1
                    worksheet.write(row, col, line.date_due.strftime("%d-%m-%Y"), style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, dta['label'])
                    col += 1
                    worksheet.write(row, col, dict(inv.fields_get(allfields=['payment_state'])['payment_state']['selection'])[inv.payment_state], style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, dict(line.student_id.fields_get(allfields=['state'])['state']['selection'])[line.student_id.state], style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, '', style=style_date_col2)
                    col += 1
                    sr += 1

                    faculty_total_amount += line.amount_residual
                    faculty_fine_amount = 0

                total_amount += faculty_total_amount
                fine_amount = faculty_fine_amount

                # ***** Faculty Total *****#
                row += 1
                col = 0
                worksheet.write(row, col, '', style=style_table_totals2)
                col += 1
                worksheet.write(row, col, '', style=style_table_totals2)
                col += 1
                worksheet.write(row, col, '', style=style_table_totals2)
                col += 1
                worksheet.write(row, col, '{0:,.2f}'.format(faculty_total_amount), style=style_table_totals2)
                col += 1
                worksheet.write(row, col, '{0:,.2f}'.format(faculty_fine_amount), style=style_table_totals2)
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

            # ***** Grand Total *****#
            row += 1
            col = 0
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '', style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.2f}'.format(total_amount), style=style_table_totals2)
            col += 1
            worksheet.write(row, col, '{0:,.2f}'.format(fine_amount), style=style_table_totals2)
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
            'name': 'Fee Defaulter Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Fee Defaulter Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
