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


class StudentFeeChargedRepWiz(models.TransientModel):
    _name = 'student.fee.charged.rep.wiz'
    _description = 'Student Fee Charged Report'

    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    institute_ids = fields.Many2many('odoocms.institute', 'student_fee_charged_institute_rel', 'fee_charged_rep_id', 'institute_id', 'Institutes')

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Student Fee Charged Report")
        style_title = xlwt.easyxf(
            "font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
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
        col1.width = 256 * 30
        col2 = worksheet.col(2)
        col2.width = 256 * 15
        col3 = worksheet.col(3)
        col3.width = 256 * 15
        col4 = worksheet.col(4)
        col4.width = 256 * 15
        col5 = worksheet.col(5)
        col5.width = 256 * 15

        tb_header = self.get_table_headers(self.institute_ids, self.term_id)
        header_length = len(tb_header) - 1
        worksheet.write_merge(0, 1, 0, header_length, 'Student Fee Charged Report of ' + self.term_id.name, style=style_table_header2)

        row = 3
        col = 0

        total_line = {}
        for key, value in tb_header.items():
            total_line[key] = 0
            worksheet.write(row, col, tb_header[key], style=style_table_header)
            col += 1

        total_line['sr'] = ''
        total_line['name'] = ''
        total_line['code'] = ''
        total_line['barcode'] = ''
        fee_receipts = self.env['account.move'].search([('institute_id', 'in', self.institute_ids.ids),
                                                        ('term_id', '=', self.term_id.id),
                                                        ('reversed_entry_id', '=', False),
                                                        ('is_scholarship_fee', '=', False),
                                                        ('amount_total', '>', 0),
                                                        ('mov_type', '=', 'out_invoice'),
                                                        ])

        sr = 0
        lines = []
        for fee_receipt in fee_receipts:
            sr += 1
            total = 0
            self.env.cr.execute("""select sum(price_subtotal) as amount,fee_head_id from account_move_line where move_id = %s and fee_head_id is not null group by fee_head_id""" % fee_receipt.id)
            results = self.env.cr.dictfetchall()
            line = {
                'sr': sr,
                'name': fee_receipt.student_id.name,
                'code': fee_receipt.student_id.code,
                'barcode': fee_receipt.barcode,
            }
            for result in results:
                key = result['fee_head_id']
                amount = result['amount']
                line[key] = amount
                total += amount if amount > 0 else 0
                total_line[key] += amount
            line['total'] = total
            total_line['total'] += total
            lines.append(line)
        lines.append(total_line)

        for ln in lines:
            row += 1
            col = 0
            for tbh in tb_header:
                worksheet.write(row, col, ln.get(tbh), style=style_date_col)
                col += 1

        row += 1
        col = 0
        ttime = fields.datetime.now() + relativedelta(hours=5)
        worksheet.write_merge(row, row, 0, header_length, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
        col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Student Fee Charged Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Student Fee Charged  Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }

    # Table Headers
    def get_table_headers(self, institute_ids, term_id):
        fee_head_list = []
        tb_header = {}
        all_receipts = self.env['account.move'].search([('institute_id', 'in', self.institute_ids.ids),
                                                        ('term_id', '=', self.term_id.id),
                                                        ('reversed_entry_id', '=', False),
                                                        ('is_scholarship_fee', '=', False),
                                                        ('amount_total', '>', 0),
                                                        ('move_type', '=', 'out_invoice'),
                                                        ])

        if all_receipts:
            self.env.cr.execute("""select distinct fee_head_id from account_move_line where move_id in %s and fee_head_id is not null order by fee_head_id;""" % (tuple(all_receipts.ids),))
            fee_head_results = self.env.cr.dictfetchall()
            if fee_head_results:
                for fee_head_result in fee_head_results:
                    fee_head_list.append(fee_head_result['fee_head_id'])

            tb_header = {
                'sr': 'SR',
                'name': 'Student',
                'code': 'Code',
                'barcode': 'Barcode',
            }
            fee_heads = self.env['odoocms.fee.head'].browse(fee_head_list)
            for fee_head in fee_heads:
                tb_header[fee_head.id] = fee_head.name
            tb_header['total'] = 'Total'
        return tb_header
