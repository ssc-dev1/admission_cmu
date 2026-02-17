import pdb

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class OdooCMSAutoEnrollment(models.TransientModel):
    _name = 'odoocms.auto.enrollment'
    _description = 'Auto Enrollment'

    @api.model
    def _get_batch(self):
        batch_id = self.env['odoocms.batch'].browse(self._context.get('active_id', False))
        if batch_id:
            return batch_id.id
        return True

    @api.model
    def _get_term(self):
        term_id = self.env['odoocms.academic.term'].search([('enrollment_active','=',True)], order='number desc', limit=1)
        if not term_id:
            term_id = self.env['odoocms.academic.term'].search([], order='number desc', limit=1)
        return term_id and term_id.id or False

    batch_id = fields.Many2one('odoocms.batch', string='Batch', required=True,
        help="""Only selected Batch will be Processed.""", default=_get_batch)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', required=True, default=_get_term)
    
    def auto_enroll(self):
        bulk_ids = self.env['odoocms.course.registration.bulk']
        for section in self.batch_id.section_ids:
            primary_class_ids = self.env['odoocms.class.primary']
            for primary_class in section.primary_class_ids:
                if primary_class.study_scheme_line_id.auto_enrollment:
                    primary_class_ids += primary_class

            # ex_bulk_ids = self.env['odoocms.course.registration.bulk'].search([('batch_id','=',self.batch_id.id),('term_id','=',self.term_id.id),('state','in',('draft','submit'))])
            # if ex_bulk_ids:
            #     primary_class_ids -= ex_bulk_ids.mapped('compulsory_course_ids')
                
            if primary_class_ids and section.student_ids:
                data = {
                    'batch_id': self.batch_id.id,
                    'term_id': self.term_id.id,
                    'enrollment_type': 'enrollment',
                    'compulsory_course_ids': [[6, 0, primary_class_ids.ids]],
                    'student_ids': [[6, 0, section.student_ids.ids]]
                }
                bulk_ids += self.env['odoocms.course.registration.bulk'].create(data)

        self.env.cr.commit()
        for bulk_id in bulk_ids:
            bulk_id.action_submit()
            bulk_id.action_approve()
            
        if bulk_ids:
            reg_list = bulk_ids.mapped('id')
            return {
                'domain': [('id', 'in', reg_list)],
                'name': _('Auto Enrollment'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'odoocms.course.registration.bulk',
                'view_id': False,
                # 'context': {'default_class_id': self.id},
                'type': 'ir.actions.act_window'
            }

        return 1



