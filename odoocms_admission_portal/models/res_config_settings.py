from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    registration_fee = fields.Float('Registration Fee', default=1000.00, config_parameter='odoocms_admission_portal.registration_fee')
    additional_fee = fields.Float('Additional Fee', default=1000.00, config_parameter='odoocms_admission_portal.additional_fee')
    registration_fee_international = fields.Float('Registration Fee International', default=100.00, config_parameter='odoocms_admission_portal.registration_fee_international')
    account_payable = fields.Char("1st: Fee Payable At", config_parameter='odoocms_admission_portal.account_payable')
    account_title = fields.Char('1st: Account Title', config_parameter='odoocms_admission_portal.account_title')
    account_no = fields.Char('1st: Account Number', config_parameter='odoocms_admission_portal.account_no')

    account_payable2 = fields.Char("2nd: Fee Payable At", config_parameter='odoocms_admission_portal.account_payable2')
    account_title2 = fields.Char('2nd: Account Title', config_parameter='odoocms_admission_portal.account_title2')
    account_no2 = fields.Char('2nd: Account Number', config_parameter='odoocms_admission_portal.account_no2')
    color_scheme = fields.Char('Color Scheme', config_parameter='odoocms_admission_portal.color_scheme', default='rgba(110, 8, 81, 1)')
    color_scheme2 = fields.Char('Color Scheme Gradient', config_parameter='odoocms_admission_portal.color_scheme2', default='rgba(197, 123, 177, 1)')
    admission_term_id = fields.Many2one('odoocms.academic.term', string='Admission Term',config_parameter='odoocms_admission_portal.admission_term_id')
    dob_max = fields.Char('Dob Maximum',config_parameter='odoocms_admission_portal.dob_max',default='1994-12-12')
    dob_min = fields.Char('Dob Minimum',config_parameter='odoocms_admission_portal.dob_min',default='2010-12-12')


class Company(models.Model):
    _inherit = 'res.company'

    admission_mail = fields.Char(string='Admission office Email')
    admission_phone = fields.Char(string='Admission office Phone')
    admission_invoice = fields.Integer('Admission Invoice', default=4)
