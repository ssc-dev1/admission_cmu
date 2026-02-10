# -*- coding: utf-8 -*-
import pdb
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import json


class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    def check_applicant_doc(self):
        """
        Company-wise prechecks before generating the admission challan:
          - Merit check        (if company.challan_check_merit_list is True)
          - Documents check    (if company.challan_check_document_verification is True)
          - Scholarship check  (if company.challan_check_scholarship is True)

        If all enabled checks pass and challan doesn't exist, create it.
        """
        MeritLine = self.env['odoocms.merit.register.line'].sudo()
        company = self.env.company
        result = False

        for rec in self:
            # -----------------------
            # 1) Merit list (optional)
            # -----------------------
            if getattr(company, 'challan_check_merit_list', False):
                domain = [('applicant_id', '=', rec.id), ('selected', '=', True)]
                # prefer current merit register if set
                if rec.meritlist_id:
                    merit_line = MeritLine.search(domain + [('merit_reg_id', '=', rec.meritlist_id.id)], limit=1)
                    if not merit_line:
                        merit_line = MeritLine.search(domain, limit=1)
                else:
                    merit_line = MeritLine.search(domain, limit=1)

                if not merit_line:
                    raise UserError(_("Record Not Found in Merit List"))
            if getattr(company, 'challan_check_offer_letter', False):
                exists = self.env['ucp.offer.letter'].sudo().search_count([
                    ('applicant_id', '=', rec.id)
                ])
                if not exists:
                    raise UserError(_("The offer letter must be sent to the applicant before proceeding."))
            # -----------------------------
            # 2) Documents verified (optional)
            # -----------------------------
            if getattr(company, 'challan_check_document_verification', False):
                pending = rec.applicant_academic_ids.filtered(
                    lambda x: x.doc_state not in ('yes', 'reg_verified')
                )
                if pending:
                    raise UserError(_("Applicant Doc not verified"))

            # --------------------------------
            # 3) Scholarship assigned (optional)
            # --------------------------------
            if getattr(company, 'challan_check_scholarship', False):
                if not rec.scholarship_id:
                    raise UserError(_("Scholarship not Assigned to Student"))

            # --------------------------------------
            # All enabled checks passed → make challan
            # --------------------------------------
            if not rec.admission_inv_id:
                try:
                    # call underlying implementation but skip internal checks there
                    result = rec.action_create_admission_invoice(bypass_check=True)
                except TypeError:
                    # in case the target method doesn't accept bypass_check
                    result = rec.action_create_admission_invoice()
            else:
                result = rec.admission_inv_id

        return result
