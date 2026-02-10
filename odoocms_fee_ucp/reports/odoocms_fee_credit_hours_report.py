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


class OdoocmsFeeCreditHoursReport(models.TransientModel):
    _name = "odoocms.fee.credit.hours.report"
    _description = "Fee Credit Hours Report"

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    institute_ids = fields.Many2many('odoocms.institute', 'credit_hours_rep_institute_rel1', 'report_id', 'institute_id', 'Faculties')
    program_ids = fields.Many2many('odoocms.program', 'credit_hours_rep_program_rel1', 'report_id', 'program_id', 'Programs')
    course_ids = fields.Many2many('odoocms.course', 'credit_hours_rep_course_rel1', 'report_id', 'course_id', 'Courses')
    credit_hour_type = fields.Selection([('confirm', 'Confirm Credit Hours'),
                                         ('unconfirmed', 'UnConfirmed Credit Hours'),
                                         ('both', 'Both')
                                         ], default='both', string='C/H Type')
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
        col_max = 11
        row = 0

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 25
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
        col7.width = 256 * 30
        col8 = worksheet.col(8)
        col8.width = 256 * 20
        col9 = worksheet.col(9)
        col9.width = 256 * 20
        col10 = worksheet.col(10)
        col10.width = 256 * 20

        worksheet.write_merge(row, row + 1, col_min, col_max, 'Credit Hour Report Detail For ' + self.term_id.name, style=style_table_header2)

        row += 2
        col = 0
        table_header = ['SR#', 'Program Registered', 'Faculty', 'Reg Number', 'Course Code', 'Credit Hours', 'Status', 'C/H Fee', 'Gross Fee', 'Paid Amount', 'Discount Percentage', 'Course Status']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        conditions = {
            'confirmed': [('state', '=', 'approved')],
            'unconfirmed': [('state', 'in', ('draft', 'submit'))],
            'both': [('state', 'not in', ('cancel', 'rejected', 'error'))]
        }

        dom = [('term_id', '=', self.term_id.id), ('action', '=', 'add')]
        dom.extend(conditions[self.credit_hour_type])
        if self.institute_ids:
            dom.append(('registration_id.program_id.institute_id', 'in', self.institute_ids.ids))
        if self.program_ids:
            dom.append(('registration_id.program_id', 'in', self.program_ids.ids))
        if self.course_ids:
            dom.append(('course_id', 'in', self.course_ids.ids))

        recs = self.env['odoocms.course.registration.line'].sudo().search(dom, order='student_id,program_id')

        sr = 1
        for rec in recs:
            _logger.info('Row No of %s Out of %s' % (sr, len(recs)))
            mv_lines = self.env['account.move.line'].search([('student_id', '=', rec.student_id.id),
                                                             ('move_id.term_id', '=', self.term_id.id),
                                                             ('course_id_new', '=', rec.primary_class_id.id),
                                                             ('move_id.payment_state', 'in', ('paid', 'in_payment'))])
            disc = mv_lines and mv_lines[0].move_id.waiver_percentage or 0

            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.course_program_id and rec.course_program_id.name or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.course_program_id.institute_id and rec.course_program_id.institute_id.name or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.student_id and rec.student_id.code or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, rec.course_code and rec.course_code or '', style=style_date_col2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(rec.credits), style=style_date_col)
            col += 1
            worksheet.write(row, col, dict(rec.fields_get(allfields=['state'])['state']['selection'])[rec.state], style=style_date_col2)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(rec.batch_id.per_credit_hour_fee), style=style_date_col)
            col += 1
            worksheet.write(row, col, '{0:,.0f}'.format(rec.credits * rec.batch_id.per_credit_hour_fee), style=style_date_col)
            col += 1
            # worksheet.write(row, col, paid_amount_result[0].get('amount', 0), style=style_date_col)
            worksheet.write(row, col, '', style=style_date_col)
            col += 1
            worksheet.write(row, col, disc, style=style_date_col)
            col += 1
            worksheet.write(row, col, rec.student_course_id.state, style=style_date_col)
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

        row += 1
        col = 0
        ttime = fields.datetime.now() + relativedelta(hours=5)
        worksheet.write_merge(row, row, 0, 4, "Print Date: " + ttime.strftime("%d-%m-%Y %H:%M:%S"), style=style_table_totals3)
        col += 1

        file_data = io.BytesIO()
        workbook.save(file_data)
        wiz_id = self.env['odoocms.fee.report.save.wizard'].create({
            'data': base64.encodebytes(file_data.getvalue()),
            'name': 'Credit Hours Detail Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Hours Detail Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }

    def make_summary_excel(self):
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
        # col_max = 11
        col_max = 8
        row = 0

        # col width
        col0 = worksheet.col(0)
        col0.width = 256 * 10
        col1 = worksheet.col(1)
        col1.width = 256 * 25
        col2 = worksheet.col(2)
        col2.width = 256 * 40
        col3 = worksheet.col(3)
        col3.width = 256 * 20
        col4 = worksheet.col(4)
        col4.width = 256 * 20
        col5 = worksheet.col(5)
        col5.width = 256 * 25
        col6 = worksheet.col(6)
        col6.width = 256 * 25
        col7 = worksheet.col(7)
        col7.width = 256 * 30
        col8 = worksheet.col(8)
        col8.width = 256 * 20
        col9 = worksheet.col(9)
        col9.width = 256 * 20
        col10 = worksheet.col(10)
        col10.width = 256 * 20
        col11 = worksheet.col(11)
        col11.width = 256 * 20
        col12 = worksheet.col(12)
        col12.width = 256 * 20

        worksheet.write_merge(row, row + 1, col_min, col_max, 'Credit Hour Summary Report For ' + self.term_id.name, style=style_table_header2)

        row += 2
        col = 0
        # table_header = ['SR#', 'Program Registered', 'Faculty', 'Distinct Course Count', 'Number of Students', 'Total Credit Hours', 'Confirmed Credit Hours', 'Un-Confirmed Credit Hours', 'Confirmed Fee', 'Un-Confirmed Fee', 'Paid Amount', 'Sponsoring Faculty']
        table_header = ['SR#', 'Program Registered', 'Faculty', 'Distinct Course Count', 'Number of Students', 'Total Credit Hours', 'Confirmed Credit Hours', 'Un-Confirmed Credit Hours', 'Sponsoring Faculty']
        for i in range(col_max + 1):
            worksheet.write(row, col, table_header[i], style=style_table_header)
            col += 1

        conditions = {
            'confirmed': [('state', '=', 'approved')],
            'unconfirmed': [('state', 'in', ('draft', 'submit'))],
            'both': [('state', 'not in', ('cancel', 'rejected', 'error'))]
        }

        dom = [('term_id', '=', self.term_id.id), ('action', '=', 'add')]
        dom.extend(conditions[self.credit_hour_type])
        if self.institute_ids:
            dom.append(('registration_id.program_id.institute_id', 'in', self.institute_ids.ids))
        if self.program_ids:
            dom.append(('registration_id.program_id', 'in', self.program_ids.ids))
        if self.course_ids:
            dom.append(('course_id', 'in', self.course_ids.ids))

        recs = self.env['odoocms.course.registration.line'].sudo().search(dom, order='student_id,program_id')

        self.env.cr.execute("""select 
                                    count(distinct(rl.student_id)) as student_cnt,
                                    sum(rl.credits) as credits,
                                    count(distinct(rl.course_code)) as course_cnt,
                                    p.id as program_id,
                                    p.code as p_code,
                                    p.name as p_name, 
                                    inst.id as institute_id, 
                                    inst.code as inst_code,
                                    inst.name as inst_name 
                                    from 
                                        odoocms_course_registration_line rl,
                                        odoocms_course_registration r,
                                        odoocms_program p,
                                        odoocms_institute inst 
                                    where 
                                        rl.registration_id = r.id and 
                                        rl.term_id=%s and 
                                        rl.action=%s and 
                                        r.program_id = p.id and 
                                        p.institute_id = inst.id and 
                                        rl.id in %s
                                    group by 
                                        p.id, 
                                        p.code,
                                        p.name,
                                        inst.id, 
                                        inst.code,
                                        inst.name 
                                    order by 
                                    inst.name""",
                            (self.term_id.id, 'add', tuple(recs.ids)))
        results = self.env.cr.dictfetchall()
        sr = 1
        for result in results:
            _logger.info('Row No of %s Out of %s' % (sr, len(results)))
            # Credit Hours
            self.env.cr.execute(""" select
                                        sum(rl.credits) as credits
                                    from 
                                        odoocms_course_registration_line rl,
                                        odoocms_course_registration r,
                                        odoocms_program p,
                                        odoocms_institute inst
                                    where 
                                        rl.registration_id = r.id and 
                                        rl.term_id=%s and 
                                        rl.action=%s and 
                                        r.program_id = p.id and 
                                        p.institute_id = inst.id and 
                                        rl.id in %s and 
                                        r.program_id=%s 
                                        and inst.id = %s 
                                        and rl.state=%s""",
                                (self.term_id.id, 'add', tuple(recs.ids), result['program_id'], result['institute_id'], 'approved'))
            approved_credit_hours_result = self.env.cr.dictfetchall()

            self.env.cr.execute(""" select 
                                        sum(rl.credits) as credits 
                                    from 
                                        odoocms_course_registration_line rl,
                                        odoocms_course_registration r,
                                        odoocms_program p,
                                        odoocms_institute inst
                                    where 
                                        rl.registration_id = r.id and 
                                        rl.term_id=%s and 
                                        rl.action=%s and 
                                        r.program_id = p.id and 
                                        p.institute_id = inst.id and 
                                        rl.id in %s and 
                                        r.program_id=%s and 
                                        inst.id = %s and 
                                        rl.state in %s """,
                                (self.term_id.id, 'add', tuple(recs.ids), result['program_id'], result['institute_id'], ('draft', 'submit')))
            unapproved_credit_hours_result = self.env.cr.dictfetchall()

            # Amount
            self.env.cr.execute(""" select 
                                        sum(rl.credits*batch.per_credit_hour_fee) as amount 
                                    from 
                                        odoocms_course_registration_line rl,
                                        odoocms_course_registration r,
                                        odoocms_program p,
                                        odoocms_institute inst,
                                        odoocms_batch batch
                                    where 
                                        rl.registration_id = r.id and 
                                        rl.term_id=%s 
                                        and rl.action=%s and 
                                        r.program_id = p.id and 
                                        p.institute_id = inst.id and 
                                        rl.id in %s and 
                                        r.program_id=%s and 
                                        inst.id = %s and 
                                        rl.state=%s and 
                                        rl.batch_id = batch.id""",
                                (self.term_id.id, 'add', tuple(recs.ids), result['program_id'], result['institute_id'], 'approved'))
            approved_credit_amount_result = self.env.cr.dictfetchall()

            self.env.cr.execute(""" select 
                                        sum(rl.credits*batch.per_credit_hour_fee) as amount 
                                    from 
                                        odoocms_course_registration_line rl,
                                        odoocms_course_registration r,
                                        odoocms_program p,
                                        odoocms_institute inst,
                                        odoocms_batch batch
                                    where 
                                        rl.registration_id = r.id and 
                                        rl.term_id=%s and 
                                        rl.action=%s and 
                                        r.program_id = p.id and 
                                        p.institute_id = inst.id and 
                                        rl.id in %s and 
                                        r.program_id=%s and 
                                        inst.id = %s and 
                                        rl.state in %s and 
                                        rl.batch_id = batch.id""",
                                (self.term_id.id, 'add', tuple(recs.ids), result['program_id'], result['institute_id'], ('draft', 'submit')))
            unapproved_credit_amount_result = self.env.cr.dictfetchall()

            # Paid Amount
            filtered_recs = recs.filtered(lambda a: a.registration_id.program_id.id == result['program_id'] and a.registration_id.program_id.institute_id.id == result['institute_id'])
            primary_class_ids = filtered_recs.mapped('primary_class_id')
            student_ids = filtered_recs.mapped('student_id')

            self.env.cr.execute(""" select 
                                        sum(mvl.price_subtotal) as amount 
                                    from 
                                        account_move_line mvl, account_move mv 
                                    where 
                                        mvl.move_id=mv.id and 
                                        mv.term_id=%s and 
                                        mv.payment_state in %s and 
                                        mvl.course_id_new in %s and
                                        mv.student_id in %s and  
                                        mv.program_id=%s and 
                                        mv.institute_id=%s
                                """,
                                (self.term_id.id, ('paid', 'in_payment'), tuple(primary_class_ids.ids), tuple(student_ids.ids), result['program_id'], result['institute_id']))
            paid_amount_result = self.env.cr.dictfetchall()

            row += 1
            col = 0
            worksheet.write(row, col, sr, style=style_date_col2)
            col += 1
            worksheet.write(row, col, result['p_code'] or '', style=style_date_col2)  # Program Code
            col += 1
            worksheet.write(row, col, result['inst_code'] or '', style=style_date_col2)  # Faculty Code
            col += 1
            worksheet.write(row, col, result['course_cnt'] or '', style=style_date_col)  # Distinct Courses
            col += 1
            worksheet.write(row, col, result['student_cnt'], style=style_date_col)  # Distinct Students
            col += 1
            worksheet.write(row, col, result['credits'], style=style_date_col)  # Total Credits
            col += 1
            worksheet.write(row, col, approved_credit_hours_result[0].get('credits', 0), style=style_date_col)  # confirmed
            col += 1
            worksheet.write(row, col, unapproved_credit_hours_result[0].get('credits', 0), style=style_date_col)  # unconfirmed
            col += 1
            # worksheet.write(row, col, approved_credit_amount_result[0].get('amount', 0), style=style_date_col)  # confirmed Fee
            # col += 1
            # worksheet.write(row, col, unapproved_credit_amount_result[0].get('amount', 0), style=style_date_col)  # unconfirmed Fee
            # col += 1
            # worksheet.write(row, col, paid_amount_result[0].get('amount', 0), style=style_date_col)  # paid fee
            # col += 1
            worksheet.write(row, col, '', style=style_date_col)  # Sponsoring Faculty
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
        # worksheet.write(row, col, '', style=style_table_totals2)
        # col += 1
        # worksheet.write(row, col, '', style=style_table_totals2)
        # col += 1
        # worksheet.write(row, col, '', style=style_table_totals2)
        # col += 1
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
            'name': 'Credit Hours Summary Report.xls'
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Credit Hours Summary Report',
            'res_model': 'odoocms.fee.report.save.wizard',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': wiz_id.id,
            'target': 'new'
        }
