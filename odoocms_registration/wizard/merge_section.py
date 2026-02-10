import pdb

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

# access_odoocms_merge_section,access.odoocms.merge.section,model_odoocms_merge_section,base.group_user,1,1,1,1


class OdooCMSMergeSection(models.TransientModel):
    _name = 'odoocms.merge.section'
    _description = 'Merge Section'

    @api.model
    def _get_class(self):
        primary_class_id = self.env['odoocms.class.primary'].browse(self._context.get('active_id', False))
        if primary_class_id:
            return primary_class_id.id
        return True

    term_id = fields.Many2one('odoocms.academic.term','Academic Term')
    primary_class_id = fields.Many2one('odoocms.class.primary', string='Primary Class', default=_get_class)
    merge_with = fields.Many2one('odoocms.class.primary','Merge With')

    def merge_section(self):
        self.primary_class_id.parent_id = self.merge_with.id
        for registration in self.primary_class_id.registration_ids:
            # move_line = self.env['account.move.line'].search([
            #     ('student_id', '=', registration.student_id.id),
            #     ('move_id.term_id', '=', self.term_id.id),
            #     ('course_id_new', '=', registration.primary_class_id.id)])
            # if move_line:
            #     move_line.write({'course_id_new': self.new_class_id.id})

            for course_component in registration.component_ids:
                new_component = self.merge_with.class_ids.filtered(lambda m: m.component == course_component.class_id.component)
                if new_component:
                    course_component.class_id = new_component.id

            registration.primary_class_id = self.merge_with.id

        return 1


