from odoo import fields, models, _, api
from datetime import date


class AdmissionDocuments(models.Model):
    _inherit = 'applicant.academic.detail'

    verification_by = fields.Char(string="Verification By")
    verification_date = fields.Date(string="Verification Date")

    def action_document_verified(self):
        for rec in self:
            rec.doc_verify = True
            rec.doc_state = 'yes'
            rec.verification_date = date.today()
            rec.verification_by = self.env.user.email
            compute_verification_status(self)

    def action_document_unverified(self):
        for rec in self:
            rec.doc_verify = True
            rec.doc_state = 'no'
            rec.verification_date = date.today()
            rec.verification_by = self.env.user.email
            compute_verification_status(self)

    def action_document_rejected(self):
        for rec in self:
            rec.doc_verify = True
            rec.doc_state = 'rejected'
            rec.verification_date = date.today()
            rec.verification_by = self.env.user.email
            compute_verification_status(self)


def compute_verification_status(self):
    if self.reference_no:
        doc_recs = self.env['applicant.academic.detail'].search(
            [('reference_no', '=', self.reference_no)], order='id asc')

        verification_status = 'not_verified'
        verified_count = 0
        if doc_recs:
            for d_rec in doc_recs:
                if d_rec.doc_state == "rejected":
                    verification_status = "rejected"
                    record = self.env['odoocms.application'].sudo().search([('id', '=', int(d_rec.application_id))])
                    record.sudo().write({'verification_status': verification_status})
                    return
                elif d_rec.doc_state == "yes":
                    verified_count += 1

            if verified_count == len(doc_recs):
                verification_status = 'verified'
            elif verified_count > 0:
                verification_status = 'partially_verified'

            record = self.env['odoocms.application'].sudo().search([('id', '=', int(d_rec.application_id))])
            record.sudo().write({'verification_status': verification_status})
