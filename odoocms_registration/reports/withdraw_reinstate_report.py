from odoo import api, fields, models


class CourseWithdrawReinstate(models.AbstractModel):
    _name = 'report.odoocms_registration.student_course_withdraw_template'
    _description = 'Course Withdraw/Reinstate Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        if data is not None:
            domain=[('type','=',data.get('type',False)),('date_request','>=',data.get('start_date',False)),('date_request','<=',data.get('end_date',False))]
            if data.get('program_id',False):
                domain.append(('program_id','=',data.get('program_id',False)))
            withdraw_student = self.env['odoocms.student.course.withdraw'].sudo().search(domain)
            docargs={
                'withdraw_student':withdraw_student
            }
            return docargs
        return docsid