
from odoo import fields, models, _, api


class PreTest(models.Model):
     _inherit = 'odoocms.pre.test'

     exempt_entry_test= fields.Boolean(string='Exempt Entry Test')
     # hec= fields.Boolean(string='HEC')