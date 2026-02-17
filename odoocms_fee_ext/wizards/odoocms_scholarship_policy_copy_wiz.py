import time
from odoo import fields, models, _, api
import json
from odoo.exceptions import ValidationError, UserError


class OdoocmsScholarshipPolicyCopyWiz(models.TransientModel):
    _name = 'odoocms.scholarship.policy.copy.wiz'
    _description = 'Scholarship Policy Copy Wiz'

    @api.model
    def _get_policy_id(self):
        if self.env.context.get('active_model', False)=='odoocms.scholarship.continue.policy' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    policy_id = fields.Many2one('odoocms.scholarship.continue.policy', 'Policy', default=_get_policy_id)
    scholarship_ids_domain = fields.Char(compute="_compute_scholarship_domain", readonly=True, store=False)
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    program_id = fields.Many2one('odoocms.program', 'Program')
    program_ids = fields.Many2many('odoocms.program', 'scholarship_copy_wiz_program_rel', 'wiz_id', 'program_id', 'Programs')

    @api.depends('policy_id')
    def _compute_scholarship_domain(self):
        for rec in self:
            s_list = []
            if rec.policy_id and rec.polpolicy_id.policy_lines:
                s_list = rec.policy_id.policy_lines.mapped('scholarship_id').ids
            rec.scholarship_ids_domain = json.dumps([('id', 'in', s_list)])

    def action_scholarship_policy_copy(self):
        if self.policy_id and self.scholarship_id:
            for program_id in self.program_ids:
                policy_lines = self.env['odoocms.scholarship.continue.policy.line'].search([('policy_id', '=', self.policy_id.id),
                                                                                            ('scholarship_id', '=', self.scholarship_id.id),
                                                                                            ('program_id', '=', self.program_id.id)])
                if policy_lines:
                    for policy_line in policy_lines:
                        data_values = {
                            'scholarship_id': policy_line.scholarship_id and policy_line.scholarship_id.id or False,
                            'credit_hours': policy_line.credit_hours,
                            'cgpa': policy_line.cgpa,
                            'program_id': program_id.id,
                            'policy_id': self.policy_id and self.policy_id.id or False,
                            'value': policy_line.value,
                            'state': policy_line.state,
                        }
                        new_rec = self.env['odoocms.scholarship.continue.policy.line'].sudo().create(data_values)
