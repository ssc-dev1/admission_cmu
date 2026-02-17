from odoo import fields, models


class TeacherInfoReportWizard(models.TransientModel):
    _name = 'teacher.info.report'
    _description = 'Teacher Information Report'
    
    faculty_id = fields.Many2one('odoocms.institute', string='Faculty/Institute',required=True)

    def print_report(self):
        datas={
            'faculty_id': self.faculty_id.id,
        }
        return self.env.ref('odoocms_registration.action_teacher_info_report').with_context(landscape=False).report_action(self, data=datas,)
