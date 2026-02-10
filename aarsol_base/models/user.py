from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = "res.users"

    user_type = fields.Selection([('system', 'System')], 'Default Access', default='system')
    home_page = fields.Selection([('back', 'Back Office')], 'Home Page')

