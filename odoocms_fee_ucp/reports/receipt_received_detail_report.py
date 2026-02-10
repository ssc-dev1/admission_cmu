import pdb
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class ReceiptReceivedDetailReport(models.AbstractModel):
    _inherit = 'report.odoocms_fee.receipt_received_detail_report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        form = data.get('form', {})
        date_from = form.get('date_from', False)
        date_to = form.get('date_to', False)
        company_id = form.get('company_id', self.env.company.id)
        institute_ids = form.get('institute_ids') or self.env['odoocms.institute'].search([]).ids
        journal_ids = form.get('journal_ids') or self.env['account.journal'].search([('type', '=', 'bank')]).ids

        total_amount = 0
        total_inv_amount = 0
        date_to = fields.Date.from_string(date_to)
        res = {}
        lines = []

        if date_from and date_to:
            date_from = fields.Date.from_string(date_from)
            date_to = fields.Date.from_string(date_to)
            if date_from > date_to:
                raise ValidationError(_('Start Date must be Anterior to End Date'))

            payment_recs = self.env['odoocms.fee.payment'].search([('date', '>=', date_from),
                                                                   ('date', '<=', date_to),
                                                                   ('invoice_id.institute_id', 'in', institute_ids),
                                                                   ('journal_id', 'in', journal_ids)], order='date')
            if payment_recs:
                for payment_rec in payment_recs:
                    total_amount += payment_rec.received_amount
                    total_inv_amount += payment_rec.amount
                    line = {
                        'student_code': payment_rec.student_id.code,
                        'student_name': payment_rec.student_id.name,
                        'inv_date': payment_rec.invoice_id.invoice_date and payment_rec.invoice_id.invoice_date.strftime('%d-%m-%Y') or '',
                        'inv_no': payment_rec.invoice_id.name,
                        'inv_barcode': payment_rec.invoice_id.old_challan_no,
                        'inv_type': dict(self.env['account.move'].fields_get(allfields=['challan_type'])['challan_type']['selection'])[payment_rec.invoice_id.challan_type],
                        'inv_amount': payment_rec.amount,
                        'received_amount': payment_rec.received_amount,
                        'bank': payment_rec.journal_id.name,
                        'institute': payment_rec.invoice_id.institute_id.code,
                        'diff': round(payment_rec.amount - payment_rec.received_amount, 2),
                    }
                    lines.append(line)

            res = lines
            report = self.env['ir.actions.report']._get_report_from_name('odoocms_fee.receipt_received_detail_report')
            docargs = {
                'doc_ids': [],
                'doc_model': report.model,
                'data': data['form'],
                'invoice': res or [],
                'total_amount': round(total_amount, 2) or '',
                'total_inv_amount': round(total_inv_amount, 2) or '',
                'date_from': date_from.strftime("%d-%m-%Y") or False,
                'date_to': date_to.strftime("%d-%m-%Y") or False,
                'amount_diff': round(total_inv_amount - total_amount, 2),
            }
            return docargs
