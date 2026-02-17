from odoo import fields, models, _, api


class TestCenter(models.Model):
    _name = 'test.center'
    _description = 'Test Center'
    _order = 'sequence'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string='Sequence')
    city =fields.Many2one('odoocms.city', 'City')
    note =fields.Char(string="Note")
    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
