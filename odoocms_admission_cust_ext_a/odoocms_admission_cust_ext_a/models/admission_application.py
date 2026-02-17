from odoo import fields, models, _, api
from datetime import datetime


class OdooCMSAdmissionApplication(models.Model):
    _inherit ='odoocms.application'

    verification_status = fields.Selection(string="Doc Verification Status", selection=[('verified', 'Verified'), ('not_verified', 'Not Verified'),('partially_verified','Partially Verified'),('rejected','Rejected') ], required=False, default='not_verified')
    ref_meritlist = fields.Many2one(comodel_name="odoocms.merit.registers", string="Merit List", required=False)
    meritlist_date = fields.Datetime(string="MeritList Date", related='ref_meritlist.posting_date', store=True, readonly=True)
    pre_test_attachment_download = fields.Binary(string="Pre-Test File Download", related='pre_test_attachment')
    # hec =  fields.Boolean(string="HEC", related='pre_test_id.hec', readonly=True, store=True)
    exempt_entry_test = fields.Boolean(string="Exempt Entry Test", related='pre_test_id.exempt_entry_test', readonly=True, store=True)
    test_center_id = fields.Many2one('test.center','Test Center')
    pre_test_verification = fields.Selection([('verify', 'Verified'), ('un_verify', 'Un verify'), ('rejected', 'Rejected'),
                                         ('waiting_for_approval', 'Waiting for Approval')], string="Pre-Test Verification",readonly=True, default='waiting_for_approval')

    @api.model
    def create(self, vals):
        active_term = self.env['odoocms.admission.register'].search([
            ('state', '=', 'application'),
            ('date_start', '<=', fields.Date.today()),
            ('date_end', '>=', fields.Date.today()),
            ('company_id','=', vals['company_id'])
        ], order='id desc', limit=1)
        if not active_term:
            raise ValueError('No active term found.')
        term_id = active_term.term_id
        vals['term_id'] =term_id.id
        application_no = vals.get('application_no')
        if application_no in [None, False, _('New')]:
            new_application_no = self.env['ir.sequence'].next_by_code('odoocms.application') or _('New')
            vals['application_no'] = f'{term_id.code}{new_application_no}'

        return super(OdooCMSAdmissionApplication, self).create(vals)

    def write(self, values):
        keys_to_capitalize = ['first_name', 'middle_name', 'last_name', 'father_name', 'mother_name', 'street',
                              'street2', 'per_street', 'per_street2', 'guardian_name', 'guardian_address',
                              'fee_payer_name']
        for key, value in values.items():
            if key in keys_to_capitalize:
                if isinstance(value, str):
                    values[key] = value.upper() if value is not None and value != "" else ""
        return super(OdooCMSAdmissionApplication, self).write(values)

    def action_document_verified(self):
        for rec in self:
            rec.pre_test_verification = 'verify'
            update_applicant_entry_test_form(self)
            mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', self.company_id.id)])
            template = self.env['mail.template'].sudo().search([
                ('name', '=', 'Pre Test Verification')
            ])

            if not template:
                raise ValueError('No email template found for Pre Test Verification')

            values = {
                'pre_test_name': self.pre_test_id.name,
                'applicant_name': self.name,
                'email': self.email,
                'company_name': self.company_id.name or "",
                'company_website': self.company_id.website or "",
                'company_email': self.company_id.admission_mail or "",
                'company_id':self.company_id.id,
                'logo':self.company_id.logo,
                'company_phone': self.company_id.admission_phone or "",
                'company_address': f"{self.company_id.street or ''}, {self.company_id.street2 or ''}, {self.company_id.city or ''}",
                'email_from': self.company_id.admission_mail
            }
            try:
                template.with_context(values).send_mail(rec.user_id.id, force_send=True)
            except Exception as e:
                print(e)


    def action_document_unverified(self):
        for rec in self:
            rec.pre_test_verification = 'un_verify'
            update_applicant_entry_test_form(self)

    def action_document_rejected(self):
        for rec in self:
            rec.pre_test_verification = 'rejected'
            update_applicant_entry_test_form(self)

def update_applicant_entry_test_form(self):
        if self.application_no:
            entry_test_record = self.env['applicant.entry.test'].sudo().search([('student_id', '=', self.id)])
            # hec_test_details = self.env['odoocms.pre.test'].sudo().search([('exempt_entry_test', '=', True)])
        if len(entry_test_record) > 0:
            for record in entry_test_record:
                for d_rec in self:
                    if d_rec.fee_voucher_state == 'verify':
                        if d_rec.pre_test_verification == "verify":
                            to_update_fields = {'paper_conducted': True,
                                                'entry_test_marks': d_rec.pre_test_id.pre_test_total_marks,
                                                'cbt_marks': self.pre_test_marks,
                                                'pre_test_id':d_rec.pre_test_id.id
                                                }
                            record.sudo().write(to_update_fields)
                        elif d_rec.pre_test_verification == "un_verify" and not record[0].applicant_line_ids:
                            to_update_fields = {'paper_conducted': False,  'entry_test_marks': 0,
                                                'cbt_marks': 0,
                                                'pre_test_id': False
                                                }
                            record.sudo().write(to_update_fields)
                        elif d_rec.pre_test_verification == "rejected" and not record.applicant_line_ids:
                            to_update_fields = {'paper_conducted': False, 'entry_test_marks': 0,
                                                'cbt_marks': 0,
                                                'pre_test_id': False
                                                }
                            record.sudo().write(to_update_fields)
                    else:
                        raise Warning(_("Fee Voucher needs to be verified first"))

