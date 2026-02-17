# -*- coding: utf-8 -*-
import pdb
import decimal
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

import logging

_logger = logging.getLogger(__name__)


def roundhalfdown(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_DOWN
    return float(round(decimal.Decimal(str(n)), decimals))


class OdooCMSDepartment(models.Model):
    _inherit = 'odoocms.department'

    integration_code = fields.Char('Integration Code', tracking=True, help="Dynamics Integration Code")


class OdooCMSProgram(models.Model):
    _inherit = "odoocms.program"

    integration_code = fields.Char('Integration Code', tracking=True, help="Dynamics Integration Code")


class OdooCMSInstitute(models.Model):
    _inherit = 'odoocms.institute'

    integration_code = fields.Char('Integration Code', tracking=True, help="Dynamics Integration Code")
    customer_code = fields.Char('Customer Code', tracking=True, help="Dynamics Integration Customer Code")


class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'

    integration_code = fields.Char('Integration Code', tracking=True, help="Dynamics Integration Code")
    ax_billing_cycle = fields.Char('AX Billing Cycle', tracking=True)
    ax_sem_code = fields.Char('AX SEM Code', tracking=True)
    ax_session_code = fields.Char('AX Session Code', tracking=True)
    ax_academic_year = fields.Char('Academic Year', tracking=True)


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_account_code = fields.Char('Bank Account Code')
    bank_ledger_code = fields.Char('Bank Ledger Code')


class AccountMove(models.Model):
    _inherit = 'account.move'
    _rec_name = "old_challan_no"

    old_challan_no = fields.Char('Challan No')
    installment_no = fields.Char('Installment No')
    transaction_id = fields.Char('Transaction ID')
    online_vendor = fields.Char('Online Vendor')
    old_challan_type = fields.Char('Challan Old Type')
    expiry_date = fields.Date('Expiry Date')
    paid_time = fields.Char('Paid Time')
    payment_mode = fields.Selection([('bank', 'Bank'),('manual', 'Manual Payment'),('cash', 'Cash')], string='Payment Mode')

    show_challan_on_portal = fields.Boolean('Show Challan on Portal', default=False, tracking=True)

    # These Variables Handle the Challan Amounts
    # Farooq - changed , may be recomputed by a cron
    admission_fee = fields.Float('Admission Fee') # , compute="_compute_fee_detail", store=True
    tuition_fee = fields.Float('Tuition Fee') # , compute="_compute_fee_detail", store=True

    hostel_fee = fields.Float('Hostel Fee') # , compute="_compute_fee_detail", store=True
    misc_fee = fields.Float('Misc Fee') # , compute="_compute_fee_detail", store=True
    fine_amount = fields.Float('Fine Amount') # , compute="_compute_fee_detail", store=True
    tax_amount = fields.Float('Tax Amount') # , compute="_compute_fee_detail", store=True

    sync_pool_entry_id = fields.Many2one('odoocms.fee.sync.pool', 'Sync Pool Ref')
    prev_challan_no = fields.Char('Prev Challan No', tracking=True)

    # Re-define this field for compute
    waiver_amount = fields.Float('Waiver Amount', compute='_compute_waiver_amount', store=True)
    misc_charges_type = fields.Many2one('odoocms.fee.additional.charges.type', 'Misc Charges Type')

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

    def create_challan_sync_pool(self, invoice):
        # invoice = rec
        if invoice:
            invoice = self.env['account.move'].browse(invoice)
            _logger.info('.......Fee Challan #%r with DB ID %r is Being Processed . ..............', invoice.old_challan_no, invoice.id)
            if invoice.amount_total > 0 and invoice.payment_state in ('paid', 'payment'):
                if invoice.payment_state == 'not_paid':
                    raise UserError(_("Invoice %s Status Should Not be in Not Paid Status.") % invoice.old_challan_no)
                discount_types = ''
                if invoice.waiver_ids:
                    discount_types = self.get_discount_titles(invoice)

                tuition_fee = invoice.tuition_fee
                # admission_fee = invoice.admission_fee
                admission_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Admission Fee')
                hostel_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Hostel Fee')
                hostel_security = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Hostel Security')

                graduation_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Graduation Fee')
                entry_test_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Entry Test Fee')
                prospectus_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Prospectus Fee')
                degree_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Degree Fee')

                fine = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Payable Fine')
                misc = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Misc Fee')

                # ***** These are not defined in the System *****#
                sports_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Sports Fee')
                library_card_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Library Card Fee')
                transport_fee = self.get_fee_head_amount(invoice=invoice, mapped_fee_head='Transport Fee')

                sync_data_dict = {
                    'student_id': invoice.student_id and invoice.student_id.id or False,
                    'invoice_id': invoice.id or False,
                    'date': fields.Date.today(),
                    'action': 'create',
                    'company_id': invoice.company_id and invoice.company_id.id or False,
                    'challan_term': invoice.term_id and invoice.term_id.id or False,
                    'tuition_fee': tuition_fee,
                    'admission_fee': admission_fee,
                    'prev_paid': invoice.back_invoice.amount_total,
                    'due_fee': invoice.semester_gross_fee,
                    'payable': invoice.amount_total,
                    'discount_types': discount_types,
                    'tuition_fee_discount': invoice.waiver_percentage,
                    'admission_fee_discount': 0,
                    'total_payable': invoice.amount_total,
                    'hostel_fee': hostel_fee,
                    'hostel_security': hostel_security,
                    'total_fine': fine,
                    'transport_fee': transport_fee,
                    'misc_fee': misc,
                    'library_card_fee': library_card_fee,
                    'graduation_fee': graduation_fee,
                    'prospectus_fee': prospectus_fee,
                    'entry_test_fee': entry_test_fee,
                    'sports_fee': sports_fee,
                    'degree_fee': degree_fee,
                }
                new_rec = self.env['odoocms.fee.sync.pool'].sudo().create(sync_data_dict)
                invoice.write({'sync_pool_entry_id': new_rec.id})

    def get_discount_titles(self, invoice=None):
        if invoice:
            return ''.join(scholarship_id.name if scholarship_id.name else '' for scholarship_id in invoice.waiver_ids)
        else:
            return ''

    def get_fee_head_amount(self, invoice=None, mapped_fee_head=''):
        amount = 0
        if mapped_fee_head:
            mapped_fee_head_id = self.env['odoocms.pgc.fee.head.mapping'].search([('name', '=', mapped_fee_head)])
            amount = sum(line.price_subtotal for line in invoice.line_ids.filtered(lambda line: line.fee_head_id.mapped_fee_head.id == mapped_fee_head_id.id and line.price_subtotal > 0)) if invoice else 0
        return amount

    @api.depends('semester_gross_fee', 'line_ids.discount')
    def _compute_waiver_amount(self):
        for rec in self:
            amt = 0
            lines = rec.line_ids.filtered(lambda a: a.discount > 0)
            for line in lines:
                amt += roundhalfdown(line.course_gross_fee * (line.discount / 100))
            rec.waiver_amount = abs(amt)

    # ***** Cron Job to Generate the Challan at the Time of Result Notify *****#
    @api.model
    def generate_challans_cron(self, reg_term, current_term, nlimit=10):
        n = 0
        registration_term_id = self.env['odoocms.academic.term'].search([('id', '=', reg_term)])  # FAll 2023
        current_term_id = self.env['odoocms.academic.term'].search([('id', '=', current_term)])  # Summer 2023

        reg_domain = [('term_id', '=', current_term_id.id), ('state', '!=', 'cancel')]
        exclude_students = self.env['odoocms.student.course'].sudo().search(reg_domain).mapped('student_id')

        domain = [('invoice_id', '=', False), ('state', '=', 'draft'), ('term_id', '=', registration_term_id.id),
                  ('student_id', 'not in', exclude_students.ids),('line_ids','<>',False)]
        # domain = [('invoice_id', '=', False), ('state', '=', 'draft'), ('term_id', '=', registration_term_id.id)]
        registration_recs = self.env['odoocms.course.registration'].search(domain, limit=nlimit)

        for registration_rec in registration_recs:
            n += 1
            _logger.info('***Record No %s Out of %s in process (%s)', n, len(registration_recs), registration_rec.id)
            registration_rec.sudo().action_submit()
            registration_rec.write({
                'enrollment_type': 'advance_enrollment',
                'generate_fee': False
            })


class OdooCMSStudentFeeLedger(models.Model):
    _inherit = 'odoocms.student.ledger'

    old_challan_no = fields.Char(related='invoice_id.old_challan_no', store=True, string='Challan No')
