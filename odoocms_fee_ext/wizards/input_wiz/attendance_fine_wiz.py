# -*- coding: utf-8 -*-
import pdb
from odoo import models, fields, api

import logging

_logger = logging.getLogger(__name__)

# access_attendance_fine_wizard,access.attendance.fine.wizard,model_attendance_fine_wizard,base.group_user,1,1,1,0
class AttendanceFineWizard(models.TransientModel):
    _name = "attendance.fine.wizard"
    _description = 'Attendance Fine Wizard'

    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    student_id = fields.Many2one('odoocms.student', 'Student')

    def action_create_student_term_att(self):
        # self.env.cr.execute(""" with fines as (select least(sum(x.fine),500) as fine_amount,x.date_class, x.student_id as student
        # from odoocms_class_attendance_line x
        #                         where x.fine > 0 and x.term_id=%s group by x.date_class,x.student_id)
        #                         select student, sum(fine_amount) as fine_amount from fines group by student""" % self.term_id.id)

        # self.env.cr.execute(""" with fines as (select least(sum(x.fine-COALESCE(discount, 0)),500) as fine_amount,x.date_class, x.student_id as student from odoocms_class_attendance_line x, odoocms_student_course c
        #                                 where x.fine > 0 and x.term_id=%s and (x.student_course_id = c.id or x.student_course_id is null) and c.grade !='W' group by x.date_class,x.student_id)
        #                                 select student, sum(fine_amount) as fine_amount from fines group by student""" % self.term_id.id)

        students = self.env['odoocms.class.attendance.line'].search([('term_id', '=', self.term_id.id),
                                                                     ('fine', '>', 0)
                                                                     ]).mapped('student_id')
        n = 1
        for student_id in students:
            _logger.info('...... Line# is being processed %s out of %s. ..............', n, len(students))
            n += 1
            total_att_fine, unpaid_att_fine, paid_att_fine, att_fine_scholarship_amount = self._compute_fine_detail(student_id=student_id)
            student_data_dict = {
                'student_id': student_id.id,
                'student_code': student_id.code,
                'student_name': student_id.name,
                'program_id': student_id.program_id.id or False,
                'institute_id': student_id.institute_id.id or False,
                'term_id': self.term_id.id or False,
                'fine': total_att_fine,
                'discount': 0,
                'net_amount': total_att_fine,
                'date': fields.Date.today(),
            }
            new_rec = self.env['odoocms.student.term.att.fine'].sudo().create(student_data_dict)
            att_recs = self.env['odoocms.class.attendance.line'].sudo().search([('student_id', '=', student_id.id),
                                                                                ('term_id', '=', self.term_id.id)
                                                                                ])
            if att_recs:
                att_recs.write({'term_attendance_id': new_rec.id})

    def action_recalculate_student_term_att(self):
        recs = self.env['odoocms.student.term.att.fine'].search([('to_be', '=', True)], limit=100)
        n = 1
        for rec in recs:
            self.env.cr.execute(""" with fines as (select least(sum(x.fine-COALESCE(discount, 0)),500) as fine_amount,x.date_class, x.student_id as student from odoocms_class_attendance_line x, odoocms_student_course c
                                               where x.fine > 0 and x.term_id=%s and x.student_id = %s and (x.student_course_id = c.id or x.student_course_id is null) and c.grade !='W' group by x.date_class,x.student_id) 
                                               select student, sum(fine_amount) as fine_amount from fines group by student""", (self.term_id.id, rec.student_id.id))
            results = self.env.cr.dictfetchall()
            rec.write({'new_amount': results[0]['fine_amount'], 'diff_amt': rec.net_amount - results[0]['fine_amount'], 'to_be': False})
            _logger.info('...... Line# is being processed %s. ..............', n)
            n += 1

