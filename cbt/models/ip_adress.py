from odoo import models, fields


class IpAddress(models.Model):
    _name = 'ip.address.login'

    name = fields.Char(string='PC Name')
    ipaddress = fields.Char('Ip Address')

    _sql_constraints = [
        ('ipaddress', 'unique(ipaddress)', 'This Ip Address Already Added')
    ]
