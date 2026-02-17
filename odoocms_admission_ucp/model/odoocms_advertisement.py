import pdb

from odoo import fields, models, _, api


class OdooCmsAdvertisement(models.Model):
    _name = 'odoocms.advertisement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Odoo CMS Adevertisement'
    _rec_name = 'advertisement'

    advertisement = fields.Char(string='How do You Know about Us?')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
