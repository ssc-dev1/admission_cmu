from odoo.fields import Datetime
from odoo import fields, models, _, api


class OdooCMSProgramInherit(models.Model):
    _inherit = 'odoocms.program'
    _description = 'Odoo CMS Program Inherit'



    work_experience_required = fields.Boolean(string="Work Experience Required", readonly=False)
    calculate_merit_with_exemption=fields.Boolean(string="Calculate Merit with Execption", readonly=False,default =False, help='Allow compute merit list without entrytest or interview' )
    publish_merit = fields.Boolean(string="Publish Merit", readonly=False , default =False)