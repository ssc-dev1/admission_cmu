import time
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError, UserError


class StudentCourseRegistrationBulkStatusUpdate(models.TransientModel):
    _name = 'student.course.registration.bulk.status.update'
    _description = 'Student Course Registration Bulk Status Update'

    status = fields.Selection([('block', 'Block'),
                               ('unblock', 'Unblock'),
                               ], default='block', string='Registration Status')
    student_ids = fields.Many2many('odoocms.student', 'student_course_registration_bulk_status_rel', 'student_id', 'course_bulk_registration_id', 'Students')

    def action_update_registration_status(self):
        if self.student_ids:
            status = True
            if self.status=='block':
                status = False
            for student_id in self.student_ids:
                old_status = student_id.registration_allowed
                student_id.registration_allowed = status
                message = "Student Registration Status Changed From <b>%s</b> to <b>%s</b>" % (old_status, status)
                student_id.message_post(body=message)
