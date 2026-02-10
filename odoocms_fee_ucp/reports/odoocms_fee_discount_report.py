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


class OdoocmsFeeDiscountReport(models.TransientModel):
    _name = "odoocms.fee.discount.report"
    _description = "Fee Discount Report"

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    institute_ids = fields.Many2many('odoocms.institute', 'odoocms_fee_discount_rep_institute_rel1', 'report_id', 'institute_id', 'Faculties')
    program_ids = fields.Many2many('odoocms.program', 'odoocms_fee_discount_rep_program_rel1', 'report_id', 'program_id', 'Programs')

    discount_ids = fields.Many2many('odoocms.fee.waiver', 'odoocms_fee_discount_discount_rel1', 'report_id', 'discount_id', 'Discounts')
    bank_ids = fields.Many2many('account.journal', 'odoocms_fee_discount_account_journal_rel1', 'report_id', 'journal_id', 'Banks')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Credit Hours Report")
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

        col_min = 0
        col_max = 19
        row = 0

        totals = {'amount_total': 0,
                  'waiver_amount': 0,
                  'tuition_fee': 0,
                  'fine_amount': 0,
                  'misc_fee': 0}

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col4 = worksheet.col(4)
        col4.width = 256 * 20
        col8 = worksheet.col(8)
        col8.width = 256 * 30
        col9 = worksheet.col(9)
        col9.width = 256 * 30

        excluded_col_width_list = [0, 4, 8, 9]
        for i in range(col_max + 1):
            if i not in excluded_col_width_list:
                coli = worksheet.col(i)
                coli.width = 256 * 25

        worksheet.write_merge(row, row + 1, col_min, col_max, 'Discount Detail Report For ' + self.term_id.name, style=style_table_header2)

        row += 2
        col = 0
        table_header = ['SR#', 'Registration No', 'Challan ID', 'Name', 'Faculty', 'Program', 'Registration Term', 'Invoice Gross', 'Discount Type', 'Discount Percentage', 'Discount on Tuition Fee',
                        'Tuition Fee Paid', 'Admission Fee Paid', 'Attendance Fine', 'Late Fee Fine', 'Misc', 'Total Invoice Amount', 'Paid Date', 'Bank', 'Installment Type']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        dom = [('term_id', '=', self.term_id.id), ('payment_state', '=', 'paid'), ('waiver_percentage', '>', 0)]
        if self.institute_ids:
            dom.append(('registration_id.program_id.institute_id', 'in', self.institute_ids.ids))
        if self.program_ids:
            dom.append(('registration_id.program_id', 'in', self.program_ids.ids))
        if self.discount_ids:
            dom.append(('waiver_ids', 'in', self.discount_ids.ids))

        recs = self.env['account.move'].sudo().search(dom, order='student_id')

        sr = 1
        for rec in recs:
            wavier_amount = 0
            invoice_gross = 0
            if rec.waiver_percentage > 0 and not rec.waiver_percentage == 100:
                invoice_gross = round(rec.tuition_fee * (100 / (100 - rec.waiver_percentage or 1)))
                wavier_amount = round(invoice_gross * (rec.waiver_percentage / 100 or 1))
            else:
                if rec.waiver_percentage == 100:
                    for line in rec.line_ids.filtered(lambda a: a.course_credit_hours > 0):
                        invoice_gross += line.course_credit_hours * rec.student_id.batch_id.per_credit_hour_fee
                    wavier_amount = invoice_gross
                else:
                    invoice_gross = rec.tuition_fee

            _logger.info('Row No of %s Out of %s' % (sr, len(recs)))
            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)  # SR
            col += 1
            worksheet.write(row, col, rec.student_id.code or '', style=style_date_col2)  # Registration No
            col += 1
            worksheet.write(row, col, rec.old_challan_no or '', style=style_date_col2)  # Challan ID
            col += 1
            worksheet.write(row, col, rec.student_id.name or '', style=style_date_col2)  # Name
            col += 1
            worksheet.write(row, col, rec.student_id.program_id and rec.student_id.program_id.institute_id.name or '', style=style_date_col2)  # Faculty
            col += 1
            worksheet.write(row, col, rec.student_id.program_id.name, style=style_date_col2)  # Program
            col += 1
            worksheet.write(row, col, rec.session_id.name, style=style_date_col2)  # Registration Term
            col += 1
            worksheet.write(row, col, invoice_gross, style=style_date_col)  # Invoice Gross
            col += 1
            worksheet.write(row, col, rec.waiver_ids and rec.waiver_ids[0].name or '', style=style_date_col2)  # Discount Type
            col += 1
            worksheet.write(row, col, rec.waiver_percentage, style=style_date_col)  # Discount Percentage
            col += 1
            worksheet.write(row, col, wavier_amount, style=style_date_col)  # Discount on Tuition Fee
            col += 1
            worksheet.write(row, col, rec.tuition_fee, style=style_date_col)  # Tuition Fee Paid
            col += 1
            worksheet.write(row, col, rec.admission_fee, style=style_date_col)  # Admission Fee Paid
            col += 1
            worksheet.write(row, col, rec.fine_amount, style=style_date_col)  # Attendance Fine
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # Late Fee Fine
            col += 1
            worksheet.write(row, col, rec.misc_fee, style=style_date_col)  # Misc
            col += 1
            worksheet.write(row, col, rec.tuition_fee + rec.admission_fee + rec.fine_amount + rec.misc_fee, style=style_date_col)  # Total Invoice Amount
            col += 1
            worksheet.write(row, col, rec.payment_date and rec.payment_date.strftime("%d-%m-%Y"), style=style_date_col2)  # Paid Date
            col += 1
            # worksheet.write(row, col, rec.paid_bank_name, style=style_date_col2)  # Bank
            # col += 1
            worksheet.write(row, col, dict(rec.fields_get(allfields=['challan_type'])['challan_type']['selection'])[rec.challan_type], style=style_date_col2)  # Installment Type
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
        worksheet.write(row, col, '', style=style_table_totals2)
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)
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
            'name': 'Discount Detail Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Discount Detail Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
