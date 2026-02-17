# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import pdb


class OdooCMS_Campus_Wise_Program_ext_campus(models.Model):
    _inherit = 'res.company'

    company_tag = fields.Char('Tag Line')
    logo_width = fields.Integer('Logo Width')
    logo_height = fields.Integer('Logo Height')
    apply_deemed_value = fields.Boolean('Apply Deemed Value', default=True)


class OdooCMSMail_Server_ubas_ext(models.Model):
    _inherit = 'ir.mail_server'

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")
