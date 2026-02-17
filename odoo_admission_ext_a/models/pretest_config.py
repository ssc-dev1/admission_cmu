from odoo import fields, models, _, api


class PreTest(models.Model):
    _inherit = 'odoocms.pre.test'

    hec = fields.Boolean(string='HEC')
