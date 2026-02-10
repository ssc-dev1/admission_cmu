import pdb
from odoo import api, fields, models, _


class OdooCMSNotifyResultWiz(models.TransientModel):
    _name = 'odoocms.notify.result.wiz'
    _description = 'Notify Result Wizard'
    
    term_id = fields.Many2one('odoocms.academic.term','Academic Term',required=True)
    institute_id = fields.Many2one('odoocms.institute',string='Institute')

    def notify_result(self):
        self.ensure_one()
        st_terms = self.env['odoocms.student.term'].search([
            ('term_id','=',self.term_id.id), ('institute_id','=',self.institute_id.id),('state','=','result')], limit=1000)
        for st_term in st_terms:
            st_term.student_course_ids.state = 'notify'
            st_term.state = 'done'
            st_term.student_id.cgpa = st_term.cgpa
            st_term.student_id.probation_cnt = st_term.probation_cnt
            st_term.student_id.set_probation_tag(st_term)
            if st_term.disposal_type_id and st_term.disposal_type_id.state:
                st_term.student_id.state = st_term.disposal_type_id.state.value

        # self.state = 'done'
        # self.grade_class_id.state = 'done'
        # self.class_ids.state = 'done'

        return {'type': 'ir.actions.act_window_close'}
