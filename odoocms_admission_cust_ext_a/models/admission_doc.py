from odoo import fields, models, _, api
from datetime import date


class AdmissionDocuments(models.Model):
    _inherit = 'applicant.academic.detail'

    verification_by = fields.Char(string="Verification By")
    verification_date = fields.Date(string="Verification Date")
    active = fields.Boolean(default=True, help="Set active to false to hide the student document without removing it.")

    def action_document_verified(self):
        for rec in self:
            values_to_update={
            'doc_verify': True,
            'doc_state':'yes',
            'verification_date':date.today(),
            'verification_by' : self.env.user.email
            }
            rec.write(values_to_update)
            rec.compute_verification_status()

    def action_document_unverified(self):
        for rec in self:
            values_to_update={
            'doc_verify': True,
            'doc_state':'no',
            'verification_date':  date.today(),
            'verification_by':  self.env.user.email
            }
            rec.write(values_to_update)
            rec.compute_verification_status()

    def action_document_rejected(self):
        for rec in self:
            values_to_update={
            'doc_verify': True,
            'doc_state': 'rejected',
            'verification_date':date.today(),
            'verification_by': self.env.user.email
            }
            rec.write(values_to_update)
            rec.compute_verification_status()

    def compute_verification_status(self):
        for rec in self:
            if rec.reference_no:
                doc_recs = rec.env['applicant.academic.detail'].search(
                    [('reference_no', '=', rec.reference_no)], order='id asc')
                verification_status = 'not_verified'
                verified_count = 0
                if doc_recs:
                    for d_rec in doc_recs:
                        if d_rec.doc_state == "rejected":
                            verification_status = "rejected"
                            record = rec.env['odoocms.application'].sudo().search([('id', '=', int(d_rec.application_id))])
                            record.sudo().write({'verification_status': verification_status})
                            return
                        elif d_rec.doc_state == "yes":
                            verified_count += 1
                    if verified_count == len(doc_recs):
                        verification_status = 'verified'
                    elif verified_count > 0:
                        verification_status = 'partially_verified'
                    record = rec.env['odoocms.application'].sudo().search([('id', '=', int(d_rec.application_id))])
                    record.sudo().write({'verification_status': verification_status})
