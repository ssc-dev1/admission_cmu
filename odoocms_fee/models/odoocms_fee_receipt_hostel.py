import datetime
from odoo import models, fields, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
import re


def cleanhtml(raw_html):
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    return cleantext


class OdooCMSStudent(models.Model):
    _inherit = 'odoocms.student'

    def generate_hostel_invoice(self, description_sub, semester, receipts, date_due, comment='', tag=False,
                                reference=False, invoice_group=False, registration_id=False):

        fine_percent = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.second_due_date_fine') or '4')
        fine_percent = (fine_percent / 100)
        registration_id = registration_id.id
        domain = [('session_id', '=', self.session_id.id), ('term_id', '=', semester.id), ('career_id', '=', self.career_id.id)]
        fee_structure = self.env['odoocms.fee.structure'].search(domain, order='id desc', limit=1)
        if not fee_structure:
            domain = [('session_id', '=', self.session_id.id), ('career_id', '=', self.career_id.id)]
            fee_structure = self.env['odoocms.fee.structure'].search(domain, order='id desc', limit=1)
        if not fee_structure:
            raise UserError(_('Fee Structure not defined.'))

        # if not fee_structure.journal_id.sequence_id:
        #     raise UserError(_('Please define sequence on the Journal related to this Invoice.'))

        date_invoice = fields.Date.context_today(self)
        # sequence = fee_structure.journal_id.sequence_id
        # new_name = sequence.with_context(ir_sequence_date=date_invoice).next_by_id()
        lines = []
        invoices = self.env['account.move']

        if self.hostel_state == 'Allocated':
            hostel_fee_charge_months = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.hostel_fee_charge_months') or '6')
            fee_head = self.env['odoocms.fee.head'].search([('hostel_fee', '=', True)], order='id', limit=1)
            if not fee_head:
                raise UserError(_("Hostel Fee Head is not defined in the System."))
            name = self.hostel_id and self.hostel_id.name or ''

            # Check Here if structure Head Line Receipt have been Generated.
            same_term_invoice = self.env['account.move'].search([('student_id', '=', self.id),
                                                                 ('term_id', '=', semester.id),
                                                                 ('move_type', '=', 'out_invoice'),
                                                                 ('reversed_entry_id', '=', False),
                                                                 ], order='id desc', limit=1)
            same_term_invoice_reverse_entry = self.env['account.move'].search([('student_id', '=', self.id),
                                                                               ('reversed_entry_id', '=', same_term_invoice.id),
                                                                               ])
            sm_mvl = False
            if same_term_invoice:
                if not same_term_invoice_reverse_entry:
                    sm_mvl = self.env['account.move.line'].search([('move_id', '=', same_term_invoice.id), ('fee_head_id', '=', fee_head.id)])

            if not sm_mvl:
                price = 0
                price_unit = 0
                if self.tag_ids:
                    is_nfs_student = self.tag_ids.filtered(lambda t: t.code == 'NFS')
                    if is_nfs_student:
                        price = self.room_id.per_month_rent_int
                        price = self.room_id.room_type.currency_id._convert(price, self.env.company.currency_id, self.env.company, fields.Date.today())
                        price_unit = round(price * hostel_fee_charge_months, 2)
                    else:
                        price = self.room_id.per_month_rent
                        price_unit = round(price * hostel_fee_charge_months, 2)

                hostel_fee_line = {
                    'sequence': 10,
                    'price_unit': price_unit,
                    'quantity': 1,
                    'product_id': fee_head.product_id.id,
                    'name': name + " Fee",
                    'account_id': fee_head.property_account_income_id.id,
                    'fee_head_id': fee_head.id,
                    'exclude_from_invoice_tab': False,
                }
                lines.append([0, 0, hostel_fee_line])
        else:
            return False, 'Hostel is not Allocated to Student'

        # Tax Calc
        # if Not NUST Foreign Student (Do not Apply the Tax on Foreign Student)
        # To skip the tax calculation, (block_tax)
        block_tax = False
        if block_tax and not self.tag_ids.filtered(lambda t: t.code == 'NFS'):
            if lines:
                tax_rate = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.tax_rate') or '5')
                taxable_amount = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.taxable_amount') or '200000')
                taxable_fee_heads = self.env['odoocms.fee.head'].search([('taxable', '=', True)])

                previous_term_taxable_amt = 0
                current_term_taxable_amt = 0
                net_amount = 0
                tax_amount = 0
                prev_tax_amount = 0
                net_tax_amount = 0

                receipt_ids = self.env['account.move'].search([('student_id', '=', self.id),
                                                               ('term_id', '=', semester.id),
                                                               ('is_hostel_fee', '=', False),
                                                               ('is_scholarship_fee', '=', False),
                                                               ('move_type', '=', 'out_invoice'),
                                                               ('reversed_entry_id', '=', False)])
                if receipt_ids:
                    # fall20_fee_recs = self.env['nust.student.fall20.fee'].search([('student_id', '=', self.id)])
                    # if fall20_fee_recs:
                    #     for fall20_fee_rec in fall20_fee_recs:
                    #         previous_term_taxable_amt += fall20_fee_rec.amount
                    for receipt_id in receipt_ids:
                        for receipt_line in receipt_id.invoice_line_ids:
                            if receipt_line.price_unit < 0:
                                current_term_taxable_amt += receipt_line.price_unit
                            else:
                                if receipt_line.fee_head_id.id in taxable_fee_heads.ids:
                                    current_term_taxable_amt += receipt_line.price_unit

                net_amount = previous_term_taxable_amt + current_term_taxable_amt + price_unit

                if net_amount > taxable_amount:
                    tax_amount = round(net_amount * (tax_rate / 100), 3)

                fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Advance Tax')])
                if not fee_head:
                    raise UserError(_("Advance Tax Fee Head is not defined in the System."))

                for receipt_id in receipt_ids:
                    prev_tax_rec = self.env['account.move.line'].search([('move_id', '=', receipt_id.id),
                                                                         ('fee_head_id', '=', fee_head.id)])
                    if prev_tax_rec:
                        prev_tax_amount = prev_tax_rec.price_subtotal

                net_tax_amount = tax_amount - prev_tax_amount

                if net_tax_amount > 0:
                    tax_line = {
                        'sequence': 900,
                        'price_unit': net_tax_amount,
                        'quantity': 1,
                        'product_id': fee_head.product_id.id,
                        'name': "Tax Charged on Fee",
                        'account_id': fee_head.property_account_income_id.id,
                        # analytic_account_id': line.fee_head_id.analytic_account_id,
                        # 'analytic_tag_ids': analytic_tag_ids,
                        'fee_head_id': fee_head.id,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append([0, 0, tax_line])

        # Fine for Late Payment
        # if lines:
        #     lines = self.create_fine_line(lines)

        # Previous Arrears
        if lines:
            hostel_arrears_amount = 0
            unpaid_hostel_receipts = self.env['account.move'].search([('student_id', '=', self.id),
                                                                      ('is_hostel_fee', '=', True),
                                                                      ('payment_state', '=', 'not_paid')])
            if unpaid_hostel_receipts:
                for unpaid_hostel_receipt in unpaid_hostel_receipts:
                    hostel_arrears_amount += unpaid_hostel_receipt.amount_residual
                    unpaid_hostel_receipt.mapped('line_ids').remove_move_reconcile()
                    unpaid_hostel_receipt.write({'state': 'cancel', 'cancel_due_to_arrears': True})

                arrears_fee_head = self.env['odoocms.fee.head'].search([('category_id.name', '=', 'Arrears')], order='id', limit=1)
                hostel_arrears_amount = hostel_arrears_amount + (hostel_arrears_amount * fine_percent)
                arrears_line = {
                    'sequence': 1000,
                    'price_unit': round(hostel_arrears_amount),
                    'quantity': 1,
                    'product_id': arrears_fee_head.product_id and arrears_fee_head.product_id.id or False,
                    'name': arrears_fee_head.product_id and arrears_fee_head.product_id.name or 'Previous Arrears ',
                    'account_id': arrears_fee_head.property_account_income_id.id,
                    # 'analytic_tag_ids': analytic_tag_ids,
                    'fee_head_id': arrears_fee_head and arrears_fee_head.id or False,
                    'exclude_from_invoice_tab': False,
                }
                lines.append((0, 0, arrears_line))

        if receipts and any([ln[2]['price_unit'] > 0 for ln in lines]):
            validity_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.challan_validity_days') or '30')
            validity_date = date_due + datetime.timedelta(days=validity_days)

            data = {
                'student_id': self.id,
                'partner_id': self.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'registration_id': registration_id,
                'journal_id': fee_structure.journal_id.id,
                # 'name': new_name,
                'invoice_date': date_invoice,
                'invoice_date_due': date_due,
                'state': 'draft',
                'narration': cleanhtml(comment),
                'tag': tag,
                'is_fee': True,
                'is_cms': True,
                'is_hostel_fee': True,
                'reference': reference,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'waiver_amount': 0,
                'term_id': semester and semester.id or False,
                'study_scheme_id': self.study_scheme_id and self.study_scheme_id.id or False,
                'validity_date': validity_date,
            }
            invoice = self.env['account.move'].create(data)
            invoices += invoice
            invoice.invoice_group_id = invoice_group

            ledger_amt = invoice.amount_total
        return True, invoices

    def generate_ad_hoc_charges_invoice(self, description_sub, semester, receipts, date_due, comment='', tag=False,
                                        reference=False, invoice_group=False, registration_id=False):
        registration_id = registration_id.id
        fee_structure = self.env['odoocms.fee.structure'].search([('session_id', '=', self.session_id.id),
                                                                  ('term_id', '=', semester.id),
                                                                  ('career_id', '=', self.career_id.id)
                                                                  ], order='id desc', limit=1)
        # if not fee_structure.journal_id.sequence_id:
        #     raise UserError(_('Please define sequence on the Journal related to this Invoice.'))
        date_invoice = fields.Date.context_today(self)
        # sequence = fee_structure.journal_id.sequence_id
        # new_name = sequence.with_context(ir_sequence_date=date_invoice).next_by_id()
        lines = []
        invoices = self.env['account.move']
        adm_charges_recs = False
        ledger_desc = 'Ad Hoc Charges Against '
        adm_charges_recs = self.env['odoocms.fee.additional.charges'].search([('student_id', '=', self.id), ('term_id', '=', semester.id), ('state', '=', 'draft')])
        if adm_charges_recs:
            for adm_charges_rec in adm_charges_recs:
                adm_charges_fee_head = adm_charges_rec.charges_type.fee_head_id
                ledger_desc = ledger_desc + adm_charges_rec.charges_type.name + " "
                if not adm_charges_fee_head:
                    continue
                adm_charges_line = {
                    'sequence': 10,
                    'price_unit': adm_charges_rec.amount,
                    'quantity': 1,
                    'product_id': adm_charges_fee_head.product_id.id,
                    'name': adm_charges_rec.charges_type.name,
                    'account_id': adm_charges_fee_head.property_account_income_id.id,
                    # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                    # 'analytic_tag_ids': analytic_tag_ids,
                    'fee_head_id': adm_charges_fee_head.id,
                    'exclude_from_invoice_tab': False,
                }
                lines.append((0, 0, adm_charges_line))
                adm_charges_rec.state = 'charged'

        # Fine for Late Payment
        if lines:
            lines = self.create_fine_line(lines)

        if receipts and any([ln[2]['price_unit'] > 0 for ln in lines]):
            validity_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.challan_validity_days') or '30')
            validity_date = date_due + datetime.timedelta(days=validity_days)

            data = {
                'student_id': self.id,
                'partner_id': self.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'registration_id': registration_id,
                'journal_id': fee_structure.journal_id.id,
                # 'name': new_name,
                'invoice_date': date_invoice,
                'invoice_date_due': date_due,
                'state': 'draft',
                'narration': cleanhtml(comment),
                'tag': tag,
                'is_fee': True,
                'is_cms': True,
                'is_hostel_fee': False,
                'reference': reference,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'waiver_amount': 0,
                'term_id': semester and semester.id or False,
                'study_scheme_id': self.study_scheme_id and self.study_scheme_id.id or False,
                'validity_date': validity_date,
            }
            invoice = self.env['account.move'].create(data)
            invoices += invoice
            invoice.invoice_group_id = invoice_group

        return invoices
