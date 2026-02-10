# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class FeeReceiptBarcodeAssignment(models.TransientModel):
    _name = 'fee.receipt.barcode.assignment'
    _description = 'Fee Receipt Barcode Assignment'

    @api.model
    def _get_invoice(self):
        if self.env.context.get('active_model', False)=='account.move' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    invoice_id = fields.Many2one('account.move', string='Invoices', help="""Only selected Invoices will be Processed.""", default=_get_invoice)

    def action_receipt_barcode_assignment(self):
        pass
        # if not self.invoice_id.barcode:
        #     self.invoice_id.compute_barcode()
        # else:
        #     raise UserError(_("This Receipt has already Barcode."))
        # return {'type': 'ir.actions.act_window_close'}
