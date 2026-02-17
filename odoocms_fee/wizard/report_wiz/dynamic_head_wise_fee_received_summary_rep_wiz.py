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


class DynamicHeadWiseFeeReceivedSummaryRepWiz(models.TransientModel):
    _name = 'dynamic.head.wise.fee.received.summary.rep.wiz'
    _description = 'Head Wise Fee Received Summary Report'

    date_from = fields.Date('From Date', default=fields.Date.today() + relativedelta(day=1))
    date_to = fields.Date('To Date', default=fields.Date.today())
    include_surplus = fields.Boolean('Include Surplus', default=False)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Head Wise Fee Received Summary Report")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
        style_date_col = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
        style_date_col2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
        style_table_totals3 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour ivory;")

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 50
        for c_no in range(2, 20):
            colc_no = worksheet.col(c_no)
            colc_no.width = 256 * 16
        fee_head_list = []
        fee_payments = self.env['odoocms.fee.payment'].search([('date', '>=', self.date_from),
                                                               ('date', '<=', self.date_to)])

        total_row_amount = 0
        invoice_list = []
        move_ids = []
        if fee_payments:
            if len(fee_payments)==1:
                self.env.cr.execute("select distinct invoice_id from odoocms_fee_payment where id = %s" % fee_payments.id)
            if len(fee_payments) > 1:
                self.env.cr.execute("select distinct invoice_id from odoocms_fee_payment where id in %s" % (tuple(fee_payments.ids),))
            inv_results = self.env.cr.dictfetchall()
            for inv_result in inv_results:
                invoice_list.append(inv_result['invoice_id'])
            if invoice_list:
                move_ids = self.env['account.move'].browse(invoice_list)

            if len(move_ids)==1:
                self.env.cr.execute("select distinct fee_head_id from account_move_line where move_id = %s" % move_ids.id)
            if len(move_ids) > 1:
                self.env.cr.execute("select distinct fee_head_id from account_move_line where move_id in %s" % (tuple(move_ids.ids),))
            fee_heads = self.env.cr.dictfetchall()
            for fee_head in fee_heads:
                if fee_head['fee_head_id'] is not None:
                    fee_head_list.append(fee_head['fee_head_id'])

            header_length = 8
            table_header = ['SR# No.', 'School Name', 'School Code']
            if fee_head_list:
                fee_head_recs = self.env['odoocms.fee.head'].search([('id', 'in', fee_head_list)], order='id asc')
                header_length += len(fee_head_recs)
                for fee_head_rec in fee_head_recs:
                    table_header.append(fee_head_rec.name)

                table_header.append('Waiver')
                table_header.append('Total')
                table_header.append('Partial Payment')
                table_header.append('Adjustment')
                table_header.append('Prev. Arrears')
                table_header.append('NET')

            worksheet.write_merge(0, 1, 0, header_length, 'Head Wise Fee Received Summary Report', style=style_table_header2)
            worksheet.write_merge(2, 2, 0, header_length, 'From ' + self.date_from.strftime('%d-%b-%Y') + " to " + self.date_to.strftime('%d-%b-%Y'), style=style_table_header2)

            row = 3
            col = 0

            for i in range(header_length + 1):
                worksheet.write(row, col, table_header[i], style=style_table_header)
                col += 1

            institute_ids = self.env['odoocms.institute'].search([])
            if institute_ids:
                surplus_amount = 0
                sr = 1
                for institute_id in institute_ids:
                    row_total = 0
                    partial_amount = 0
                    institute_net = 0
                    adjustment_amount = 0
                    prev_arrears_amount = 0

                    row += 1
                    col = 0
                    worksheet.write(row, col, sr, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, institute_id.name, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, institute_id.code, style=style_date_col2)
                    col += 1
                    sr += 1

                    if fee_payments:
                        for fee_head_rec in fee_head_recs:
                            self.env.cr.execute("select sum(price_total) as total from account_move_line where  move_id in %s and fee_head_id = %s and institute_id	= %s", (tuple(move_ids.ids), fee_head_rec.id, institute_id.id))
                            result = self.env.cr.dictfetchall()
                            worksheet.write(row, col, result[0]['total'], style=style_date_col)
                            row_total = row_total + (result[0]['total'] if result[0]['total'] is not None else 0)
                            col += 1

                        # Waiver Amount
                        waiver_amount = 0
                        if len(move_ids)==1:
                            self.env.cr.execute("select sum(waiver_amount) as waiver_amount from account_move where id = %s and institute_id= %s", (move_ids.id, institute_id.id))
                        if len(move_ids) > 1:
                            self.env.cr.execute("select sum(waiver_amount) as waiver_amount from account_move where id in %s and institute_id= %s", (tuple(move_ids.ids), institute_id.id))
                        w_result = self.env.cr.dictfetchall()
                        if w_result[0]['waiver_amount'] is not None:
                            waiver_amount = w_result[0]['waiver_amount']
                        worksheet.write(row, col, waiver_amount, style=style_date_col)
                        col += 1
                        worksheet.write(row, col, row_total, style=style_date_col)
                        col += 1

                        partial_payment_recs = self.env['odoocms.fee.payment'].search([('invoice_id', 'in', move_ids.ids),
                                                                                       ('date', '<', self.date_from),
                                                                                       ('institute_id', '=', institute_id.id)], order='institute_id')
                        # Partial Payment
                        if partial_payment_recs:
                            for partial_payment_rec in partial_payment_recs:
                                partial_amount += partial_payment_rec.received_amount
                        worksheet.write(row, col, partial_amount, style=style_date_col)
                        col += 1

                        # Adjustment Calculations
                        if len(move_ids)==1:
                            self.env.cr.execute("select sum(price_subtotal) as adjustment_amount from account_move_line where name='Adjustment' and move_id = %s and institute_id = %s", (move_ids.id, institute_id.id))
                        if len(move_ids) > 1:
                            self.env.cr.execute("select sum(price_subtotal) as adjustment_amount from account_move_line where name='Adjustment' and move_id in %s and institute_id = %s", (tuple(move_ids.ids), institute_id.id))
                        result100 = self.env.cr.dictfetchall()
                        if result100[0]['adjustment_amount'] is not None:
                            adjustment_amount = result100[0]['adjustment_amount']

                        worksheet.write(row, col, adjustment_amount, style=style_date_col)
                        col += 1

                        # Previous Arrears Calculations
                        if len(move_ids)==1:
                            self.env.cr.execute("select sum(price_subtotal) as prev_arrears_amount from account_move_line where name in ('Previous Arrears ','Previous Arrears',' Previous Arrears', 'Previous Arrears ', ' Previous Arrears ') and move_id = %s and institute_id = %s", (move_ids.id, institute_id.id))
                        if len(move_ids) > 1:
                            self.env.cr.execute("select sum(price_subtotal) as prev_arrears_amount from account_move_line where name in ('Previous Arrears ','Previous Arrears',' Previous Arrears', 'Previous Arrears ', ' Previous Arrears ') and move_id in %s and institute_id = %s", (tuple(move_ids.ids), institute_id.id))
                        result101 = self.env.cr.dictfetchall()
                        if result101[0]['prev_arrears_amount'] is not None:
                            prev_arrears_amount = result101[0]['prev_arrears_amount']
                        worksheet.write(row, col, prev_arrears_amount, style=style_date_col)
                        col += 1

                        # Institute NET
                        institute_net = row_total - waiver_amount - partial_amount - abs(adjustment_amount) + prev_arrears_amount
                        total_row_amount += institute_net
                        worksheet.write(row, col, institute_net, style=style_date_col)
                        col += 1

                # Total
                row += 1
                col = 0
                worksheet.write(row, col, 'Total', style=style_date_col)
                col += 1
                for r in range(header_length - 1):
                    worksheet.write(row, col, '', style=style_date_col)
                    col += 1
                worksheet.write(row, col, total_row_amount, style=style_date_col)
                col += 1

                # Surplus
                row += 1
                col = 0
                if self.include_surplus:
                    payment_registers = self.env['odoocms.fee.payment.register'].search([('date', '>=', self.date_from),
                                                                                         ('date', '<=', self.date_to),
                                                                                         ('state', 'in', ('Draft', 'Posted'))])
                    for payment_register in payment_registers:
                        surplus_amount = surplus_amount + payment_register.total_diff_amount

                worksheet.write(row, col, 'Surplus', style=style_date_col)
                col += 1
                for s in range(header_length - 1):
                    worksheet.write(row, col, '', style=style_date_col)
                    col += 1
                worksheet.write(row, col, surplus_amount, style=style_date_col)
                col += 1

                # Report Print Datetime
                row += 1
                col = 0
                ttime = fields.datetime.now() + relativedelta(hours=5)
                worksheet.write_merge(row, row, 0, 2, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
                col += 1
                # Create
                self.create_partial_payment_sheet(workbook)

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Head Wise Fee Received Summary Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Head Wise Fee Received Summary Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }

    def create_partial_payment_sheet(self, workbook):
        worksheet = workbook.add_sheet("Partial Payment Report")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")

        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
        style_date_col = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
        style_date_col2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
        table_header = ['SR# No.', 'Student', 'Student ID', 'Institute ', 'Invoice Barcode', 'Invoice Amount', 'Paid Amount', 'Paid Date']

        col0 = worksheet.col(0)
        col0.width = 256 * 20
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
        col6 = worksheet.col(6)
        col6.width = 256 * 20
        col7 = worksheet.col(7)
        col7.width = 256 * 20
        col8 = worksheet.col(8)
        col8.width = 256 * 20
        col9 = worksheet.col(9)
        col9.width = 256 * 20
        col10 = worksheet.col(10)
        col10.width = 256 * 20

        row = 0
        col = 0
        for i in range(len(table_header)):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        fee_head_list = []
        fee_payments = self.env['odoocms.fee.payment'].search([('date', '>=', self.date_from),
                                                               ('date', '<=', self.date_to),
                                                               ])

        invoice_list = []
        move_ids = False
        if len(fee_payments)==1:
            self.env.cr.execute("select distinct invoice_id from odoocms_fee_payment where id = %s" % fee_payments.id)
        if len(fee_payments) > 1:
            self.env.cr.execute("select distinct invoice_id from odoocms_fee_payment where id in %s" % (tuple(fee_payments.ids),))

        inv_results = self.env.cr.dictfetchall()
        for inv_result in inv_results:
            invoice_list.append(inv_result['invoice_id'])
        if invoice_list:
            partial_payment_recs = self.env['odoocms.fee.payment'].search([('invoice_id', 'in', invoice_list),
                                                                           ('date', '<', self.date_from)], order='institute_id')
            sr = 1
            if partial_payment_recs:
                for partial_payment_rec in partial_payment_recs:
                    row += 1
                    col = 0
                    worksheet.write(row, col, sr, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.student_id.name, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.student_id.code, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.institute_id.code, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.receipt_number, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.amount, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.received_amount, style=style_date_col2)
                    col += 1
                    worksheet.write(row, col, partial_payment_rec.date.strftime('%d-%m-%Y'), style=style_date_col2)
                    col += 1
                    sr += 1
