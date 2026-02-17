from odoo import api, fields, models


class TeacherInfoReport(models.AbstractModel):
    _name = 'report.odoocms_registration.teacher_info_report_template'
    _description = 'Teacher Info Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        if data is not None:
            domain = [('state','in',('active','notice_period'))]
            faculty_id = data.get('faculty_id', False)
            if faculty_id:
                domain.append(('institute', '=', int(faculty_id)))

            faculty_staff_ids = self.env['odoocms.faculty.staff'].sudo().search(domain)
            docargs = {
                'docs': faculty_staff_ids,
            }
            return docargs
        return docsid
