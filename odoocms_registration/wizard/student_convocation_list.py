from odoo import fields, models, api, _
from odoo.exceptions import UserError


class StudentConvocationList(models.TransientModel):
    _name = 'student.convocation.list'
    _description = 'Student Convocation List'

    institute_id = fields.Many2one('odoocms.institute', string='Institute')
    batch_ids = fields.Many2many('odoocms.batch', string='Batch')
    cgpa = fields.Integer('CGPA', required=True)
    cr_hr = fields.Integer('Cr Hrs', required=True)

    def print_report(self):
        datas = {
            'institute_id': self.institute_id.id,
            'batch_id': self.batch_ids.ids,
            'cgpa': self.cgpa,
            'cr_hr': self.cr_hr,
        }
        return self.env.ref('odoocms_registration.student_convocation_list_report_action').with_context(landscape=False).report_action(self, data=datas, config=False)

    def get_student_list(self):
        domain = []
        if self.institute_id:
            domain.append(('institute_id', '=', self.institute_id.id))
        if self.batch_ids:
            domain.append(('batch_id', 'in', self.batch_ids.ids))
        if self.cgpa:
            domain.append(('cgpa', '>=', self.cgpa))
        if self.cr_hr:
            domain.append(('attempted_credits', '>=', self.cr_hr))
        students = self.env['odoocms.student'].sudo().search(domain)
        if not students:
            raise UserError('No Students Found!')

        action = self.env.ref('odoocms.action_odoocms_student').read()[0]
        context = {
            'domain': [('id', 'in', students.ids)]
        }
        action['domain'] = [('id', 'in', students.ids)]
        return action
