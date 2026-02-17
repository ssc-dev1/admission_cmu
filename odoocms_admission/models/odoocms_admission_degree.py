from odoo import fields, models, _


class OdooCmsAdmissionDegree(models.Model):
    _name = 'odoocms.admission.degree'
    _description = 'Admission Education Degree'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    code = fields.Char(string='Code', required=True)
    year_age = fields.Integer(string='Year of Education', required=True)
    admission_education_id = fields.Many2one('odoocms.admission.education')
    specialization_ids = fields.One2many('applicant.academic.group', 'degree_id')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    active = fields.Boolean(string="Active", default=True)

    _sql_constraints = [
        ('code', 'unique(code , company_id)', 'Code Must Be Unique (Another Record of This Code Already Added)')
    ]
