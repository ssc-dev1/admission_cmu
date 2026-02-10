from odoo import models, fields


class EducationInstituteSchool(models.Model):
    _name = 'odoocms.application.institute.school'
    _description = 'Educational Institute School'

    name = fields.Char(string='Odoo CMS Institute')
    code = fields.Char('code')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


class EducationInstituteCollege(models.Model):
    _name = 'odoocms.application.institute.college'
    _description = 'Educational Institute College'

    name = fields.Char(string='Odoo CMS Institute')
    code = fields.Char('code')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


class EducationInstituteUniversity(models.Model):
    _name = 'odoocms.application.institute.university'
    _description = 'Educational Institute University '

    name = fields.Char(string='Odoo CMS Institute')
    code = fields.Char('code')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
