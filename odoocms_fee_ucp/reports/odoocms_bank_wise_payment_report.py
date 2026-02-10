# -*- coding: utf-8 -*-
import pdb

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


class OdoocmsBankWisePaymentReport(models.TransientModel):
    _name = "odoocms.bank.wise.payment.report"
    _description = "Bank Wise Payment Report"

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    date_from = fields.Date('From Date', default=fields.Date.today() - relativedelta(day=1))
    date_to = fields.Date('To Date', default=fields.Date.today)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    bank_ids = fields.Many2many('account.journal', 'odoocms_bank_wise_payment_rep_journal_rel1', 'report_id', 'journal_id', 'Banks')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Bank Wise Payment Report")
        style_title = xlwt.easyxf(
            "font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_table_header2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")

        style_table_header3 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin;alignment: wrap True;")

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

        col_min = 0
        col_max = 19
        row = 0

        totals = {
            'n_student_cnt': 0,
            'n_tuition_fee': 0,
            'n_admission_fee': 0,
            'n_late_fee': 0,
            'n_attendance_fine': 0,
            'n_misc_fee': 0,
            'n_hostel_fee': 0,
            'n_total': 0,

            'e_student_cnt': 0,
            'e_tuition_fee': 0,
            'e_admission_fee': 0,
            'e_late_fee': 0,
            'e_attendance_fine': 0,
            'e_misc_fee': 0,
            'e_hostel_fee': 0,
            'e_total': 0,

            'g_student_cnt': 0,
            'g_total': 0
        }

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        for j in range(1, col_max + 1):
            colj = worksheet.col(j)
            colj.width = 256 * 30

        period_st = self.date_from.strftime("%d-%m-%Y") + " To " + self.date_to.strftime("%d-%m-%Y")
        worksheet.write_merge(row, row + 1, col_min, col_max, 'Bank Wise Payment Report ' + period_st, style=style_table_header2)

        row += 2
        col = 0
        worksheet.write_merge(row, row, col, col + 1, '', style=style_table_header3)
        col += 2
        worksheet.write_merge(row, row, col, col + 8, 'New', style=style_table_header3)
        col += 9
        worksheet.write_merge(row, row, col, col + 7, 'Existing', style=style_table_header3)

        row += 1
        col = 0
        table_header = ['SR#', 'Date',
                        'Students Unique Count', 'Tuition Fee', 'Admission Fee', 'Late Fee', 'Attendance Fine', 'MISC', 'Hostel', 'Total',
                        'Students Unique Count', 'Tuition Fee', 'Late Fee', 'Attendance Fine', 'MISC', 'Hostel', 'Total',
                        'Students', 'Amt', 'Bank']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        dom = [('term_id', '=', self.term_id.id),
               ('payment_date', '>=', self.date_from),
               ('payment_date', '<=', self.date_to)]
        recs = self.env['account.move'].sudo().search(dom, order='student_id')

        self.env.cr.execute("""select 
                                    count(student_id) as student_cnt,sum(amount_total) as total_amount,sum(tuition_fee) as tuition_fee,sum(admission_fee) as admission_fee,
                                    sum(fine_amount) as fine_amount,sum(misc_fee) as misc_fee,sum(hostel_fee) as hostel_fee, 
                                    payment_date
                                from 
                                    account_move 
                                where 
                                    payment_date between %s and  %s and id in %s and move_type='out_invoice' 
                                group by 
                                    payment_date
                            """,
                            (self.date_from, self.date_to, tuple(recs.ids),)
                            )
        results = self.env.cr.dictfetchall()

        sr = 1
        for result in results:
            _logger.info('Row No of %s Out of %s' % (sr, len(recs)))
            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)  # Sr
            col += 1
            worksheet.write(row, col, result['payment_date'] and result['payment_date'].strftime('%d-%m-%Y') or '', style=style_date_col2)  # Date
            col += 1

            worksheet.write(row, col, '', style=style_date_col)  # N-Count
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-Tuition
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-Admission
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-Late Fee
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-Attendance
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-MISC
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-Hostel
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # N-Total
            col += 1

            worksheet.write(row, col, result['student_cnt'], style=style_date_col)  # E-Count
            col += 1
            worksheet.write(row, col, result['tuition_fee'], style=style_date_col)  # E-Tuition
            col += 1
            worksheet.write(row, col, result['fine_amount'], style=style_date_col)  # E-Late Fee
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # E-Attendance
            col += 1
            worksheet.write(row, col, result['misc_fee'], style=style_date_col)  # E-MISC
            col += 1
            worksheet.write(row, col, result['hostel_fee'], style=style_date_col)  # E-Hostel
            col += 1
            worksheet.write(row, col, result['total_amount'], style=style_date_col)  # E-Total
            col += 1

            worksheet.write(row, col, result['student_cnt'], style=style_date_col)  # G-Students
            col += 1
            worksheet.write(row, col, result['total_amount'], style=style_date_col)  # G-Amount
            col += 1
            # worksheet.write(row, col, result['paid_bank_name'], style=style_date_col2)  # Bank
            # col += 1

            sr += 1

        row += 1
        col = 0
        worksheet.write_merge(row, row, col, col + 1, 'Totals', style=style_table_totals2)
        col += 2

        worksheet.write(row, col, totals['n_student_cnt'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_tuition_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_admission_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_late_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_attendance_fine'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_misc_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_hostel_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['n_total'], style=style_table_totals2)
        col += 1

        worksheet.write(row, col, totals['e_student_cnt'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['e_tuition_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['e_late_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['e_attendance_fine'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['e_misc_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['e_hostel_fee'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['e_total'], style=style_table_totals2)
        col += 1

        worksheet.write(row, col, totals['g_student_cnt'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, totals['g_total'], style=style_table_totals2)
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)
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
            'name': 'Bank Wise Payment Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Bank Wise Payment Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
