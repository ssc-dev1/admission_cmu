from odoo import api, fields, models


class TeacherCourseLoadReportWizard(models.TransientModel):
    _name = 'teacher.course.load.wizard'
    _description = 'Teacher Course Load Report Wizard'
    
    institute_id = fields.Many2one('odoocms.institute', string='Faculty/Institute')
    term_id = fields.Many2one('odoocms.academic.term', string='Term')
    type = fields.Selection([('all', 'All'),('permanent', 'Permanent'),('contract', 'Contract'),('visiting', 'Visiting')],string='Teacher Type')
    teacher_id = fields.Many2one('odoocms.faculty.staff', string='Teacher')
    cross_faculty = fields.Boolean('Cross Faculty', default=False)
    include_other = fields.Boolean('Include Others', default=False)

    @api.onchange('term_id','institute_id')
    def onchange_term_id(self):
        domain = []
        today = fields.Date.today()
        if self.term_id and self.institute_id:
            teacher_ids = self.env['odoocms.class.primary'].search([('institute_id', '=', self.institute_id.id), ('term_id', '=', self.term_id.id)]).mapped('class_ids').mapped('faculty_ids').mapped('faculty_staff_id')
            domain = [('id', 'in', teacher_ids.ids)]
        return {'domain': {'teacher_id': domain}}

    def view_list_report(self):
        tree_view = self.env.ref('odoocms_registration.faculty_staff_load_view_tree')
        pivot_view = self.env.ref('odoocms_registration.faculty_staff_load_pivot')
        return {
            'domain': [('term_id', '=', self.term_id.id)],
            'name': 'Faculty Staff Load',
            'view_type': 'tree',
            'view_mode': 'tree,pivot',   #
            'res_model': 'faculty.staff.load',
            'view_id': False,
            'views': [
                (tree_view and tree_view.id or False, 'list'),
                (pivot_view and pivot_view.id or False, 'pivot'),
            ],
            # 'context': {'default_class_id': self.id},
            'type': 'ir.actions.act_window'
        }

    def print_report(self):
        type= self.type
        if self.type == 'all':
            type = False
            
        datas= {
            'institute_id': self.institute_id.id,
            'teacher_id': self.teacher_id.id,
            'type': type,
            'term_id': self.term_id.id,
            'cross_faculty': self.cross_faculty,
            'include_other': self.include_other
        }
        return self.env.ref('odoocms_registration.action_teacher_course_load_report').with_context(landscape=False).report_action(self, data=datas)
