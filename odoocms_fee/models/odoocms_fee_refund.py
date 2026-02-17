import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdooCMSFeeRefundReason(models.Model):
    _name = 'odoocms.fee.refund.reason'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Fee Refund Reason"

    name = fields.Char('Refund Reason', required=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('lock', 'Locked')
                              ], string='Status', default='draft', tracking=True)

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'


class OdooCMSFeeRefundTypes(models.Model):
    _name = 'odoocms.fee.refund.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Refund Types'

    name = fields.Char('Name', tracking=True)
    code = fields.Char('Code', tracking=True)
    sequence = fields.Integer('Sequence')
    receipt_type = fields.Many2one('odoocms.receipt.type', string='Receipt Type', tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('lock', 'Locked')
                              ], string='Status', default='draft', tracking=True)

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'


class OdooCMSFeeRefundHeads(models.Model):
    _name = 'odoocms.fee.refund.heads'
    _description = 'Fee Refund Security Heads'

    fee_head_id = fields.Many2one('odoocms.fee.head', string='Fee Heads', readonly=True)
    amount = fields.Monetary(string='Amount', readonly=True, default=0.0)
    refund_id = fields.Many2one('odoocms.fee.refund.request', string='Refund')
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, default=lambda self: self.env.company.currency_id.id)


class OdooCMSFeeRefundRequest(models.Model):
    _name = 'odoocms.fee.refund.request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Fee Refund Request'

    READONLY_STATES = {
        'approve': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    student_id = fields.Many2one('odoocms.student', 'Student', states=READONLY_STATES)
    session_id = fields.Many2one('odoocms.academic.session', 'Academic Session', states=READONLY_STATES, compute='_compute_student_info', store=True)
    career_id = fields.Many2one('odoocms.career', 'Career', compute='_compute_student_info', store=True)
    program_id = fields.Many2one('odoocms.program', 'Program', compute='_compute_student_info', store=True)
    batch_id = fields.Many2one('odoocms.batch', compute='_compute_student_info', store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Institute', compute='_compute_student_info', store=True)
    institute_code = fields.Char(string='Institute Code', compute='_compute_student_info', store=True)

    discipline_id = fields.Many2one('odoocms.discipline', 'Discipline', compute='_compute_student_info', store=True)
    campus_id = fields.Many2one('odoocms.campus', 'Campus', compute='_compute_student_info', store=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester', compute='_compute_student_info', store=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', compute='_compute_student_info', store=True)

    date = fields.Date('Request Date', default=fields.Date.today, states=READONLY_STATES, required=True)
    refund_by = fields.Selection([('cash', 'Cash'),
                                  ('bank', 'Bank'),
                                  ('cheque', 'Cheque'),
                                  ('adjustment', 'Adjustment in Next Fee')
                                  ], default='bank', string='Refund Mode', tracking=True)
    reason_id = fields.Many2one('odoocms.fee.refund.reason', 'Refund Reason', required=True)
    refund_line_ids = fields.One2many('odoocms.fee.refund.request.line', 'refund_id', string='Refund Lines')
    description = fields.Text('Description', states=READONLY_STATES, required=True)

    state = fields.Selection([('draft', 'Submitted'),
                              ('approve', 'Approved'),
                              ('reject', 'Rejected'),
                              ('done', 'Done'),
                              ('cancel', 'Canceled')
                              ], default='draft', string="Status", tracking=True)

    refund_type_domain = fields.Char(compute="_compute_refund_type_domain", readonly=True, store=False)
    refund_type = fields.Many2one('odoocms.fee.head', 'Fee Head', required=True, states=READONLY_STATES)

    total_amount = fields.Float('Total Amount', compute='_compute_total_amount', store=True)
    total_refund_amount = fields.Float('Total Refund Amount', compute='_compute_total_refund', store=True)
    student_ledger_id = fields.Many2one('odoocms.student.ledger', 'Ledger Ref', tracking=True)
    student_payment_ledger_id = fields.Many2one('odoocms.student.ledger', 'Payment Ledger Ref', tracking=True)
    payment_journal_id = fields.Many2one('account.journal', 'Payment Journal', tracking=True)
    payment_id = fields.Many2one('account.payment', 'Payment', tracking=True)

    # Added @16-10-2021
    invoice_type = fields.Selection([('semester', 'Semester Fee'),
                                     ('hostel', 'Hostel Fee'),
                                     ('scholarship', 'Scholarship Fee'),
                                     ], default='semester', string='Invoice Type', tracking=True)
    invoice_id = fields.Many2one('account.move', 'Invoice', compute="_get_invoice_id", store=True, readonly=False)
    invoice_term_id = fields.Many2one('odoocms.academic.term', 'Invoice Term', tracking=True)
    refund_invoice_id = fields.Many2one('account.move', 'Refund Invoice')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.depends('student_id')
    def _compute_student_info(self):
        for rec in self:
            if rec.student_id:
                rec.session_id = rec.student_id.session_id and rec.student_id.session_id.id or False
                rec.career_id = rec.student_id.career_id and rec.student_id.career_id.id or False
                rec.program_id = rec.student_id.program_id and rec.student_id.program_id.id or False
                rec.batch_id = rec.student_id.batch_id and rec.student_id.batch_id.id or False
                rec.term_id = rec.student_id.term_id and rec.student_id.term_id.id or False
                rec.semester_id = rec.student_id.semester_id and rec.student_id.semester_id.id or False
                rec.discipline_id = rec.student_id.discipline_id and rec.student_id.discipline_id.id or False
                rec.institute_id = rec.student_id.institute_id and rec.student_id.institute_id.id or False
                rec.institute_code = rec.student_id.institute_id and rec.student_id.institute_id.code or ''
                rec.campus_id = rec.student_id.campus_id and rec.student_id.campus_id.id or False

    @api.model
    def create(self, values):
        if not values.get('name', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.fee.refund.request')
        result = super(OdooCMSFeeRefundRequest, self).create(values)
        return result

    def unlink(self):
        for rec in self:
            if not rec.state=='draft':
                raise UserError(_('Record Status should be in Draft for This Action.'))
        return super(OdooCMSFeeRefundRequest, self).unlink()

    def action_approve_refund(self):
        for rec in self:
            if not rec.refund_line_ids:
                raise UserError(_('No Refund Detail.'))
            # rec.invoice_id.write({
            #     'fee_refund_id': rec.id,
            #     'fee_refund_amount': rec.total_refund_amount
            # })
            rec.state = 'approve'
            rec.refund_line_ids.write({'state': 'approve'})
            if not rec.refund_by=='adjustment':
                if not rec.payment_journal_id:
                    rec.payment_journal_id = 1

            # refundable_fee_heads = self.env['odoocms.fee.head'].search([('refund', '=', True)])
            # Remarked @ 15102021 Sarfraz
            # apply_refund = False
            # if rec.term_id and rec.batch_id and rec.batch_id.can_apply('full_refund', rec.date):
            #     apply_refund = 'full'
            # if not apply_refund and rec.term_id and rec.batch_id and rec.batch_id.can_apply('half_refund', rec.date):
            #     apply_refund = 'half'

            # if apply_refund:
            #     if apply_refund=='full' and rec.refund_line_ids:
            #         for line in rec.refund_line_ids:
            #             line.refund_amount = line.actual_amount
            #     if apply_refund=='half':
            #         for line in rec.refund_line_ids:
            #             line.refund_amount = round(line.actual_amount / 2, 3)
            # else:
            #     for line in rec.refund_line_ids:
            #         line.refund_amount = 0

    def action_refund_paid(self):
        for rec in self:
            if not rec.refund_by=='adjustment':
                refund_invoice_id = rec.action_create_refund_invoice()
                rec.student_ledger_id = rec.create_refund_student_ledger_entry(debit=rec.total_refund_amount, credit=0, description="Student Refund Adjustment To be Paid.", invoice_id=rec.refund_invoice_id)
                if refund_invoice_id:
                    rec.refund_invoice_id = refund_invoice_id.id
                    rec.refund_invoice_id.action_post()
                    rec.create_refund_payment_entry()
                    rec.student_payment_ledger_id = rec.create_refund_student_ledger_entry(debit=0, credit=rec.total_refund_amount, description="Student Refund Adjustment Paid.", invoice_id=rec.refund_invoice_id)

            # If to be Adjust in next invoice
            if rec.refund_by=='adjustment':
                rec.student_ledger_id = rec.create_refund_student_ledger_entry(debit=rec.total_refund_amount, credit=0, description="Student Refund To be Adjustment in Fee", invoice_id=rec.invoice_id)
            rec.state = 'done'
            rec.refund_line_ids.write({'state': 'done'})
            rec.invoice_id.refund_date = fields.Date.today()

    def action_refund_cancel(self):
        for rec in self:
            if rec.refund_line_ids:
                rec.refund_line_ids.write({'state': 'cancel'})
            # if rec.invoice_id.fee_refund_id:
            #     rec.invoice_id.fee_refund_id = False
            #     rec.invoice_id.write({'fee_refund_id': False, 'fee_refund_amount': 0})
            if rec.student_ledger_id:
                rec.student_ledger_id.unlink()
            rec.state = 'cancel'

    def action_turn_to_draft(self):
        for rec in self:
            if rec.refund_line_ids:
                rec.refund_line_ids.write({'state': 'draft'})
            # if rec.invoice_id.fee_refund_id:
            #     rec.invoice_id.write({'fee_refund_id': False, 'fee_refund_amount': rec.total_refund_amount})
            if rec.student_ledger_id:
                rec.student_ledger_id.unlink()
            rec.state = 'draft'

    @api.depends('student_id', 'invoice_type', 'invoice_term_id')
    def _get_invoice_id(self):
        for rec in self:
            fee_receipts = False
            rec.invoice_id = False
            if rec.invoice_type=='scholarship':
                fee_receipts = self.env['account.move'].search(([('student_id', '=', rec.student_id.id),
                                                                 ('term_id', '=', rec.invoice_term_id.id),
                                                                 ('payment_state', 'in', ('in_payment', 'paid')),
                                                                 ('is_scholarship_fee', '=', True),
                                                                 ('move_type', '=', 'out_invoice')]))
            elif rec.invoice_type=='hostel':
                fee_receipts = self.env['account.move'].search(([('student_id', '=', rec.student_id.id),
                                                                 ('term_id', '=', rec.invoice_term_id.id),
                                                                 ('payment_state', 'in', ('in_payment', 'paid')),
                                                                 ('is_hostel_fee', '=', True),
                                                                 ('move_type', '=', 'out_invoice')
                                                                 ]))
            else:
                fee_receipts = self.env['account.move'].search(([('student_id', '=', rec.student_id.id),
                                                                 ('term_id', '=', rec.invoice_term_id.id),
                                                                 ('payment_state', 'in', ('in_payment', 'paid')),
                                                                 ('is_hostel_fee', '=', False),
                                                                 ('is_scholarship_fee', '=', False),
                                                                 ('move_type', '=', 'out_invoice')]))
            if fee_receipts:
                rec.invoice_id = fee_receipts[0].id

    @api.constrains('invoice_id', 'student_id', 'refund_type')
    def duplicate_refund_constrains(self):
        for rec in self:
            if rec.invoice_id and rec.student_id:
                refund_already_exist = self.env['odoocms.fee.refund.request'].search([('student_id', '=', rec.student_id.id),
                                                                                      ('invoice_id', '=', rec.invoice_id.id),
                                                                                      ('refund_type', '=', rec.refund_type.id),
                                                                                      ('state', '!=', 'cancel'),
                                                                                      ('id', '!=', rec.id)])
                if refund_already_exist:
                    raise UserError(_('Duplicate Refund Request are not Allowed. System Found Request %s') % refund_already_exist[0].name)

    @api.onchange('student_id')
    def onchange_student_id(self):
        for rec in self:
            if rec.student_id:
                if rec.invoice_type:
                    rec.invoice_type = 'semester'
                    config_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms.current_term') or 0)
                    if config_term==0:
                        rec.invoice_term_id = rec.student_id.term_id.id
                    else:
                        rec.invoice_term_id = config_term

    def action_create_refund_invoice(self):
        refund_invoice_id = False
        lines = []
        for rec in self:
            if not rec.invoice_id:
                raise UserError(_('Please Select the Invoice to Refund.'))
            refund_invoice_id = rec.invoice_id.copy(
                default={
                    'state': 'draft',
                    'invoice_date_due': fields.Date.today(),
                    'invoice_date': fields.Date.today(),
                    'payment_date': False,
                    'invoice_line_ids': False,
                    'line_ids': [],
                    'waiver_amount': 0.0,
                    'waiver_ids': False,
                    'payment_state': 'not_paid',
                    'type': 'out_refund'
                }
            )
            if rec.refund_line_ids:
                for refund_line in rec.refund_line_ids:
                    fee_line = {
                        'quantity': 1.00,
                        'price_unit': refund_line.refund_amount,
                        'product_id': refund_line.invoice_line_id.product_id.id,
                        'name': refund_line.invoice_line_id.name,
                        'account_id': refund_line.invoice_line_id.account_id.id,
                        'move_id': refund_invoice_id.id,
                        'fee_head_id': refund_line.invoice_line_id.fee_head_id.id,
                        'fee_category_id': refund_line.invoice_line_id.fee_category_id.id,
                        'exclude_from_invoice_tab': False,
                    }
                    lines.append((0, 0, fee_line))
            refund_invoice_id.invoice_line_ids = lines
        return refund_invoice_id

    def create_refund_payment_entry(self):
        for rec in self:
            if not rec.payment_journal_id:
                raise UserError(_('Please Select the Payment Journal/Bank.'))
            if not rec.total_refund_amount > 0:
                raise UserError(_('Refund Amount should be greater then Zero.'))
            payment_method_id = '2'
            payment_type = 'outbound'
            partner_type = 'supplier'
            data = {
                'payment_type': payment_type,
                'payment_method_id': payment_method_id,
                'partner_type': partner_type,
                'partner_id': rec.student_id.partner_id and rec.student_id.partner_id.id or False,
                'payment_date': fields.Date.today(),
                'communication': "Amount Paid Against the Student Refund",
                'amount': rec.total_refund_amount,
                'journal_id': rec.payment_journal_id and rec.payment_journal_id.id or False,
                'invoice_ids': rec.refund_invoice_id and rec.refund_invoice_id.ids or [],
                # 'analytic_account_id': invoice.student_id.campus_id.analytic_account_id.id,
                # 'analytic_account_id': False,
                # 'analytic_tag_ids': [],
            }

            pay_rec = self.env['account.payment'].create(data)
            pay_rec.post()
            rec.payment_id = pay_rec.id

    def create_refund_student_ledger_entry(self, debit=0, credit=0, description="Student Refund To be Adjustment in Fee", invoice_id=False):
        ledger_id = False
        for rec in self:
            ledger_entry_type = 'semester'
            if rec.invoice_type=='hostel':
                ledger_entry_type = 'hostel'
            if rec.total_refund_amount > 0:
                ledger_data = {
                    'student_id': rec.student_id.id,
                    'debit': debit,
                    'credit': credit,
                    'date': fields.Date.today(),
                    'description': description,
                    'refund_request_id': rec.id,
                    'ledger_entry_type': ledger_entry_type,
                    'invoice_id': invoice_id and invoice_id.id or False,
                }
                ledger_id = self.env['odoocms.student.ledger'].create(ledger_data)
        return ledger_id

    @api.depends('invoice_id')
    def _compute_refund_type_domain(self):
        for rec in self:
            f_list = []
            if rec.invoice_id:
                self.env.cr.execute("""select distinct fee_head_id as fee_head_id from account_move_line where move_id=%s""" % rec.invoice_id.id)
                fee_heads = self.env.cr.dictfetchall()
                for fee_head in fee_heads:
                    f_list.append(fee_head['fee_head_id'])
            rec.refund_type_domain = json.dumps([('id', 'in', f_list)])

    @api.depends('refund_line_ids', 'refund_line_ids.actual_amount')
    def _compute_total_amount(self):
        for rec in self:
            total_amount = 0
            if rec.refund_line_ids:
                for line in rec.refund_line_ids:
                    total_amount += line.actual_amount
            rec.total_amount = total_amount

    @api.depends('refund_line_ids', 'refund_line_ids.refund_amount')
    def _compute_total_refund(self):
        for rec in self:
            total_refund = 0
            if rec.refund_line_ids:
                for line in rec.refund_line_ids:
                    total_refund += line.refund_amount
            rec.total_refund_amount = total_refund


class OdooCMSFeeRefundRequestLine(models.Model):
    _name = 'odoocms.fee.refund.request.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Fee Refund Request Line'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    refund_id = fields.Many2one('odoocms.fee.refund.request', 'Refund', index=True, auto_join=True, ondelete='cascade')

    invoice_id = fields.Many2one('account.move', 'Invoice', related='refund_id.invoice_id', store=True)
    invoice_line_id = fields.Many2one('account.move.line', 'Invoice Line', compute="compute_invoice_line_data", store=True, readonly=False)
    actual_amount = fields.Integer(string='Invoice Amount')

    refund_type_domain = fields.Char(compute="_compute_refund_type_domain", readonly=True, store=False)
    refund_type = fields.Many2one('odoocms.fee.head', 'Fee Head', required=True)
    refund_amount = fields.Integer(string='Refund Amount', required=True)

    state = fields.Selection([('draft', 'Submitted'),
                              ('approve', 'Approved'),
                              ('reject', 'Rejected'),
                              ('done', 'Done'),
                              ('cancel', 'Canceled')
                              ], default='draft', string="Status", tracking=True)
    description = fields.Char('Description')
    remarks = fields.Text('Refund Remarks')

    @api.model
    def create(self, values):
        result = super(OdooCMSFeeRefundRequestLine, self).create(values)
        return result

    def refund_granted(self):
        self.state = 'done'

    def cancel_refund_request(self):
        self.state = 'cancel'

    @api.depends('refund_type')
    def compute_invoice_line_data(self):
        for rec in self:
            if rec.refund_type:
                mvl = self.env['account.move.line'].search([('move_id', '=', rec.invoice_id.id),
                                                            ('fee_head_id', '=', rec.refund_type.id)])
                if mvl:
                    rec.invoice_line_id = mvl.id
                    rec.actual_amount = mvl.price_subtotal
                    rec.refund_amount = mvl.price_subtotal
                    rec.description = mvl.name
                if not mvl:
                    rec.invoice_line_id = False
                    rec.actual_amount = 0
                    rec.refund_amount = 0
                    rec.description = ''

    @api.depends('invoice_id')
    def _compute_refund_type_domain(self):
        for rec in self:
            f_list = []
            if rec.invoice_id:
                self.env.cr.execute("""select distinct fee_head_id as fee_head_id from account_move_line where move_id=%s""" % rec.invoice_id.id)
                fee_heads = self.env.cr.dictfetchall()
                for fee_head in fee_heads:
                    f_list.append(fee_head['fee_head_id'])
            rec.refund_type_domain = json.dumps([('id', 'in', f_list)])
