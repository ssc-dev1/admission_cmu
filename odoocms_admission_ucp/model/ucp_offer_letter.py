import pdb
from odoo import fields, models, _, api



class OdooCmsApplication(models.Model):
    _inherit = 'odoocms.application'

    offer_allocated = fields.Boolean('Offer Allocated',default=False)


class UcpOfferLetter(models.Model):
    _name = 'ucp.offer.letter'
    _description = 'UCP Offer Letter'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'applicant_id'

    applicant_id = fields.Many2one('odoocms.application', string='Name')
    program_id = fields.Many2one('odoocms.program', string='Program')
    reference_no = fields.Char(string='Reference No',related='applicant_id.application_no')
    is_blacklisted = fields.Boolean('Is Blacklisted',default=False)
    date = fields.Datetime(string='Date')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    def send_mail(self):
        if not self.is_blacklisted:
            # template = self.env.ref('odoocms_merit_ucp.mail_template_offer_letter').sudo()
            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', self.applicant_id.company_id.id)])
            template = self.env['mail.template'].sudo().search([('name', '=', 'Offer Letter'), ('mail_server_id', '=', mail_server_id.id)])
            template.send_mail(self.id, force_send=True)
    
    @api.model
    def create(self, vals):
        result = super().create(vals)
        if result:
            result.applicant_id.offer_allocated = True
        return result
