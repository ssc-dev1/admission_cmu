from odoo import api, fields, models
import pdb


class ClassActivityReport(models.AbstractModel):
    _name = 'report.odoocms_academic.class_activity_report_template'
    _description = 'Class Activity Report '

    @api.model
    def _get_report_values(self, docsid, data=None):
        if data is not None:
            domain = [('faculty_staff_id', '!=', False)]
            faculty_id = data.get('faculty_id', False)
            term_id = data.get('term_id', False)
            if faculty_id:
                domain.append(('primary_class_id.institute_id', '=', faculty_id))
            if data.get('term_id', False):
                domain.append(('primary_class_id.term_id', '=', term_id))
    
            faculty_class_ids = self.env['odoocms.class'].sudo().search(domain)
            data = []
            headers = set(faculty_class_ids.mapped('assessment_component_ids').mapped('type_id'))
            for rec in faculty_class_ids:
                line = {
                    'Name': rec.faculty_staff_id.name,
                    'Program': rec.primary_class_id.batch_id.program_id.code,
                    'Course Code': rec.code.split('-')[0] if rec.code else '-',
                    'Course Title': rec.name,
                    'Sections': rec.primary_class_id.section_name or '-',
                }
                for header in headers:
                    assessments = rec.assessment_ids.filtered(lambda x: x.assessment_component_id.type_id == header)
                    if assessments:
                        assessments_approved = assessments.filtered(lambda x: x.is_approved)
                        line.update({
                            header.name: f"{ len(assessments - assessments_approved) } + {len(assessments_approved)} = {len(assessments)}"
                        })
                    else:
                        line.update({
                            header.name: f"{0}+{0}={0}"
                        })
                data.append(line)

            docargs = {
                'data': data,
            }
            return docargs
        return docsid
