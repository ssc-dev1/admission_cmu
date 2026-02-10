from odoo import fields, models, api, _


class OdooCMSStudySchemeLine(models.Model):
    _inherit = 'odoocms.study.scheme.line'
    _description = 'CMS Study Course Offer'



    course_type = fields.Selection(selection_add=[('deficiency', 'Deficiency')], ondelete={'deficiency': 'set default'})