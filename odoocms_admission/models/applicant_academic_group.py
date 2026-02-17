from odoo import fields, models, _, api


class AdmissionDocuments(models.Model):
    _name = 'applicant.academic.group'
    _description = 'Applicant Academic Group'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    degree_id = fields.Many2one('odoocms.admission.degree')
    short_name = fields.Char('Short Name')
    academic_subject_ids = fields.One2many('applicant.academic.subjects', 'academic_group_id')
    active = fields.Boolean(string="Active", default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
