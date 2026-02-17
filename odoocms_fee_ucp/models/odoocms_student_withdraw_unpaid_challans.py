# -*- coding: utf-8 -*-
import logging
import pdb

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class OdoocmsWithdrawStudentUnapidChallans(models.Model):
    _name = 'odoocms.withdraw.student.unpaid.challans'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Withdraw Student Unpaid Challans'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    program_id = fields.Many2one('odoocms.program', 'Program', tracking=True, compute='_compute_student_info', store=True)
    institute_id = fields.Many2one('odoocms.institute', 'Faculty', tracking=True, compute='_compute_student_info', store=True)

    date = fields.Date('Date', tracking=True, default=fields.Date.today())
    state = fields.Selection([('draft', 'draft'), ('done', 'Done'), ('cancel', 'Cancel'),
                              ], string='Status', index=True, tracking=True, default='draft')
    to_be = fields.Boolean('To Be')
    lines = fields.One2many('odoocms.withdraw.student.unpaid.challans.line', 'withdraw_student_unpaid_challan_id', 'Lines')

    @api.model_create_multi
    def create(self, vals):
        result = super().create(vals)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.withdraw.student.unpaid.challans')
        return result

    @api.depends('student_id')
    def _compute_student_info(self):
        for rec in self:
            if rec.student_id:
                rec.program_id = rec.student_id.program_id and rec.student_id.program_id.id or False
                rec.institute_id = rec.student_id.institute_id and rec.student_id.institute_id.id or False

    def get_detail(self):
        for rec in self:
            student_courses = self.env['odoocms.student.course'].sudo().search([('student_id', '=', rec.student_id.id), ('grade', 'in', ('w', 'W'))])
            term_ids = student_courses.filtered(lambda c: c.grade in ('W', 'w')).mapped('term_id')
            for term_id in term_ids:
                term_courses = student_courses.filtered(lambda c: c.term_id == term_id)
                if all(course.grade in ('W', 'w') for course in term_courses):
                    challans = self.env['account.move'].search([('student_id', '=', rec.student_id.id),
                                                                ('term_id', '=', term_id.id),
                                                                ('move_type', '=', 'out_invoice'),
                                                                ('payment_state', 'not in', ['paid', 'in_payment'])
                                                                ])

                    for challan in challans:
                        data_values = {
                            'student_id': rec.student_id.id,
                            'term_id': term_id.id,
                            'move_id': challan.id,
                            'amount': challan.amount_total,
                            'withdraw_student_unpaid_challan_id': rec.id,
                        }
                        new_rec = self.env['odoocms.withdraw.student.unpaid.challans.line'].sudo().create(data_values)

    def action_done(self):
        for rec in self:
            if rec.lines:
                for line in rec.lines:
                    if line.action == 'clear':
                        rec.action_delete_challan(line)
                    elif line.action == 'delete':
                        rec.action_clear_challan(line)
            rec.state = 'done'

    def action_delete_challan(self, line):
        line.move_id.sudo().unlink()

    def action_clear_challan(self, line):
        move_id = line.move_id
        for line in move_id.line_ids:
            line.with_context(check_move_validity=False).write({'price_unit': 0})
        move_id.with_context(check_move_validity=False).write({'amount_total': 0, 'amount_residual': 0, 'payment_state': 'paid'})
        move_id.student_ledger_id.credit = 0
        move_id.payment_ledger_id.debit = 0


class OdoocmsWithdrawStudentUnapidChallansLines(models.Model):
    _name = 'odoocms.withdraw.student.unpaid.challans.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Withdraw Student Unpaid Challans Lines'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    move_id = fields.Many2one('account.move', 'Invoice')
    amount = fields.Float('Amount')
    action = fields.Selection([('clear', 'Clear'), ('delete', 'Delete'), ('no_action', 'No Action')], default='no_action', string='Action')

    date = fields.Date('Date', tracking=True, default=fields.Date.today())
    state = fields.Selection([('draft', 'draft'),('done', 'Done'), ('cancel', 'Cancel'),
                              ], string='Status', index=True, tracking=True, default='draft')
    withdraw_student_unpaid_challan_id = fields.Many2one('odoocms.withdraw.student.unpaid.challans', 'Unpaid Challan Ref')
