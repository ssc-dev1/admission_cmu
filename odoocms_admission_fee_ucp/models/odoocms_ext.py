# -*- coding: utf-8 -*-
import pdb

from odoo import api, fields, models, tools, _
from datetime import datetime, date


class AccountMove(models.Model):
    _inherit = 'account.move'
    _rec_name = "old_challan_no"

    old_challan_no = fields.Char('Challan No', tracking=True, index=True, copy=False)
    installment_no = fields.Char('Installment No')
    transaction_id = fields.Char('Transaction ID')
    online_vendor = fields.Char('Online Vendor')
    expiry_date = fields.Date('Expiry Date')
    paid_time = fields.Char('Paid Time')
    paid_bank_name = fields.Char('Paid Bank Name')
    show_challan_on_portal = fields.Boolean('Show Challan on Portal', default=False, tracking=True)

    # These Variables Handle the Challan Amounts
    admission_fee = fields.Float('Admission Fee', compute="_compute_fee_detail", store=True)
    tuition_fee = fields.Float('Tuition Fee', compute="_compute_fee_detail", store=True)
    misc_fee = fields.Float('Misc Fee', compute="_compute_fee_detail", store=True)
    hostel_fee = fields.Float('Hostel Fee', compute="_compute_fee_detail", store=True)
    fine_amount = fields.Float('Fine Amount', compute="_compute_fee_detail", store=True)
    tax_amount = fields.Float('Tax Amount', compute="_compute_fee_detail", store=True)
    prev_challan_no = fields.Char('Prev Challan No', tracking=True)

    @api.model
    def create(self, values):
        invoice = super(AccountMove, self).create(values)
        find_show_on_portal_rec = self.env['odoocms.show.challan.on.portal.line'].search([
            ('term_id', '=', invoice.term_id.id),
            ('faculty_id', '=', invoice.student_id.institute_id.id),
            ('program_id', '=', invoice.student_id.program_id.id),
            ('type', '=', invoice.challan_type),
            ('state', '=', 'confirm')])
        if find_show_on_portal_rec:
            invoice.write({'show_challan_on_portal': True})
        return invoice

    @api.depends('name')
    def compute_barcode(self):
        for rec in self:
            if rec.name and not rec.name == '/':    # and not rec.barcode
                # rec.barcode = self.env['ir.sequence'].with_context({'company_id': rec.company_id.id}).next_by_code('odoocms.fee.receipt.barcode.sequence')
                if not rec.old_challan_no and rec.challan_type == 'prospectus_challan':
                    rec.old_challan_no = self.env['ir.sequence'].with_context({'company_id': rec.company_id.id}).next_by_code('odoocms.processing.fee.challan.sequence')

    def get_fee_head_amount(self, invoice=None, fee_head=''):
        if fee_head == "Fine":
            amount = sum(line.price_subtotal for line in invoice.line_ids.filtered(lambda line: line.fee_category_id.name == 'Fine' and line.price_subtotal > 0)) if invoice else 0
        elif fee_head == "Hostel Fee":
            amount = sum(line.price_subtotal for line in invoice.line_ids.filtered(lambda line: line.fee_head_id.name in ("Hostel Fee (Monthy)", "Hostel Fee (Semester)") and line.price_subtotal > 0)) if invoice else 0
        else:
            amount = sum(line.price_subtotal for line in invoice.line_ids.filtered(lambda line: line.fee_head_id.name == fee_head and line.price_subtotal > 0)) if invoice else 0
        return amount

    @api.depends('line_ids', 'line_ids.price_total', 'line_ids.fee_head_id')
    def _compute_fee_detail(self):
        for rec in self:
            fees = {
                'Admission Fee': 'admission_fee',
                'Tuition Fee': 'tuition_fee',
                'Misc Fee': 'misc_fee',
                'Hostel Fee': 'hostel_fee',
                'Fine': 'fine_amount',
                'Tax': 'tax_amount',
            }
            fee_totals = {field: 0 for field in fees.values()}
            for fee_category, field in fees.items():
                fee_lines = rec.invoice_line_ids.filtered(lambda line: line.fee_category_id.name == fee_category)
                fee_totals[field] = sum(fee_lines.mapped('price_total'))
            rec.sudo().write(fee_totals)

    def action_prod_invoice_inquiry(self, param_dict=None):
        if param_dict is not None:
            invoice = self.env['account.move'].sudo().search([('old_challan_no', '=', param_dict['old_challan_no'])])
            if invoice:
                inv_date = invoice.invoice_date_due or date.today()
                # ***** INACTIVE ACCOUNT *****#
                # id->9---Description->INACTIVE_ACCOUNT---Long Description->Inactive Account Status
                if invoice.expiry_date and date.today() > invoice.expiry_date:
                    data = {
                        'ReturnValue': '9',
                    }
                    return data

                # ***** Paid Challan *****#
                if invoice.payment_state in ('in_payment', 'paid'):
                    data = {
                        'ReturnValue': '4',
                    }
                    return data

                data = {
                    'p_StudentName': invoice.application_id.name,
                    'p_Amount': int(invoice.amount_total),
                    'p_BillingMonth': invoice.invoice_date.strftime("%Y-%m"),
                    'p_DueDate': inv_date.strftime("%Y-%m-%d"),
                    'p_ReferenceNo': invoice.application_no.code,
                    'p_CompanyName': invoice.company_id.name,
                    'p_CampusName': invoice.program_id.institute_id.name,
                    'p_CustomerCode': '',  # invoice.program_id and invoice.student_id.program_id.institute_id.customer_code or ''
                    'p_ChallanNumber': invoice.old_challan_no,
                    'ReturnValue': '0',
                }
                return data
            else:
                # ***** INCORRECT_CHALLAN_NO *****#
                data = {
                    'ReturnValue': '3',
                }
                return data

        else:
            # Invalid User + Password
            data = {
                'ReturnValue': '2',
            }
            return data

    def get_paid_bank_name(self):
        payments = self.env['odoocms.fee.payment'].search([('invoice_id', '=', self.id)])
        if payments:
            return payments[0].journal_id.name.title()
        if self.application_id.fee_voucher_verify_source:
            return self.application_id.fee_voucher_verify_source
        if not self.application_id.create_uid.login == 'public':
            return 'Admission Department'


class OdooCMSStudentFeeLedger(models.Model):
    _inherit = 'odoocms.student.ledger'

    old_challan_no = fields.Char(related='invoice_id.old_challan_no', store=True, string='Challan No')


class ResUsers(models.Model):
    _inherit = 'res.users'

    department_id_new = fields.Many2one('hr.department', 'New Department')
