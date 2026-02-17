import time
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError, UserError


class OdoocmsProgramTermScholarshipCopyWiz(models.TransientModel):
    _name = 'odoocms.program.term.scholarship.copy.wiz'
    _description = 'Program Term Scholarship Copy Wiz'

    @api.model
    def get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        if term_id:
            return term_id.id
        else:
            return False

    @api.model
    def _get_scholarship_ids(self):
        if self.env.context.get('active_model', False)=='odoocms.program.term.scholarship' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    copy_to_term = fields.Many2one('odoocms.academic.term', 'Copy To Term', default=get_current_term)
    prev_scholarship_ids = fields.Many2many('odoocms.program.term.scholarship', 'program_term_scholarship_copy_rel2',
                                            'wiz_id', 'scholarship_id', 'Prev Scholarships', default=_get_scholarship_ids)

    def action_copy_scholarships(self):
        if self.copy_to_term:
            for scholarship_rec in self.prev_scholarship_ids:
                data_values = {
                    'term_id': self.copy_to_term and self.copy_to_term.id or False,
                    'program_id': scholarship_rec.program_id and scholarship_rec.program_id.id or False,
                    'scholarship_ids': scholarship_rec.scholarship_ids and scholarship_rec.scholarship_ids.ids or [],
                }
                new_rec = self.env['odoocms.program.term.scholarship'].sudo().create(data_values)
