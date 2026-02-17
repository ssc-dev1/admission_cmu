# -*- coding: utf-8 -*-
import pdb
import time
import tempfile
import binascii
import xlrd
from odoo import models, fields, exceptions, api, _
from io import StringIO
import io
from odoo.exceptions import UserError, ValidationError

import logging

_logger = logging.getLogger(__name__)

try:
    import csv
except ImportError:
    _logger.debug('Cannot `import csv`.')
try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class FeePaymentRegisterImportWizard(models.TransientModel):
    _inherit = "fee.payment.register.import.wizard"

    def fee_payment_import_action(self):
        """Load data from the CSV file."""
        if self.import_option == 'csv':
            keys = ['barcode']
            data = base64.b64decode(self.file)
            file_input = io.StringIO(data.decode("utf-8"))
            file_input.seek(0)
            reader_info = []
            reader = csv.reader(file_input, delimiter=',')
            try:
                reader_info.extend(reader)
            except Exception:
                raise exceptions.Warning(_("Not a valid file!"))
            values = {}
            for i in range(len(reader_info)):
                field = list(map(str, reader_info[i]))
                values = dict(zip(keys, field))
                if values:
                    if i == 0:
                        continue
                    else:
                        values.update({'option': self.import_option, 'seq_opt': self.sequence_opt})
                        res = self.make_sale(values)

        else:
            if self.file:
                fp = tempfile.NamedTemporaryFile(suffix=".xlsx")
                fp.write(binascii.a2b_base64(self.file))
                fp.seek(0)
                workbook = xlrd.open_workbook(fp.name)
                sheet = workbook.sheet_by_index(0)
                register_id = self.env['odoocms.fee.payment.register'].browse(self._context.get('active_id', False))

                if register_id and register_id.state == 'Draft':
                    for row_no in range(sheet.nrows):
                        val = {}
                        if row_no <= 0:
                            fields = list(map(lambda row: row.value.encode('utf-8'), sheet.row(row_no)))
                        else:
                            line = list(map(lambda row: str(row.value), sheet.row(row_no)))
                            barcode = line[0]
                            vals = barcode.split('.')
                            if vals:
                                barcode = vals[0]
                            if barcode:
                                invoice_id = False
                                already_exist = False
                                already_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', barcode), ('payment_register_id', '=', register_id.id)])
                                if not already_exist:
                                    already_exist = self.env['account.move'].search([('old_challan_no', '=', barcode), ('move_type', '=', 'out_invoice'), ('payment_state', 'in', ('in_payment', 'paid'))])

                                if not already_exist:
                                    invoice_id = self.env['account.move'].search([('old_challan_no', '=', barcode), ('move_type', '=', 'out_invoice'), ('payment_state', 'not in', ('in_payment', 'paid'))])
                                    if not invoice_id:
                                        invoice_id = self.env['account.move'].search([('name', '=', barcode), ('move_type', '=', 'out_invoice'), ('payment_state', 'not in', ('in_payment', 'paid'))])

                                    # Create the Record in the Fee Payment Receipts
                                    if invoice_id:
                                        if invoice_id.amount_residual == float(line[1]):
                                            values = {
                                                'invoice_id': invoice_id.id,
                                                'receipt_number': barcode,
                                                'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
                                                'invoice_status': invoice_id.payment_state and invoice_id.payment_state or '',
                                                'amount': invoice_id.amount_residual,
                                                'term_id': invoice_id.student_id.term_id and invoice_id.student_id.term_id.id or False,
                                                'journal_id': register_id.journal_id and register_id.journal_id.id or False,
                                                'date': register_id.date,
                                                'payment_register_id': register_id.id,
                                                'received_amount': line[1] and float(line[1]),
                                            }
                                            self.env['odoocms.fee.payment'].create(values)

                                        # Amount Mismatch Record Creation
                                        elif not invoice_id.amount_residual == float(line[1]):
                                            mm_values = {
                                                'barcode': barcode,
                                                'invoice_id': invoice_id.id,
                                                'invoice_amount': invoice_id.amount_residual,
                                                'payment_amount': float(line[1]),
                                                'diff_amount': invoice_id.amount_residual - float(line[1]),
                                                'payment_register_id': register_id.id,
                                            }
                                            self.env['odoocms.fee.payments.amount.mismatch'].create(mm_values)

                                # Already Exit But Payment Register is not Set
                                if already_exist and already_exist._table == 'odoocms_fee_payment':
                                    for already_exist_id in already_exist:
                                        if already_exist_id.payment_register_id:
                                            already_exist_id.payment_register_id = register_id.id

                                # Already Exit And Payment Register is also Set
                                if already_exist and already_exist._table == 'odoocms_fee_payment':
                                    for already_exist_id in already_exist:
                                        if already_exist.payment_register_id:
                                            # Create Records in the Processed Receipts
                                            notes = "Already Processed in " + (already_exist_id.payment_register_id.name and already_exist_id.payment_register_id.name or '') + " on " + already_exist_id.date.strftime("%d/%m/%Y")
                                            processed_values = {
                                                'barcode': barcode,
                                                'name': barcode,
                                                'payment_register_id': register_id.id,
                                                'notes': notes,
                                            }
                                            self.env['odoocms.fee.processed.receipts'].create(processed_values)

                                if already_exist and already_exist._table == 'account_move':
                                    for already_exist_id in already_exist:
                                        processed_values = {
                                            'barcode': barcode,
                                            'name': barcode,
                                            'payment_register_id':  register_id.id,
                                            'notes': "Already Paid",
                                        }
                                        self.env['odoocms.fee.processed.receipts'].create(processed_values)

                                # If invoice_id is not found then create in the Non Barcode Receipts
                                if not invoice_id and not already_exist:
                                    non_barcode_exit = self.env['odoocms.fee.non.barcode.receipts'].search([('barcode', '=', barcode)])
                                    if not non_barcode_exit:
                                        non_barcode_vals = {
                                            'barcode': barcode,
                                            'name': barcode,
                                            'payment_register_id': register_id.id,
                                        }
                                        self.env['odoocms.fee.non.barcode.receipts'].create(non_barcode_vals)
                else:
                    raise UserError('This Fee Register (Bank Scroll) is not in the Draft State.')

            else:
                raise UserError(_('Please Select the File to Import'))
