import pdb
from odoo import fields, models, _, api


class AdmissionOfferLetter(models.Model):
    _name = 'admission.offer.letter'
    _description = 'Admission Offer Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'merit_reg_id'

    applicant_id = fields.Many2one('odoocms.application', string='Name')
    merit_reg_id = fields.Many2one('odoocms.merit.registers', string='Merit Register ID')
    program_id = fields.Many2one('odoocms.program')
    reference_no = fields.Char(string='Reference No', related='applicant_id.application_no', store=True)
    date = fields.Date(string='Date')
