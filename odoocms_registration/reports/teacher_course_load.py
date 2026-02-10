import pdb

from odoo import api, fields, models


class TeacherCourseLoadReport(models.AbstractModel):
    _name = 'report.odoocms_registration.teacher_course_load_report_template'
    _description = 'Teacher Course Load Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        if data is not None:
            institute_id = data.get('institute_id', False)
            type = data.get('type', False)
            term_id = data.get('term_id', False)
            teacher_id = data.get('teacher_id', False)
            term = self.env['odoocms.academic.term'].browse(term_id)

            domain = [('state','in',('active','notice_period')), ('institute', '=', institute_id)]
            if type:
                domain.append(('employment_nature', '=', type))
            if teacher_id:
                domain.append(('id', '=', teacher_id))
            
            faculty_staff_ids = self.env['odoocms.faculty.staff'].sudo().search(domain)

            if not teacher_id and data.get('include_other'):
                teacher_ids = self.env['odoocms.class.primary'].search([
                    ('institute_id','=',institute_id),('term_id','=',term_id)]).mapped('class_ids').mapped('faculty_ids').mapped('faculty_staff_id')
                if type:
                    teacher_ids.filtered(lambda l: l.employment_nature == type)
                faculty_staff_ids += teacher_ids

            faculty_staff_ids = list(set(faculty_staff_ids))
            docargs = {
                'docs': faculty_staff_ids,
                'term': term,
                'cross_faculty': data.get('cross_faculty'),
                'institute_id': institute_id,
            }
            return docargs
        return docsid
