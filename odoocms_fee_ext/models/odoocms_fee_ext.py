# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, AccessError
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import formatLang, format_date, get_lang
from odoo.tools import float_compare, date_utils, email_split, email_re
from collections import defaultdict
import math


class OdooCMSBatch(models.Model):
    _inherit = 'odoocms.batch'

    per_fee_type = fields.Selection([('per_credit_hour','Per Credit Hour'),('per_contact_hour','Per Contact Hour'),('per_course','Per Course')],
        'Fee Type', default='per_credit_hour')
    per_credit_hour_fee = fields.Float('Per Credit Hour Fee', tracking=True)
    # per_contact_hour_fee = fields.Float('Per Contact Hour Fee', tracking=True)
    # per_course_fee = fields.Float('Per Course Fee', tracking=True)

    admission_fee = fields.Float('Admission Fee', tracking=True)
    batch_tuition_structure_head = fields.Many2one('odoocms.fee.structure.head', 'Tuition Structure Head', tracking=True)
    admission_tuition_structure_head = fields.Many2one('odoocms.fee.structure.head', 'Admission Structure Head', tracking=True)

    def action_create_structure_head(self):
        for rec in self:
            # ***** First Check if, Fee Structure Record for that Batch already exists *****#
            # ('session_id', '=', rec.session_id.id), , ('career_id', '=', rec.career_id.id)
            if not rec.fee_structure_id:
                domain = [('batch_id', '=', rec.id)]
                fee_structure = self.env['odoocms.fee.structure'].search(domain)
                if not fee_structure:
                    fee_structure = rec.action_create_fee_structure()

                rec.fee_structure_id = fee_structure.id
                fee_structure.state = 'lock'

            if rec.per_fee_type == 'per_credit_hour' and rec.per_credit_hour_fee <= 0:
                raise UserError(_('Per Credit Hour Fee should be a Positive Number.'))
            # elif rec.per_fee_type == 'per_contact_hour' and rec.per_contact_hour_fee <= 0:
            #     raise UserError(_('Per Contact Hour Fee should be a Positive Number.'))
            # elif rec.per_fee_type == 'per_course' and rec.per_course_fee <= 0:
            #     raise UserError(_('Per Course Fee should be a Positive Number.'))

            if rec.admission_fee <= 0:
                raise UserError(_('Admission Fee should be a Positive Number.'))

            if rec.per_credit_hour_fee > 0:
                new_rec = rec.create_fee_structure_head(type='tuition')
                if new_rec:
                    new_rec.fee_structure_id = rec.fee_structure_id.id
                    rec.fee_structure_id.write({'head_ids': [(4, new_rec.id, None)]})

            if rec.admission_fee > 0:
                new_rec = rec.create_fee_structure_head(type='admission')
                if new_rec:
                    new_rec.fee_structure_id = rec.fee_structure_id.id
                    rec.fee_structure_id.write({'head_ids': [(4, new_rec.id, None)]})

    def action_create_fee_structure(self):
        journal_id = self.env['account.journal'].search([('name', '=', 'Customer Invoices'),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='id', limit=1)
        if not journal_id:
            self.env['account.journal'].search([('type', '=', 'sale'),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='id', limit=1)
        if not journal_id:
            raise UserError(_('Please First Define the Accounting Journal.'))

        data_values = {
            'name': self.name + "  Fee Structure",
            'session_id': self.session_id.id,
            'batch_id': self.id,
            'career_id': self.career_id and self.career_id.id or False,
            'journal_id': journal_id.id,
            'current': True,
            'effective_date': fields.Date.today() + relativedelta(day=1),
            'date_start': fields.Date.today() + relativedelta(day=1),
            'date_end': fields.Date.today() + relativedelta(years=+2, day=31),
        }
        fee_structure = self.env['odoocms.fee.structure'].sudo().create(data_values)
        return fee_structure

    def create_fee_structure_head(self, type=False):
        for rec in self:
            lines = []
            if type:
                if type == 'tuition':
                    tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
                    domain = ['|',('code', '=', 'TF'),('name', '=', tuition_fee_head),'|',('company_id','=',rec.company_id.id),('company_id','=',False)]
                    fee_category = self.env['odoocms.fee.category'].search(domain)
                    if not fee_category:
                        raise UserError(_('Please define the Tuition Fee Category in the System'))

                    # ***** Check if Structure Head Already Exist ***** #
                    domain = [('reference', '=', rec.name + " Tuition Fee"),'|',('company_id','=',rec.company_id.id),('company_id','=',False)]
                    record_already_exist = self.env['odoocms.fee.structure.head'].search(domain)
                    if record_already_exist:
                        if record_already_exist and record_already_exist.line_ids:
                            record_already_exist.line_ids[0].amount = rec.per_credit_hour_fee
                            record_already_exist.line_ids[0].per_fee_type = rec.per_fee_type
                        continue

                    domain = [('reference', '=', rec.name),('category_id.code','=','TF'),'|',('company_id','=',rec.company_id.id),('company_id','=',False)]
                    record_already_exist = self.env['odoocms.fee.structure.head'].search(domain)
                    if record_already_exist:
                        if record_already_exist and record_already_exist.line_ids:
                            record_already_exist.line_ids[0].amount = rec.per_credit_hour_fee
                            record_already_exist.line_ids[0].per_fee_type = rec.per_fee_type
                        continue

                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', tuition_fee_head),'|',('company_id','=',rec.company_id.id),('company_id','=',False)])
                    if not fee_head:
                        raise UserError(_('Please define the Tuition Fee Head in the System'))

                    dom_rule = "[['batch_id.code','='," + "'" + rec.code + "'" + "]]"

                    fee_structure_line_data = {
                        'sequence': 10,
                        'name': rec.name + " Tuition Fee",
                        'per_fee_type': self.per_fee_type,
                        'amount': rec.per_credit_hour_fee,
                        'domain': dom_rule,
                        'current': True,
                    }
                    lines.append((0, 0, fee_structure_line_data))

                    fee_structure_head_data = {
                        'sequence': 10,
                        'category_id': fee_category.id,
                        'fee_head_id': fee_head.id,
                        'payment_type': fee_head.payment_type,
                        'fee_description': fee_head.description_sale,
                        'current': True,
                        'effective_date': fields.Date.today(),
                        'reference': rec.name + " Tuition Fee",
                        'line_ids': lines,
                    }
                    new_tuition_structure_head = self.env['odoocms.fee.structure.head'].create(fee_structure_head_data)
                    rec.batch_tuition_structure_head = new_tuition_structure_head.id
                    return new_tuition_structure_head

                if type == 'admission':
                    domain = ['|', ('code', '=', 'AF'), ('name', 'in', ('Admission Fee', '​Admission & Registration Fee')), '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)]
                    fee_category = self.env['odoocms.fee.category'].search(domain)
                    if not fee_category:
                        raise UserError(_('Please define the Admission Fee Category in the System'))

                    # ***** Check if Structure Head Already Exist ***** #
                    domain = [('reference', '=', rec.name + " Admission Fee"), '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)]
                    record_already_exist = self.env['odoocms.fee.structure.head'].search(domain)
                    if record_already_exist:
                        if record_already_exist and record_already_exist.line_ids:
                            record_already_exist.line_ids[0].amount = rec.admission_fee
                        continue

                    domain = [('reference', '=', rec.name), ('category_id.code', '=', 'AF'), '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)]
                    record_already_exist = self.env['odoocms.fee.structure.head'].search(domain)
                    if record_already_exist:
                        if record_already_exist and record_already_exist.line_ids:
                            record_already_exist.line_ids[0].amount = rec.admission_fee
                        continue

                    fee_head = self.env['odoocms.fee.head'].search([('name', '=', 'Admission Fee'), '|', ('company_id', '=', self.env.company.id), ('company_id', '=', False)])
                    if not fee_head:
                        raise UserError(_('Please define the Admission Fee Head in the System'))

                    dom_rule = "[['batch_id.code','='," + "'" + rec.code + "'" + "]]"
                    fee_structure_line_data = {
                        'sequence': 10,
                        'name': rec.name + " Admission Fee",
                        'amount': rec.admission_fee,
                        'domain': dom_rule,
                        'current': True,
                    }
                    lines.append((0, 0, fee_structure_line_data))

                    fee_structure_head_data = {
                        'sequence': 10,
                        'category_id': fee_category.id,
                        'fee_head_id': fee_head.id,
                        'payment_type': fee_head.payment_type,
                        'fee_description': fee_head.description_sale,
                        'current': True,
                        'effective_date': fields.Date.today(),
                        'reference': rec.name + " Admission Fee",
                        'line_ids': lines,
                    }
                    new_admission_structure_head = self.env['odoocms.fee.structure.head'].create(fee_structure_head_data)
                    rec.admission_tuition_structure_head = new_admission_structure_head.id
                    return new_admission_structure_head


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    first_installment = fields.Boolean('First Installment', default=False)
    second_installment = fields.Boolean('Second Installment', default=False)
    scholarship_continue_policy_id = fields.Many2one('odoocms.scholarship.continue.policy', 'Scholarship Policy')
    scholarship_continue_policy_line_id = fields.Many2one('odoocms.scholarship.continue.policy.line', 'Scholarship Policy Line')

    old_challan_no = fields.Char('Old Challan No', tracking=True, index=True, copy=False)
    installment_no = fields.Char('Installment No')
    transaction_id = fields.Char('Transaction ID')
    online_vendor = fields.Char('Online Vendor')
    old_challan_type = fields.Char('Challan Old Type')
    expiry_date = fields.Date('Expiry Date')
    paid_time = fields.Char('Paid Time')
    confirmation_date = fields.Date('Confirmation Date')

    def get_previously_paid_invoice(self):
        adjustment_amt = 0
        for line in self.line_ids:
            if line.name and "Adjustment" in line.name:
                adjustment_amt += line.price_subtotal
        return adjustment_amt

    def get_adjusted_amount(self):
        lines = self.line_ids.filtered(lambda l: l.account_internal_type in ('receivable', 'payable'))
        payments = lines.matched_credit_ids.mapped('credit_move_id').filtered(lambda l: not l.payment_id)
        amount_adjusted = sum([payment.credit for payment in payments])
        return amount_adjusted

    def get_paid_amount(self):
        lines = self.line_ids.filtered(lambda l: l.account_internal_type in ('receivable', 'payable'))
        payments = lines.matched_credit_ids.mapped('credit_move_id').filtered(lambda l: l.payment_id)
        amount_paid = sum([payment.credit for payment in payments])
        return amount_paid

    def get_installment_amount(self):
        installment_amount = 0
        # installment_amount = self.back_invoice.tuition_fee or self.back_invoice.amount_total
        add_drop_recs = self.env['account.move'].sudo().search([
            ('student_id', '=', self.student_id.id),
            ('term_id', '=', self.term_id.id),
            ('payment_state', 'in', ('in_payment', 'paid'))
        ])
        if add_drop_recs:
            installment_amount += sum(add_drop_rec.tuition_fee for add_drop_rec in add_drop_recs)
        return installment_amount

    # Method by Sarfraz
    def action_check_fine_policy(self):
        pass

    # Inherited to remove 2 checks, one by Sarfraz and other by Farooq" #
    def _post(self, soft=True):
        """Post/Validate the documents.

        Posting the documents will give it a number, and check that the document is complete
        (some fields might not be required if not posted but are required otherwise).
        If the journal is locked with a hash table, it will be impossible to change  some fields afterwards.

        :param soft (bool): if True, future documents are not immediately posted,
            but are set to be auto posted automatically at the set accounting date.
            Nothing will be performed on those documents before the accounting date.
        :return Model<account.move>: the documents that have been posted
        """
        if soft:
            future_moves = self.filtered(lambda move: move.date > fields.Date.context_today(self))
            future_moves.auto_post = True
            for move in future_moves:
                msg = _('This move will be posted at the accounting date: %(date)s', date=format_date(self.env, move.date))
                move.message_post(body=msg)
            to_post = self - future_moves
        else:
            to_post = self

        # `user_has_group` won't be bypassed by `sudo()` since it doesn't change the user anymore.
        if not self.env.su and not self.env.user.has_group('account.group_account_invoice'):
            raise AccessError(_("You don't have the access rights to post an invoice."))
        for move in to_post:
            if move.partner_bank_id and not move.partner_bank_id.active:
                raise UserError(_("The recipient bank account link to this invoice is archived.\nSo you cannot confirm the invoice."))
            if move.state == 'posted':
                raise UserError(_('The entry %s (id %s) is already posted.') % (move.name, move.id))

            # Remarked this check by Sarfraz
            # if not move.line_ids.filtered(lambda line: not line.display_type):
            #     raise UserError(_('You need to add a line before posting.'))
            if move.auto_post and move.date > fields.Date.context_today(self):
                date_msg = move.date.strftime(get_lang(self.env).date_format)
                raise UserError(_("This move is configured to be auto-posted on %s", date_msg))

            if not move.journal_id.active:
                raise UserError(_("You cannot post an entry in an archived journal (%(journal)s)", journal=move.journal_id.display_name))

            if not move.partner_id:
                if move.is_sale_document():
                    raise UserError(_("The field 'Customer' is required, please complete it to validate the Customer Invoice."))
                elif move.is_purchase_document():
                    raise UserError(_("The field 'Vendor' is required, please complete it to validate the Vendor Bill."))

            # Remarked this check by Farooq
            # if move.is_invoice(include_receipts=True) and float_compare(move.amount_total, 0.0, precision_rounding=move.currency_id.rounding) < 0:
            #     for line in move.line_ids:
            #         line.quantity = -line.quantity
            #     move.move_type = 'out_refund'
            #     # raise UserError(_("You cannot validate an invoice with a negative total amount. You should create a credit note instead. Use the action menu to transform it into a credit note or refund."))

            if move.display_inactive_currency_warning:
                raise UserError(_("You cannot validate an invoice with an inactive currency: %s", move.currency_id.name))

            if move.line_ids.account_id.filtered(lambda account: account.deprecated):
                raise UserError(_("A line of this move is using a deprecated account, you cannot post it."))

            # Handle case when the invoice_date is not set. In that case, the invoice_date is set at today and then,
            # lines are recomputed accordingly.
            # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
            # environment.
            if not move.invoice_date:
                if move.is_sale_document(include_receipts=True):
                    move.invoice_date = fields.Date.context_today(self)
                    move.with_context(check_move_validity=False)._onchange_invoice_date()
                elif move.is_purchase_document(include_receipts=True):
                    raise UserError(_("The Bill/Refund date is required to validate this document."))

            # When the accounting date is prior to a lock date, change it automatically upon posting.
            # /!\ 'check_move_validity' must be there since the dynamic lines will be recomputed outside the 'onchange'
            # environment.
            affects_tax_report = move._affect_tax_report()
            lock_dates = move._get_violated_lock_dates(move.date, affects_tax_report)
            if lock_dates:
                move.date = move._get_accounting_date(move.invoice_date or move.date, affects_tax_report)
                if move.move_type and move.move_type != 'entry':
                    move.with_context(check_move_validity=False)._onchange_currency()

        # Create the analytic lines in batch is faster as it leads to less cache invalidation.
        to_post.mapped('line_ids').create_analytic_lines()
        for move in to_post:
            # Fix inconsistencies that may occure if the OCR has been editing the invoice at the same time of a user. We force the
            # partner on the lines to be the same as the one on the move, because that's the only one the user can see/edit.
            wrong_lines = move.is_invoice() and move.line_ids.filtered(lambda aml: aml.partner_id != move.commercial_partner_id and not aml.display_type)
            if wrong_lines:
                wrong_lines.write({'partner_id': move.commercial_partner_id.id})

        to_post.write({
            'state': 'posted',
            'posted_before': True,
        })

        for move in to_post:
            move.message_subscribe([p.id for p in [move.partner_id] if p not in move.sudo().message_partner_ids])

            # Compute 'ref' for 'out_invoice'.
            # if move._auto_compute_invoice_reference():
            #     to_write = {
            #         'payment_reference': move._get_invoice_computed_reference(),
            #         'line_ids': []
            #     }
            #     for line in move.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable')):
            #         to_write['line_ids'].append((1, line.id, {'name': to_write['payment_reference']}))
            #     move.write(to_write)

        for move in to_post:
            if move.is_sale_document() \
                    and move.journal_id.sale_activity_type_id \
                    and (move.journal_id.sale_activity_user_id or move.invoice_user_id).id not in (self.env.ref('base.user_root').id, False):
                move.activity_schedule(
                    date_deadline=min((date for date in move.line_ids.mapped('date_maturity') if date), default=move.date),
                    activity_type_id=move.journal_id.sale_activity_type_id.id,
                    summary=move.journal_id.sale_activity_note,
                    user_id=move.journal_id.sale_activity_user_id.id or move.invoice_user_id.id,
                )

        customer_count, supplier_count = defaultdict(int), defaultdict(int)
        for move in to_post:
            if move.is_sale_document():
                customer_count[move.partner_id] += 1
            elif move.is_purchase_document():
                supplier_count[move.partner_id] += 1
        for partner, count in customer_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('customer_rank', count)
        for partner, count in supplier_count.items():
            (partner | partner.commercial_partner_id)._increase_rank('supplier_rank', count)

        # Trigger action for paid invoices in amount is zero
        to_post.filtered(
            lambda m: m.is_invoice(include_receipts=True) and m.currency_id.is_zero(m.amount_total)
        ).action_invoice_paid()

        # Force balance check since nothing prevents another module to create an incorrect entry.
        # This is performed at the very end to avoid flushing fields before the whole processing.
        to_post._check_balanced()
        return to_post

    def get_invoice_remaining_amount(self, challan_id):
        lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable') and not line.reconciled
            and line.challan_id.id != challan_id)
        amount = sum([line.amount_residual for line in lines])
        return amount

    # ***** (02-03-2023) This Function is Called from Challan Print Report****#
    def get_challan_installment_due_date(self):
        next_line = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable') and line.installment == 2)
        return next_line and next_line[0].date_maturity.strftime('%d-%b-%Y') or ''
        # return self.forward_invoice and self.forward_invoice.invoice_date_due and self.forward_invoice.invoice_date_due.strftime('%d-%b-%Y') or ''

    # ***** (25-12-2022) This Function is Called from Challan Print Report****#
    def get_challan_tax_amount(self):
        amt = 0
        lines = self.line_ids.filtered(lambda a: a.fee_head_id.name in ('Advance Tax', 'Tax', 'Taxes'))
        for line in lines:
            amt += line.price_unit
        return amt

    # ***** (25-12-2022) This Function is Called from Challan Print Report****#
    def get_challan_fine_amount(self):
        amt = 0
        # lines = self.line_ids.filtered(lambda l: "Fine" in l.name)
        lines = self.line_ids.filtered(lambda l: l.fee_category_id.name == 'Fine')
        for line in lines:
            amt += line.price_unit
        return amt

    # ***** (03-03-2023) This Function is Called from Challan Print Report****#
    def get_challan_added_lines(self):
        course_ids = self.line_ids.filtered(lambda a: a.registration_type in ('main', 'add')).mapped('course_id_new').mapped('course_id')
        drop_courses = self.env['account.move.line'].sudo().search([('move_id.student_id', '=', self.student_id.id),
                                                                    ('move_id.term_id', '=', self.term_id.id),
                                                                    ('move_id.challan_type', '=', 'add_drop'),
                                                                    ('registration_type', '=', 'drop')]).mapped('course_id_new').mapped('course_id')

        course_ids = course_ids + drop_courses
        lines = self.env['account.move.line'].sudo().search([('move_id.student_id', '=', self.student_id.id),
                                                             ('move_id.term_id', '=', self.term_id.id),
                                                             ('move_id.challan_type', '=', 'add_drop'),
                                                             ('registration_type', '=', 'add'),
                                                             ('course_id_new.course_id', 'not in', course_ids.ids),
                                                             ('move_id.payment_state', 'in', ('in_payment', 'paid'))])
        return lines

    # ***** (03-04-2023) This Function is Called from Challan Print Report****#
    def get_student_pga(self):
        pga = ''
        student_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', self.student_id.id), ('state', '=', 'done')], order='number desc', limit=1)
        if student_term:
            pga = student_term.sgpa
        return pga


    # ==================================================#
    # This Will be used in Adjust in Second installment #
    # ================================================= #
    # Button For Adjust in Second Installment
    def action_merge_in_second_installment(self):
        added_courses_total_amount = 0
        second_installment = self.env['account.move'].search([('student_id', '=', self.student_id.id),
                                                              ('term_id', '=', self.term_id.id),
                                                              ('challan_type', '=', '2nd_challan'),
                                                              ('id', '!=', self.id)
                                                              ])
        if not second_installment:
            raise UserError(_('Second Installment Not Found in the System'))
        second_installment_receivable_line = second_installment.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
        add_drop_inv_receivable_line = self.line_ids.filtered(lambda l: l.account_id.user_type_id.name == 'Receivable')
        added_courses_mvl = self.line_ids.filtered(lambda ln: ln.registration_type == 'add')
        if not added_courses_mvl:
            raise (_('No Added Course Found'))

        if added_courses_mvl:
            i = 0
            dropped_courses = self.line_ids.filtered(lambda ln: ln.registration_type == 'drop' and not ln.price_subtotal == 0).sorted(key="course_credit_hours", reverse=True)
            for added_course_mvl in added_courses_mvl.sorted(key="course_credit_hours", reverse=True):
                if dropped_courses and len(dropped_courses) >= i + 1:
                    dropped_course = dropped_courses[i]
                    if added_course_mvl.course_credit_hours >= dropped_course.course_credit_hours:
                        amt = dropped_course.debit
                        added_courses_total_amount += (added_course_mvl.credit - dropped_course.debit)
                        i += 1
                    else:
                        amt = 0
                        added_courses_total_amount += added_course_mvl.credit
                    amt2 = 0

                    # Update Dropped Course Line
                    self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s,debit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                        , (amt2, amt2, amt2, -amt2, -amt2, amt2, amt2, dropped_course.id))
                    # Update Added Course Line
                    self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                        , (amt2, amt2, -amt2, -amt2, amt2, amt2, added_course_mvl.id))

                    # If Same Course Line Available in second installment
                    if added_course_mvl.course_id_new and self.env['account.move.line'].search([('move_id', '=', second_installment.id), ('course_id_new', '=', added_course_mvl.course_id_new.id)]):
                        second_installment_added_course_same_line = self.env['account.move.line'].search([('move_id', '=', second_installment.id), ('course_id_new', '=', added_course_mvl.course_id_new.id)])
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                            , (added_course_mvl.credit, added_course_mvl.credit, -added_course_mvl.credit, -added_course_mvl.credit, added_course_mvl.credit, added_course_mvl.credit, second_installment_added_course_same_line.id))

                    else:
                        ret_ln = self.action_mvl_adjust_in_2nd_credit(added_course_mvl, second_installment, amt if amt > 0 else added_course_mvl.credit)

                else:
                    if added_course_mvl.price_subtotal >= 0:
                        amt = 0
                        added_courses_total_amount += added_course_mvl.credit
                        self.env.cr.execute("update account_move_line set price_unit = %s, credit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                            , (amt, amt, -amt, -amt, amt, amt, added_course_mvl.id))
                        ret_ln = self.action_mvl_adjust_in_2nd_credit(added_course_mvl, second_installment, added_course_mvl.credit)
                    elif added_course_mvl.price_subtotal < 0:
                        amt = 0
                        added_courses_total_amount -= added_course_mvl.debit
                        self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                            , (amt, amt, amt, amt, amt, amt, added_course_mvl.id))
                        ret_ln = self.action_mvl_adjust_in_2nd_debit(added_course_mvl, second_installment, added_course_mvl.debit)

            debit_amount = add_drop_inv_receivable_line.debit - added_courses_total_amount
            if debit_amount < 0:
                debit_amount = 0

            # ***** Update add drop challan ******#
            self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s where id=%s \n"
                                , (-debit_amount, debit_amount, debit_amount, debit_amount, -debit_amount, -debit_amount, add_drop_inv_receivable_line.id))
            # Invoice Total Update
            self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                , (debit_amount, debit_amount, debit_amount, debit_amount, debit_amount, debit_amount, add_drop_inv_receivable_line.move_id.id))
            ledger_id = self.env['odoocms.student.ledger'].search([('invoice_id', '=', add_drop_inv_receivable_line.move_id.id)], order='id desc', limit=1)
            ledger_id.credit = debit_amount

            # ***** Update 2nd Installment *****#
            second_debit_amount = second_installment_receivable_line.debit + added_courses_total_amount
            self.env.cr.execute("update account_move_line set price_unit = %s, debit=%s, balance=%s,amount_currency=%s, price_subtotal=%s, price_total=%s,amount_residual=%s,amount_residual_currency=%s where id=%s \n"
                                , (-second_debit_amount, second_debit_amount, second_debit_amount, second_debit_amount, -second_debit_amount, -second_debit_amount, second_debit_amount, second_debit_amount, second_installment_receivable_line.id))

            # ***** Invoice Total Update *****#
            self.env.cr.execute("update account_move set amount_untaxed=%s,amount_total = %s,amount_residual=%s, amount_untaxed_signed=%s, amount_total_signed=%s, amount_residual_signed=%s where id=%s \n"
                                , (second_debit_amount, second_debit_amount, second_debit_amount, second_debit_amount, second_debit_amount, second_debit_amount, second_installment_receivable_line.move_id.id))

            ledger_id = self.env['odoocms.student.ledger'].search([('invoice_id', '=', second_installment_receivable_line.move_id.id)], order='id desc', limit=1)
            ledger_id.credit = second_debit_amount
            self._cr.commit()
            # update Invoice
            if self.amount_total == 0:
                self.write({'state': 'posted', 'payment_state': 'paid', 'narration': 'Adjust in Second Installment'})
                if self.registration_id:
                    self.registration_id.sudo().action_approve()

    def action_mvl_adjust_in_2nd_credit(self, mvl, second_installment, amt):
        credit_amt = amt
        # add_drop_no_txt = (mvl.registration_type.capitalize() + "->" + mvl.registration_id.add_drop_request_no_txt if mvl.registration_id else '')
        add_drop_no_txt = f"{mvl.registration_type.capitalize()}->{mvl.registration_id.add_drop_request_no_txt}" if mvl.registration_id else ''
        new_mvl = self.env.cr.execute("""insert into account_move_line 
                                            (
                                                account_id,partner_id,fee_head_id,is_add_drop_line,name,move_id,currency_id,product_id,quantity,price_unit,
                                                price_total,price_subtotal,balance,amount_currency,course_gross_fee,course_credit_hours,course_id_new,credit,registration_id,registration_line_id,
                                                move_name,date,parent_state,journal_id,company_id,company_currency_id,account_root_id,sequence,debit,discount,
                                                reconciled,blocked,amount_residual,amount_residual_currency,exclude_from_invoice_tab,fee_category_id,student_id,career_id,program_id,session_id,
                                                institute_id,campus_id,term_id,create_uid,create_date,write_date,write_uid,registration_type,add_drop_no
                                            ) 
                                        VALUES 
                                            (
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                %s,%s,%s,%s,%s,%s,%s,%s,%s
                                            ) 
                                        RETURNING id """,
                                      (
                                          mvl.account_id.id, mvl.partner_id and mvl.partner_id.id or False, mvl.fee_head_id.id, True, mvl.name, second_installment.id, mvl.currency_id.id, mvl.product_id.id, 1.00, credit_amt,
                                          credit_amt, credit_amt, -credit_amt, -credit_amt, mvl.course_gross_fee, mvl.course_credit_hours, mvl.course_id_new.id, credit_amt, mvl.registration_id.id, mvl.registration_line_id.id,
                                          mvl.move_name, mvl.date, mvl.parent_state, mvl.journal_id.id, mvl.company_id.id, mvl.company_currency_id.id, mvl.account_root_id.id, 250, 0.00, mvl.discount,
                                          mvl.reconciled, mvl.blocked, mvl.amount_residual, mvl.amount_residual_currency, mvl.exclude_from_invoice_tab, mvl.fee_category_id.id, mvl.student_id.id, mvl.career_id.id, mvl.program_id.id, mvl.session_id.id,
                                          mvl.institute_id.id, mvl.campus_id.id, mvl.term_id.id, self.env.user.id, fields.Datetime.now(), fields.Datetime.now(), self.env.user.id, mvl.registration_type, add_drop_no_txt
                                      )
                                      )
        return new_mvl

    def action_mvl_adjust_in_2nd_debit(self, mvl, second_installment, amt):
        debit_amt = amt
        new_mvl = self.env.cr.execute("""insert into account_move_line 
                                                    (account_id,partner_id,fee_head_id,is_add_drop_line,name,move_id,currency_id,
                                                    product_id,quantity,price_unit,price_total,price_subtotal,balance,amount_currency,
                                                    course_gross_fee,course_credit_hours,course_id_new,credit,registration_id,registration_line_id,move_name,
                                                    date,parent_state,journal_id,company_id,company_currency_id,account_root_id,sequence,
                                                    debit,discount,reconciled,blocked,amount_residual,amount_residual_currency,
                                                    exclude_from_invoice_tab,fee_category_id,student_id,career_id,program_id,session_id,institute_id,
                                                    campus_id,term_id,create_uid,create_date,write_date,write_uid,registration_type,add_drop_no) 
                                                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                                                    %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id """,
                                      (mvl.account_id.id, mvl.partner_id.id, mvl.fee_head_id.id if mvl.fee_head_id else None, True, mvl.name, second_installment.id, mvl.currency_id.id,
                                       mvl.product_id.id if mvl.product_id else None, 1.00, -debit_amt, -debit_amt, -debit_amt, debit_amt, debit_amt,
                                       mvl.course_gross_fee, mvl.course_credit_hours, mvl.course_id_new.id if mvl.course_id_new else None, 0.00, mvl.registration_id.id if mvl.registration_id else None, mvl.registration_line_id.id if mvl.registration_line_id else None, mvl.move_name,
                                       mvl.date, mvl.parent_state, mvl.journal_id.id, mvl.company_id.id, mvl.company_currency_id.id, mvl.account_root_id.id, 250,
                                       debit_amt, mvl.discount, mvl.reconciled, mvl.blocked, 0.00, 0.00,
                                       mvl.exclude_from_invoice_tab, mvl.fee_category_id.id if mvl.fee_category_id else None, mvl.student_id.id, mvl.career_id.id, mvl.program_id.id, mvl.session_id.id, mvl.institute_id.id,
                                       mvl.campus_id.id, mvl.term_id.id, self.env.user.id, fields.Datetime.now(), fields.Datetime.now(), self.env.user.id, mvl.registration_type, (mvl.registration_type.capitalize() + "->" + mvl.registration_id.add_drop_request_no_txt if mvl.registration_id else '')
                                       ))
        return new_mvl


    def int_to_word(self):
        num = int(float(self.installment_no))
        ones = ['Zero', 'One', 'Second', 'Third', 'Fourth', 'Fifth', 'Sixth', 'Seventh', 'Eighth', 'Ninth']
        return ones[num]

    def _recompute_payment_terms_lines(self):
        ''' Compute the dynamic payment term lines of the journal entry.'''
        self.ensure_one()
        self = self.with_company(self.company_id)
        in_draft_mode = self != self._origin
        today = fields.Date.context_today(self)
        self = self.with_company(self.journal_id.company_id)

        def _get_payment_terms_computation_date(self):
            ''' Get the date from invoice that will be used to compute the payment terms.
            :param self:    The current account.move record.
            :return:        A datetime.date object.
            '''
            if self.invoice_payment_term_id:
                return self.invoice_date or today
            else:
                return self.invoice_date_due or self.invoice_date or today

        def _get_payment_terms_account(self, payment_terms_lines):
            ''' Get the account from invoice that will be set as receivable / payable account.
            :param self:                    The current account.move record.
            :param payment_terms_lines:     The current payment terms lines.
            :return:                        An account.account record.
            '''
            if payment_terms_lines:
                # Retrieve account from previous payment terms lines in order to allow the user to set a custom one.
                return payment_terms_lines[0].account_id
            else:
                accounts = {
                    account_type: acc or self.env['account.account'].search([
                        ('company_id', '=', self.company_id.id),
                        ('internal_type', '=', account_type),
                        ('deprecated', '=', False),
                    ], limit=1)
                    for acc, account_type in [(self.partner_id.property_account_payable_id, 'payable'), (self.partner_id.property_account_receivable_id, 'receivable')]}
                account_map = (self.fiscal_position_id or self.env['account.fiscal.position']).map_accounts(accounts)
                if self.is_sale_document(include_receipts=True):
                    return account_map['receivable']
                elif self.is_purchase_document(include_receipts=True):
                    return account_map['payable']

        def _compute_payment_terms(self, date, total_balance, total_amount_currency):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id:
                to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                if self.currency_id == self.company_id.currency_id:
                    # Single-currency.
                    return [(b[0], b[1], b[1]) for b in to_compute]
                else:
                    # Multi-currencies.
                    to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency, date_ref=date, currency=self.currency_id)
                    return [(b[0], b[1], ac[1]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency)]

        def _compute_payment_terms_new(self, date, total_balance, total_amount_currency, total_balance_nosplit,total_amount_currency_nosplit):
            ''' Compute the payment terms.
            :param self:                    The current account.move record.
            :param date:                    The date computed by '_get_payment_terms_computation_date'.
            :param total_balance:           The invoice's total in company's currency.
            :param total_amount_currency:   The invoice's total in invoice's currency.
            :return:                        A list <to_pay_company_currency, to_pay_invoice_currency, due_date>.
            '''
            if self.invoice_payment_term_id and total_balance != 0:
                if self.invoice_payment_term_id.line_ids[0].value == 'percent':
                    if total_balance-total_balance_nosplit == 0:
                        to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                        if self.currency_id == self.company_id.currency_id:
                            # Single-currency.
                            to_compute[0] = (to_compute[0][0], to_compute[0][1], to_compute[0][2])
                            return [(b[0], b[1], b[1], b[2]) for b in to_compute]
                        else:
                            # Multi-currencies.
                            to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency * total_amount_currency_nosplit, date_ref=date, currency=self.currency_id)
                            to_compute_currency[0] = (to_compute_currency[0][0], to_compute_currency[0][1] + total_amount_currency_nosplit, to_compute_currency[0][2])
                            return [(b[0], b[1], ac[1], b[2]) for b, ac in zip(to_compute, to_compute_currency)]
                    else:
                        to_compute = self.invoice_payment_term_id.compute(total_balance-total_balance_nosplit, date_ref=date, currency=self.company_id.currency_id)
                        if self.currency_id == self.company_id.currency_id:
                            # Single-currency.
                            to_compute[0] = (to_compute[0][0],to_compute[0][1] + total_balance_nosplit,to_compute[0][2])
                            return [(b[0], b[1], b[1], b[2]) for b in to_compute]
                        else:
                            # Multi-currencies.
                            to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency*total_amount_currency_nosplit, date_ref=date, currency=self.currency_id)
                            to_compute_currency[0] = (to_compute_currency[0][0], to_compute_currency[0][1] + total_amount_currency_nosplit, to_compute_currency[0][2])
                            return [(b[0], b[1], ac[1], b[2]) for b, ac in zip(to_compute, to_compute_currency)]
                else:
                    to_compute = self.invoice_payment_term_id.compute(total_balance, date_ref=date, currency=self.company_id.currency_id)
                    if self.currency_id == self.company_id.currency_id:
                        # Single-currency.
                        to_compute[0] = (to_compute[0][0], to_compute[0][1], to_compute[0][2])
                        return [(b[0], b[1], b[1], b[2]) for b in to_compute]
                    else:
                        # Multi-currencies.
                        to_compute_currency = self.invoice_payment_term_id.compute(total_amount_currency * total_amount_currency, date_ref=date, currency=self.currency_id)
                        to_compute_currency[0] = (to_compute_currency[0][0], to_compute_currency[0][1], to_compute_currency[0][2])
                        return [(b[0], b[1], ac[1], b[2]) for b, ac in zip(to_compute, to_compute_currency)]
            else:
                return [(fields.Date.to_string(date), total_balance, total_amount_currency,False)]

        def _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute):
            ''' Process the result of the '_compute_payment_terms' method and creates/updates corresponding invoice lines.
            :param self:                    The current account.move record.
            :param existing_terms_lines:    The current payment terms lines.
            :param account:                 The account.account record returned by '_get_payment_terms_account'.
            :param to_compute:              The list returned by '_compute_payment_terms'.
            '''
            # As we try to update existing lines, sort them by due date.
            existing_terms_lines = existing_terms_lines.sorted(lambda line: line.date_maturity or today)
            existing_terms_lines_index = 0

            # Recompute amls: update existing line or create new one for each payment term.
            new_terms_lines = self.env['account.move.line']
            for date_maturity, balance, amount_currency, label_id in to_compute:
                currency = self.journal_id.company_id.currency_id
                if currency and currency.is_zero(balance) and len(to_compute) > 1:
                    continue

                if existing_terms_lines_index < len(existing_terms_lines):
                    # Update existing line.
                    candidate = existing_terms_lines[existing_terms_lines_index]
                    existing_terms_lines_index += 1
                    candidate.update({
                        'date_maturity': date_maturity,
                        'amount_currency': -amount_currency,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'label_id': label_id,
                    })
                else:
                    # Create new line.
                    create_method = in_draft_mode and self.env['account.move.line'].new or self.env['account.move.line'].create
                    candidate = create_method({
                        'name': self.payment_reference or '',
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'quantity': 1.0,
                        'amount_currency': -amount_currency,
                        'date_maturity': date_maturity,
                        'move_id': self.id,
                        'currency_id': self.currency_id.id,
                        'account_id': account.id,
                        'partner_id': self.commercial_partner_id.id,
                        'exclude_from_invoice_tab': True,
                        'label_id': label_id,
                    })
                new_terms_lines += candidate
                if in_draft_mode:
                    candidate.update(candidate._get_fields_onchange_balance(force_computation=True))
            return new_terms_lines

        existing_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable') and not line._origin.reconciled)
        reconciled_terms_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable') and line._origin.reconciled)
        others_lines = self.line_ids.filtered(lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
        others_lines_nosplit = self.line_ids.filtered(lambda line: line.no_split and line.account_id.user_type_id.type not in ('receivable', 'payable'))
        company_currency_id = (self.company_id or self.env.company).currency_id

        total_balance = sum(others_lines.mapped(lambda l: company_currency_id.round(l.balance)))
        total_balance_nosplit = sum(others_lines_nosplit.mapped(lambda l: company_currency_id.round(l.balance)))
        total_amount_currency = sum(others_lines.mapped('amount_currency'))
        total_amount_currency_nosplit = sum(others_lines_nosplit.mapped('amount_currency'))

        if reconciled_terms_lines:
            paid_balance = sum(reconciled_terms_lines.mapped(lambda l: company_currency_id.round(l.balance)))
            total_balance += paid_balance
            total_amount_currency += paid_balance
            total_balance_nosplit = 0
            total_amount_currency_nosplit = 0

        if not others_lines:
            self.line_ids -= existing_terms_lines
            return

        computation_date = _get_payment_terms_computation_date(self)
        account = _get_payment_terms_account(self, existing_terms_lines)
        to_compute = _compute_payment_terms_new(self, computation_date, total_balance, total_amount_currency, total_balance_nosplit, total_amount_currency_nosplit)
        new_terms_lines = _compute_diff_payment_terms_lines(self, existing_terms_lines, account, to_compute)
        # Remove old terms lines that are no longer needed.
        self.line_ids -= existing_terms_lines - new_terms_lines
        if new_terms_lines:
            self.payment_reference = new_terms_lines[-1].name or ''
            self.invoice_date_due = new_terms_lines[-1].date_maturity


class AccountInvoiceLine(models.Model):
    _inherit = "account.move.line"

    registration_id = fields.Many2one('odoocms.course.registration', 'Registration')
    registration_line_id = fields.Many2one('odoocms.course.registration.line', 'Registration Line')
    is_add_drop_line = fields.Boolean('Is Add Drop', default=False)
    dropped_mvl_id = fields.Many2one('account.move.line', 'Dropped Move Line Ref')

    @api.model
    def _get_price_total_and_subtotal_model(self, price_unit, quantity, discount, currency, product, partner, taxes, move_type):
        res = {}

        line_discount_price_unit = (price_unit - self.discount_fixed ) if self.discount_fixed != 0 else price_unit * (1 - (discount / 100.0))
        subtotal = quantity * line_discount_price_unit

        # Compute 'price_total'.
        if taxes:
            taxes_res = taxes._origin.with_context(force_sign=1).compute_all(line_discount_price_unit,
                quantity=quantity, currency=currency, product=product, partner=partner, is_refund=move_type in ('out_refund', 'in_refund'))
            res['price_subtotal'] = math.ceil(taxes_res['total_excluded']) if taxes_res['total_excluded'] > 0 else math.floor(taxes_res['total_excluded'])
            res['price_total'] = math.ceil(taxes_res['total_included']) if taxes_res['total_included'] > 0 else math.floor(taxes_res['total_included'])
        else:
            res['price_total'] = res['price_subtotal'] = math.ceil(subtotal) if subtotal > 0 else math.floor(subtotal)
        # In case of multi currency, round before it's use for computing debit credit
        if currency:
            res = {k: currency.round(v) for k, v in res.items()}
        return res

    def get_move_line_withdraw_repeat_status(self):
        return_status = ''
        withdraw_req = self.env['odoocms.student.course'].sudo().search([('student_id', '=', self.move_id.student_id.id),
                                                                         ('primary_class_id', '=', self.course_id_new.id),
                                                                         ('state', '=', 'withdraw')])
        if withdraw_req:
            return_status = ' (W)'
        else:
            if self.registration_line_id and self.registration_line_id.course_type == 'repeat':
                return_status = ' (R)'
        return return_status

