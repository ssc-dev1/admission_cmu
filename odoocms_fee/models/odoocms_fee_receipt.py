import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo import tools

import logging
_logger = logging.getLogger(__name__)

try:
    from num2words import num2words
except ImportError:
    _logger.warning("The num2words python library is not installed, amount-to-text features won't be fully available.")
    num2words = None


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_cancel(self):
        for rec in self:
            fee_payment_ids = self.env['odoocms.fee.payment'].sudo().search([('payment_id', '=', rec.id)])
            fee_payment_ids.write({
                'payment_id': False,
                'state': 'draft'
            })
            super(AccountPayment, rec).action_cancel()


class OdooCMSFeeReceipt(models.Model):
    _inherit = 'account.move'
    _order = "date desc, name desc, id desc"

    student_id = fields.Many2one('odoocms.student', 'Student', ondelete="restrict", index=True)

    session_id = fields.Many2one('odoocms.academic.session', 'Session', related='student_id.session_id', store=True)
    institute_id = fields.Many2one('odoocms.institute','Institute', related='student_id.institute_id', store=True)
    program_id = fields.Many2one('odoocms.program','Program', related='student_id.program_id', store=True)

    fee_structure_id = fields.Many2one('odoocms.fee.structure', string='Fee Structure', readonly=True, states={'draft': [('readonly', False)]})
    term_id = fields.Many2one('odoocms.academic.term', 'Student Term')
    term_code = fields.Char(related='term_id.code', string='Term Code', store=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester')

    registration_id = fields.Many2one('odoocms.course.registration', 'Registration', ondelete='restrict')

    # ***** Set True if it is Student Fee Voucher *****#
    is_fee = fields.Boolean('Is Fee', default=False)
    is_cms = fields.Boolean('CMS Receipt?', default=False)
    is_late_fee = fields.Boolean('Is Late Fee', default=False)
    is_scholarship_fee = fields.Boolean('Scholarship Fee', default=False)
    is_hostel_fee = fields.Boolean('Is Hostel Fee', default=False)
    is_admission_fee = fields.Boolean('Admission Voucher', default=False)
    is_prospectus_fee = fields.Boolean('Prospectus Voucher', default=False)
    is_library_fine_fee = fields.Boolean('Library Fine Voucher', default=False)

    student_ledger_id = fields.Many2one('odoocms.student.ledger', 'Student Ledger')
    payment_ledger_id = fields.Many2one('odoocms.student.ledger', 'Payment Ledger')

    back_invoice = fields.Many2one('account.move', 'Back Invoice')
    forward_invoice = fields.Many2one('account.move', 'Forward Invoice')

    receipt_type_ids = fields.Many2many('odoocms.receipt.type', string='Receipt For')
    waiver_ids = fields.Many2many('odoocms.fee.waiver', string='Fee Waiver')
    waiver_amount = fields.Float('Waiver Amount')
    waiver_percentage = fields.Float('Waiver Discount %')

    payment_date = fields.Date('Payment Date')
    fee_paid = fields.Boolean('Is Fee Paid', default=False)

    # If fee payment is late, system will generate an invoice for fine.
    # Fine invoice will be linked to original invoice
    super_invoice = fields.Many2one('account.move', 'Super Invoice')
    sub_invoice = fields.Many2one('account.move', 'Sub Invoice')

    tag = fields.Char('Tag', help='Attach the tag', readonly=True)
    reference = fields.Char('Receipt Reference')

    description_id = fields.Many2one('odoocms.fee.description', 'Fee Description')
    invoice_group_id = fields.Many2one('account.move.group', 'Invoice Group')

    total_fine = fields.Integer(default=0)
    amount_total_with_fine = fields.Integer(default=0)
    download_time = fields.Datetime()

    barcode = fields.Char('Barcode', index=True, compute='compute_barcode', store=True,)
    donor_id = fields.Many2one('odoocms.fee.donors', 'Donor', tracking=True)
    validity_date = fields.Date('Validity Date')
    student_tags = fields.Char('Student Tags', compute='_compute_student_tags', store=True)

    # @added 10102021 For Dashboard Purpose
    student_dashboard_tag = fields.Char('Student Dashboard Tag', compute='_compute_student_tags', store=True)

    # fee_structure_head_id = fields.Many2one('odoocms.fee.structure.head', string='Fee Structure Head')
    # fee_structure_head_line_id = fields.Many2one('odoocms.fee.structure.head.line', string='Fee Structure Head Line')
    to_be = fields.Boolean('To Be', default=False)
    cancel_due_to_arrears = fields.Boolean('Cancel Due to Arrears')

    challan_type = fields.Selection([('main_challan', 'Main Challan'),
                                     ('2nd_challan', '2nd Challan'),
                                     ('admission', 'New Admission'),
                                     ('admission_2nd_challan', 'Admission 2nd Challan'),
                                     ('add_drop', 'Add Drop'),
                                     ('prospectus_challan', 'Prospectus Challan'),
                                     ('hostel_fee', 'Hostel Fee'),
                                     ('misc_challan', 'Misc Challan'),
                                     ('installment', 'Installment')
                                     ], string='Challan Type', tracking=True, index=True)
    semester_gross_fee = fields.Float('Semester Gross Fee', compute='_compute_semester_gross_fee', store=True)
    add_drop_no = fields.Char('Add Drop No')  # , compute='_compute_add_drop_no', store=True
    aarsol_process = fields.Boolean()
    old_challan_no = fields.Char('Challan No', tracking=True, index=True, copy=False)


    @api.onchange('student_id')
    def onchange_student_id(self):
        for rec in self:
            if rec.student_id:
                rec.partner_id = rec.student_id.partner_id.id

    def add_follower(self, partners, subtype_ids=None):
        self.message_subscribe(partner_ids=partners.ids, subtype_ids=subtype_ids)

    def add_followers(self, partners):
        mt_comment = self.env.ref('mail.mt_comment').id

        self.add_follower(partners, [mt_comment, ])
        if self.student_id and self.student_id.user_id:
            self.add_follower(self.student_id.user_id.partner_id, [mt_comment, ])

    def generate_challan_barcode(self, student_id, label=None, late_fine=0):
        challan_ids = self.env['odoocms.fee.barcode'].sudo()

        receivable_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
        i = 0
        for receivable_line in receivable_lines.sorted(key=lambda a: a.date_maturity, reverse=False):
            # if i == 0 and receivable_line.challan_id:
            #     receivable_line.challan_id.late_fine = late_fine
            # elif not receivable_line.challan_id:
            term_id = receivable_line.move_id.term_id
            if not receivable_line.challan_id:
                label_id = self.env['account.payment.term.label']
                if label:
                    label_id = self.env['account.payment.term.label'].search(['|', ('name', '=', label), ('code', '=', label)], order='id', limit=1)

                if not label_id:
                    if receivable_line.label_id:
                        label_id = receivable_line.label_id
                    else:
                        # Add here an other condition to get the label from invoice type
                        label_id = self.env['account.payment.term.label'].search(['|', ('name', '=', 'Misc'), ('code', '=', 'Misc')], order='id', limit=1)

                fine_policy_line = student_id.check_fine_policy(term_id, label_id)

                data = {
                    'student_id': student_id.id,
                    'model': 'account.move.line',
                    'res_id': receivable_line.id,
                    'waiver_percentage': self.waiver_percentage,
                    'label_id': label_id and label_id.id or False,
                    'show_on_portal': label_id and label_id.auto_publish,
                    'name': self._context.get('challan_no',False),
                    'term_id': term_id.id,
                    'date_due': receivable_line.date_maturity,
                    'company_id': student_id.company_id.id,
                    'fine_policy_line_id': fine_policy_line.id,
                    'late_fine': fine_policy_line.fine_amount,
                }
                challan_id = self.env['odoocms.fee.barcode'].sudo().create(data)

                receivable_line.write({
                    'challan_id': challan_id.id,
                })
                challan_ids += challan_id

            i += 1

        if challan_ids:
            student = challan_ids[0].student_id
            term = challan_ids[0].term_id
            registration = self.env['odoocms.course.registration'].search([('invoice_id','=', self.id)])
            if registration.enrollment_type == 'add_drop':
                domain = [('student_id','=',student.id),('term_id','=',term.id),('state','=','draft'),('label_id.type','=','main')]
                unpaid_main_challan = self.env['odoocms.fee.barcode'].sudo().search(domain)
                if unpaid_main_challan:
                    for challan_id in challan_ids:
                        data = {
                            'student_id': student.id,
                            'challan_id2': unpaid_main_challan.id,
                            'challan_id': challan_id.id,
                            'company_id': student.company_id.id,
                            # 'registration_id': registration and registration.id or False,
                        }
                        merged = self.env['odoocms.fee.barcode.merge'].sudo().create(data)
                        merged.post_merge()

        return challan_ids

    def get_challan_remaining_amount(self):
        amt = 0
        invoices = self.env['account.move'].search([('student_id', '=', self.student_id.id),
                                                    ('term_id', '=', self.term_id.id),
                                                    ('payment_state', '=', 'not_paid'),
                                                    ('id', '!=', self.id)])
        for invoice in invoices:
            amt += invoice.tuition_fee
        return amt

    # @api.depends('challan_type')
    # def _compute_add_drop_no(self):
    #     for rec in self:
    #         if rec.challan_type == 'add_drop':
    #             prev_add_drop_rec = self.env['account.move'].search([('student_id', '=', rec.student_id.id),
    #                                                                  ('term_id', '=', rec.term_id.id),
    #                                                                  ('challan_type', '=', 'add_drop'),
    #                                                                  ('id', '!=', rec._origin.id),
    #                                                                  ('id', '<', rec._origin.id)
    #                                                                  ], order='id desc', limit=1)
    #             if prev_add_drop_rec and prev_add_drop_rec.add_drop_no and not len(prev_add_drop_rec.add_drop_no) == 0:
    #                 rec.add_drop_no = str(int(prev_add_drop_rec.add_drop_no) + 1)
    #             else:
    #                 rec.add_drop_no = "1"

    def post_fee_payment(self):
        for rec in self:
            _logger.warning("POSTING Fee: Invoice:%s" % (rec.name,))
            destination_account_id = self.env['account.account'].search([('user_type_id.name', '=', 'Receivable')], order='id asc', limit=1)
            journal_id = self.env['account.journal'].search([('code', '=', 'FDB')], order='id asc', limit=1)
            data = {
                'payment_type': 'inbound',
                'payment_method_id': 1,
                'partner_type': 'customer',
                'currency_id': rec.currency_id.id,
                'partner_id': rec.partner_id and rec.partner_id.id or False,
                'payment_date': rec.date,
                'date': rec.date,
                'ref': rec.reference or rec.name,
                'amount': rec.amount_residual,
                'journal_id': journal_id.id,
                'partner_bank_id': False,
                'destination_account_id': destination_account_id and destination_account_id.id or False,
            }
            payment_id = self.env['account.payment'].create(data)
            payment_id.action_post()

            domain = [('account_internal_type', 'in', ('receivable', 'payable')), ('reconciled', '=', False)]
            to_reconcile = rec.line_ids.filtered_domain(domain)
            for payment, lines in zip(payment_id, to_reconcile):
                payment_lines = payment.line_ids.filtered_domain(domain)
                for account in payment_lines.account_id:
                    (payment_lines + lines).filtered_domain([('account_id', '=', account.id), ('reconciled', '=', False)]).reconcile()

            rec.student_ledger_id.aarsol_process = True
            rec.payment_ledger_id.aarsol_process = True
            rec.aarsol_process = True

    @api.depends('line_ids', 'line_ids.course_gross_fee', 'challan_type', 'payment_state')
    def _compute_semester_gross_fee(self):
        for rec in self:
            gross_amt = 0
            if rec.line_ids:
                # for line in rec.line_ids.filtered(lambda a: not a.registration_type or a.registration_type in ('main', 'add')):
                for line in rec.line_ids.filtered(lambda l: l.course_credit_hours > 0):
                    if line.course_gross_fee == 0: #and line.credit > 0:
                        gross_amt += line.price_subtotal
                    else:
                        gross_amt += line.course_gross_fee
                rec.semester_gross_fee = gross_amt

    def button_set_draft(self):
        AccountMoveLine = self.env['account.move.line']
        excluded_move_ids = []

        if self._context.get('suspense_moves_mode'):
            excluded_move_ids = AccountMoveLine.search(AccountMoveLine._get_suspense_moves_domain() + [('move_id', 'in', self.ids)]).mapped('move_id').ids

        for move in self:
            if move in move.line_ids.mapped('full_reconcile_id.exchange_move_id'):
                raise UserError(_('You cannot reset to draft an exchange difference journal entry.'))
            if move.tax_cash_basis_rec_id or move.tax_cash_basis_origin_move_id:
                # If the reconciliation was undone, move.tax_cash_basis_rec_id will be empty;
                # but we still don't want to allow setting the caba entry to draft
                # (it'll have been reversed automatically, so no manual intervention is required),
                # so we also check tax_cash_basis_origin_move_id, which stays unchanged
                # (we need both, as tax_cash_basis_origin_move_id did not exist in older versions).
                raise UserError(_('You cannot reset to draft a tax cash basis journal entry.'))
            if move.restrict_mode_hash_table and move.state == 'posted' and move.id not in excluded_move_ids:
                raise UserError(_('You cannot modify a posted entry of this journal because it is in strict mode.'))
            # We remove all the analytics entries for this journal
            move.mapped('line_ids.analytic_line_ids').unlink()

        # Remarked the following line - Farooq
        # self.mapped('line_ids').remove_move_reconcile()
        self.write({'state': 'draft', 'is_move_sent': False})

    def action_invoice_send(self):
        pass

    def action_invoice_open(self):
        # lots of duplicate calls to action_invoice_open, so we remove those already open
        to_open_invoices = self.filtered(lambda inv: inv.payment_state == 'not_paid')
        to_open_invoices.write({'state': 'draft'})
        return super(OdooCMSFeeReceipt, self).action_invoice_open()

    def action_post(self):
        if self.term_id and self.invoice_payment_term_id:
            domain = [('company_id','=',self.company_id.id),('payment_term_id','=',self.invoice_payment_term_id.id),('term_id','=',self.term_id.id)]
            payment_term_term = self.env['account.payment.term.term'].sudo().search(domain)
            if payment_term_term and payment_term_term.allowed > 0:
                domain = [('company_id', '=', self.company_id.id), ('invoice_payment_term_id', '=', self.invoice_payment_term_id.id), ('term_id', '=', self.term_id.id)]
                same_payment_term_invoices = len(self.env['account.move'].sudo().search(domain))
                if not payment_term_term.allowed > same_payment_term_invoices:
                    raise UserError('Max allowed limit for Payment Term %s exceeds (%s/%s)' % (self.invoice_payment_term_id.name, same_payment_term_invoices, payment_term_term.allowed,))
                payment_term_term.actual = same_payment_term_invoices + 1

        result = super(OdooCMSFeeReceipt, self).action_post()
        if self.move_type == 'out_invoice' and self.is_fee and self.challan_type != 'prospectus_challan' and not self.env.context.get('no_challan',False):
            self.generate_challan_barcode(self.student_id)
        return result

    # def _get_refund_common_fields(self):
    #     return super(OdooCMSFeeReceipt, self)._get_refund_common_fields() + ['student_id', 'applicant_id', 'program_id',
    #                                                                          'fee_structure_id', 'is_fee', 'is_cms']

    def _get_report_base_filename(self):
        self.ensure_one()
        return self.move_type == 'out_invoice' and self.state == 'draft' and _('Draft Invoice') or \
            self.move_type == 'out_invoice' and self.state in ('not_paid', 'in_payment', 'paid') and _(
                'Invoice - %s') % (self.number) or \
            self.move_type == 'out_refund' and self.state == 'draft' and _('Credit Note') or \
            self.move_type == 'out_refund' and _('Credit Note - %s') % self.number or \
            self.move_type == 'in_invoice' and self.state == 'draft' and _('Vendor Bill') or \
            self.move_type == 'in_invoice' and self.state in ('open', 'in_payment', 'paid') and _(
                'Vendor Bill - %s') % (self.number) or \
            self.move_type == 'in_refund' and self.state == 'draft' and _('Vendor Credit Note') or \
            self.move_type == 'in_refund' and _('Vendor Credit Note - %s') % self.number

    def is_zero(self, amount):
        return tools.float_is_zero(amount, precision_rounding=2)

    def amount_to_text(self, amount):
        self.ensure_one()

        def _num2words(number, lang):
            try:
                return num2words(number, lang=lang).title()
            except NotImplementedError:
                return num2words(number, lang='en').title()

        if num2words is None:
            logging.getLogger(__name__).warning("The library 'num2words' is missing, cannot render textual amounts.")
            return ""

        formatted = "%.{0}f".format(2) % amount
        parts = formatted.partition('.')
        integer_value = int(parts[0])
        fractional_value = int(parts[2] or 0)

        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)])
        amount_words = tools.ustr('{amt_value} {amt_word}').format(
            amt_value=_num2words(integer_value, lang=lang.iso_code),
            amt_word='.',
        )
        if not self.is_zero(amount - integer_value):
            amount_words += ' ' + 'and' + tools.ustr(' {amt_value} {amt_word}').format(
                amt_value=_num2words(fractional_value, lang=lang.iso_code),
                amt_word='.',
            )
        return amount_words

    def unlink(self):
        for move in self:
            if move.is_fee and move.payment_state not in ("paid", "in_payment"):
                move.write({'payment_state': 'not_paid', 'state': 'draft', 'posted_before': False})

            # For IMS
            # slip_barcode = move.barcode
            # move.name = '/'
            # self._context.get('force_delete')
            # if not move.payment_state == "not_paid":
            #     raise UserError(_("You cannot delete an entry which has been posted once."))



            # Remarked by Farooq
            # have_defer_link = self.env['odoocms.tuition.fee.deferment.line'].search(
            #     [('defer_invoice_id', '=', move.id), ('state', '!=', 'done')])
            # student_waivers = self.env['odoocms.student.fee.waiver'].search([('invoice_id', '=', move.id)])
            #
            # if student_waivers:
            #     student_waivers.unlink()
            # if have_defer_link:
            #     have_defer_link.unlink()
            # move.line_ids.unlink()
            # move.invoice_line_ids.unlink()
            # move.student_ledger_id.unlink()
            # move.action_create_receipt_deletion_log()
            # if slip_barcode:
            #     br_ledger_entries = self.env['odoocms.student.ledger'].search([('slip_barcode', '=', slip_barcode)])
            #     if br_ledger_entries:
            #         br_ledger_entries.unlink()
            #
            # # Recalculate the Ledger Balance
            # # This Method is defined in odoocms.student
            # move.student_id.update_student_ledger_balance()
            #
            # # ******* Add @01-08-2021 *******
            # adjustment_lines = self.env['odoocms.fee.adjustment.request'].search(
            #     [('student_id', '=', move.student_id.id),
            #      ('invoice_id', '=', move.id),
            #      ('adjustment_term_id', '=', move.term_id.id),
            #      ('charged', '=', True)])
            # if adjustment_lines:
            #     adjustment_lines.write({'charged': False,
            #                             'invoice_id': False})
            # ******* End *******
        return super(OdooCMSFeeReceipt, self).unlink()

    def amount_after_first_due_date(self):
        first_due_date = ''
        first_due_date_amount = ''
        for rec in self:
            if rec.invoice_date:
                first_due_date_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.first_due_date_days') or '15')
                fine_charge_type = (self.env['ir.config_parameter'].sudo().get_param(
                    'odoocms_fee.fine_charge_type') or 'percentage')
                first_due_date_fine = int(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.first_due_date_fine') or '5')
                if fine_charge_type and fine_charge_type == 'percentage':
                    first_due_date_amount = round(rec.amount_total * (first_due_date_fine / 100), 0)
                if fine_charge_type and fine_charge_type == "fixed":
                    first_due_date_amount = first_due_date_fine
                invoice_date_due = rec.invoice_date_due + datetime.timedelta(days=1)
                invoice_date_due_end = rec.invoice_date_due + datetime.timedelta(days=first_due_date_days)
                first_due_date = "Between " + invoice_date_due.strftime(
                    "%d-%b-%y") + " to " + invoice_date_due_end.strftime("%d-%b-%y")

                first_due_date_amount = round(rec.amount_total + first_due_date_amount, 2)
        return first_due_date, first_due_date_amount

    def amount_after_second_due_date(self):
        second_due_date = ''
        second_due_date_amount = ''
        for rec in self:
            if rec.invoice_date:
                first_due_date_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.first_due_date_days') or '15')
                second_due_date_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.second_due_date_days') or '30')
                fine_charge_type = (self.env['ir.config_parameter'].sudo().get_param(
                    'odoocms_fee.fine_charge_type') or 'percentage')
                second_due_date_fine = int(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.second_due_date_fine') or '10')
                if fine_charge_type and fine_charge_type == 'percentage':
                    second_due_date_amount = round(rec.amount_total * (second_due_date_fine / 100), 0)
                if fine_charge_type and fine_charge_type == "fixed":
                    second_due_date_amount = second_due_date_fine

                invoice_date1 = rec.invoice_date_due + datetime.timedelta(days=first_due_date_days + 1)
                invoice_date = rec.invoice_date_due + datetime.timedelta(days=second_due_date_days)
                # second_due_date = "From " + invoice_date1.strftime("%d-%b-%y") + " to Onward " + invoice_date.strftime("%d-%b-%y")
                second_due_date = "From " + invoice_date1.strftime("%d-%b-%y") + " to Onward"
                second_due_date_amount = round(rec.amount_total + second_due_date_amount, 0)
        return second_due_date, second_due_date_amount

    def get_first_due_date(self):
        first_due_date = ''
        for rec in self:
            if rec.invoice_date:
                first_due_date_days = int(
                    self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.first_due_date_days') or '15')
                invoice_date_due = rec.invoice_date_due + datetime.timedelta(days=first_due_date_days)
                invoice_date_due = invoice_date_due.strftime("%d-%b-%Y")
        return invoice_date_due

    @api.depends('name')
    def compute_barcode(self):
        for rec in self:
            if rec.name and not rec.name == '/' and not rec.barcode:
                rec.barcode = self.env['ir.sequence'].next_by_code('odoocms.fee.receipt.barcode.sequence')
                if not rec.old_challan_no and rec.challan_type == 'prospectus_challan':
                    rec.old_challan_no = self.env['ir.sequence'].next_by_code('odoocms.processing.fee.challan.sequence')

    def action_create_receipt_deletion_log(self):
        for rec in self:
            values = {
                'name': rec.name,
                'move_id': rec.id,
                'barcode': rec.barcode,
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
            }
            self.env['odoocms.fee.receipt.deletion.log'].create(values)

    def button_cancel(self):
        for rec in self:
            fee_additional_charges = self.env['odoocms.fee.additional.charges'].sudo().search([('receipt_id', '=', rec.id)])
            fee_additional_charges.write({
                'state': 'draft',
                'receipt_id': False
            })
            input_other_fine_ids = self.env['odoocms.input.other.fine'].sudo().search([('receipt_id', '=', rec.id)])
            input_other_fine_ids.write({
                'state': 'draft',
                'receipt_id': False
            })
            student_attendance_fine_ids = self.env['odoocms.student.attendance.fine'].sudo().search([('move_id', '=', rec.id)])
            student_attendance_fine_ids.write({
                'state': 'draft',
                'move_id': False
            })
            overdraft_ids = self.env['odoocms.overdraft'].sudo().search([('move_id', '=', rec.id)])
            overdraft_ids.write({
                'state': 'draft',
                'move_id': False
            })
            registration_ids = self.env['odoocms.course.registration'].sudo().search([('invoice_id', '=', rec.id)])
            registration_ids.write({
                'state': 'draft',
                'invoice_id': False
            })
            waiver_ids = self.env['odoocms.student.fee.waiver'].sudo().search([('invoice_id', '=', rec.id)])
            waiver_ids.unlink()

            rec.line_ids.mapped('challan_id').write({
                'state': 'cancel'
            })
            super(OdooCMSFeeReceipt, rec).button_cancel()


    def group_invoice_lines(self):
        for rec in self:
            res = {}
            lines = []
            results = self.env['account.move.line'].read_group(
                [('move_id', '=', rec.id), ('fee_category_id', '!=', False)],
                fields=['fee_category_id', 'price_subtotal'], groupby=['fee_category_id'])
            for result in results:
                fee_categ_id = self.env['odoocms.fee.category'].search([('id', '=', result['fee_category_id'][0])])
                if result['price_subtotal'] > 0:
                    lines.append({'category': fee_categ_id.name,
                                  'amount': result['price_subtotal'],
                                  })
        res = lines
        return res

    @api.model
    def create_tax_line100(self, nlimit=100):
        tax_rate = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.tax_rate') or '5')
        taxable_amount = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.taxable_amount') or '200000')
        taxable_fee_heads = self.env['odoocms.fee.head'].search([('taxable', '=', True)])

        receipts = self.env['account.move'].search([('to_be', '=', True)], limit=nlimit)
        for receipt in receipts:
            previous_term_taxable_amt = 0
            current_term_taxable_amt = 0
            net_amount = 0
            tax_amount = 0
            if not any([inv_ln.fee_head_id.id == 60 for inv_ln in receipt.invoice_line_ids]):
                fall20_fee_recs = self.env['nust.student.fall20.fee'].search(
                    [('student_id', '=', receipt.student_id.id)])
                if fall20_fee_recs:
                    for fall20_fee_rec in fall20_fee_recs:
                        fall20_fee_rec.invoice_id = receipt.id
                        fall20_fee_rec.fee_status = 'c'
                        previous_term_taxable_amt += fall20_fee_rec.amount

                for receipt_line in receipt.invoice_line_ids:
                    # if not 'Discounts' in line[2]:
                    if receipt_line.price_unit < 0:
                        current_term_taxable_amt += receipt_line.price_unit
                    else:
                        if receipt_line.fee_head_id.id in taxable_fee_heads.ids:
                            current_term_taxable_amt += receipt_line.price_unit

                net_amount = previous_term_taxable_amt + current_term_taxable_amt

                if net_amount > taxable_amount:
                    tax_amount = round(net_amount * (tax_rate / 100), 3)

                fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Advance Tax')])
                if not fee_head:
                    raise UserError(_("Advance Tax Fee Head is not defined in the System."))
                if tax_amount > 0:
                    lines = []
                    tax_line = {
                        'sequence': 900,
                        'price_unit': tax_amount,
                        'quantity': 1,
                        'product_id': fee_head.product_id.id,
                        'name': "Tax Charged on Fee",
                        'account_id': fee_head.property_account_income_id.id,
                        # 'analytic_account_id': line.fee_head_id.analytic_account_id,
                        # 'analytic_tag_ids': analytic_tag_ids,
                        'fee_head_id': fee_head.id,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append([0, 0, tax_line])
                    receipt.update({'invoice_line_ids': lines})
            receipt.to_be = False

    @api.depends('student_id', 'student_id.tag_ids')
    def _compute_student_tags(self):
        for rec in self:
            dashboard_tags = ['NS', 'NFS', 'ASC', 'NFSPKR']
            if rec.student_id and rec.student_id.tag_ids:
                student_groups = ''
                for tag in rec.student_id.tag_ids:
                    if tag.code:
                        student_groups = student_groups + tag.code + ", "
                rec.student_tags = student_groups

                # Handling dashboard tags
                if rec.student_id.tag_ids.filtered(lambda d: d.code in dashboard_tags):
                    if 'NS' in student_groups:
                        rec.student_dashboard_tag = 'NS'
                    elif 'NFS' in student_groups:
                        rec.student_dashboard_tag = 'NFS'
                    elif 'ASC' in student_groups:
                        rec.student_dashboard_tag = 'ASC'
                    elif 'NFSPKR' in student_groups:
                        rec.student_dashboard_tag = 'NFSPKR'
                    else:
                        rec.student_dashboard_tag = ''


class AccountInvoiceLine(models.Model):
    _inherit = 'account.move.line'
    _order = "move_id desc,sequence"

    fee_head_id = fields.Many2one('odoocms.fee.head', 'Fee Head')
    fee_category_id = fields.Many2one('odoocms.fee.category', 'Fee Category', related='fee_head_id.category_id', store=True)
    student_id = fields.Many2one('odoocms.student', 'Student', related='move_id.student_id', store=True, ondelete="cascade", index=True)

    term_id = fields.Many2one('odoocms.academic.term', 'Current Term', related='move_id.term_id', store=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester', related='move_id.semester_id', store=True)
    tag = fields.Char('Tag', related='move_id.tag', store=True)

    course_id = fields.Many2one('odoocms.student.course', 'Course')
    course_credit_hours = fields.Float('Course Credit Hours')
    course_gross_fee = fields.Float('Course Gross Fee')

    challan_id = fields.Many2one('odoocms.fee.barcode','Challan Rec')
    challan_no = fields.Char('Challan No', related='challan_id.name', store=True)
    payment_date = fields.Date('Payment Date')
    no_split = fields.Boolean()
    installment = fields.Integer('Installment')
    registration_type = fields.Selection([('main', 'Main'), ('add', 'Add'), ('drop', 'Drop'), ('misc_challan', 'Misc Challan')], string='Registration Type')
    course_id_new = fields.Many2one('odoocms.class.primary', 'Course New Field')
    section_name = fields.Char('Section Name', compute='_compute_section_name', store=True)

    add_drop_no = fields.Char('Add Drop No.')
    add_drop_paid_amount = fields.Float('Amount Paid By Add Drop', help="This Variable will Contain the Amount Adjusted by the Add Drop Course")

    @api.depends('course_id_new', 'course_id_new.section_id')
    def _compute_section_name(self):
        for rec in self:
            rec.section_name = rec.course_id_new.section_id and rec.course_id_new.section_id.name or ''

    def action_challan_entry(self):
        for line in self:
            line.move_id.generate_challan_barcode(line.move_id.student_id)


class AccountInvoiceGroup(models.Model):
    _name = "account.move.group"
    _description = 'Invoice Group'
    _rec_name = 'tag'

    invoice_ids = fields.One2many('account.move', 'invoice_group_id', 'Invoice')
    tag = fields.Char('Tag')
    reference = fields.Char('Reference')
    description = fields.Html('Description')
    date = fields.Date('Date')
    state = fields.Selection([('draft', 'Generated'),
                              ('cancel', 'Cancelled')], default='draft')

    def action_cancel_invoice_group(self):
        for rec in self:
            if rec.invoice_ids:
                if any([inv.payment_state != 'not_paid' for inv in rec.invoice_ids]):
                    for invoice_id in rec.invoice_ids:
                        invoice_id.button_cancel()
                else:
                    raise UserError('Please check that, there are some receipts in payment status.')

            else:
                raise UserError(_('There is no invoice in this Group to Cancel.'))
