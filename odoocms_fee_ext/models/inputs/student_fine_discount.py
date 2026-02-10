# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class OdoocmsStudentFineDiscounts(models.Model):
    _name = 'odoocms.student.fine.discounts'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Fine Discounts'

    @api.model
    def get_term_id(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    student_name = fields.Char(related='student_id.name', string='Student Name', tracking=True)
    student_code = fields.Char(related='student_id.code', string='Student Code', tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=get_term_id, tracking=True)

    lines = fields.One2many('odoocms.student.fine.discounts.line', 'fine_discount_id', 'Lines')

    total_fine = fields.Float('Total Fine', compute='_compute_totals', store=True)
    total_discount = fields.Float('Total Discount', compute='_compute_totals', store=True)
    due_amount = fields.Float('Due Amount', compute='_compute_totals', store=True)

    date = fields.Date('Date', default=fields.Date.today(), tracking=True)
    fine_discount_type = fields.Selection([('attendance_fine', 'Attendance Fine'), ('other_fine', 'Other Fine')], string="Type")
    state = fields.Selection([('draft', 'Draft'), ('approved', 'Approved'), ('cancel', 'Cancelled')], default='draft', string='Status', tracking=True)
    processed = fields.Boolean('Processed', compute='_compute_fine_discount_lines', store=True)

    @api.depends('student_id', 'term_id', 'fine_discount_type')
    def _compute_fine_discount_lines(self):
        for rec in self:
            fine_att_date_list = []
            if rec.lines:
                rec.lines.sudo().unlink()
            if rec.student_id and rec.term_id:
                if rec.fine_discount_type == 'other_fine':
                    domain = [('student_id', '=', rec.student_id.id), ('term_id', '=', rec.term_id.id), ('state', '!=', 'cancel')]
                    misc_charges_lines = self.env['odoocms.fee.additional.charges'].search(domain)
                    for misc_charges_line in misc_charges_lines:
                        record_already_processed = self.env['odoocms.student.fine.discounts.line'].search([('other_fine_id', '=', misc_charges_line.id)])
                        if record_already_processed:
                            continue
                        if misc_charges_line.receipt_id and misc_charges_line.receipt_id.payment_state in ('in_payment', 'paid'):
                            continue
                        data_values = {
                            'student_id': misc_charges_line.student_id.id,
                            'date_class': misc_charges_line.date,
                            'fine': misc_charges_line.amount,
                            'other_fine_id': misc_charges_line.id,
                            'other_fine_type': misc_charges_line.charges_type.name,
                            'other_fine_challan': misc_charges_line.receipt_id and misc_charges_line.receipt_id.id or False,
                            'fine_discount_id': rec.id,
                        }
                        self.env['odoocms.student.fine.discounts.line'].sudo().create(data_values)
                        rec.processed = True

                    other_fine_lines = self.env['odoocms.input.other.fine'].search(domain)
                    for other_fine_line in other_fine_lines:
                        record_already_processed = self.env['odoocms.student.fine.discounts.line'].search([('other_fine_id2', '=', other_fine_line.id)])
                        if record_already_processed:
                            continue
                        if other_fine_line.receipt_id and other_fine_line.receipt_id.payment_state in ('in_payment', 'paid'):
                            continue

                        data_values = {
                            'student_id': other_fine_line.student_id.id,
                            'date_class': other_fine_line.date,
                            'fine': other_fine_line.net_amount,
                            'other_fine_id2': other_fine_line.id,
                            'other_fine_type': other_fine_line.type.name,
                            'other_fine_challan': other_fine_line.receipt_id and other_fine_line.receipt_id.id or False,
                            'fine_discount_id': rec.id,
                        }
                        self.env['odoocms.student.fine.discounts.line'].sudo().create(data_values)
                        rec.processed = True

    @api.depends('lines', 'lines.fine', 'lines.discount')
    def _compute_totals(self):
        for rec in self:
            rec.total_fine = sum(line.fine for line in rec.lines)
            rec.total_discount = sum(line.discount for line in rec.lines)
            rec.due_amount = rec.total_fine - rec.total_discount

    def action_approve_fine_discounts(self):
        for rec in self:
            if not rec.lines:
                raise UserError("Please Select Lines")

            # ***** Delete the Unchanged Lines *****#
            lines_to_delete = rec.lines.filtered(lambda a: a.fine == 0)
            if lines_to_delete:
                lines_to_delete.sudo().unlink()

            # *****Lines on Which Discount Applied *****#
            lines = rec.lines.filtered(lambda a: a.fine > 0)
            if rec.fine_discount_type == 'other_fine':
                for line in lines:
                    new_amt = max(line.due_amount, 0)
                    discount = min(line.discount, line.fine)

                    if line.other_fine_challan and line.other_fine_challan.payment_state == ('paid', 'in_payment', 'partial'):
                        raise UserError(_("Challan Already Paid"))
                    elif line.other_fine_challan and line.other_fine_challan.payment_state not in ('paid', 'in_payment', 'partial'):
                        if line.other_fine_id:
                            line.other_fine_id.write({'discount': discount, 'amount': new_amt})
                        elif line.other_fine_id2:
                            line.other_fine_id2.write({'discount_amount': discount, 'net_amount': new_amt})

                    elif not line.other_fine_challan:
                        if line.other_fine_id:
                            line.other_fine_id.write({'discount': discount, 'amount': new_amt})
                        elif line.other_fine_id2:
                            line.other_fine_id2.write({'discount_amount': discount, 'net_amount': new_amt})

            rec.state = 'approved'

    @api.model_create_multi
    def create(self, vals):
        result = super().create(vals)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.student.fine.discounts')
        return result

    def unlink(self):
        for rec in self:
            if rec.state == 'approved':
                raise UserError(_('You cannot Delete This Records'))
        record = super().unlink()
        return record


class OdoocmsStudentFineDiscountsLine(models.Model):
    _name = 'odoocms.student.fine.discounts.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Student Fine Discounts Lines'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student')
    class_id = fields.Many2one('odoocms.class', string='Class')
    date_class = fields.Date('Date')
    fine = fields.Float('Fine')
    discount = fields.Float('Discount')
    due_amount = fields.Float('Due Amount', compute='_compute_due_amount', store=True)
    apply_discount = fields.Boolean('Apply Discount')
    remarks = fields.Text('Remarks')

    other_fine_id = fields.Many2one('odoocms.fee.additional.charges', 'Misc Fine')
    other_fine_id2 = fields.Many2one('odoocms.input.other.fine', 'Other Fine')
    other_fine_type = fields.Char('Charges Type')
    other_fine_challan = fields.Many2one('account.move', 'Other Fine Challan')

    fine_discount_id = fields.Many2one('odoocms.student.fine.discounts', string='Fine Discounts', index=True, ondelete='cascade', auto_join=True)

    @api.model_create_multi
    def create(self, vals):
        result = super().create(vals)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.student.fine.discounts.line')
        return result

    @api.depends('fine', 'discount')
    def _compute_due_amount(self):
        for rec in self:
            rec.due_amount = rec.fine - rec.discount if rec.fine - rec.discount > 0 else 0

    @api.onchange('apply_discount')
    def onchange_apply_discount(self):
        self.discount = self.fine
