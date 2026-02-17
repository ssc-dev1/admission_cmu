# -*- coding: utf-8 -*-
import tempfile
import binascii
import xlrd
from odoo import models, fields, exceptions, api, _
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
    _name = "fee.payment.register.import.wizard"
    _description = 'Fee Import into the Payment Register'

    file = fields.Binary('File')
    sequence_opt = fields.Selection([('custom', 'Use Excel/CSV Sequence Number'), ('system', 'Use System Default Sequence Number')], string='Sequence Option', default='custom')
    import_option = fields.Selection([('csv', 'CSV File'), ('xls', 'XLS File')], string='Select', default='xls')

    def fee_payment_import_action(self):
        """Load data from the CSV file."""
        if self.import_option=='csv':
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
                    if i==0:
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
                if register_id and register_id.state=='Draft':
                    for row_no in range(sheet.nrows):
                        if row_no <= 0:
                            fields = list(map(lambda row: row.value.encode('utf-8'), sheet.row(row_no)))
                        else:
                            barcode = None
                            amount = None
                            line = list(map(lambda row: str(row.value), sheet.row(row_no)))
                            barcode_vals = line[0]
                            amount_vals = line[1]
                            barcode_val = barcode_vals.split('.')
                            amount_val = amount_vals.split('.')
                            if barcode_val and amount_val:
                                barcode = barcode_val[0]
                                amount = amount_val[0]
                            if barcode and amount:
                                register_id.store_barcode(barcode, float(amount))  # , date_payment=register_id.date
                else:
                    raise UserError('This Fee Register (Bank Scroll) is not in the Draft State.')

            else:
                raise UserError(_('Please Select the File to Import'))
