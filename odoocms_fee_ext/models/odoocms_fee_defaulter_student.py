# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdoocmsFeeDefaulterStudent(models.Model):
    _name = 'odoocms.fee.defaulter.student'
    _description = 'Fee Defaulter Students'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Date('Start Date', default=fields.Date.today(), tracking=True)
    institute_id = fields.Many2one('odoocms.institute', 'Faculty', tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term, tracking=True)
    label_id = fields.Many2one('account.payment.term.label', 'Label')
    state = fields.Selection([('draft', 'New'),('withdraw', 'Withdraw'),('cancel', 'Cancel')], string='Status', default='draft', tracking=True)

    exclude_due_date_not_end = fields.Boolean('Exclude Due Date Not End', tracking=True)
    exclude_withdraw_student = fields.Boolean('Exclude Withdraw Student', tracking=True)
    lines = fields.One2many('odoocms.fee.defaulter.student.line', 'fee_defaulter_id', 'Lines')
    to_be = fields.Boolean('To Be', default=True)
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_get_students(self):
        if self.lines:
            self.lines.sudo().unlink()

        dom = [('state', '=', 'draft'), ('amount_residual', '>', 0)]
        if self.term_id:
            dom.append(('term_id', '=', self.term_id.id))
        if self.institute_id:
            dom.append(('student_id.institute_id', '=', self.institute_id.id))
        if self.label_id:
            dom.append(('label_id', '=', self.label_id.id))
        if self.exclude_withdraw_student:
            dom.append(('student_id.state', '!=', 'withdraw'))
        if self.exclude_due_date_not_end:
            dom.append(('date_due', '<', fields.Date.today()))

        challan_ids = self.env['odoocms.fee.barcode'].search(dom, order='student_id')
        for challan in challan_ids:
            line_values = {
                'student_id': challan.student_id.id,
                'institute_id': challan.student_id.institute_id and challan.student_id.institute_id.id or False,
                'program_id': challan.student_id.program_id and challan.student_id.program_id.id or False,
                'amount': challan.amount_residual - challan.fine_amount,
                'fine_amount': challan.fine_amount,
                'total_dues': challan.amount,
                'fee_defaulter_id': self.id
            }
            self.env['odoocms.fee.defaulter.student.line'].sudo().create(line_values)

    def action_withdraw(self):
        if not self.lines:
            raise UserError("Line Detail Not Found")
        reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
        reason = reason_id and reason_id.id or False
        for line in self.lines:
            fee_defaulter_courses = line.student_id.course_ids.filtered(lambda a: a.state == 'current')
            if fee_defaulter_courses:
                fee_defaulter_courses.write({
                    'state': 'withdraw',
                    'withdraw_date': fields.datetime.now(),
                    'withdraw_reason': reason,
                    'grade': 'W',
                })
        self.state = 'withdraw'
        self.lines.write({'state': 'withdraw'})

    def action_cancel(self):
        self.state = 'cancel'
        self.lines.write({'state': 'cancel'})

    @api.model
    def create(self, values):
        result = super(OdoocmsFeeDefaulterStudent, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.defaulter.student')
        return result

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('You can delete the Records that are in the Draft State.'))
        return super(OdoocmsFeeDefaulterStudent, self).unlink()


class OdoocmsFeeDefaulterStudentLine(models.Model):
    _name = 'odoocms.fee.defaulter.student.line'
    _description = 'Fee Defaulter Student Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True)
    student_name = fields.Char('Student Name')
    student_code = fields.Char('Student Code')
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')
    institute_name = fields.Char(related='institute_id.code', string="Faculty Name", store=True)
    program_id = fields.Many2one('odoocms.program', 'Program')
    program_name = fields.Char(related='program_id.code', string='Program Name', store=True)
    amount = fields.Float('Amount')
    fine_amount = fields.Float('Fine Amount')
    total_dues = fields.Float('Total Dues')
    state = fields.Selection([('draft', 'New'),
                              ('withdraw', 'Withdraw'),
                              ('cancel', 'Cancel')
                              ], string='Status', default='draft', tracking=True)
    registration_status = fields.Selection(related='student_id.state', store=True, string='Registration Status')
    remarks = fields.Char('Remarks')
    fee_defaulter_id = fields.Many2one('odoocms.fee.defaulter.student', 'Fee Defaulter Ref', index=True, ondelete='cascade', auto_join=True)

    @api.model
    def create(self, values):
        result = super(OdoocmsFeeDefaulterStudentLine, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.defaulter.student.line')
        return result
