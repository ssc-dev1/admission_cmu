# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import decimal
import logging

_logger = logging.getLogger(__name__)


def roundhalfup(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_UP
    return float(round(decimal.Decimal(str(n)), decimals))


class OdooCMSFeePaymentRegister(models.Model):
    _name = 'odoocms.fee.payment.register'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Payment Register, Combine multiple fee payment receipts'
    _order = 'date desc, id desc'

    name = fields.Char('Name', tracking=True)
    sequence = fields.Char('Sequence')
    date = fields.Date('Date', default=fields.Date.today(), tracking=True)

    state = fields.Selection([('Draft', 'Draft'),('Posted', 'Posted'),('Cancel', 'Cancel')], string='Status', default='Draft')

    barcode = fields.Char('Barcode')

    fee_payment_ids = fields.One2many('odoocms.fee.payment', 'payment_register_id', 'Fee Payments')
    non_barcode_ids = fields.One2many('odoocms.fee.non.barcode.receipts', 'payment_register_id', 'Non Barcode Ref')
    fee_processed_ids = fields.One2many('odoocms.fee.processed.receipts', 'payment_register_id', 'Processed Receipts')
    payment_mismatch_ids = fields.One2many('odoocms.fee.payments.amount.mismatch', 'payment_register_id', 'Amount Mismatch Detail')
    total_amount_mismatch_receipts = fields.Float('Amount Mismatch Receipts', compute='compute_total_amount_mismatch_receipt', store=True, tracking=True)

    total_receipts = fields.Float('Total Receipts', compute='compute_total_receipt', store=True, tracking=True)
    non_barcode_receipts = fields.Float('Non Barcode Receipts', compute='compute_total_receipt', store=True, tracking=True)
    total_amount = fields.Float('Total Invoice Amount', compute='compute_total_amount', store=True, tracking=True)
    total_received_amount = fields.Float('Total Received Amount', compute='compute_total_amount', store=True, tracking=True)
    total_diff_amount = fields.Float('Total Diff Amount', compute='compute_total_amount', store=True, tracking=True)

    journal_id = fields.Many2one('account.journal', 'Bank Journal')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, values):
        fee_payment_days_lock = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_payment_days_lock') or '10')
        # fee_payment_days_lock = 365
        if values.get('date', False):
            dt_diff = (fields.Date.today() - fields.Date.to_date(values['date']))
            dt_diff = dt_diff.days
            if dt_diff > fee_payment_days_lock:
                raise UserError(_('You cannot enter the payment beyond the %s, Current Difference is %s') % (fee_payment_days_lock, dt_diff))
        result = super(OdooCMSFeePaymentRegister, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.payment.register')
        return result

    def write(self, values):
        if values.get('date', False):
            fee_payment_days_lock = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_payment_days_lock') or '10')
            # fee_payment_days_lock = 365
            dt_diff = (fields.Date.today() - fields.Date.to_date(values['date']))
            dt_diff = dt_diff.days
            if dt_diff > fee_payment_days_lock:
                raise UserError(_('You cannot enter the payment beyond the %s, Current Difference is %s') % (fee_payment_days_lock, dt_diff))
            if self.fee_payment_ids:
                self.fee_payment_ids.write({'date': values['date']})
        record = super(OdooCMSFeePaymentRegister, self).write(values)
        return record

    def unlink(self):
        for rec in self:
            if rec.fee_payment_ids:
                for line in rec.fee_payment_ids:
                    line.unlink()
            deletion_values = {
                'payment_register': rec.name,
            }
            self.env['odoocms.fee.payment.register.deletion.log'].create(deletion_values)
            return super(OdooCMSFeePaymentRegister, self).unlink()

    @api.depends('fee_payment_ids', 'non_barcode_ids')
    def compute_total_receipt(self):
        for rec in self:
            rec.total_receipts = len(rec.fee_payment_ids)
            rec.non_barcode_receipts = len(rec.non_barcode_ids)

    @api.depends('fee_payment_ids', 'fee_payment_ids.amount', 'fee_payment_ids.received_amount')
    def compute_total_amount(self):
        for rec in self:
            total = 0
            received_amt = 0
            diff_amt = 0
            for payment in rec.fee_payment_ids:
                total = total + payment.amount
                received_amt = received_amt + payment.received_amount
                diff_amt = diff_amt + payment.diff_amount
            rec.total_amount = total
            rec.total_received_amount = received_amt
            rec.total_diff_amount = diff_amt

    def store_barcode(self, barcode, amount=None):  # , date_payment=False
        precision = self.env['decimal.precision'].precision_get('Payroll')
        diff = 0
        barcode_id = self.env['odoocms.fee.barcode'].search([('name', '=', barcode)])
        if barcode_id:
            if barcode_id.model == 'account.move.line':
                invoice_line_id = barcode_id.line_ids[0]
                # invoice_line_id = self.env['account.move.line'].browse(barcode_id.res_id)
                invoice_id = invoice_line_id.move_id
            elif barcode_id.model == 'account.move':
                invoice_line_id = False
                invoice_id = self.env['account.move'].browse(barcode_id.res_id)

            if amount:
                difference = barcode_id.amount_residual - amount
                if abs(difference) > 1:
                    diff = barcode_id.amount_residual - amount

            already_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', barcode)])
            if not already_exist and diff == 0:
                values = {
                    'challan_id': barcode_id.id,
                    'receipt_number': barcode,
                    'student_id': barcode_id.student_id.id,
                    'amount': amount and amount or barcode_id.amount_residual,
                    'term_id': barcode_id.term_id.id,
                    'journal_id': self.journal_id and self.journal_id.id or False,
                    'date': self.date,
                    'payment_register_id': self.id,
                    'received_amount': barcode_id.amount_residual,
                    'invoice_id': invoice_id.id,
                    'invoice_line_id': invoice_line_id.id,
                    # 'semester_id': invoice_id.semester_id and invoice_id.semester_id.id or False,
                }
                payment_rec = self.env['odoocms.fee.payment'].create(values)
                challan_data = {
                    'state': 'paid',
                    'payment_id': payment_rec.id,
                }
                barcode_id.write(challan_data)

            if not already_exist and diff != 0:
                data = {
                    'barcode': barcode,
                    'payment_register_id': self.id,
                    'invoice_amount': barcode_id.amount_residual,
                    'payment_amount': amount,
                    'invoice_id': invoice_id.id,
                    'diff_amount': diff
                }
                self.env['odoocms.fee.payments.amount.mismatch'].create(data)

            # Already Exist But Payment Register is not Set
            if already_exist and already_exist._table == 'odoocms_fee_payment' and not already_exist.payment_register_id:
                for already_exist_id in already_exist:
                    already_exist_id.payment_register_id = self._origin.id

            # Already Exit And Payment Register is also Set
            if already_exist and already_exist._table == 'odoocms_fee_payment' and already_exist.payment_register_id:
                for already_exist_id in already_exist:
                    # Create Records in the Processed Receipts
                    notes = "Already Processed in " + (already_exist_id.payment_register_id.name and already_exist_id.payment_register_id.name or '') + " on " + already_exist_id.date.strftime("%d/%m/%Y")
                    processed_values = {
                        'barcode': barcode,
                        'name': barcode,
                        'payment_register_id': self.id,
                        'notes': notes,
                    }
                    self.env['odoocms.fee.processed.receipts'].create(processed_values)

        else:
            invoice_id = self.env['account.move'].search([('barcode', '=', barcode), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
            if not invoice_id:
                invoice_id = self.env['account.move'].search([('name', '=', barcode), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
            if not invoice_id:
                invoice_id = self.env['account.move'].search([('old_challan_no', '=', barcode), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])

            already_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', barcode), ('invoice_id.amount_residual', '=', 0.0)])
            if not already_exist:
                already_exist = self.env['account.move'].search([('barcode', '=', barcode),('move_type', '=', 'out_invoice'),('amount_residual', '=', 0.0)])
            if not already_exist:
                fee_payment_rec_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', barcode)], order='id', limit=1)
                if fee_payment_rec_exist:
                    if fee_payment_rec_exist.received_amount >= fee_payment_rec_exist.amount:
                        already_exist = fee_payment_rec_exist

            if not already_exist:
                already_exist = self.env['odoocms.fee.payment'].search([('invoice_id', '=', invoice_id.id),('payment_register_id', '=', self.id),
                    ('invoice_id.amount_residual', '>', 0.0),], order='id', limit=1)

            # Create the Record in the Fee Payment Receipts
            if invoice_id and not already_exist:
                if not self.journal_id:
                    raise UserError(_('Please Enter Bank in which Payments are to be Received'))
                values = {
                    'invoice_id': invoice_id.id,
                    'receipt_number': barcode,
                    'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
                    'amount': amount or invoice_id.amount_residual,
                    'journal_id': self.journal_id and self.journal_id.id or False,
                    'date': self.date,
                    'payment_register_id': self.id,
                    'received_amount': invoice_id.amount_residual,
                }
                self.env['odoocms.fee.payment'].create(values)

            # Already Exist But Payment Register is not Set
            if already_exist and already_exist._table == 'odoocms_fee_payment' and not already_exist.payment_register_id:
                for already_exist_id in already_exist:
                    already_exist_id.payment_register_id = self._origin.id

            # Already Exit And Payment Register is also Set
            if already_exist and already_exist._table == 'odoocms_fee_payment' and already_exist.payment_register_id:
                for already_exist_id in already_exist:
                    # Create Records in the Processed Receipts
                    notes = "Already Processed in " + (already_exist_id.payment_register_id.name and already_exist_id.payment_register_id.name or '') + " on " + already_exist_id.date.strftime("%d/%m/%Y")
                    processed_values = {
                        'barcode': barcode,
                        'name': barcode,
                        'payment_register_id': self.id,
                        'notes': notes,
                    }
                    self.env['odoocms.fee.processed.receipts'].create(processed_values)

            # If invoice_id is not found then create in the Non Barcode Receipts
            if not invoice_id and not already_exist:
                non_barcode_exit = self.env['odoocms.fee.non.barcode.receipts'].search([('barcode', '=', barcode)])
                if not non_barcode_exit:
                    non_barcode_vals = {
                        'barcode': barcode,
                        'name': barcode,
                        'payment_register_id': self.id,
                    }
                    self.env['odoocms.fee.non.barcode.receipts'].create(non_barcode_vals)

    @api.onchange('barcode')
    def onchange_barcode(self):
        if self.barcode:
            if self.state == 'Draft':
                if not self.journal_id:
                    raise UserError(_('Please Enter Bank in which Payments are to be Received'))

                self.store_barcode(self.barcode)

            self.barcode = None

    def action_post(self):
        for rec in self:
            # loop_counter = 0
            for payment in rec.fee_payment_ids.filtered(lambda l: not l.payment_id):
                # loop_counter += 1

                payment.action_post_fee_payment()
                self.env.cr.commit()
                # if loop_counter == 10:
                #     self.env.cr.commit()
                #     loop_counter = 0

            if rec.non_barcode_receipts == 0 and all([line.state == 'done' for line in rec.fee_payment_ids]):
                rec.state = 'Posted'

    def action_confirm_registration(self, payment, invoice):
        fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
        fee_charge_term_rec = self.env['odoocms.academic.term'].browse(fee_charge_term)
        # *****  Registration Approval *****#
        registration_id = invoice.registration_id
        if not registration_id:
            registration_id = self.env['odoocms.course.registration'].sudo().search([('student_id', '=', invoice.student_id.id),
                                                                                     ('term_id', '=', fee_charge_term_rec.id),
                                                                                     ('state', '!=', 'approved')
                                                                                     ], order='id desc', limit=1)
        if registration_id and invoice.challan_type in ('main_challan', 'add_drop', 'admission'):
            registration_id.sudo().action_approve()

        # ***** # Prospectus Fee Handling *****#
        # if invoice.narration == 'Prospectus Fee':
        #     application_id = self.env['odoocms.application'].search([('prospectus_inv_id', '=', invoice.id)])
        #     if application_id:
        #         application_id.write({'fee_voucher_state': 'verify'})

        # ***** # Admission Fee Handling *****#
        # if invoice.is_admission_fee:
        #     student = invoice.application_id.sudo().create_student()
        #     if student:
        #         payment.write({'student_id': student.id})
        #         if not invoice.student_id:
        #             invoice.write({'student_id': student.id, })
        #         if invoice.batch_id:
        #             reg_no = invoice.batch_id.program_id.campus_id.code + invoice.batch_id.session_id.code + invoice.batch_id.program_id.code + self.env['ir.sequence'].next_by_code('student.reg.no.seq')
        #             student.write({'code': reg_no,
        #                            'id_number': reg_no
        #                            })
        #         invoice.application_id.sudo().new_student_registration()
        #         payment_ledger_recs = self.env['odoocms.student.ledger'].search([('invoice_id', '=', invoice.id),
        #                                                                          ('debit', '>', 0)
        #                                                                          ])
        #         if payment_ledger_recs:
        #             payment_ledger_recs.write({
        #                 'student_id': student.id,
        #                 'id_number': student.code
        #             })
        #         invoice.application_id.admission_link_invoice_to_student()

        # ***** Reinstate with Drap Courses@06-06-2023 *****#
        # ***** # Handling Withdrawn Courses, Search Out Withdraw Courses *****#
        if invoice.challan_type in ('2nd_challan', 'installment'):
            reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
            if reason_id:
                withdraw_courses = payment.student_id.course_ids.filtered(lambda a: a.state == "withdraw" and a.withdraw_reason == reason_id)
                if withdraw_courses:
                    withdraw_courses.write({'state': 'current',
                                            'withdraw_date': False,
                                            'withdraw_reason': False,
                                            'grade': False,
                                            })
        # added@11042023
        invoice.write({
            'confirmation_date': fields.Date.today(),
        })

    @api.depends('payment_mismatch_ids')
    def compute_total_amount_mismatch_receipt(self):
        for rec in self:
            rec.total_amount_mismatch_receipts = rec.total_amount_mismatch_receipts and len(rec.total_amount_mismatch_receipts.ids) or 0.0

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Fee Import From Fee Register'),
            'template': '/odoocms_fee/static/xls/fee_payment_register.xlsx'
        }]

    def action_cancel(self):
        for rec in self:
            rec.state = 'Cancel'


class OdooCMSFeePayment(models.Model):
    _name = 'odoocms.fee.payment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Payment'

    payment_register_id = fields.Many2one('odoocms.fee.payment.register', 'Payment Register', tracking=True, index=True, auto_join=True, ondelete='cascade')
    name = fields.Char()
    sequence = fields.Integer('Sequence')
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today())
    description = fields.Char('Description', readonly=True, states={'draft': [('readonly', False)]})
    amount = fields.Float('Amount', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=0)
    receipt_number = fields.Char('Receipt No', required=True, readonly=True, states={'draft': [('readonly', False)]})
    journal_id = fields.Many2one('account.journal', 'Journal', related='payment_register_id.journal_id', store=True)
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('done', 'Posted'),
            ('error', 'Error')
        ], 'Status', default='draft', readonly=True, states={'draft': [('readonly', False)]})

    transaction_date = fields.Date('Transaction Date', default=fields.Date.today(), required=True)
    post_date = fields.Date('Post Date')
    student_ledger_id = fields.Many2one('odoocms.student.ledger', 'Student Ledger')
    student_id = fields.Many2one('odoocms.student', 'Student')

    tag = fields.Char('Batch-ID/Tag', help='Attach the tag', readonly=True)

    received_amount = fields.Float('Received Amount')
    diff_amount = fields.Float('Diff Amount', compute='compute_diff_amt', store=True)

    payment_id = fields.Many2one('account.payment', 'Account Payment')
    invoice_id = fields.Many2one('account.move', 'Student Invoice')
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line')
    invoice_status = fields.Selection(related='invoice_id.payment_state', string='Invoice Status', store=True)

    challan_id = fields.Many2one('odoocms.fee.barcode', 'Challan')
    challan_status = fields.Selection(related='challan_id.state', string='Challan Status', store=True)

    processed = fields.Boolean('Processed', default=False)
    company_id = fields.Many2one('res.company', string='Company', related='payment_register_id.company_id', store=True)

    career_id = fields.Many2one('odoocms.career', 'Career')
    program_id = fields.Many2one('odoocms.program', 'Program')
    institute_id = fields.Many2one('odoocms.institute', 'Institute')
    discipline_id = fields.Many2one('odoocms.discipline', 'Discipline')
    campus_id = fields.Many2one('odoocms.campus', 'Campus')
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    session_id = fields.Many2one('odoocms.academic.session', 'Session')
    semester_id = fields.Many2one('odoocms.semester', 'Semester')
    to_be = fields.Boolean('To Be', default=False)
    ext_a = fields.Integer()
    ext_b = fields.Integer()

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Student Fee Payments'),
            'template': '/odoocms_fee/static/xls/fee_collection.xlsx'
        }]

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError('You Cannot delete this Record, The payment have been Posted.')
            rec.action_create_payment_deletion_log()
            return super(OdooCMSFeePayment, self).unlink()

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.depends('amount', 'received_amount')
    def compute_diff_amt(self):
        for rec in self:
            rec.diff_amount = int(roundhalfup(rec.amount)) - rec.received_amount

    # Called from Services
    def fee_payment_record(self, date, consumer_no, amount, journal_id, invoice_id=False, challan_id=False):
        # ***** Check if Any Previous Entry Not Post then Please Post it *****#
        # Why Here
        prev_date_draft_payment_registers = self.env['odoocms.fee.payment.register'].sudo().search([('journal_id', '=', journal_id.id),
                                                                                                    ('state', '=', 'Draft'), ('date', '<', fields.Date.today())])
        if prev_date_draft_payment_registers:
            for prev_date_draft_payment_register in prev_date_draft_payment_registers:
                if all([line.state == 'done' for line in prev_date_draft_payment_register.fee_payment_ids]):
                    prev_date_draft_payment_register.state = 'Posted'

        # ***** Payment Register *****#
        payment_register_id = self.env['odoocms.fee.payment.register'].search([('date', '=', date), ('journal_id', '=', journal_id.id), ('state', '=', 'Draft')])
        if not payment_register_id:
            register_values = {
                'date': date,
                'journal_id': journal_id and journal_id.id or False,
                'company_id': journal_id.company_id.id,
            }
            payment_register_id = self.env['odoocms.fee.payment.register'].sudo().create(register_values)

        # ****** Create the Record in the Fee Payment Receipts *****#
        if invoice_id:
            values = {
                'invoice_id': invoice_id.id,
                'receipt_number': consumer_no,
                'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
                'amount': invoice_id.amount_residual,
                'term_id': invoice_id.term_id and invoice_id.term_id.id or False,
                'journal_id': journal_id and journal_id.id or False,
                'date': date,
                'received_amount': invoice_id.amount_residual,
                'payment_register_id': payment_register_id and payment_register_id.id or False,
            }
        elif challan_id:
            values = {
                'challan_id': challan_id.id,
                'receipt_number': consumer_no,
                'student_id': challan_id.student_id and challan_id.student_id.id or False,
                'amount': challan_id.amount,
                'term_id': challan_id.term_id and challan_id.term_id.id or False,
                'journal_id': journal_id and journal_id.id or False,
                'date': date,
                'received_amount': amount,
                'payment_register_id': payment_register_id and payment_register_id.id or False,
            }
        new_rec = self.env['odoocms.fee.payment'].create(values)
        return new_rec

    def late_fee_invoice(self):
        for rec in self:
            challan = rec.challan_id
            lines = []
            fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Late Fee Fine'),'|',('company_id','=',challan.company_id.id),('company_id','=',False)])
            latefee_line = {
                'sequence': 300,
                'price_unit': challan.late_fine,
                'quantity': 1.00,
                'product_id': fee_head.product_id and fee_head.product_id.id or False,
                'name': fee_head.name,
                'account_id': fee_head.property_account_income_id and fee_head.property_account_income_id.id or False,
                'fee_head_id': fee_head and fee_head.id or False,
                'exclude_from_invoice_tab': False,
                'course_gross_fee': challan.late_fine,
            }
            lines.append([0, 0, latefee_line])

            # Create Late Fee Invoice
            fee_structure = rec.student_id.batch_id.fee_structure_id
            if not fee_structure:
                structure_domain = [
                    ('session_id', '=', rec.student_id.session_id.id),
                    ('batch_id', '=', rec.student_id.batch_id.id),
                    ('career_id', '=', rec.student_id.career_id.id)]
                fee_structure = self.env['odoocms.fee.structure'].search(structure_domain, order='id desc', limit=1)
            if not fee_structure:
                raise UserError(_('No Fee Structure Found For Batch-%s') % rec.student_id.batch_id.name)

            receipts = self.env['odoocms.receipt.type'].search([('code', '=', 'LF'),'|',('company_id','=',challan.company_id.id),('company_id','=',False)], order='id desc', limit=1)
            if not receipts:
                receipts = self.env['odoocms.receipt.type'].search([('code', '=', 'MiSC'),'|',('company_id','=',challan.company_id.id),('company_id','=',False)], order='id desc', limit=1)

            data = {
                'student_id': rec.student_id.id,
                'partner_id': rec.student_id.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'is_fee': True,
                'is_cms': True,
                'is_late_fee': True,
                'move_type': 'out_invoice',
                'invoice_line_ids': lines,
                'journal_id': fee_structure.journal_id.id,
                'invoice_date': rec.date,
                'invoice_date_due': rec.date,
                'state': 'draft',
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'term_id': challan.term_id and challan.term_id.id or False,
            }
            latefee_invoice = self.env['account.move'].create(data)

            receivable_lines = latefee_invoice.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            for receivable_line in receivable_lines.sorted(key=lambda a: a.date_maturity, reverse=False):
                if not receivable_line.challan_id:
                    receivable_line.write({
                        'challan_id': challan.id,
                    })
            challan.late_fine = 0
            latefee_invoice.action_post()

    def full_payment_discount_credit(self):
        for rec in self:
            challan = rec.challan_id
            lines = []
            payment_discount_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.payment_discount_head', 'Payment Discount')
            fee_head = self.env['odoocms.fee.head'].search([('name', '=', payment_discount_head),'|',('company_id','=',challan.company_id.id),('company_id','=',False)])
            company = challan.company_id
            account_id = fee_head.product_id.with_company(company).property_account_income_id

            discount_line = {
                'sequence': 350,
                'price_unit': challan.discount,
                'quantity': 1.00,
                'product_id': fee_head.product_id and fee_head.product_id.id or False,
                'name': fee_head.name,
                'account_id': account_id.id,
                'fee_head_id': fee_head and fee_head.id or False,
                'exclude_from_invoice_tab': False,
                'course_gross_fee': challan.discount,
            }
            lines.append([0, 0, discount_line])

            # Create Payment Discount Credit
            fee_structure = rec.student_id._get_fee_structure(log_message=False)
            if not fee_structure:
                raise UserError(_('No Fee Structure Found For Student-%s') % rec.student_id.code)

            receipts = self.env['odoocms.receipt.type'].search([('code', '=', 'FP'),'|',('company_id','=',challan.company_id.id),('company_id','=',False)], order='id desc', limit=1)
            if not receipts:
                receipts = self.env['odoocms.receipt.type'].search([('code', '=', 'MiSC'),'|',('company_id','=',challan.company_id.id),('company_id','=',False)], order='id desc', limit=1)

            payment_discount_journal = self.env['ir.config_parameter'].sudo().get_param('aarsol.payment_discount_journal','Payment Discount')
            journal_id = self.env['account.journal'].search([('name', '=', payment_discount_journal), '|', ('company_id', '=', challan.company_id.id), ('company_id', '=', False)], order='id desc', limit=1)

            data = {
                'student_id': rec.student_id.id,
                'partner_id': rec.student_id.partner_id.id,
                'fee_structure_id': fee_structure.id,
                'is_fee': True,
                'is_cms': True,
                'is_late_fee': True,
                'move_type': 'out_refund',
                'invoice_line_ids': lines,
                'journal_id': journal_id and journal_id.id or False,
                'invoice_date': rec.date,
                'invoice_date_due': rec.date,
                'state': 'draft',
                'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                'term_id': challan.term_id and challan.term_id.id or False,
            }
            discount_invoice = self.env['account.move'].create(data)

            receivable_lines = discount_invoice.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            for receivable_line in receivable_lines.sorted(key=lambda a: a.date_maturity, reverse=False):
                if not receivable_line.challan_id:
                    receivable_line.write({
                        'challan_id': challan.id,
                    })
            challan.discount = 0
            discount_invoice.action_post()

    # Called from Service
    def action_post_fee_payment(self, fee_term_id=False, student_ledger=True):
        for rec in self:
            if not fee_term_id:
                if rec.term_id:
                    fee_term_id = rec.term_id.id
                else:
                    fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
                    fee_term_id = self.env['odoocms.academic.term'].browse(fee_charge_term).id

            if rec.payment_id:
                continue

            if rec.challan_id:
                flag = True
                challan = rec.challan_id
                if abs(rec.received_amount - challan.amount_residual) > 2:
                    # if (challan.late_fine + challan.amount_residual) == rec.received_amount:
                    #     rec.late_fee_invoice()
                    # else:
                        flag = False

                if challan.discount > 0:
                    rec.full_payment_discount_credit()
                if challan.late_fine > 0 and abs(rec.received_amount - challan.amount_residual) < 1:
                    rec.late_fee_invoice()

                if flag:
                    to_reconcile = challan.line_ids
                    partner_id = rec.student_id and rec.student_id.partner_id or False
                    destination_account_id = self.env['account.account'].search([('company_id','=',challan.company_id.id),('user_type_id.name', '=', 'Receivable')], order='id asc', limit=1)
                    invoice_id = challan.line_ids[0].move_id
                    _logger.warning("POSTING Fee: Challan:%s, Invoice:%s" % (challan.name, invoice_id.name,))

                    if invoice_id.state != 'posted':
                        invoice_id.action_post()

                    data = {
                        'payment_type': 'inbound',
                        'payment_method_id': 1,
                        'partner_type': 'customer',
                        'currency_id': rec.journal_id.company_id.currency_id.id,
                        'partner_id': partner_id and partner_id.id or False,
                        'payment_date': rec.date,
                        'date': rec.date,
                        'ref': rec.receipt_number,
                        'amount': rec.received_amount,
                        'journal_id': rec.journal_id.id,
                        # 'donor_id': invoice.donor_id and invoice.donor_id.id or False,
                        'partner_bank_id': False,
                        'destination_account_id': destination_account_id and destination_account_id.id or False,
                    }
                    payment_id = self.env['account.payment'].create(data)
                    payment_id.action_post()
                    domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                    payment_lines = payment_id.line_ids.filtered_domain(domain)
                    for account in payment_lines.account_id:
                        (payment_lines + to_reconcile).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()

                    rec.write({
                        'name': payment_id.name,
                        'invoice_id': invoice_id.id,
                        'payment_id': payment_id.id,
                        'state': 'done',
                        'post_date': fields.Date.today(),
                        'processed': True,
                    })

                    # ***** Approve Registration *****
                    registration_id = self.env['odoocms.course.registration'].sudo().search([('invoice_id', '=', invoice_id.id),('state','=','submit')], order='id desc', limit=1)
                    registration_confirm_at_fee_paid = self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.registration_confirm_at_fee_paid', False)
                    if registration_confirm_at_fee_paid:
                        registration_id.write({
                            'date_effective': rec.date
                        })
                    registration_id.sudo().action_approve()

                    # if not registration_id:
                    #     registration_id = self.env['odoocms.course.registration'].sudo().search([('student_id', '=', invoice.student_id.id),
                    #                                                                              ('term_id', '=', fee_term_id),
                    #                                                                              ('state', '!=', 'approved')
                    #                                                                              ], order='id desc', limit=1)
                    # if registration_id and invoice.challan_type in ('main_challan', 'add_drop', 'admission'):
                    #     registration_id.sudo().action_approve()

                    if challan.label_id.type == 'admission':
                        student = challan.student_id
                        program_sequence_number = student.program_id.sequence_number
                        company_code = getattr(invoice_id.company_id, 'code', False)
                        if company_code:
                            if invoice_id.company_id.code in ('CUST','UBAS'):
                                reg_no = student.program_id.short_code + invoice_id.term_id.short_code + str(student.program_id.sequence_number).zfill(3)
                            else:
                                # last_student = self.env['odoocms.student'].search([('program_id', '=', invoice_id.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
                                # if last_student:
                                #     last_student_code = last_student.code[-4:]
                                #     program_sequence_number = int(last_student_code) + 1
                                reg_no = 'L1' + invoice_id.term_id.short_code + student.program_id.short_code + str(program_sequence_number).zfill(4)
                        else:
                            last_student = self.env['odoocms.student'].search([('program_id', '=', student.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
                            # if last_student:
                            #     last_student_code = last_student.code[-4:]
                            #     program_sequence_number = int(last_student_code) + 1
                            reg_no = 'L1' + invoice_id.term_id.short_code + student.program_id.short_code + str(program_sequence_number).zfill(4)

                        student.program_id.sequence_number = program_sequence_number + 1
                        student.write({
                            'code': reg_no,
                            'id_number': reg_no
                        })

                        # invoice_id.application_id.sudo().new_student_registration()
                        invoice_id.application_id.admission_link_invoice_to_student()

                        # Email And SMS
                        # rec.sudo().send_fee_receive_sms(reg_no)
                        # if invoice_id.company_id.code == 'UCP':
                        #     rec.send_fee_receive_email(student, reg_no)

                    # ***** Reinstate Drap Courses due to Fee *****#
                    # ***** Search Out Withdraw Courses *****#

                    if challan.label_id.type != 'other':
                        reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
                        if reason_id:
                            withdraw_courses = challan.student_id.course_ids.filtered(lambda a: a.state == 'withdraw' and a.withdraw_reason == reason_id)
                            if withdraw_courses:
                                withdraw_courses.write({
                                    'state': 'current',
                                    'withdraw_date': False,
                                    'withdraw_reason': False,
                                    'grade': False,
                                })


            else:
                invoice = rec.invoice_id
                _logger.warning("POSTING Fee: Invoice:%s" % (invoice.name,))
                if invoice.state != 'posted':
                    rec.write({
                        'state': 'error',
                    })
                    continue
                to_reconcile = invoice.line_ids._origin
                invoice_ids2 = invoice
                due_date = invoice.invoice_date_due
                date_invoice = rec.date
                payment_date = fields.Date.from_string(rec.date)
                invoice.payment_date = rec.date
                # days = (payment_date - due_date).days

                partner_id = invoice.student_id and invoice.student_id.partner_id or False
                destination_account_id = self.env['account.account'].search([('company_id','=',invoice.company_id.id),('user_type_id.name', '=', 'Receivable')], order='id asc', limit=1)
                data = {
                    'payment_type': 'inbound',
                    'payment_method_id': 1,
                    'partner_type': 'customer',
                    'currency_id': invoice.journal_id.company_id.currency_id.id,
                    'partner_id': partner_id and partner_id.id or False,
                    'payment_date': rec.date,
                    'date': rec.date,
                    'ref': rec.receipt_number,
                    'amount': rec.received_amount,
                    'journal_id': rec.journal_id.id,
                    'donor_id': invoice.donor_id and invoice.donor_id.id or False,
                    'partner_bank_id': False,
                    'destination_account_id': destination_account_id and destination_account_id.id or False,
                }

                payment_vals_list = [data]
                new_payment_recs = self.env['account.payment'].create(payment_vals_list)
                new_payment_recs.action_post()
                rec.name = new_payment_recs.name
                domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
                to_reconcile2 = to_reconcile.filtered_domain([('account_internal_type', 'in', ('receivable', 'payable')),
                                                              ('reconciled', '=', False)])
                for new_payment_rec, lines in zip(new_payment_recs, to_reconcile2):
                    if new_payment_rec.state != 'posted':
                        continue
                    payment_lines = new_payment_rec.line_ids.filtered_domain(domain)
                    for account in payment_lines.account_id:
                        (payment_lines + lines).filtered_domain([('account_id', '=', account.id),
                                                                 ('reconciled', '=', False)
                                                                 ]).reconcile()

                # invoice.payment_id = new_payment_rec.id
                invoice_ids2.payment_date = rec.date
                rec.write({
                    'state': 'done',
                    'processed': True,
                })
                invoice.write({
                    'confirmation_date': fields.Date.today(),
                })

                # ***** Approve Registration *****#
                registration_id = invoice.registration_id
                if not registration_id:
                    reg_domain = [('student_id', '=', invoice.student_id.id), ('term_id', '=', fee_term_id), ('state', '!=', 'approved')]
                    registration_id = self.env['odoocms.course.registration'].sudo().search(reg_domain, order='id desc', limit=1)
                if registration_id and invoice.challan_type in ('main_challan', 'add_drop', 'admission'):
                    registration_id.sudo().action_approve()

                # Prospectus Fee
                admission_fee_installed = self.env['ir.module.module'].sudo().search([('name', '=', 'odoocms_admission_fee'), ('state', '=', 'installed')])
                if admission_fee_installed and invoice.application_id and invoice.challan_type == 'prospectus_challan' and not invoice.application_id.fee_voucher_state == 'verify':
                    invoice.application_id.sudo().verify_voucher(manual=False)
                    invoice.application_id.sudo().write({
                        'voucher_date': invoice.payment_date or rec.date or fields.Date.today(),
                        'voucher_verified_date': fields.Date.today(),
                        'fee_voucher_state': 'verify'
                    })

                # ***** Reinstate Drap Courses due to fee *****#
                # ***** Search Out Withdraw Courses *****#
                if invoice.challan_type in ('2nd_challan', 'installment'):
                    reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
                    if reason_id:
                        withdraw_courses = invoice.student_id.course_ids.filtered(lambda a: a.state == 'withdraw' and a.withdraw_reason == reason_id)
                        if withdraw_courses:
                            withdraw_courses.write({
                                'state': 'current',
                                'withdraw_date': False,
                                'withdraw_reason': False,
                                'grade': False,
                            })


    # Invalid Practice here, should create a new invoice of fine.
    def action_update_invoice(self, invoice=False):
        for rec in self:
            amount = 0
            if invoice:
                first_due_date_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.first_due_date_days') or '15')
                second_due_date_days = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.second_due_date_days') or '30')
                first_due_date_fine = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.first_due_date_fine') or '5')
                second_due_date_fine = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.second_due_date_fine') or '10')

                days = (rec.date - invoice.invoice_date_due).days
                if days <= first_due_date_days:
                    amount = round(invoice.amount_residual * (first_due_date_fine / 100))
                if days > first_due_date_days:
                    amount = round(invoice.amount_residual * (second_due_date_fine / 100))
            fine_line = invoice.invoice_line_ids.filtered(lambda l: l.fee_head_id.name == 'Fine')
            receivable_line = invoice.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')

            if fine_line:
                # Will Credit
                self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                    , (amount, amount, -amount, amount, amount, fine_line.id))

                # Receivable Line, it will debit
                debit_amt = receivable_line.debit + amount
                self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s, price_subtotal=%s, price_total=%s, amount_residual=%s,amount_residual_currency=%s where id=%s \n"
                                    , (-debit_amt, debit_amt, debit_amt, -debit_amt, -debit_amt, debit_amt, debit_amt, receivable_line.id,))

                # Invoice Total Update
                self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                    , (debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, debit_amt, invoice.id))
                ledger_id = self.env['odoocms.student.ledger'].search([('invoice_id', '=', invoice.id)], order='id desc', limit=1)
                ledger_id.credit = ledger_id.credit + amount
                rec.amount += amount
        return amount

    # Setup button to show form
    def action_read_fee_payments(self):
        self.ensure_one()
        return {
            'name': "Fee Payments Form",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'odoocms.fee.payment',
            'res_id': self.id,
        }

    def action_create_payment_deletion_log(self):
        for rec in self:
            values = {
                'name': rec.name,
                'move_id': rec.invoice_id and rec.invoice_id.id or False,
                'barcode': rec.receipt_number,
                'number': rec.name,
                'student_id': rec.student_id.id,
                'session_id': rec.student_id.session_id and rec.student_id.session_id.id or False,
                'career_id': rec.student_id.career_id and rec.student_id.career_id.id or False,
                'institute_id': rec.student_id.institute_id and rec.student_id.institute_id.id or False,
                'campus_id': rec.student_id.campus_id and rec.student_id.campus_id.id or False,
                'program_id': rec.student_id.program_id and rec.student_id.program_id.id or False,
                'discipline_id': rec.student_id.discipline_id and rec.student_id.discipline_id.id or False,
                'term_id': rec.student_id.term_id and rec.student_id.term_id.id or False,
                'semester_id': rec.student_id.semester_id and rec.student_id.semester_id.id or False,
                'payment_register': rec.payment_register_id and rec.payment_register_id.name or False,
            }
            self.env['odoocms.fee.payment.deletion.log'].create(values)

    # This Method is used for Payment creation in the 1LINK, also available in ext_ucp
    @api.model
    def create_1link_payment(self, date, consumer_no, amount):
        new_rec = False
        if date and consumer_no:
            # dt1 = fields.Date.from_string(date).strftime('%Y-%m-%d')
            # date = dt1
            register_id = self.env['odoocms.fee.payment.register'].search([('date', '=', date)])
            if not register_id:
                register_values = {
                    'date': date,
                }
                register_id = self.env['odoocms.fee.payment.register'].create(register_values)

            if register_id.state == 'Draft':
                already_exist = False
                invoice_id = self.env['account.move'].search([('barcode', '=', consumer_no), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
                if not invoice_id:
                    invoice_id = self.env['account.move'].search([('name', '=', consumer_no), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])

                already_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', consumer_no),
                                                                        ('invoice_id.amount_residual', '=', 0.0)])
                if not already_exist:
                    already_exist = self.env['account.move'].search([('barcode', '=', consumer_no),
                                                                     ('move_type', '=', 'out_invoice'),
                                                                     ('amount_residual', '=', 0.0)])
                if not already_exist:
                    fee_payment_rec_exist = self.env['odoocms.fee.payment'].search([('receipt_number', '=', consumer_no)], order='id', limit=1)
                    if fee_payment_rec_exist:
                        if fee_payment_rec_exist.received_amount >= fee_payment_rec_exist.amount:
                            already_exist = fee_payment_rec_exist

                if not already_exist:
                    already_exist = self.env['odoocms.fee.payment'].search([('invoice_id', '=', invoice_id.id),
                                                                            ('payment_register_id', '=', register_id.id),
                                                                            ('invoice_id.amount_residual', '>', 0.0),
                                                                            ], order='id', limit=1)

                # Create the Record in the Fee Payment Receipts
                if invoice_id and not already_exist:
                    values = {
                        'invoice_id': invoice_id.id,
                        'receipt_number': consumer_no,
                        'student_id': invoice_id.student_id and invoice_id.student_id.id or False,
                        'amount': invoice_id.amount_residual,
                        'term_id': invoice_id.term_id and invoice_id.term_id.id or False,
                        'journal_id': 7,
                        'date': date,
                        'payment_register_id': register_id.id,
                        'received_amount': invoice_id.amount_residual,
                    }
                    new_rec = self.env['odoocms.fee.payment'].create(values)

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


# ***** This Class Will Handle all the Records Whose Total Amount and Receive Amount not Matched. ****#
class OdoocmsFeePaymentsAmountMismatch(models.Model):
    _name = 'odoocms.fee.payments.amount.mismatch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Payments Amount Mismatch'

    name = fields.Char('Name')
    barcode = fields.Char('Challan#')
    payment_register_id = fields.Many2one('odoocms.fee.payment.register', 'Payment Register', index=True, ondelete='cascade', auto_join=True)
    invoice_id = fields.Many2one('account.move', 'Invoice')
    invoice_amount = fields.Float('Invoice Amount')
    payment_amount = fields.Float('Payment Amount')
    diff_amount = fields.Float('Diff Amount')
    state = fields.Selection([('Draft', 'Draft'),
                              ('Posted', 'Posted'),
                              ('Cancel', 'Cancel')], string='Status', default='Draft')
    notes = fields.Char('Notes')


    @api.model
    def create(self, values):
        result = super(OdoocmsFeePaymentsAmountMismatch, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.payments.amount.mismatch')
        return result


# This Class Will Handle all the barcode Records whose Invoice is
# Not found. (Invoice Barcode does not Match With Barcode)
class OdooCMSFeeNonBarcodeReceipts(models.Model):
    _name = 'odoocms.fee.non.barcode.receipts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Non Barcode Receipts'

    name = fields.Char('Name')
    barcode = fields.Char('Barcode')
    payment_register_id = fields.Many2one('odoocms.fee.payment.register', 'Payment Register', index=True, ondelete='cascade', auto_join=True)
    state = fields.Selection([('Draft', 'Draft'), ('Posted', 'Posted'), ('Cancel', 'Cancel')], string='Status', default='Draft')


# This Class Will Handle all the Records that is already processed But User Scan the barcode again.
class OdooCMSFeeProcessedReceipts(models.Model):
    _name = 'odoocms.fee.processed.receipts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Processed Receipts'

    name = fields.Char('Name')
    barcode = fields.Char('Barcode')
    payment_register_id = fields.Many2one('odoocms.fee.payment.register', 'Payment Register', index=True, ondelete='cascade', auto_join=True)
    state = fields.Selection([('Draft', 'Draft'), ('Posted', 'Posted'), ('Cancel', 'Cancel')], string='Status', default='Draft')
    notes = fields.Char('Notes')


