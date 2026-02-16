import pdb

from odoo import fields, models, _, api
from datetime import datetime


class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    verification_status = fields.Selection(string="Doc Verification Status", selection=[('verified', 'Verified'), ('not_verified', 'Not Verified'), ('partially_verified', 'Partially Verified'), ('rejected', 'Rejected')], required=False, default='not_verified')
    ref_meritlist = fields.Many2one(comodel_name="odoocms.merit.registers", string="Merit List", required=False)
    meritlist_date = fields.Datetime(string="MeritList Date", related='ref_meritlist.posting_date', store=True,
                                     readonly=True)
    pwwf_file = fields.Binary('PWWF File', attachment=True)
    pwwf_file_download = fields.Binary(string="PWWF File Download", related='pwwf_file')
    pre_test_attachment_download = fields.Binary(string="Pre-Test File Download", related='pre_test_attachment')
    pwwf_scholarship = fields.Boolean(string="PWWF Scholarship", required=False)
    pwwf_verification_state = fields.Selection(string="PWWF Verification State", selection=[('verified', 'Verified'), ('not_verified', 'Not Verified'), ('rejected', 'Rejected')], default='not_verified')
    scholarshio_allocate_by = fields.Many2one(comodel_name="res.users", string="Scholarship Allocated By", required=False, readonly=True)
    scholarship_allocation_date = fields.Datetime(string="Scholarship Allocation Date", required=False, readonly=True)
    hec = fields.Boolean(string="HEC", related='pre_test_id.hec', readonly=True, store=True)
    hec_verification = fields.Selection([('verify', 'Verified'),
                                         ('un_verify', 'Un verify'),
                                         ('rejected', 'Rejected'),
                                         ('waiting_for_approval', 'Waiting for Approval')
                                         ], string="HEC Verification", readonly=True, default='waiting_for_approval')

    def write(self, values):
        if values.get('scholarship_ids', False):
            old_scholarship_list = self.scholarship_ids
            new_scholarship_list = self.env['odoocms.fee.waiver'].browse(values['scholarship_ids'][0][1])
            added_title = "Following Scholarships are Added "
            dropped_title = "Following Scholarships Are Dropped "
            added_body = ''
            dropped_body = ''

            for new_scholarship_list1 in new_scholarship_list:
                if new_scholarship_list1 not in old_scholarship_list:
                    added_body = added_body + ", " + new_scholarship_list1.name

            for old_scholarship_list1 in old_scholarship_list:
                if old_scholarship_list1 not in new_scholarship_list:
                    dropped_body = dropped_body + ", " + old_scholarship_list1.name

            if len(added_body) > 1:
                added_body = added_title + added_body
                self.message_post(body=added_body)

            if len(dropped_body) > 1:
                dropped_body = dropped_title + dropped_body
                self.message_post(body=dropped_body)
                # value updated for scholarship_allocation_date and scholarshio_allocate_by
            for rec in self:
                rec.scholarship_allocation_date = datetime.now()
                rec.scholarshio_allocate_by = self.env.user

        res = super(OdooCMSAdmissionApplication, self).write(values)
        return res

    def action_document_verified(self):
        for rec in self:
            rec.hec_verification = 'verify'
            update_applicant_entry_test_form(self)

    def action_document_unverified(self):
        for rec in self:
            rec.hec_verification = 'un_verify'
            update_applicant_entry_test_form(self)

    def action_document_rejected(self):
        for rec in self:
            rec.hec_verification = 'rejected'
            update_applicant_entry_test_form(self)

    def pwwf_document_verified(self):
        for rec in self:
            rec.pwwf_verification_state = 'verified'

    def pwwf_document_unverified(self):
        for rec in self:
            rec.pwwf_verification_state = 'not_verified'

    def pwwf_document_rejected(self):
        for rec in self:
            rec.pwwf_verification_state = 'rejected'


def update_applicant_entry_test_form(self):
    if self.application_no:
        record = self.env['applicant.entry.test'].sudo().search([('student_id', '=', self.id)])
        hec_test_details = self.env['odoocms.pre.test'].sudo().search([('hec', '=', True)])
    if record and hec_test_details:
        for d_rec in self:
            if d_rec.fee_voucher_state == 'verify':
                if d_rec.hec_verification == "verify":
                    to_update_fields = {'paper_conducted': True, 'hec': True, 'entry_test_marks': hec_test_details.pre_test_total_marks, 'cbt_marks': self.pre_test_marks}
                    record.sudo().write(to_update_fields)
                elif d_rec.hec_verification == "un_verify" and not record.applicant_line_ids:
                    to_update_fields = {'paper_conducted': False, 'hec': False, 'entry_test_marks': 0, 'cbt_marks': 0}
                    record.sudo().write(to_update_fields)
                elif d_rec.hec_verification == "rejected" and not record.applicant_line_ids:
                    to_update_fields = {'paper_conducted': False, 'hec': False, 'entry_test_marks': 0, 'cbt_marks': 0}
                    record.sudo().write(to_update_fields)
            else:
                raise Warning(_("Fee Voucher needs to be verified first"))

# @api.model
# def create(self, vals):
#     active_term = self.env['odoocms.admission.register'].search([
#         ('state', '=', 'application'),
#         ('date_start', '<=', fields.Date.today()),
#         ('date_end', '>=', fields.Date.today())
#     ], order='id desc', limit=1)
#     if not active_term:
#         raise ValueError('No active term found.')
#     term_id = active_term.term_id
#     application_no = vals.get('application_no')
#     if application_no in [None, False, _('New')]:
#         new_application_no = self.env['ir.sequence'].next_by_code('odoocms.application') or _('New')
#         vals['application_no'] = f'{term_id.code}{new_application_no}'
#     return super(OdooCMSAdmissionApplication, self).create(vals)




# test