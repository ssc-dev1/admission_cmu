# -*- coding: utf-8 -*-
import pdb

from odoo import models, fields, api, _


class OdooCMSFeeBarcode(models.Model):
    _inherit = 'odoocms.fee.barcode'

    admission_no = fields.Char(related='student_id.admission_no', store=True)

    def unlink(self):
        # pdb.set_trace()
        for rec in self:
            invoice_ids = rec.line_ids.mapped('move_id')
            invoice_ids.unlink()
        return super().unlink()


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    application_id = fields.Many2one('odoocms.application', 'Application')
    application_ref_no = fields.Char(related='application_id.application_no', string='Application No')


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    study_scheme_line = fields.Many2one('odoocms.study.scheme.line', string='Study Scheme Line')
