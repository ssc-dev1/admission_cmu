from odoo import models, fields


class BlackListApplication(models.Model):
    _name = 'admission.blacklist.application'
    _description = 'BlackList Applicant'
    _rec_name = 'cnic'

    name = fields.Char('Name',required=True)
    cnic = fields.Char('CNIC/Passport',required=True)
    description = fields.Char('Reason',required=True)
    date = fields.Date('Entry Date',default=fields.Date.today())
    dob = fields.Date('Date of Birth')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    