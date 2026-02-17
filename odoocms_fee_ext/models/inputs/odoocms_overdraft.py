# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class OdoocmsOverDraft(models.Model):
    _name = 'odoocms.overdraft'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _description = "Over Draft (OD)"

    name = fields.Char('Name')
    sequence = fields.Char('Sequence')
    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)

    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    amount = fields.Float('Amount', required=True, tracking=True)
    date = fields.Date('Date', required=True, default=lambda self: fields.Date.today(), tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Processed'), ('cancel', 'Cancelled')], string='Status', index=True,
        tracking=True, compute='_get_state', store=True, readonly=False, default='draft')

    move_id = fields.Many2one('account.move', 'Invoice/ Move', tracking=True)
    student_ledger_id = fields.Many2one('odoocms.student.ledger', 'Ledger Ref', tracking=True)
    notes = fields.Text('Additional Notes', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    to_be = fields.Boolean('To Be', default=False)

    @api.model
    def create(self, values):
        if not values.get('sequence', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.overdraft')
        result = super(OdoocmsOverDraft, self).create(values)
        return result

    def unlink(self):
        for rec in self:
            if rec.state == 'done' or rec.move_id:
                raise UserError('You Cannot Delete Done Records.')
        return super(OdoocmsOverDraft, self).unlink()

    @api.depends('move_id')
    def _get_state(self):
        for rec in self:
            if rec.state != 'cancel':
                rec.state = 'done' if rec.move_id else 'draft'

    def action_cancel(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'cancel'

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'cancel':
                rec.state = 'draft'

    def get_overdraft_lines(self, student_id, term_id, lines):
        domain = [('student_id', '=', student_id), ('term_id','=',term_id), ('move_id','=',False),('state', '!=', 'cancel')]
        term_overdraft_recs = self.env['odoocms.overdraft'].search(domain)
        if term_overdraft_recs:
            domain = [('name', '=', 'Fee Adjustment'), '|', ('company_id', '=', False), ('company_id', '=', term_overdraft_recs[0].student_id.company_id.id)]
            overdraft_fee_head = self.env['odoocms.fee.head'].search(domain)
            for term_overdraft_rec in term_overdraft_recs:
                att_fine_line_date_dict = {
                    'sequence': 250,
                    'price_unit': -term_overdraft_rec.amount,
                    'quantity': 1,
                    'product_id': overdraft_fee_head.product_id.id,
                    'name': overdraft_fee_head.name,
                    'account_id': overdraft_fee_head.property_account_income_id.id,
                    'fee_head_id': overdraft_fee_head.id,
                    'exclude_from_invoice_tab': False,
                    'no_split': overdraft_fee_head.no_split,
                }
                lines.append((0, 0, att_fine_line_date_dict))
        return lines, term_overdraft_recs

    @api.onchange('student_id')
    def onchange_student_id(self):
        for rec in self:
            fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
            fee_charge_term_rec = self.env['odoocms.academic.term'].browse(fee_charge_term)
            if rec.student_id:
                rec.term_id = fee_charge_term_rec and fee_charge_term_rec.id or False
