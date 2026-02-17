from odoo import models, fields, api, _



class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'

    admission_start_date = fields.Date('Admission Start Date')