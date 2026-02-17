

from odoo import fields, models, _, api


class PGCInstitute(models.Model):
    _name = 'pgc.institute'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'PGC Institute'

    name = fields.Char()
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


class PgcScholarship(models.Model):
    _name = 'applicant.pgc.scholarship'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Need Base Scholarship'
    _rec_name = 'previous_school_attend'

    previous_school_attend = fields.Char(string='Previous Institute Attend')
    pgc_registration_no = fields.Char(string='Previous Registration No')
    pgc_institute_id = fields.Many2one('pgc.institute', string='PGC Institute')
    # application_id = fields.Many2one('odoocms.application')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
