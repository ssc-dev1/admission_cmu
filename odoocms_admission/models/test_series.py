from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import pdb


class OdooCMSEntryTestSeries(models.Model):
    _name = 'odoocms.admission.test.series'
    _description = "Entry Test Series"

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    state = fields.Boolean(string='State', default=False)
    register_id = fields.Many2one('odoocms.admission.register', 'Register')
    test_center_ids = fields.One2many('odoocms.admission.test.center', 'test_series_id', 'Test Series')
    applicant_ids = fields.One2many('odoocms.application', 'test_series_id', 'Application')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
