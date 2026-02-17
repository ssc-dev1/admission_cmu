# -*- coding: utf-8 -*-
import pdb

from odoo import api, fields, models, _, tools
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


class RegistrationStatReport(models.TransientModel):
    _name = 'registration.stat.detail.report'
    _description = 'Registration Stat Detail Report'

    @api.model
    def get_default_term(self):
        term_id = self.env['odoocms.academic.term'].search([], order='id desc', limit=1)
        if term_id:
            return term_id.id
        else:
            return False

    institute_ids = fields.Many2many('odoocms.institute', 'registration_stat_detail_institute_rep_rel', 'wiz_id', 'institute_id', 'Faculties')
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_default_term)

    def make_excel(self):
        workbook = xlwt.Workbook(encoding="utf-8")
        worksheet = workbook.add_sheet("Registration Stat Detail Report")

        style_table_header = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
        style_date_col = xlwt.easyxf(
            "font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
        style_date_col2 = xlwt.easyxf(
            "font:height 200; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 25
        col1 = worksheet.col(1)
        col1.width = 256 * 30
        col2 = worksheet.col(2)
        col2.width = 256 * 30
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

        col_min = 0
        col_max = 7
        col = 0
        row = 0

        table_header = ['Registration No', 'Student Name', 'Batch', 'Faculty', 'Program Code', 'Program Name', 'Fee Status', 'Per Credit Hour Rate']
        for i in range(col_min, col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        institute_ids = self.institute_ids or self.env['odoocms.institute'].search([])
        for institute_id in institute_ids:
            confirmed_students = self.env['odoocms.student.course'].search([('institute_id', '=', institute_id.id), ('term_id', '=', self.term_id.id)]).mapped('student_id')
            registered_students = self.env['odoocms.course.registration'].search([('student_id.institute_id', '=', institute_id.id), ('term_id', '=', self.term_id.id), ('state', 'in', ('submit', 'approved', 'part_approved'))]).mapped('student_id')
            unconfirmed_students = registered_students - confirmed_students

            for confirmed_student in confirmed_students:
                row += 1
                col = 0
                worksheet.write(row, col, confirmed_student.code, style=style_date_col2)
                col += 1
                worksheet.write(row, col, confirmed_student.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, confirmed_student.batch_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, confirmed_student.institute_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, confirmed_student.program_id.code, style=style_date_col2)
                col += 1
                worksheet.write(row, col, confirmed_student.program_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, 'Y', style=style_date_col2)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(confirmed_student.batch_id.per_credit_hour_fee), style=style_date_col)
                col += 1

            for unconfirmed_student in unconfirmed_students:
                row += 1
                col = 0
                worksheet.write(row, col, unconfirmed_student.code, style=style_date_col2)
                col += 1
                worksheet.write(row, col, unconfirmed_student.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, unconfirmed_student.batch_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, unconfirmed_student.institute_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, unconfirmed_student.program_id.code, style=style_date_col2)
                col += 1
                worksheet.write(row, col, unconfirmed_student.program_id.name, style=style_date_col2)
                col += 1
                worksheet.write(row, col, 'N', style=style_date_col2)
                col += 1
                worksheet.write(row, col, '{0:,.0f}'.format(unconfirmed_student.batch_id.per_credit_hour_fee), style=style_date_col)
                col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Registration Stat Detail Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Registration Stat Detail Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
