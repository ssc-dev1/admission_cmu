from odoo import models, fields

class CustomLog(models.Model):
    _name = 'custom.log'
    _description = 'Custom Log'

    name = fields.Char(string='Log Name')
    model = fields.Char(string='Model')
    method = fields.Char(string='Method')
    log_level = fields.Selection([
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error')
    ], string='Log Level')
    message = fields.Text(string='Message')
    to_be =fields.Boolean('To Be')
    company_id = fields.Many2one('res.company', string='Company')
