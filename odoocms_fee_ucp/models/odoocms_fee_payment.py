import pdb
from odoo import api, fields, models, tools, _
import logging

_logger = logging.getLogger(__name__)


class OdooCMSFeePayment(models.Model):
    _inherit = 'odoocms.fee.payment'

    # This Method is used for Payment creation in the 1LINK
    @api.model
    def create_1link_payment(self, date, consumer_no, amount, journal_id):
        new_rec = False
        if date and consumer_no:
            register_id = self.env['odoocms.fee.payment.register'].sudo().search([('date', '=', date), ('journal_id', '=', journal_id)])
            if not register_id:
                register_values = {
                    'date': date,
                }
                register_id = self.env['odoocms.fee.payment.register'].sudo().create(register_values)

            if register_id.state == 'Draft':
                invoice_id = self.env['account.move'].search([('old_challan_no', '=', consumer_no), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
                already_exist = self.env['odoocms.fee.payment'].sudo().search([('receipt_number', '=', consumer_no), ('invoice_id.amount_residual', '=', 0.0)])
                if not already_exist:
                    already_exist = self.env['account.move'].search([('old_challan_no', '=', consumer_no), ('move_type', '=', 'out_invoice'), ('amount_residual', '=', 0.0)])
                if not already_exist:
                    fee_payment_rec_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', consumer_no)], order='id', limit=1)
                    if fee_payment_rec_exist:
                        if fee_payment_rec_exist.received_amount >= fee_payment_rec_exist.amount:
                            already_exist = fee_payment_rec_exist

                if not already_exist:
                    already_exist = self.env['odoocms.fee.payment'].search([('invoice_id', '=', invoice_id.id), ('payment_register_id', '=', register_id.id), ('invoice_id.amount_residual', '>', 0.0), ], order='id', limit=1)

                # Create the Record in the Fee Payment Receipts
                if invoice_id and not already_exist:
                    values = {
                        'invoice_id': invoice_id.id,
                        'receipt_number': consumer_no,
                        'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
                        'invoice_status': invoice_id.payment_state and invoice_id.payment_state or '',
                        'amount': invoice_id.amount_residual,
                        'id_number': invoice_id.student_id.code and invoice_id.student_id.code or '',
                        'session_id': invoice_id.session_id and invoice_id.session_id.id or False,
                        # 'career_id': invoice_id.career_id and invoice_id.career_id.id or False,
                        # 'institute_id': invoice_id.institute_id and invoice_id.institute_id.id or False,
                        # 'discipline_id': invoice_id.discipline_id and invoice_id.discipline_id.id or False,
                        # 'campus_id': invoice_id.campus_id and invoice_id.campus_id.id or False,
                        'term_id': invoice_id.term_id and invoice_id.term_id.id or False,
                        # 'semester_id': invoice_id.semester_id and invoice_id.semester_id.id or False,
                        'journal_id': journal_id,
                        'date': date,
                        'payment_register_id': register_id.id,
                        'received_amount': invoice_id.amount_residual,
                    }
                    new_rec = self.env['odoocms.fee.payment'].sudo().create(values)

                # Already Exist But Payment Register is not Set
                if already_exist and already_exist._table == 'odoocms_fee_payment' and not already_exist.payment_register_id:
                    for already_exist_id in already_exist:
                        already_exist_id.payment_register_id = register_id._origin.id

                # Already Exit And Payment Register is also Set
                if already_exist and already_exist._table == 'odoocms_fee_payment' and already_exist.payment_register_id:
                    for already_exist_id in already_exist:
                        # Create Records in the Processed Receipts
                        notes = "Already Processed in " + (already_exist_id.payment_register_id.name and already_exist_id.payment_register_id.name or '') + " on " + already_exist_id.date.strftime("%d/%m/%Y")
                        processed_values = {
                            'barcode': consumer_no,
                            'name': consumer_no,
                            'payment_register_id': register_id.id,
                            'notes': notes,
                        }
                        self.env['odoocms.fee.processed.receipts'].create(processed_values)

                # If invoice_id is not found then create in the Non Barcode Receipts
                if not invoice_id and not already_exist:
                    non_barcode_exit = self.env['odoocms.fee.non.barcode.receipts'].search([('barcode', '=', self.barcode)])
                    if not non_barcode_exit:
                        non_barcode_vals = {
                            'barcode': consumer_no,
                            'name': consumer_no,
                            'payment_register_id': register_id.id,
                        }
                        self.env['odoocms.fee.non.barcode.receipts'].create(non_barcode_vals)
        return new_rec


