import pdb
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class StudentFineHistoryReport(models.AbstractModel):
    _name = 'report.odoocms_fee_ucp.student_fine_history_report'
    _description = 'Student Fine History Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        term_id = self.env['odoocms.academic.term']
        term = data['form']['term_id'] and data['form']['term_id'][0] or False
        student = data['form']['student_id'][0] or False
        course_ids = data['form']['registered_courses']
        show_all_history = data['form']['show_all_history']

        student_id = self.env['odoocms.student'].search([('id', '=', student)])
        if term:
            term_id = self.env['odoocms.academic.term'].browse(term)

        if term and course_ids:
            student_course_ids = student_id.enrolled_course_ids.filtered(lambda a: a.term_id.id == term and a.course_ids.ids in course_ids)

        elif term and not course_ids:
            student_course_ids = student_id.enrolled_course_ids.filtered(lambda a: a.term_id.id == term)

        elif course_ids and not term:
            student_course_ids = student_id.enrolled_course_ids.filtered(lambda a: a.course_ids.ids in course_ids)
        else:
            student_course_ids = student_id.enrolled_course_ids

        present, absent, leave = 0, 0, 0
        fine_amt, discount_amt = 0, 0
        totals = {
            'fine': 0,
            'discount': 0,
            'paid': 0,
            'due': 0
        }

        student_courses = []
        absent_date_list = []
        for student_course in student_course_ids:
            course = student_course.mapped('component_ids')
            course_lines = []
            att_ids = course.att_line_ids.filtered(lambda l: l.state != 'draft')
            present += len(att_ids.filtered(lambda l: l.present or (not l.present and (l.reason_id and l.reason_id.present))))
            absent += len(att_ids.filtered(lambda l: not l.present or (not l.reason_id or (l.reason_id and l.reason_id.absent)) and not l.leave))
            leave += len(att_ids.filtered(lambda l: not l.present or (not l.reason_id or (l.reason_id and l.reason_id.absent)) and l.leave))
            lines = att_ids.filtered(lambda l: not l.present or (not l.reason_id or (l.reason_id and l.reason_id.absent)) or l.came_late)

            course_fine = course_discount = 0
            lines = lines and lines.sorted(key=lambda x: x.date_class)
            for line in lines:
                line_fine = line.fine if not student_course.grade == 'W' else 0
                line_discount = 0
                remarks = ''
                came_late = False

                if not line.present and not line.leave:
                    if line.date_class in absent_date_list:
                        remarks = 'Adjusted Against Per Day Fine'
                        course_discount += line_fine
                        line_discount = line_fine
                    else:
                        remarks = 'Pay it Immediately' if not student_course.grade == 'W' else 0
                        absent_date_list.append(line.date_class)

                elif line.present and line.came_late:
                    came_late = True
                    remarks = 'Pay it Immediately' if not student_course.grade == 'W' else 0

                c_line = ({
                    'term': course.term_id.code,
                    'absent_date': line.date_class,
                    'status': dict(line.fields_get(allfields=['state'])['state']['selection'])[line.state],
                    'line_fine': line_fine,
                    'line_discount': line_discount,
                    'remarks': remarks,
                    'present': line.present,
                    'leave': line.leave,
                    'came_late': came_late,
                })
                course_lines.append(c_line)
                course_fine += line_fine
                course_discount += line_discount

            course_data = {
                'name': course.class_id.name,
                'code': student_course.course_id.code,
                'section': student_course.primary_class_id.section_id.name,
                'state': dict(student_course.fields_get(allfields=['state'])['state']['selection']),
                'lines': course_lines,
                'course_fine': course_fine,
                'course_discount': course_discount,
                'course_status': 'Withdrawn' if student_course.grade == 'W' else 'Current',
                'withdraw_date': student_course.withdraw_date if student_course.state == 'withdraw' else False,
                'withdraw_reason': student_course.withdraw_reason.name if student_course.grade == 'W' else ''
            }
            student_courses.append(course_data)
            fine_amt += course_fine
            discount_amt += course_discount

        totals['fine'] += fine_amt

        # ***** Misc Fine Lines *****#
        other_fine_lines = []
        total_other_fine = 0
        total_other_fine_discount = 0
        total_other_fine_paid = 0
        total_other_fine_due = 0

        # Temporary Blocked Misc Fines to Show
        show_flag = False
        if show_flag:
            misc_fine_dom = [('student_id', '=', student_id), ('state', '!=', 'cancel')]
            if term_id:
                misc_fine_dom.append(('term_id', '=', term_id))
            misc_fine_recs = self.env['odoocms.fee.additional.charges'].search(misc_fine_dom)

            if misc_fine_recs:
                for misc_fine_rec in misc_fine_recs:
                    other_line_data_values = ({
                        'term': misc_fine_rec.term_id.code,
                        'date': misc_fine_rec.date,
                        'type': misc_fine_rec.charges_type.name,
                        'amount': misc_fine_rec.amount,
                        'discount': misc_fine_rec.discount,
                        'due': 0 if misc_fine_rec.receipt_id and misc_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else misc_fine_rec.amount,
                        'paid_amount': misc_fine_rec.receipt_id.amount_total if misc_fine_rec.receipt_id and misc_fine_rec.receipt_id in ('paid', 'in_payment', 'partial') else 0,
                        'remarks': misc_fine_rec.notes,
                    })
                    other_fine_lines.append(other_line_data_values)
                    total_other_fine += misc_fine_rec.amount
                    total_other_fine_paid += misc_fine_rec.receipt_id.amount_total if misc_fine_rec.receipt_id and misc_fine_rec.receipt_id in ('paid', 'in_payment', 'partial') else 0
                    total_other_fine_due += 0 if misc_fine_rec.receipt_id and misc_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else misc_fine_rec.amount
                    totals['fine'] += misc_fine_rec.amount
                    totals['paid'] += misc_fine_rec.receipt_id.amount_total if misc_fine_rec.receipt_id and misc_fine_rec.receipt_id in ('paid', 'in_payment', 'partial') else 0
                    totals['due'] += 0 if misc_fine_rec.receipt_id and misc_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else misc_fine_rec.amount

        # ***** Other Fine Lines *****#
        other_fine_dom = [('student_id', '=', student), ('state', '!=', 'cancel')]
        if term_id:
            other_fine_dom.append(('term_id', '=', term))

        other_fine_recs = self.env['odoocms.input.other.fine'].search(other_fine_dom)
        for other_fine_rec in other_fine_recs:
            other_line_data_values = ({
                'term': other_fine_rec.term_id.code,
                'date': other_fine_rec.date,
                'type': other_fine_rec.type.name,
                'amount': other_fine_rec.net_amount,
                'discount': 0,
                'due': 0 if other_fine_rec.receipt_id and other_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else other_fine_rec.net_amount,
                'paid_amount': other_fine_rec.net_amount if other_fine_rec.receipt_id and other_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else 0,
                'remarks': other_fine_rec.notes,
            })
            other_fine_lines.append(other_line_data_values)
            total_other_fine += other_fine_rec.net_amount
            total_other_fine_paid += other_fine_rec.net_amount if other_fine_rec.receipt_id and other_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else 0
            total_other_fine_due += 0 if other_fine_rec.receipt_id and other_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else other_fine_rec.net_amount
            totals['fine'] += other_fine_rec.net_amount
            totals['paid'] += other_fine_rec.net_amount if other_fine_rec.receipt_id and other_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else 0
            totals['due'] += 0 if other_fine_rec.receipt_id and other_fine_rec.receipt_id.payment_state in ('paid', 'in_payment', 'partial') else other_fine_rec.net_amount

        # ***** Library Fines *****#
        library_fine_lines = []
        total_library_fine = 0
        total_library_fine_discount = 0
        total_library_fine_paid = 0
        total_library_fine_due = 0
        member_id = self.env['odoocms.library.member'].search([('student_id', '=', student)])

        report = self.env['ir.actions.report']._get_report_from_name('odoocms_fee_ucp.student_fine_history_report')
        docargs = {
            'doc_ids': docsid,
            'doc_model': report.model,
            'data': data,

            'company_rec': self.env.company,
            'present': present,
            'absent': absent,
            'leave': leave,
            'fine_amt': fine_amt,
            'discount_amt': discount_amt,
            # 'paid_amt': paid_amt,
            # 'due_amt': due_amt,

            'student_courses': student_courses,
            'student_id': student_id,
            'term': term_id,

            'other_fines': other_fine_lines,
            'total_other_fine': total_other_fine,
            'total_other_fine_discount': total_other_fine_discount,
            'total_other_fine_paid': total_other_fine_paid,
            'total_other_fine_due': total_other_fine_due,

            'library_fine_lines': library_fine_lines,
            'total_library_fine': total_library_fine,
            'total_library_fine_discount': total_library_fine_discount,
            'total_library_fine_paid': total_library_fine_paid,
            'total_library_fine_due': total_library_fine_due,
            'totals': totals,
        }
        return docargs
