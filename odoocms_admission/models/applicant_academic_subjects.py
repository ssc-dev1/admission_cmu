from odoo import fields, models, _, api


class ApplicantAcademicSubects(models.Model):
    _name = 'applicant.academic.subjects'
    _description = 'Applicant Academic Subjects'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    academic_group_id = fields.Many2one('applicant.academic.group')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

