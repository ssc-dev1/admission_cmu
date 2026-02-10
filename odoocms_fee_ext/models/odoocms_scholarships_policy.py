# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdoocmsScholarshipContinuePolicy(models.Model):
    _name = 'odoocms.scholarship.continue.policy'
    _description = 'Scholarship Continue policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    start_term = fields.Many2one('odoocms.academic.term', 'Start Term')
    end_term = fields.Many2one('odoocms.academic.term', 'End Term')
    policy_lines = fields.One2many('odoocms.scholarship.continue.policy.line', 'policy_id', 'Policy Detail')
    to_be = fields.Boolean('To Be', default=True)
    current = fields.Boolean('Current')
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_lock(self):
        self.state = 'lock'
        if self.policy_lines:
            self.policy_lines.write({'state': 'lock'})

    def action_unlock(self):
        self.state = 'draft'
        if self.policy_lines:
            self.policy_lines.write({'state': 'draft'})

    @api.model
    def create(self, values):
        result = super(OdoocmsScholarshipContinuePolicy, self).create(values)
        if not result.name:
            result.name = result.start_term.code
            if result.end_term:
                result.name = result.name + "-" + result.end_term.code
        return result


# referred in studenr, move, applied
class OdoocmsScholarshipContinuePolicyLines(models.Model):
    _name = 'odoocms.scholarship.continue.policy.line'
    _description = 'Scholarship Continue policy Detail'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'scholarship_id'

    sequence = fields.Integer('Sequence')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship', tracking=True)

    credit_hours = fields.Float('Credit Hours', tracking=True)
    course_count = fields.Float('Course Count')
    cgpa = fields.Float('CGPA', tracking=True)
    sgpa = fields.Float('SGPA', tracking=True)

    current_credit_hours = fields.Float('Cur. Credit Hours', tracking=True, default=0)
    current_course_count = fields.Float('Cur. Course Count', default=0)

    program_id = fields.Many2one('odoocms.program', 'Program', tracking=True)
    program_name = fields.Char('Program Name', compute='_compute_program_info', store=True)
    program_code = fields.Char('Program Code', compute='_compute_program_info', store=True)
    policy_id = fields.Many2one('odoocms.scholarship.continue.policy', 'Policy', index=True, ondelete='cascade')
    value = fields.Float('Value')
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    to_be = fields.Boolean('To Be', default=True)
    merge_policy_line = fields.Boolean('Merge Policy Line')
    company_id = fields.Many2one('res.company', string='Company', related='scholarship_id.company_id', store=True)

    @api.depends('program_id')
    def _compute_program_info(self):
        for rec in self:
            if rec.program_id:
                rec.program_name = rec.program_id.name
                rec.program_code = rec.program_id.code
