import pdb

from odoo import fields, models


class ApplicantEntryTest(models.Model):
    _inherit = 'applicant.entry.test'

    hec = fields.Boolean(string="HEC", readonly=True)
