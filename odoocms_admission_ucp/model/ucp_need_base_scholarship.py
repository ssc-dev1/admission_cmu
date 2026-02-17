import pdb
from odoo import fields, models, _, api


class NeedBaseScholarship(models.Model):
    _name = 'applicant.need.base.scholarship'
    _description = 'Need Base Scholarship'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'guardian_occupation'

    guardian_occupation = fields.Char(string='Father/Guardian Occupation')
    guardian_job_status = fields.Selection(string='Guardian Job Status',
        selection=[('serving', 'Serving'),('retired', 'Retired'), ],
        required=False, default='serving')
    guardian_monthly_income = fields.Char(string='Father/Guardians Monthly Income')
    residential_status = fields.Selection(string='Residential Status',
        selection=[('r', 'Resident'),('nr', 'Non Resident'), ],
        required=False, default='r')
    family_member = fields.Char(string='Family Member')
    # application_id = fields.Many2one('odoocms.application')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
