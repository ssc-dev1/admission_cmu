# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


class OdooCMSFeeAdditionalChargesType(models.Model):
    _name = 'odoocms.fee.additional.charges.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Ad-hoc Charges Types"

    name = fields.Char("Name")
    code = fields.Char("Code")
    fee_head_id = fields.Many2one('odoocms.fee.head', 'Fee Head')
    amount = fields.Float('Amount', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'


class OdooCMSFeeAdditionalCharges(models.Model):
    _name = 'odoocms.fee.additional.charges'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _description = "AdHoc Charges"

    def get_term_id(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name')
    sequence = fields.Char('Sequence')

    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester')
    term_id = fields.Many2one('odoocms.academic.term', 'Charge On Term', default=get_term_id)

    date = fields.Date('Date', required=True, default=lambda self: fields.Date.today(), tracking=True)
    due_date = fields.Date('Due Date', default=fields.Date.today() + relativedelta(days=7))

    charges_type = fields.Many2one('odoocms.fee.additional.charges.type', 'Charges Type', required=True, tracking=True)
    amount = fields.Float('Amount', required=True, tracking=True, compute='compute_amount', store=True, readonly=False)
    discount = fields.Float('Discount')

    challan_id = fields.Many2one('odoocms.fee.barcode','Challan')
    receipt_id = fields.Many2one('account.move', 'Receipt Ref.', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('charged', 'Generated'), ('cancel', 'Cancelled')], 'Status',
        tracking=True, compute='_get_state', store=True, readonly=False, index=True)

    notes = fields.Text('Additional Notes', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    to_be = fields.Boolean('To Be', default=False)

    # Added by Sarfraz
    challan_payment_state = fields.Selection(related='receipt_id.payment_state', store=True)
    old_challan_no = fields.Char(related='receipt_id.old_challan_no', store=True)
    challan_paid_date = fields.Date(related='receipt_id.payment_date', store=True)

    @api.constrains('amount')
    def validate_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError('Amount Should be Greater then the Zero.')

    @api.model
    def create(self, values):
        if not values.get('sequence', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.fee.additional.charges')
        result = super().create(values)
        return result

    def unlink(self):
        for rec in self:
            if rec.receipt_id:
                raise UserError('You Cannot Delete this record, As this Record is already Include in the Invoice. Please contact the System Administrator.')
        return super().unlink()

    @api.depends('charges_type')
    def compute_amount(self):
        for rec in self:
            if not rec.amount and rec.charges_type.amount:
                rec.amount = rec.charges_type.amount

    @api.depends('receipt_id')
    def _get_state(self):
        for rec in self:
            if rec.state != 'cancel':
                rec.state = 'charged' if rec.receipt_id else 'draft'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'cancel'

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'cancel':
                rec.state = 'draft'

    @api.model
    def get_import_templates(self):
        return [{
            'label': _('Import Template for Ad hoc Fee Charges'),
            'template': '/odoocms_fee/static/xls/ad_hoc_charges.xlsx'
        }]

    def get_additional_charges_lines(self, student_id, term_id, lines):
        domain = [('student_id', '=', student_id), ('term_id', '=', term_id), ('receipt_id','=',False),('state', '!=', 'cancel')]
        adhoc_charges = self.env['odoocms.fee.additional.charges'].search(domain)
        for adhoc_charge in adhoc_charges:
            adhoc_charge_fee_head = adhoc_charge.charges_type.fee_head_id
            if adhoc_charge_fee_head:
                adhoc_charge_line = {
                    'sequence': 300,
                    'price_unit': adhoc_charge.amount,
                    'quantity': 1,
                    'product_id': adhoc_charge_fee_head.product_id.id,
                    'name': adhoc_charge.charges_type.name,
                    'account_id': adhoc_charge_fee_head.property_account_income_id.id,
                    'fee_head_id': adhoc_charge_fee_head.id,
                    'exclude_from_invoice_tab': False,
                    'no_split': adhoc_charge_fee_head.no_split,
                }
                lines.append((0, 0, adhoc_charge_line))
        return lines, adhoc_charges

    def action_create_misc_challan(self):
        for rec in self:
            lines = []
            structure_domain = [
                ('session_id', '=', rec.student_id.session_id.id), ('batch_id', '=', rec.student_id.batch_id.id),
                ('career_id', '=', rec.student_id.career_id.id)]
            fee_structure = self.env['odoocms.fee.structure'].search(structure_domain, order='id desc', limit=1)
            if not fee_structure:
                raise UserError(_('No Fee Structure Found For Batch-%s') % rec.student_id.batch_id.name)

            receipts = self.env['odoocms.receipt.type'].search([('name', '=', 'Misc Fee')], order='id desc', limit=1)
            domain = [('student_id', '=', rec.student_id.id), ('receipt_id', '=', False)]
            misc_charge_lines = self.env['odoocms.fee.additional.charges'].search(domain)

            for misc_charge_line in misc_charge_lines:
                fee_head = misc_charge_line.charges_type.fee_head_id
                misc_mvl = {
                    'sequence': 10,
                    'name': misc_charge_line.charges_type.name,
                    'quantity': 1,
                    'course_gross_fee': misc_charge_line.amount,
                    'price_unit': misc_charge_line.amount,
                    'product_id': fee_head.product_id.id,
                    'account_id': fee_head.property_account_income_id.id,
                    'fee_head_id': fee_head.id,
                    'exclude_from_invoice_tab': False,
                    'course_id_new': False,
                    'registration_id': False,
                    'registration_line_id': False,
                    'course_credit_hours': 0,
                    'discount': 0,
                    'is_add_drop_line': False,
                    'registration_type': 'misc_challan',
                    'add_drop_paid_amount': 0,
                    'no_split': fee_head.no_split,
                    'student_id': rec.student_id.id,
                    'partner_id': rec.student_id.partner_id.id,
                }
                lines.append((0, 0, misc_mvl))

            if misc_charge_lines:
                data = {
                    'student_id': rec.student_id.id,
                    'partner_id': rec.student_id.partner_id.id,
                    'fee_structure_id': fee_structure.id,
                    'journal_id': fee_structure.journal_id.id,
                    'invoice_date': rec.date,
                    'invoice_date_due': rec.due_date,
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                    'waiver_amount': 0,
                    'validity_date': rec.due_date,
                    'challan_type': 'misc_challan',
                    'misc_charges_type': rec.charges_type and rec.charges_type.id or False,

                    # 'registration_id': registration_id and registration_id.id or False,
                }
                # Create Fee Receipt
                invoice_id = self.env['account.move'].sudo().create(data)

                if invoice_id.amount_total > 0:
                    challan_ids = invoice_id.generate_challan_barcode(rec.student_id, 'Misc')

                    misc_charge_lines.write({
                        'challan_id': challan_ids[0].id,
                        'receipt_id': invoice_id.id,
                        'state': 'charged'
                    })
