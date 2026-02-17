from odoo import api, fields, models


class StudentConvocationReport(models.AbstractModel):
    _name = 'report.odoocms_registration.student_convocation_template'
    _description = 'Convocation Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        if data is not None:
            institute_id = data.get('institute_id', False)
            batch_id = data.get('batch_id', False)
            cgpa = data.get('cgpa', False)
            cr_hr = data.get('cr_hr', False)
            
            domain=[]  
            if institute_id:
                domain.append(('institute_id','=',institute_id))
            if batch_id:
                domain.append(('batch_id','in',batch_id))
            if cgpa:
                domain.append(('cgpa','>=',cgpa))
            if cr_hr:
                domain.append(('attempted_credits','>=',cr_hr))
            students=self.env['odoocms.student'].sudo().search(domain)

            docargs = {
                'docs': students,
            }
            return docargs
        return docsid
