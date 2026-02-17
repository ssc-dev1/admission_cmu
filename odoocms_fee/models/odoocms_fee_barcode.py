from odoo import fields, models, api, _
import decimal

import logging
_logger = logging.getLogger(__name__)


def roundhalfdown(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_DOWN
    return float(round(decimal.Decimal(str(n)), decimals))


class OdooCMSFeeBarcode(models.Model):
    _name = 'odoocms.fee.barcode'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _description = 'Fee Challans'

    name = fields.Char(tracking=True)
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today())
    date_due = fields.Date('Due Date', tracking=True)
    date_download = fields.Datetime(string='Download Date')
    date_expiry = fields.Date('Expiry Date', tracking=True)

    model = fields.Char('Model')
    res_id = fields.Integer('Resource')
    label_id = fields.Many2one('account.payment.term.label', 'Label')

    waiver_ids = fields.Many2many('odoocms.fee.waiver', string='Fee Waiver', compute='compute_data', store=True)
    tag_ids = fields.Many2many('odoocms.student.tag', string='Tags.', compute='compute_data', store=True)
    discount_types = fields.Char('Discounts', compute="compute_data", store=True)

    state = fields.Selection([('draft', 'Unpaid'), ('paid', 'Paid'), ('error','Error'), ('cancel', 'Canceled')], 'Status',
        default='draft', readonly=True, states={'draft': [('readonly', False)]}, compute='_get_state', store=True)
    show_on_portal = fields.Boolean('Show on Portal', default=False, tracking=True)

    payment_id = fields.Many2one('odoocms.fee.payment','Payment')
    journal_id = fields.Many2one('account.journal','Bank/Journal',related='payment_id.journal_id', store=True)
    date_payment = fields.Date('Payment Date', related='payment_id.date', store=True)
    date_post = fields.Date('Post Date', related='payment_id.post_date', store=True)

    transaction_id = fields.Char('Transaction ID')
    paid_time = fields.Char('Paid Time')

    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', tracking=True, compute='compute_data', store=True)

    waiver_percentage = fields.Float('Waiver Discount %')
    gross_amount = fields.Float('Gross Amount', compute='_get_amount', store=True, help="Gross Amount of invoices linked to Challan")
    # waiver_amount = fields.Float('Waiver Amount', compute='_get_amount', store=True)
    amount = fields.Float('Net Amount', compute='_get_amount', store=True, help="Total Amount of Challan (Linked Receivable Lines), Plus imposed Late Fee Fine")
    amount_residual = fields.Float('Residual Amount', compute='_get_amount', store=True, help="Residual Amount of Challan (Linked Receivable Lines), Plus imposed Late Fee Fine")
    amount_paid = fields.Float('Paid', related='payment_id.received_amount', store=True, help="Paid Challan Amount")
    adjusted_amount = fields.Float(compute='get_adjusted_amount', help="Adjusted Challan Amount")
    adjusted_fee = fields.Float(compute='get_adjusted_fee', store=True)

    admission_fee = fields.Float('Admission Fee', compute="_get_amount", store=True)
    admission_gross = fields.Float('Admission Gross', compute="_get_amount", store=True)
    admission_discount = fields.Float('Admission Discount', compute="_get_amount", store=True)
    prospectus_fee = fields.Float('Prospectus Fee', compute="_get_amount", store=True)
    entry_test_fee = fields.Float('Entry Test Fee', compute="_get_amount", store=True)
    graduation_fee = fields.Float('Graduation Fee', compute="_get_amount", store=True)
    gross_tuition_fee = fields.Float('Gross Tuition', compute="_get_amount", store=True, help="Gross Tuition Fee of Challan Lines")
    tuition_fee = fields.Float('Tuition Fee', compute="_get_amount", store=True, help="Total Tuition Fee of Challan Lines")
    hostel_fee = fields.Float('Hostel Fee', compute="_get_amount", store=True)
    hostel_security = fields.Float('Hostel Security', compute="_get_amount", store=True)
    degree_fee = fields.Float('Degree Fee', compute="_get_amount", store=True)
    sports_fee = fields.Float('Sports Fee', compute="_get_amount", store=True)
    library_card_fee = fields.Float('Library Card Fee', compute="_get_amount", store=True)
    transport_fee = fields.Float('Transport Fee', compute="_get_amount", store=True)
    misc_fee = fields.Float('Misc Fee', compute="_get_amount", store=True)
    fine_amount = fields.Float('Fine Amount', compute="_get_amount", store=True)
    tax_amount = fields.Float('Tax Amount', compute="_get_amount", store=True)
    # late_fine_amount = fields.Float('Late Fine Charged', compute="_get_amount", store=True)

    line_ids = fields.One2many('account.move.line', 'challan_id', 'Invoice Lines')

    fine_policy_line_id = fields.Many2one('odoocms.challan.fine.policy.line','Fine Policy')
    late_fine = fields.Float('Late Fine', default=0, tracking=True)
    discount = fields.Float('Payment Discount', default=0, tracking=True)
    renewed = fields.Boolean('Renewed',default=False)

    to_be = fields.Boolean('To Be', default=False)

    invoice_remaining_amount = fields.Float(compute='get_invoice_remaining_data')
    invoice_remaining_due_date = fields.Date(compute='get_invoice_remaining_data')
    paid_amount = fields.Float('Paid Fee (To Remove)',compute='get_paid_amount')  # No need of it.
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, related='student_id.company_id', store=True, ondelete='restrict')

    adjusted_gross = fields.Float('Adjusted Gross')
    adjusted_payable = fields.Float('Adjusted Payable')

    _sql_constraints = [
        ('name', 'unique(name)', "Another Challan already exists with this code!"),
    ]

    @api.model
    def create(self, values):
        result = super().create(values)
        if not result.name:
            name = self.env['ir.sequence'].with_company(result.company_id).next_by_code('odoocms.fee.receipt.challan.sequence')
            result.name = name
        return result

    @api.depends('name')
    def compute_data(self):
        for rec in self:
            obj = None
            if rec.name and rec.model and rec.res_id:
                if rec.model == 'account.move.line':
                    invoice_line_id = self.env['account.move.line'].search([('id', '=', rec.res_id)])
                    if invoice_line_id:
                        obj = invoice_line_id.move_id
                        date_due = invoice_line_id.date_maturity

                elif rec.model == 'account.move':
                    invoice_id = self.env['account.move'].search([('barcode', '=', rec.name), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
                    if not invoice_id:
                        invoice_id = self.env['account.move'].search([('name', '=', rec.receipt_number), ('move_type', '=', 'out_invoice'), ('amount_residual', '>', 0)])
                    if invoice_id:
                        obj = invoice_id
                        date_due = invoice_id.invoice_date_due

                if obj:
                    waiver_ids = [(4, waiver.id, None) for waiver in obj.waiver_ids]
                    tag_ids = [(4, tag.id, None) for tag in rec.student_id.tag_ids]
                    discount_types = ''.join(waiver_id.name if waiver_id.name else '' for waiver_id in obj.waiver_ids)
                    rec.write({
                        'term_id': obj.term_id and obj.term_id.id or False,
                        'date_due': date_due,
                        'waiver_ids': waiver_ids,
                        'tag_ids': tag_ids,
                        'discount_types': discount_types,
                    })

    @api.depends('payment_id', 'payment_id.state','amount_residual')
    def _get_state(self):
        for rec in self:
            if rec.state == 'cancel':
                continue
            elif rec.payment_id and rec.payment_id.state == 'done':
                rec.state = 'paid'
            elif rec.payment_id and rec.payment_id.state == 'error':
                rec.state = 'error'
            elif rec.amount_residual == 0:
                rec.state = 'paid'
            else:
                rec.state = 'draft'

    def get_invoice_remaining_data(self):
        for rec in self:
            invoice_ids = rec.line_ids.mapped('move_id')
            move_line_ids = invoice_ids.mapped('line_ids')
            lines = move_line_ids.filtered(lambda line: line.account_id.user_type_id.type in ('receivable', 'payable') and not line.reconciled
                and line.challan_id.id != rec.id)
            if lines:
                invoice_remaining_amount = sum([line.amount_residual for line in lines])
                due_date = lines[0].date_maturity
            else:
                invoice_remaining_amount = 0
                due_date = False

            rec.write({
                'invoice_remaining_amount': invoice_remaining_amount,
                'invoice_remaining_due_date': due_date,
            })

    def roundhalfup(self, n, decimals=0):
        context = decimal.getcontext()
        context.rounding = decimal.ROUND_HALF_UP
        return float(round(decimal.Decimal(str(n)), decimals))

    def get_paid_amount(self):
        for rec in self:
            invoice_ids = rec.line_ids.mapped('move_id')
            move_line_ids = invoice_ids.mapped('line_ids')
            lines = move_line_ids.filtered(lambda l: l.account_internal_type in ('receivable', 'payable'))
            payments = lines.matched_credit_ids.mapped('credit_move_id').filtered(lambda l: l.payment_id and l.payment_id.id != rec.payment_id.payment_id.id)
            paid_amount = sum([payment.credit for payment in payments])
            rec.paid_amount = paid_amount

    @api.depends('amount','amount_residual','amount_paid','state')
    def get_adjusted_fee(self):
        for rec in self:
            adjusted_fee = 0
            if rec.state == 'paid':
                adjusted_fee =  rec.amount - rec.amount_residual - rec.amount_paid
                if adjusted_fee > -1 and adjusted_fee < 1:
                    adjusted_fee = 0

                rec.adjusted_fee = adjusted_fee
                if adjusted_fee != 0:
                    rec.adjusted_gross = rec.gross_tuition_fee - (adjusted_fee*100)/ (100-rec.waiver_percentage) if (100-rec.waiver_percentage) > 0 else 1
                    rec.adjusted_payable = rec.amount - rec.adjusted_fee
                else:
                    rec.adjusted_gross = rec.gross_tuition_fee
                    rec.adjusted_payable = rec.amount

    def get_adjusted_amount(self):
        for rec in self:
            payment_discount_journal = self.env['ir.config_parameter'].sudo().get_param('aarsol.payment_discount_journal', 'Payment Discount')
            journal_id = self.env['account.journal'].search([('name', '=', payment_discount_journal), '|', ('company_id', '=', rec.company_id.id), ('company_id', '=', False)], order='id desc', limit=1)

            move_line_ids = rec.line_ids
            lines = move_line_ids.filtered(lambda l: l.journal_id.id != journal_id.id and l.account_internal_type in ('receivable', 'payable'))
            payments = lines.matched_credit_ids.mapped('credit_move_id').filtered(lambda l: not l.payment_id)
            adjusted_amount = sum([payment.credit for payment in payments])
            rec.adjusted_amount = adjusted_amount

    def get_amount_temp(self):
        for rec in self:
            invoice_ids = rec.line_ids.mapped('move_id')
            invoice_line_ids = invoice_ids.mapped('invoice_line_ids')
            gross_tuition = 0

            for line in invoice_line_ids:
                if line.course_gross_fee == 0 and line.credit > 0:
                    continue
                else:
                    gross_tuition += line.course_gross_fee
            if rec.waiver_percentage == 0:
                rec.gross_tuition_fee = rec.tuition_fee
            elif rec.waiver_percentage > 0 and rec.waiver_percentage < 100:
                rec.gross_tuition_fee = rec.tuition_fee * 100 / (100- rec.waiver_percentage)
            elif rec.waiver_percentage == 100:
                rec.gross_tuition_fee = gross_tuition

    @api.depends('model','renewed','line_ids','line_ids.amount_residual','line_ids.price_total','line_ids.fee_head_id','late_fine','line_ids.move_id.invoice_payment_term_id','line_ids.challan_id')
    def _get_amount(self):
        for rec in self:
            discount = 0
            tuition_fee_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.tuition_fee_head', 'Tuition Fee')
            fee_head = self.env['odoocms.fee.head'].search([('name', '=', tuition_fee_head),'|',('company_id','=',rec.company_id.id),('company_id','=',False)], order='id desc', limit=1)

            amount = sum([line.balance for line in rec.line_ids]) + (rec.late_fine or 0)
            amount_residual = sum([line.amount_residual for line in rec.line_ids]) + (rec.late_fine or 0)

            if not rec.renewed:
                discountable_lines = rec.line_ids.filtered(lambda l: l.move_id.invoice_payment_term_id.discount > 0 and l.label_id.type == 'main')
                if discountable_lines:
                    tuition_fee = 0
                    for line in discountable_lines:
                        tuition_fee = sum(line.move_id.line_ids.filtered(lambda m: m.fee_head_id.id == fee_head.id).mapped('price_subtotal'))
                        # discount += roundhalfdown(line.balance * line.move_id.invoice_payment_term_id.discount / 100)
                    discount = roundhalfdown(tuition_fee * discountable_lines[0].move_id.invoice_payment_term_id.discount / 100)

            if rec.state != 'paid':
                amount_residual -= discount

            invoice_ids = rec.line_ids.mapped('move_id')
            move_line_ids = invoice_ids.mapped('line_ids')
            invoice_line_ids = invoice_ids.mapped('invoice_line_ids')
            challan_ids = move_line_ids.mapped('challan_id')
            other = tuition = late_fine = 0

            gross_amount = 0
            gross_tuition = 0
            for line in invoice_line_ids:
                if line.course_gross_fee == 0 and line.credit > 0:
                    gross_amount += line.price_subtotal
                else:
                    gross_amount += line.course_gross_fee
                    gross_tuition += line.course_gross_fee

            fee_heads = {
                'Admission Fee': 'admission_fee',
                'Graduation Fee': 'graduation_fee',
                'Prospectus Fee': 'prospectus_fee',
                'Entry Test Fee': 'entry_test_fee',
                'Tuition Fee': 'tuition_fee',
                'Degree Fee': 'degree_fee',
                'Sports Fee': 'sports_fee',
                'Library Card Fee': 'library_card_fee',
                'Transport Fee': 'transport_fee',
                'Misc Fee': 'misc_fee',
                'Hostel Fee': 'hostel_fee',
                'Hostel Security': 'hostel_security',
                'Attendance Fine': 'fine_amount',
                'Payable Fine': 'fine_amount',
                'Late Fee Fine': 'fine_amount',
                'Tax': 'tax_amount',
            }

            fee = {
                field: 0 for field in fee_heads.values()
            }
            for fee_category, field in fee_heads.items():
                mapped_fee_head_id = self.env['odoocms.pgc.fee.head.mapping'].search([('name', '=', fee_category)])
                if mapped_fee_head_id:
                    fee_lines = invoice_line_ids.filtered(lambda line: line.fee_head_id.mapped_fee_head.id == mapped_fee_head_id.id)
                    amount_head = sum(fee_lines.mapped('price_total'))
                    fee[field] += amount_head
                    if field == 'admission_fee':
                        fee_line = fee_lines[:1]
                        gross = fee_line.course_gross_fee if fee_line else 0.0
                        discount = fee_line.discount if fee_line else 0.0

                        fee['admission_gross'] = gross
                        fee['admission_discount'] = gross * discount / 100
                    if field == 'tuition_fee':
                        tuition += amount_head
                    elif fee_category == 'Late Fee Fine':
                        late_fine += amount_head
                    else:
                        other += amount_head

            fee_lines = invoice_line_ids.filtered(lambda line: not line.fee_head_id.mapped_fee_head)
            amount_head = sum(fee_lines.mapped('price_total'))
            fee['fine_amount'] += amount_head

            fee['amount_residual'] = amount_residual
            fee['amount'] = amount
            fee['gross_amount'] = gross_amount
            fee['discount'] = discount

            if len(challan_ids) > 1:
                if rec.label_id.type in ('main','admission'):
                    fee['tuition_fee'] = amount - rec.late_fine - other - late_fine
                else:
                    for field in fee_heads.values():
                        fee[field] = 0
                    fee['tuition_fee'] = amount - rec.late_fine - late_fine
                    fee['fine_amount'] = late_fine

            if rec.waiver_percentage == 0:
                fee['gross_tuition_fee'] = fee['tuition_fee']
            if rec.waiver_percentage > 0 and rec.waiver_percentage < 100:
                fee['gross_tuition_fee'] = fee['tuition_fee'] * 100 / (100- rec.waiver_percentage)
            elif rec.waiver_percentage == 100:
                fee['gross_tuition_fee'] = gross_tuition

            rec.sudo().write(fee)

    def print_challan(self):
        context = {
            'ids': self._ids,
            'model': self._name,
        }
        if self.label_id.type == 'other':
            report_action = 'odoocms_fee_ext.action_misc_fee_challan_report'
            context = {}
        elif self.label_id.type == 'admission':
            report_action = 'odoocms_fee_ext.action_report_admission_fee_challan'
            context = {}
        else:
            report_action = 'odoocms_fee_ext.action_report_term_fee_challan'

        # call the report
        return self.env.ref(report_action).report_action(self, data=context)

    def action_challan_installment(self):
        invoice_ids = self.line_ids.mapped('move_id')
        if invoice_ids:
            invoice_form = {
                'domain': [('id', 'in', invoice_ids.ids)],
                'name': _('Student Invoice'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'type': 'ir.actions.act_window',
                'search_view_id': [self.env.ref('account.view_account_move_filter').id, 'search'],
                'views': [[self.env.ref('account.view_move_tree').id, 'list'], [self.env.ref('odoocms_fee.odoocms_receipt_form').id, 'form']],
            }
            return invoice_form

    def renew_with_fine_policy(self):
        today = fields.Date.today()
        for rec in self:
            dom = [
                ('payment_term_id','=',rec.line_ids[0].move_id.invoice_payment_term_id.id),
                ('start_date', '<=', today), ('due_date', '>=', today), ('state', '=', 'confirm'),
                ('term_id', '=', rec.term_id.id), ('label_id', '=', rec.label_id.id),
                ('program_id', '=', rec.program_id.id), ('faculty_id', '=', rec.department_id.id)
            ]
            fine_policy_line = self.env['odoocms.challan.fine.policy.line'].search(dom, order='id desc', limit=1)
            if fine_policy_line:
                rec.write({
                    'fine_policy_line_id': fine_policy_line.id,
                    'late_fine': fine_policy_line.fine_amount,
                    'date_due': fine_policy_line.due_date,
                    'renewed': True
                })

    def cron_extension(self):
        today = fields.Date.today()
        unpaid_expired_ids = self.search([('state','=','draft'),('date_due','>=',today)])
        for challan in unpaid_expired_ids:
            challan.renew_with_fine_policy()


class OdooCMSFeeBarcodeUnregister(models.Model):
    _name = 'odoocms.fee.barcode.unregister'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Challans Unregister'

    name = fields.Char()
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today())
    student_id = fields.Many2one('odoocms.student','Student', required=True)
    challan_id = fields.Many2one('odoocms.fee.barcode','Challan', required=True, tracking=True)
    amount = fields.Float(related='challan_id.amount',store=True)
    registration_id = fields.Many2one('odoocms.course.registration')
    state = fields.Selection([('draft','Draft'),('done','Unregistered'),('cancel','Cancelled')], 'Status', default='draft')
    note = fields.Char('Notes')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, values):
        result = super().create(values)
        result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.barcode.unregister.sequence')
        return result

    def unregister_payment(self):
        payment_id = self.challan_id.payment_id
        if payment_id:
            account_payment_id = payment_id.payment_id
            if account_payment_id:
                invoice_ids = account_payment_id.reconciled_invoice_ids

                for invoice_id in invoice_ids:
                    invoice_id.mapped('line_ids').remove_move_reconcile()
                    invoice_id.write({'payment_state': 'not_paid', 'payment_date': '', 'confirmation_date': ''})

                account_payment_id.sudo().action_draft()
                self._cr.execute("delete from account_move where id='%s'" % account_payment_id.move_id.id)
                self._cr.execute("delete from account_payment where id='%s'" % account_payment_id.id)

            fee_payment_register = payment_id.payment_register_id
            fee_payment_register.total_receipts = fee_payment_register.total_receipts - 1
            fee_payment_register.total_amount = fee_payment_register.total_amount - payment_id.amount
            fee_payment_register.total_received_amount = fee_payment_register.total_received_amount - payment_id.received_amount

            payment_id.write({'state': 'draft'})
            payment_id.sudo().unlink()

        if self.registration_id:
            for line in self.registration_id.line_ids:
                line.student_course_id.unlink()
                line.state = 'submit'
            self.registration_id.state = 'submit'

        self.challan_id.write({
            'state': 'draft'
        })
        self.state = 'done'


class OdooCMSFeeBarcodeMerge(models.Model):
    _name = 'odoocms.fee.barcode.merge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Challans Marge'

    name = fields.Char()
    date = fields.Date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]}, default=fields.Date.today())
    student_id = fields.Many2one('odoocms.student','Student', required=True)
    challan_id = fields.Many2one('odoocms.fee.barcode','Challan', required=True, tracking=True)
    challan_id2 = fields.Many2one('odoocms.fee.barcode','Merge In', required=True, tracking=True)
    registration_id = fields.Many2one('odoocms.course.registration')
    state = fields.Selection([('draft','Draft'),('post','Posted'),('cancel','Cancelled')], 'Status', default='draft')
    note = fields.Char('Notes')
    company_id = fields.Many2one('res.company', string='Company', index=True, related='student_id.company_id', store=True)

    @api.model
    def create(self, values):
        result = super().create(values)
        result.name = self.env['ir.sequence'].with_company(result.company_id).next_by_code('odoocms.fee.barcode.merge.sequence')
        return result

    def post_merge(self):
        for rec in self:
            for line in rec.challan_id.line_ids:
                line.challan_id = rec.challan_id2.id

            rec.challan_id.write({
                'show_on_portal': False,
                'state': 'cancel'
            })

            if rec.registration_id:
                rec.registration_id.action_approve()
            rec.state = 'post'

    def post_unmerge(self):
        for rec in self:
            if rec.challan_id2 != 'paid':
                for line in rec.challan_id2.line_ids:
                    if line.label_id.id != 1:
                        line.challan_id = rec.challan_id.id

                rec.challan_id.write({
                    'show_on_portal': False,
                    'state': 'draft'
                })
                rec.challan_id2.write({
                    'show_on_portal': True,
                    'state': 'draft'
                })
                rec.write({
                    'state': 'cancel'
                })
