# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class OdoocmsChallanFinePolicy(models.Model):
    _name = 'odoocms.challan.fine.policy'
    _description = 'Challan Fine Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term, tracking=True)
    start_date = fields.Date('Start Date', default=fields.Date.today(), tracking=True, required=True)
    due_date = fields.Date('Due Date', tracking=True, required=True)

    faculty_type = fields.Selection([
        ('Faculty', 'Select Faculty ...'),
        ('All', 'All Faculties'),
    ], default='Faculty', tracking=True, index=True, string="Faculty Selection")
    program_selection_type = fields.Selection([
        ('Program', 'Select Program ...'),
        ('All', 'All Program'),
    ], default='Program', string='Program Selection', tracking=True, index=True)

    faculty_ids = fields.Many2many('odoocms.department', 'challan_fine_policy_department_rel1', 'challan_fine_policy_id', 'department_id', 'Departments')
    program_ids = fields.Many2many('odoocms.program', 'challan_fine_policy_program_rel1', 'challan_fine_policy_id', 'program_id', 'Programs')

    state = fields.Selection([('draft', 'New'), ('confirm', 'Confirmed'), ('cancel', 'Cancel')], string='Status', default='draft', tracking=True)

    payment_term_id = fields.Many2one('account.payment.term','Payment Term')
    label_id = fields.Many2one('account.payment.term.label', 'Label')

    fine_amount = fields.Float('Fine Amount', tracking=True)
    remarks = fields.Text('Remarks')
    lines = fields.One2many('odoocms.challan.fine.policy.line', 'fine_policy', 'Lines')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    to_be = fields.Boolean('To Be', default=True)

    @api.onchange('start_date')
    def onchange_start_date(self):
        for rec in self:
            if rec.start_date and not rec.due_date:
                rec.due_date = rec.start_date + relativedelta(days=+5)

    @api.constrains('start_date', 'due_date')
    def validate_date(self):
        for rec in self:
            start_date = fields.Date.from_string(rec.start_date)
            due_date = fields.Date.from_string(rec.due_date)
            if start_date >= due_date:
                raise ValidationError(_('Start Date must be Anterior to Due Date'))

    def action_confirm(self):
        self.action_generate_detail()
        self.state = 'confirm'
        self.lines.write({'state': 'confirm'})

    def action_cancel(self):
        self.state = 'cancel'
        self.lines.write({'state': 'cancel'})

    @api.model
    def create(self, values):
        result = super(OdoocmsChallanFinePolicy, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.challan.fine.policy')
        return result

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('You can delete the Records that are in the Draft State.'))
        return super(OdoocmsChallanFinePolicy, self).unlink()

    def action_generate_detail(self):
        program_ids = self.env['odoocms.program']
        for rec in self:
            if rec.faculty_type == "Faculty":
                if not self.faculty_ids:
                    raise UserError(_('Please Select Faculties'))
                department_ids = self.faculty_ids
            else:
                department_ids = self.env['odoocms.department'].search([], order='id asc')

            if rec.program_selection_type == "Program":
                if not self.program_ids:
                    raise UserError(_('Please Select Programs'))
                program_ids = self.program_ids
            else:
                for department_id in department_ids:
                    program_ids += self.env['odoocms.program'].search([('department_id', '=', department_id.id)])

            for program_id in program_ids:
                data_values = {
                    'fine_policy': rec.id,
                    'faculty_id': program_id.department_id.id,
                    'program_id': program_id.id,
                    'term_id': rec.term_id.id,
                    'start_date': rec.start_date,
                    'due_date': rec.due_date,
                    'payment_term_id': rec.payment_term_id.id,
                    'fine_amount': rec.fine_amount,
                    'label_id': rec.label_id.id,
                    'state': rec.state,
                }
                self.env['odoocms.challan.fine.policy.line'].create(data_values)


class OdoocmsChallanFinePolicyLine(models.Model):
    _name = 'odoocms.challan.fine.policy.line'
    _description = 'Challan Fine Policy Detail'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer('Sequence', default=10)

    term_id = fields.Many2one('odoocms.academic.term', 'Term', tracking=True)
    start_date = fields.Date('Start Date', default=fields.Date.today(), tracking=True)
    due_date = fields.Date('Due Date', default=fields.Date.today(), tracking=True)

    faculty_id = fields.Many2one('odoocms.department', 'Faculty', tracking=True)
    faculty_name = fields.Char(related='faculty_id.code', string="Faculty Name", store=True)
    program_id = fields.Many2one('odoocms.program', 'Program')
    program_name = fields.Char(related='program_id.code', string='Program Name', store=True)

    payment_term_id = fields.Many2one('account.payment.term', 'Payment Term')
    label_id = fields.Many2one('account.payment.term.label', 'Label')
    state = fields.Selection([('draft', 'New'),('confirm', 'Confirmed'),('cancel', 'Cancel')], string='Status', default='draft', tracking=True)

    fine_policy = fields.Many2one('odoocms.challan.fine.policy', 'Fine Policy', index=True, ondelete='cascade', auto_join=True)
    name = fields.Char('Name', related='fine_policy.name', store=True)

    fine_amount = fields.Float('Fine Amount', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

