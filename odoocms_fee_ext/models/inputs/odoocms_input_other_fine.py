# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class OdoocmsInputOtherFineType(models.Model):
    _name = 'odoocms.input.other.fine.type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Input Other Fine Types"

    def get_default_fee_head(self):
        return self.env['odoocms.fee.head'].search([('name', '=', "Discipline Fine")]).id

    name = fields.Char("Name")
    code = fields.Char("Code")
    fee_head_id = fields.Many2one('odoocms.fee.head', 'Fee Head', default=get_default_fee_head)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)

    def action_lock(self):
        for rec in self:
            rec.state = 'lock'

    def action_unlock(self):
        for rec in self:
            rec.state = 'draft'

    def unlink(self):
        for rec in self:
            if not rec.state == "draft":
                raise UserError('You Cannot Delete this record, Only Draft Status Records cannot be deleted.')
        return super().unlink()


class OdooCMSInputOtherFine(models.Model):
    _name = 'odoocms.input.other.fine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _description = "Input Other Fines"

    name = fields.Char('Name')
    sequence = fields.Char('Sequence')
    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)

    term_id = fields.Many2one('odoocms.academic.term', 'Charge On Term')
    semester_id = fields.Many2one('odoocms.semester', 'Semester')

    date = fields.Date('Date', required=True, default=lambda self: fields.Date.today(), tracking=True)
    type = fields.Many2one('odoocms.input.other.fine.type', 'Type', required=True, tracking=True)
    amount = fields.Float('Amount', required=True, tracking=True)
    discount_amount = fields.Float('Discount', tracking=True, groups="odoocms_fee_ucp.group_other_fine_discount_user", help="Enter in Figure not in Percentage")
    net_amount = fields.Float('Net Amount', compute="_compute_net_amount", store=True)

    receipt_id = fields.Many2one('account.move', 'Challan', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('charged', 'Generated'), ('cancel', 'Cancelled')], string='Status',
        compute='_get_state', store=True, readonly=False, index=True)

    notes = fields.Text('Additional Notes', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    to_be = fields.Boolean('To Be', default=False)

    @api.constrains('amount')
    def validate_amount(self):
        for rec in self:
            if rec.amount <= 0:
                raise ValidationError('Amount Should be Greater then the Zero.')

    @api.model
    def create(self, values):
        if not values.get('sequence', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.input.other.fine')
        result = super().create(values)
        return result

    def unlink(self):
        for rec in self:
            if rec.receipt_id:
                raise UserError('You Cannot Delete this record, As this Record is already Include in the Invoice. Please contact the System Administrator.')
        return super().unlink()

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
            'label': _('Import Template for Input Other Fine'),
            'template': '/odoocms_fee_ucp/static/xls/input_other_fine.xlsx'
        }]

    @api.depends('amount', 'discount_amount')
    def _compute_net_amount(self):
        for rec in self:
            if rec.discount_amount and rec.discount_amount > rec.amount:
                raise UserError(_("Discount Amount Should be Equal or Less Than Amount"))
            rec.net_amount = rec.amount - rec.discount_amount

    def get_input_other_fine_lines(self, student_id, term_id, lines):
        domain = [('student_id', '=', student_id), ('term_id', '=', term_id), ('receipt_id','=',False),('state', '!=', 'cancel')]
        other_fine_recs = self.env['odoocms.input.other.fine'].search(domain)
        if other_fine_recs:
            self.env.cr.execute("""select sum(net_amount) as net_amount, type as type_id from odoocms_input_other_fine 
                where student_id=%s and term_id=%s and receipt_id is null and state != 'cancel' group by type;""", (student_id, term_id))
            query_results = self.env.cr.dictfetchall()
            for query_result in query_results:
                other_fine_type = self.env['odoocms.input.other.fine.type'].sudo().search([('id', '=', query_result['type_id'])])
                other_fine_fee_head = other_fine_type.fee_head_id
                if other_fine_fee_head:
                    other_fine_line = {
                        'sequence': 350,
                        'price_unit': query_result['net_amount'],
                        'quantity': 1,
                        'product_id': other_fine_fee_head.product_id.id,
                        'name': other_fine_type.name,
                        'account_id': other_fine_fee_head.property_account_income_id.id,
                        'fee_head_id': other_fine_fee_head.id,
                        'exclude_from_invoice_tab': False,
                        'no_split': other_fine_fee_head.no_split,
                    }
                    lines.append((0, 0, other_fine_line))
        return lines, other_fine_recs