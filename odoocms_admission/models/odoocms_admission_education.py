import pdb

from odoo import fields, models, _, api


class OdooCmsAdmissionEducation(models.Model):
    _name = 'odoocms.admission.education'
    _description = 'Admission Education'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    student_type = fields.Selection([('national','National'),('international','International')],string='Student Type', default='national')
    degree_ids = fields.One2many('odoocms.admission.degree', 'admission_education_id', string='Degree')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

