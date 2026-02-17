from odoo import models, fields, api, _



class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'

    admission_start_date = fields.Date('Admission Start Date')



class OdooCMSCourseComponent(models.Model):
    _inherit = 'odoocms.course.component'

    server_id = fields.Integer('Client ID')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    to_be = fields.Boolean()



class OdooCMSCourseType(models.Model):
    _inherit = 'odoocms.course.type'

    client_id = fields.Integer('Client ID')
    to_be = fields.Boolean()
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)