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


class OdoocmsRegistrationStatusReport(models.TransientModel):
    _name = "odoocms.registration.status.report"
    _description = "Registration Status Report"

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    institute_ids = fields.Many2many('odoocms.institute', 'odoocms_registration_status_rep_institute_rel1', 'report_id', 'institute_id', 'Faculties')
    program_ids = fields.Many2many('odoocms.program', 'odoocms_registration_status_rep_program_rel1', 'report_id', 'program_id', 'Programs')
    report_type = fields.Selection([('detail', 'Detail Report'),
                                    ('summary', 'Summary Report'),
                                    ], default='detail', string='Report Type')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    def make_excel(self):
        if self.report_type == 'detail':
            return self.make_detail_excel()
        elif self.report_type == 'summary':
            return self.make_summary_excel()

    def make_detail_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Registration Status Report")
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
        col_max = 5
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
        col5.width = 256 * 20

        worksheet.write_merge(row, row + 1, col_min, col_max, 'Registration Status Detail Report For ' + self.term_id.name, style=style_table_header2)

        row += 2
        col = 0
        table_header = ['SR#', 'Registration No', 'Name', 'Faculty', 'Program', 'Status']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        dom = [('term_id', '=', self.term_id.id)]
        if self.institute_ids:
            dom.append(('program_id.institute_id', 'in', self.institute_ids.ids))
        if self.program_ids:
            dom.append(('program_id', 'in', self.program_ids.ids))

        recs = self.env['odoocms.course.registration'].sudo().search(dom, order='student_id')

        sr = 1
        for rec in recs:
            _logger.info('Row No of %s Out of %s' % (sr, len(recs)))
            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.student_id.code or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.student_id.name or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.program_id.name or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.program_id and rec.program_id.institute_id.name or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, dict(rec.fields_get(allfields=['state'])['state']['selection'])[rec.state], style=style_date_col2)
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

        row += 1
        col = 0
        ttime = fields.datetime.now() + relativedelta(hours=5)
        worksheet.write_merge(row, row, 0, 4, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
        col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Registration Status Detail Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Registration Status Detail Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }

    def make_summary_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Registration Status Summary Report")
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
        col_max = 11
        row = 0

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        for i in range(1, col_max + 1):
            coli = worksheet.col(i)
            coli.width = 256 * 30

        worksheet.write_merge(row, row + 1, col_min, col_max, 'Registration Status Summary Report For ' + self.term_id.name, style=style_table_header2)

        row += 2
        col = 0
        table_header = ['SR#', 'Faculty', 'Program', 'New Students', 'Refund', 'Transfer In', 'Transfer Out',
                        'Net New Students', 'On-Going', 'Total Confirmed', 'Un-Confirmed', 'Withdrawn']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        dom = [('term_id', '=', self.term_id.id)]
        if self.institute_ids:
            dom.append(('program_id.institute_id', 'in', self.institute_ids.ids))
        if self.program_ids:
            dom.append(('program_id', 'in', self.program_ids.ids))

        recs = self.env['odoocms.course.registration'].sudo().search(dom, order='student_id')

        # ***** Total Result Query *****#
        self.env.cr.execute(""" select 
                                    count(r.*) as cnt,p.id as program_id, p.code as program_code, i.id as faculty_id, i.code as faculty_code
                                from 
                                    odoocms_course_registration r,odoocms_program p,odoocms_institute i 
                                where 
                                    r.term_id=%s and r.id in %s and r.program_id = p.id and p.institute_id = i.id and state !='cancel' 
                                group by 
                                    p.code,i.code,p.id,i.id 
                                order by p.id
                            """,
                            (self.term_id.id, tuple(recs.ids))
                            )
        results = self.env.cr.dictfetchall()

        sr = 1
        for result in results:
            _logger.info('Row No of %s Out of %s' % (sr, len(recs)))

            # ***** Confirmed Result Query *****#
            self.env.cr.execute(""" select 
                                        count(r.*) as cnt
                                    from 
                                        odoocms_course_registration r,odoocms_program p,odoocms_institute i 
                                    where 
                                        r.term_id=%s and r.id in %s and r.program_id = p.id and p.institute_id = i.id and state ='approved' and p.id = %s and i.id= %s  
                                      """,
                                (self.term_id.id, tuple(recs.ids), result['program_id'], result['faculty_id'])
                                )
            confirmed_result = self.env.cr.dictfetchall()

            # ***** Unconfirmed Result Query *****#
            self.env.cr.execute(""" select 
                                        count(r.*) as cnt
                                    from 
                                        odoocms_course_registration r,odoocms_program p,odoocms_institute i 
                                    where 
                                        r.term_id=%s and r.id in %s and r.program_id = p.id and p.institute_id = i.id and state not in ('approved','cancel') and p.id = %s and i.id= %s  
                                """,
                                (self.term_id.id, tuple(recs.ids), result['program_id'], result['faculty_id'])
                                )
            unconfirmed_result = self.env.cr.dictfetchall()

            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)
            col += 1
            worksheet.write(row, col, result['faculty_code'], style=style_date_col2)  # Faculty
            col += 1
            worksheet.write(row, col, result['program_code'], style=style_date_col2)  # Program
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # New Students
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # Refund
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # In
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # Out
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # Net New Students
            col += 1
            worksheet.write(row, col, result['cnt'], style=style_date_col)  # On-Going
            col += 1
            worksheet.write(row, col, confirmed_result[0]['cnt'], style=style_date_col)  # Total Confirmed
            col += 1
            worksheet.write(row, col, unconfirmed_result[0]['cnt'], style=style_date_col)  # Un-Confirmed
            col += 1
            worksheet.write(row, col, '', style=style_date_col)  # Withdrawn
            col += 1
            sr += 1

        row += 1
        col = 0
        worksheet.write(row, col, '', style=style_table_totals2)  # Sr
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Faculty
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Program
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # New Students
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Refund
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # In
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Out
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Net New Students
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # On-Going
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Total Confirmed
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Un-Confirmed
        col += 1
        worksheet.write(row, col, '', style=style_table_totals2)  # Withdrawn
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
            'name': 'Registration Status Summary Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Registration Status Summary Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
