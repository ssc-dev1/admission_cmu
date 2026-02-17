from odoo import api, fields, models, _
import time
import logging
from odoo.tools.safe_eval import safe_eval


_logger = logging.getLogger(__name__)


class StudentInvoiceSlip(models.AbstractModel):
    _name= 'report.odoocms_fee_ext.term_fee_challan_template'
    _description = "Fee Challan Report"

    @api.model
    def _get_report_values(self, docsid, data=None):
        if docsid:
            challan_ids = self.env['odoocms.fee.barcode'].sudo().browse(docsid)
        elif data and data.get('ids',False):
            challan_ids = self.env['odoocms.fee.barcode'].sudo().browse(data['ids'])

        #     term_id = self.env['odoocms.datesheet'].search([], order='number desc', limit=1).term_id.id
        # else:
        #     batch_id = data['form']['batch_id'] and data['form']['batch_id'][0] or False
        #     term_id = data['form']['term_id'] and data['form']['term_id'][0] or False
        #     student_id = data['form']['student_id'] and data['form']['student_id'][0] or False
        #     if batch_id:
        #         students = self.env['odoocms.student'].search([('batch_id', '=', batch_id)])
        #     elif student_id:
        #         students = self.env['odoocms.student'].search([('id', '=', student_id)])

        # for challan_id in challan_ids:

        challan = challan_ids[0]
        challan_type = 'main'
        courses = []
        gross = 0
        faculty_wise_fee_rec = self.env['odoocms.student.faculty.wise.challan'].sudo().search([('term_id', '=', challan.term_id.id)], order='id desc', limit=1)
        price_unit = 0
        receipt_type_ids = faculty_wise_fee_rec.receipt_type_ids

        fee_structure = challan.student_id._get_fee_structure(log_message=False)
        tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
        structure_fee_heads = challan.student_id._get_fee_heads(fee_structure, receipt_type_ids, tuition_fee_head)  # odoocms.fee.structure on session,batch,career, odoocms.fee.structure.head of required receipts

        for structure_fee_head in structure_fee_heads:
            for head_line in structure_fee_head.line_ids:  # odoocms.fee.structure.head.line
                if not head_line.domain and price_unit == 0:
                    price_unit = head_line.amount
                if head_line.domain and self.env['odoocms.student'].sudo().search(safe_eval(head_line.domain) + [('id', '=', challan.student_id.id)]):
                    price_unit = head_line.amount

        if challan.label_id.type == 'installment':
            challan_type = 'installment'
            course_lines = challan.sudo().student_id.enroll_term_ids.filtered(lambda l: l.term_id.id == challan.term_id.id).student_course_ids
            gross = 0
            for line in course_lines:
                course_fee = line.credits * price_unit
                course = {
                    'code': line.course_code,
                    'name': line.course_name[:35],
                    'credits': int(line.credits),
                    'section': line.primary_class_id.section_id and line.primary_class_id.section_id.name or '',
                    'gross': course_fee,
                }
                courses.append(course)
                gross += course_fee

        elif challan.label_id.type in ('main','add_drop'):
            challan_type = challan.label_id.type
            course_lines = challan.sudo().line_ids.mapped('move_id').mapped('invoice_line_ids').filtered(lambda line: not line.fee_head_id.exclude_from_report)
            # course_lines = challan.sudo().student_id.unconfirmed_registration_request_ids.filtered(lambda l: l.term_id.id == challan.term_id.id)
            gross = 0
            for line in course_lines.filtered(lambda l: l.course_id_new):
                course_fee = line.course_id_new.course_id.credits * price_unit
                course = {
                    'code': line.course_id_new.course_id.code,
                    'name': line.course_id_new.course_id.name[:35],
                    'credits': line.course_id_new.course_id.credits,
                    'section': line.course_id_new.section_id and line.course_id_new.section_id.name or '',
                    'gross': course_fee,
                }
                courses.append(course)
                gross += course_fee

        company_id = self.env.company


        # student_list = []
        # for student in students:
        #     personal_info, course_list = student.get_datesheet(term_id)
        #     student_list.append({
        #         'gender': student.gender,
        #         'personal_info': personal_info,
        #         'course_info': course_list,
        #         'section': student.batch_section_id.name or '',
        #         'datesheet_name': self.env['odoocms.datesheet'].sudo().search([('student_visible', '=', True)])[0].name or '',
        #     })

        docargs = {
            'challan_type': challan_type,
            'docs': challan_ids,
            'data': data and data.get('form', False) or False,
            'company_id': company_id or False,
            'timestamp': time.strftime('%A, %B %d, %Y'),
            'course_lines': courses,
            'gross': gross,
            # 'students_list': student_list or False,
        }
        return docargs
