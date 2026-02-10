from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    code = fields.Char('Code')
    company_code = fields.Integer("Company Code")
    identifier = fields.Char('Identifier')
    short_name = fields.Char('Short Name')

    company_tag = fields.Char('Tag Line')
    logo_width = fields.Integer('Logo Width')
    logo_height = fields.Integer('Logo Height')

    apply_deemed_value = fields.Boolean('Apply Deemed Value', default=True)

