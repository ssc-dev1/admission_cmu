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


class OdoocmsChallanStatusReport(models.TransientModel):
    _name = "odoocms.challan.status.report"
    _description = "Challan Status Report"

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    institute_ids = fields.Many2many('odoocms.institute', 'odoocms_challan_status_rep_institute_rel1', 'report_id', 'institute_id', 'Faculties')
    program_ids = fields.Many2many('odoocms.program', 'odoocms_challan_status_rep_program_rel1', 'report_id', 'program_id', 'Programs')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Challan Status Report")
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

        totals = {
            'generated_challan': 0,
            'generated_challan_amount': 0,
            'paid_challan': 0,
            'paid_challan_amount': 0,
            'printed_challan': 0,
            'printed_challan_amount': 0,
        }

        challan_type = {'main_challan': 'Main Challan',
                        '2nd_challan': 'Second Challan',
                        'admission': 'New Admission',
                        'admission_2nd_challan': 'Admission 2nd Challan',
                        'add_drop': 'Add Drop',
                        'prospectus_challan': 'Prospectus Challan',
                        'hostel_fee': 'Hostel Fee',
                        'misc_challan': 'Misc Challan',
                        'installment': 'Installment'
                        }

        col_min = 0
        col_max = 12
        row = 0

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 25
        col2 = worksheet.col(2)
        col2.width = 256 * 40
        col3 = worksheet.col(3)
        col3.width = 256 * 30
        col4 = worksheet.col(4)
        col4.width = 256 * 30
        col5 = worksheet.col(5)
        col5.width = 256 * 30
        col6 = worksheet.col(6)
        col6.width = 256 * 30
        col7 = worksheet.col(7)
        col7.width = 256 * 30
        col8 = worksheet.col(8)
        col8.width = 256 * 30
        col9 = worksheet.col(9)
        col9.width = 256 * 30
        col10 = worksheet.col(10)
        col10.width = 256 * 30
        col11 = worksheet.col(11)
        col11.width = 256 * 30
        col12 = worksheet.col(12)
        col12.width = 256 * 30

        worksheet.write_merge(row, row + 1, col_min, col_max, 'Challan Status Report For ' + self.term_id.name, style=style_table_header2)

        row += 2
        col = 0
        table_header = ['SR#', 'Term', 'Faculty', 'Program', 'Challan Type', 'No. of Challan Generated', 'Amount', 'No. of Challan Printed',
                        'Amount of Printed Challans', 'No. of Challan Paid', 'Amount Collected', 'No. of Challan Unpaid', 'Amount To be Collected']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        dom = [('term_id', '=', self.term_id.id)]
        if self.institute_ids:
            dom.append(('institute_id', 'in', self.institute_ids.ids))
        if self.program_ids:
            dom.append(('program_id', 'in', self.program_ids.ids))

        recs = self.env['account.move'].sudo().search(dom, order='student_id')

        self.env.cr.execute("""
                            select 
                                count(m.*) as challan_cnt, sum(m.amount_total) as challan_amount, m.challan_type as challan_type,p.code as program_code,p.id as program_id,i.code as faculty_code,i.id as faculty_id,t.code as term_code
                            from 
                                account_move m, odoocms_program p,odoocms_institute i, odoocms_academic_term t
                            where 
                                m.term_id=%s and m.id in %s and m.program_id = p.id and p.institute_id = i.id and m.term_id = t.id 
                            group by 
                                m.challan_type,m.challan_type,p.code,p.id,i.code,i.id,t.code
                            """,
                            (self.term_id.id, tuple(recs.ids),)
                            )
        results = self.env.cr.dictfetchall()

        sr = 1
        for result in results:
            _logger.info('Row No of %s Out of %s' % (sr, len(recs)))

            # ***** Paid Challan Detail *****#
            self.env.cr.execute("""
                                    select 
                                        count(m.*) as paid_challan_cnt, sum(m.amount_total) as paid_amount,m.challan_type as challan_type
                                    from 
                                            account_move m, odoocms_program p,odoocms_institute i, odoocms_academic_term t
                                    where 
                                            m.term_id=%s and m.id in %s and m.program_id = p.id and p.institute_id = i.id and m.term_id = t.id  and m.payment_state = 'paid' and m.challan_type = %s and p.id= %s and i.id=%s and t.id=%s
                                    group by 
                                            m.challan_type
                                """,
                                (self.term_id.id, tuple(recs.ids), result['challan_type'], result['program_id'], result['faculty_id'], self.term_id.id)
                                )
            paid_result = self.env.cr.dictfetchall()

            # ***** unpaid Challan Detail *****#
            self.env.cr.execute("""
                                    select 
                                        count(m.*) as unpaid_challan_cnt, sum(m.amount_total) as unpaid_amount,m.challan_type as challan_type
                                    from 
                                        account_move m, odoocms_program p,odoocms_institute i, odoocms_academic_term t
                                    where 
                                        m.term_id=%s and m.id in %s and m.program_id = p.id and p.institute_id = i.id and m.term_id = t.id  and m.payment_state not in('in_payment','paid','cancel') and m.challan_type = %s and p.id= %s and i.id=%s and t.id=%s
                                    group by 
                                        m.challan_type
                                """,
                                (self.term_id.id, tuple(recs.ids), result['challan_type'], result['program_id'], result['faculty_id'], self.term_id.id)
                                )
            unpaid_result = self.env.cr.dictfetchall()

            # ***** Printed Challan Detail *****#
            self.env.cr.execute("""
                                    select 
                                        count(m.*) as printed_challan_cnt, sum(m.amount_total) as printed_amount,m.challan_type as challan_type
                                    from 
                                        account_move m, odoocms_program p,odoocms_institute i, odoocms_academic_term t
                                    where 
                                        m.term_id=%s and m.id in %s and m.program_id = p.id and p.institute_id = i.id and m.term_id = t.id  and 
                                        m.challan_type = %s and p.id= %s and i.id=%s and t.id=%s and m.download_time is not null
                                    group by 
                                    m.challan_type
                                """,
                                (self.term_id.id, tuple(recs.ids), result['challan_type'], result['program_id'], result['faculty_id'], self.term_id.id)
                                )
            printed_result = self.env.cr.dictfetchall()

            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)  # Sr
            col += 1
            worksheet.write(row, col, result['term_code'], style=style_date_col2)  # Term
            col += 1
            worksheet.write(row, col, result['faculty_code'], style=style_date_col2)  # Faculty
            col += 1
            worksheet.write(row, col, result['program_code'], style=style_date_col2)  # Program
            col += 1
            worksheet.write(row, col, challan_type.get(result['challan_type'], '-'), style=style_date_col2)  # Challan Type
            col += 1
            worksheet.write(row, col, result['challan_cnt'], style=style_date_col)  # No. of Challan Generated
            col += 1
            worksheet.write(row, col, result['challan_amount'], style=style_date_col)  # Amount
            col += 1
            worksheet.write(row, col, printed_result and printed_result[0]['printed_challan_cnt'] or 0, style=style_date_col)  # No. of challan Printed
            col += 1
            worksheet.write(row, col, printed_result and printed_result[0]['printed_amount'] or 0, style=style_date_col)  # Amount of Printed Challans
            col += 1
            worksheet.write(row, col, paid_result and paid_result[0]['paid_challan_cnt'] or 0, style=style_date_col)  # No. of Challan Paid
            col += 1
            worksheet.write(row, col, paid_result and paid_result[0]['paid_amount'] or 0, style=style_date_col)  # Paid Challan Amount
            col += 1
            worksheet.write(row, col, unpaid_result and unpaid_result[0]['unpaid_challan_cnt'] or 0, style=style_date_col)  # Amount to be Collected
            col += 1
            worksheet.write(row, col, unpaid_result and unpaid_result[0]['unpaid_amount'] or 0, style=style_date_col)  # Amount to be Collected
            col += 1
            sr += 1

        row += 2
        col = 0
        ttime = fields.datetime.now() + relativedelta(hours=5)
        worksheet.write_merge(row, row, 0, 4, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
        col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Challan Status Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Challan Status Detail Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
