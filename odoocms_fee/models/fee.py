from odoo import models, fields, api
import datetime

import logging
_logger = logging.getLogger(__name__)


class OdooCMSFee(models.Model):
    _name = 'odoocms.fee'
    _description = 'Student Fee'

    student_id = fields.Many2one('odoocms.student','Student')
    program_id = fields.Many2one('odoocms.program','Program')
    session_id = fields.Many2one('odoocms.academic.session','Session')
    term_id = fields.Many2one('odoocms.academic.term','Term')
    semester_id = fields.Many2one('odoocms.semester','Semester')

    challan_no = fields.Char('Challan No')
    issue_date = fields.Date('Issue Date')
    due_date = fields.Date('Due Date')
    paid_date = fields.Date('Paid Date')

    admission_fee = fields.Float('Admission Fee')
    tuition_fee = fields.Float('Tuition Fee')

    installment_no = fields.Integer('Installment')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    discount = fields.Float('Discount')
    receipt_type = fields.Many2one('odoocms.receipt.type','Receipt Type')
    journal_id = fields.Many2one('account.journal','Journal')
    fee_head_id = fields.Many2one('odoocms.fee.head','Fee Head')
    paid = fields.Boolean('Paid')
    label_id = fields.Many2one('account.payment.term.label', 'Label')

    state = fields.Char()

    payment_term_id = fields.Many2one('account.payment.term','Payment Term')
    invoice_id = fields.Many2one('account.move','Invoice')
    challan_id = fields.Many2one('odoocms.fee.barcode','Challan')
    payment_id = fields.Many2one('odoocms.fee.payment','Payment')

    error = fields.Char('Error')
    to_be = fields.Boolean()

    def process(self, limit=10):
        for rec in self.search([('to_be','=',True)], limit=limit):
            student_id = rec.student_id
            _logger.warning("AARSOL FEE: Processing id %s" % (rec.id,))

            if not rec.invoice_id:
                lines = []
                if rec.admission_fee > 0:
                    fee_head_id = self.env['odoocms.fee.head'].browse(102)
                    fee_line = {
                        'sequence': 10,
                        'quantity': 1,
                        'price_unit': rec.admission_fee,
                        'product_id': fee_head_id.product_id.id,
                        'name': fee_head_id.product_id.name,
                        'account_id': fee_head_id.property_account_income_id.id,
                        'fee_head_id': fee_head_id.id,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append((0, 0, fee_line))
                if rec.tuition_fee > 0:
                    fee_head_id = self.env['odoocms.fee.head'].browse(101)
                    fee_line = {
                        'sequence': 20,
                        'quantity': 1,
                        'price_unit': rec.tuition_fee,
                        'product_id': fee_head_id.product_id.id,
                        'name': fee_head_id.product_id.name,
                        'account_id': fee_head_id.property_account_income_id.id,
                        'fee_head_id': fee_head_id.id,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append((0, 0, fee_line))

                validity_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.challan_validity_days') or '30')
                validity_date = rec.due_date + datetime.timedelta(days=validity_days)
                challan_type = 'main_challan'

                data = {
                    'move_type': 'out_invoice',
                    'student_id': student_id.id,
                    'partner_id': student_id.partner_id.id,
                    'journal_id': 48,
                    'term_id': rec.term_id and rec.term_id.id or False,
                    'invoice_date': rec.issue_date,
                    'invoice_date_due': rec.due_date,
                    'payment_date': rec.paid_date,
                    'invoice_line_ids': lines,
                    'is_fee': True,
                    'state': 'draft',

                    'receipt_type_ids': [(4, rec.receipt_type.id, None)],
                    'waiver_percentage': rec.discount,
                    'validity_date': validity_date,
                    'challan_type': challan_type,
                    'invoice_payment_term_id': rec.payment_term_id and rec.payment_term_id.id or 12,
                }

                invoice_id = self.env['account.move'].with_context(challan_no=rec.challan_no).create(data)
                invoice_id.action_post()
                rec.invoice_id = invoice_id.id
            else:
                invoice_id = rec.invoice_id

            challan_id = self.env['odoocms.fee.barcode'].search([('name', '=', rec.challan_no)])

            if rec.paid:
                order_data = {
                    'date_payment': rec.paid_date,
                    'state': 'paid',
                    # 'bank_ref': '123456'
                }
                payment_obj = self.env['odoocms.fee.payment'].sudo()
                payment_rec = payment_obj.fee_payment_record(rec.paid_date, rec.challan_no, rec.admission_fee+rec.tuition_fee, rec.journal_id, challan_id=challan_id)
                payment_rec.sudo().action_post_fee_payment()

                order_data['payment_id'] = payment_rec.id
                challan_id.sudo().write(order_data)

                rec.write({
                    'challan_id': challan_id.id,
                    'payment_id': payment_rec.id,
                    'to_be': False
                })
            else:
                rec.write({
                    'challan_id': challan_id.id,
                    'to_be': False
                })



