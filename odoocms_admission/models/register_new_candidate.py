
from odoo import fields, models, _, api
import random
import string
import logging
from datetime import datetime, date
import re
from odoo.exceptions import UserError


class RegisterCandidate(models.Model):
    _name = 'register.candidate'
    _description = 'Register New Candidate'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'first_name'

    first_name = fields.Char(string='First Name', required=True)
    last_name = fields.Char(string='Last Name', required=True)
    email = fields.Char(string='Email', required=True)
    phone = fields.Char(string='Mobile', size=11)
    country_id = fields.Many2one('res.country', string='Nationality',required=True)
    province_id = fields.Many2one('odoocms.province', string='Province')
    province = fields.Char('Province/State')
    domicile_id = fields.Many2one('odoocms.domicile', string='Domicile')
    fee_receipt_no = fields.Char(string='Fee Receipt No')
    amount = fields.Integer(string='Amount')
    cnic = fields.Char(string="CNIC", size=15)
    applicant_id = fields.Many2one('odoocms.application', string='Application')
    reference_no = fields.Char('Reference No',related='applicant_id.application_no')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    # @api.constrains('cnic')
    # def _check_cnic(self):
    #     for rec in self:
    #         if rec.cnic:
    #             cnic_com = re.compile('^[0-9+]{5}-[0-9+]{7}-[0-9]{1}$')
    #             a = cnic_com.search(rec.cnic)
    #             if a:
    #                 return True
    #             else:
    #                 raise UserError(_("CNIC Format is Incorrect. Format Should like this 00000-0000000-0"))
    #     return True

    def sign_up(self):

        application = self.env['odoocms.application'].search(
            [('email', '=', self.email)])
        length = 8
        all = string.ascii_letters + string.digits + '$#'
        password = "".join(random.sample(all, length))

        for rec in self:
            already_exist = self.env['res.users'].sudo().search([('email','=',rec.email)])
            if already_exist:
                raise UserError(
                    _('Applicant Already Registered with this email.'))
            if len(rec.cnic) != 13:
                raise UserError(_("CNIC Format is Incorrect. Format Should like this 0000000000000"))
            if len(rec.phone) != 11:
                raise UserError(_("Mobile Format is Incorrect. Format Should like this 030XXXXXXXX"))
            if rec.email != application.email:
                values = {
                    'first_name': rec.first_name,
                    'last_name': rec.last_name,
                    'email': rec.email,
                    'mobile': rec.phone,
                    'applicant_type': 'national' if rec.country_id.id == 177 else 'international',
                    'password': password,
                    'cnic': rec.cnic,
                    'nationality': rec.country_id.id,
                    'term_id':self.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.admission_term_id'),
                    'step_no': 1,
                }
                    # 'fee_voucher_state': 'verify',
                    # 'voucher_date': date.today(),
                    # 'voucher_verified_date': fields.Date.today(),
                if rec.country_id.id == 177:
                    values.update({
                        'province_id': rec.province_id.id,
                        'domicile_id': rec.domicile_id.id,  
                    })
                else:
                    values.update({
                        'province2': rec.province
                    })

                app_id = self.env['odoocms.application'].sudo().create(values)
                rec.applicant_id = app_id.id
                app_id.backend_sale = True
                user_create = self.env['res.users'].sudo().create({
                    'name': str(rec.first_name) + ' ' + str(rec.last_name),
                    'sel_groups_1_9_10': 9,
                    'email': rec.email,
                    'user_type': 'student',
                    'login': app_id.application_no,
                    'phone': rec.phone,
                    'password': password,
                })
                app_id.user_id = user_create.id
                if user_create:
                    app_id.action_create_prospectus_invoice()
                    app_id.voucher_number = app_id.prospectus_inv_id and app_id.prospectus_inv_id.barcode or ''
                    app_id.amount = app_id.prospectus_inv_id.amount_total
                    # app_id.fee_voucher_state ='verify'
                    # app_id.voucher_verified_date = fields.Datetime.today().date()
                    rec.fee_receipt_no = app_id.voucher_number
                    rec.amount = app_id.amount
                    user = self.env['res.users'].sudo().search([('login', '=', app_id.application_no)])

                    processing_fee = self.env['ir.config_parameter'].sudo().search([('key', '=', 'odoocms_admission_portal.registration_fee')])
                    if not processing_fee:
                        return
                    pass_val = {
                        'email': rec.email,
                        'password': password,
                        'login': app_id.application_no,
                        'applicant_name':app_id.name,
                        'company_name': self.env.company.name,
                        'company_website': self.env.company.website,
                        'company_email': self.env.company.admission_mail,
                        'company_phone': self.env.company.admission_phone,
                        'processing_fee': processing_fee or 0
                    }
                    template = self.env['mail.template'].sudo().find_template(company_id=self.company_id, event='admission_signup', name='Admission Signup')
                    if template:
                        template.sudo().with_context(pass_val).send_mail(user.id, force_send=True)
                    message_id = self.env['success.message.wizard'].create({
                        'message': 'New Student Registered Successfully...'
                    })
                    return {
                        'name': 'Message',
                        'type': 'ir.actions.act_window',
                        'view_mode': 'form',
                        'res_model': 'success.message.wizard',
                        'res_id': message_id.id,
                        'target': 'new'
                    }

            elif application.email == rec.email:
                raise UserError(
                    _('Student Already Registered with this email.'))

    @api.depends('cnic')
    def _get_application(self):
        for rec in self:
            rec.applicant_id = False
            application = self.env['odoocms.application'].sudo().search([('cnic','=',rec.cnic)],limit=1)
            rec.applicant_id = application.id
