# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdoocmsProgramTermScholarship(models.Model):
    _name = 'odoocms.program.term.scholarship'
    _description = 'Program Term Scholarship'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def get_default_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        if term_id:
            return term_id.id
        else:
            return False

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', tracking=True, default=get_default_term)
    program_id = fields.Many2one('odoocms.program', 'Program', tracking=True)
    scholarship_ids = fields.Many2many('odoocms.fee.waiver', 'program_term_scholarship_rel2', 'program_term_id', 'scholarship_id', 'Scholarships')
    to_be = fields.Boolean('To Be', default=True)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('unique_program_term', 'unique(program_id,term_id)', "Duplicate Record are not Allowed."),
    ]

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdoocmsProgramTermScholarship, self).create(values)
        if not result.name:
            result.name = result.program_id.code + "-" + result.term_id.name
        return result
