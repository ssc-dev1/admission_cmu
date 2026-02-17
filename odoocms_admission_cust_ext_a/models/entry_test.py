import pdb

from odoo import fields, models


class ApplicantEntryTest(models.Model):
    _inherit = 'applicant.entry.test'

    # hec = fields.Boolean(string="HEC", readonly=True)
    pre_test_id = fields.Many2one(comodel_name="odoocms.pre.test",required=False, string="Pre-Test Name", readonly=True)
    exempt_entry_test = fields.Boolean(string="Exempt Entry Test", required=False,related ="pre_test_id.exempt_entry_test" , readonly=True, store=True)
    pre_test_name = fields.Char(string="Pre-Test Name", required=False,  related ="pre_test_id.name" , readonly=True)
    cbt_sync = fields.Boolean(string="CBT Sync Status",default=False )