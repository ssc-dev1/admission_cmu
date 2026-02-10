# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import api, fields, models, tools, _

import logging

_logger = logging.getLogger(__name__)


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
    to_be = fields.Boolean('To Be')


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    bank_account_code = fields.Char('Bank Account Code')
    bank_ledger_code = fields.Char('Bank Ledger Code')


class OdoocmsPGCFeeHeadMapping(models.Model):
    _name = 'odoocms.pgc.fee.head.mapping'
    _description = "PGC Fee Head Mapping"

    name = fields.Char('Fee Head')


class OdoocmsFeeHead(models.Model):
    _inherit = 'odoocms.fee.head'

    mapped_fee_head = fields.Many2one('odoocms.pgc.fee.head.mapping', 'Mapped Fee Head')


class ResCompany(models.Model):
    _inherit = 'res.company'

    code = fields.Char('Code')
    business_unit = fields.Char('Business Unit')
    integration_bank = fields.Char('Integration Bank')


class AccountMove(models.Model):
    _inherit = 'account.move'

    sync_pool_entry = fields.Many2one('odoocms.fee.sync.pool', 'Sync Pool Ref')

    def create_challan_sync_pool(self, invoice):
        # invoice = rec
        if invoice:
            invoice = self.env['account.move'].browse(invoice)
            _logger.info('.......Fee Challan #%r with DB ID %r is Being Processed . ..............', invoice.old_challan_no, invoice.id)
            if invoice.amount_total > 0 and invoice.payment_state in ('paid', 'payment'):
                if invoice.payment_state == 'not_paid':
                    raise UserError(_("Invoice %s Status Should Not be in Verify or Issue to Student.") % invoice.old_challan_no)
                discount_types = ''
                if invoice.waiver_ids:
                    discount_types = self.get_discount_titles(invoice)

                tuition_fee = invoice.tuition_fee
                # admission_fee = invoice.admission_fee
                admission_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Admission Fee')
                hostel_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Hostel Fee')
                hostel_security = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Hostel Security')

                graduation_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Graduation Fee')
                entry_test_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Entry Test Fee')
                prospectus_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Prospectus Fee')
                degree_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Degree Fee')

                fine = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Payable Fine')
                misc = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Misc Fee')

                # ***** These are not defined in the System *****#
                sports_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Sports Fee')
                library_card_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Library Card Fee')
                transport_fee = self.get_fee_head_amount_conn(invoice=invoice, mapped_fee_head='Transport Fee')

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
                    'graduation_fee': 0,
                    'prospectus_fee': prospectus_fee,
                    'entry_test_fee': entry_test_fee,
                    'sports_fee': sports_fee,
                    'degree_fee': degree_fee,
                }
                new_rec = self.env['odoocms.fee.sync.pool'].sudo().create(sync_data_dict)
                invoice.write({'sync_pool_entry': new_rec.id})

    def get_discount_titles(self, invoice=None):
        if invoice:
            return ''.join(scholarship_id.name if scholarship_id.name else '' for scholarship_id in invoice.waiver_ids)
        else:
            return ''

    def get_fee_head_amount_conn(self, invoice=None, mapped_fee_head=''):
        amount = 0
        if mapped_fee_head:
            mapped_fee_head_id = self.env['odoocms.pgc.fee.head.mapping'].search([('name', '=', mapped_fee_head)])
            amount = sum(line.price_subtotal for line in invoice.line_ids.filtered(lambda line: line.fee_head_id.mapped_fee_head.id == mapped_fee_head_id.id and line.price_subtotal > 0)) if invoice else 0
        return amount
