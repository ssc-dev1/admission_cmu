from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _
import pdb


class OdooCMSEntryTestCenter(models.Model):
    _name = "odoocms.admission.test.center"
    _description = "Admission Test Center"

    name = fields.Char(string='City Name', required=True)
    code = fields.Char(string='City Code', required=True)
    test_type = fields.Selection([('cbt', 'Computer Based Test'), ('pbt', 'Paper Based Test')], default="cbt")
    session = fields.Char(string='Session')
    series = fields.Char(string='Test Series')
    test_series_id = fields.Many2one('odoocms.admission.test.series', string='Test Series')

    # discipline_id = fields.Many2one('odoocms.discipline', required=True)
