# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError


class OdooCMSDepartment(models.Model):
    _inherit = 'odoocms.department'

    account_payable = fields.Char("Fee Payable At")
    account_title = fields.Char('Account Title')
    account_no = fields.Char('Account Number')
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')


class OdooCMSProgram(models.Model):
    _inherit = 'odoocms.program'

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')


class OdooCMSCampus(models.Model):
    _inherit = 'odoocms.campus'

    analytic_tag_id = fields.Many2one('account.analytic.tag', 'Analytic Tag')
    late_fee_per_day_fine = fields.Char(string='Late fee Fine/day', default=100, help='Write percentage sign if you want to add percentage, add value otherwise. i.e. 100 or 0.20%')
    late_fee_max_fine = fields.Integer(string='Late Fee Max Fine', default=1800)
    fee_banks = fields.Char('Fee Banks')
    fee_instructions = fields.Html('Fee Instructions')
    fee_instructions_admission = fields.Html('Fee Instructions - Admission')
    fee_instructions_short = fields.Html('Fee Instructions Short')

    fee_query_email = fields.Char('Queries Email')
    fee_query_phone = fields.Char('Queries Phone')


class OdooCMSBatch(models.Model):
    _inherit = 'odoocms.batch'

    fee_structure_id = fields.Many2one('odoocms.fee.structure', 'Fee Structure', tracking=True)
    late_fee_per_day_fine = fields.Char(string='Late fee Fine/day', default=100, help='Write percentage sign if you want to add percentage, add value otherwise. i.e. 100 or 0.20%')
    late_fee_max_fine = fields.Integer(string='Late Fee Max Fine', default=1800)


class AccountPaymentTermTerm(models.Model):
    _name = 'account.payment.term.term'

    sequence = fields.Integer('Sequence')
    company_id = fields.Many2one('res.company','Company')
    payment_term_id = fields.Many2one('account.payment.term','Payment Term')
    term_id = fields.Many2one('odoocms.academic.term','Academic Term')
    allowed = fields.Integer('Allowed No')
    actual = fields.Integer('Actual No')

    _sql_constraints = [
        ('unique_company_payment_term', 'unique(course_id,component)', "Component already exists in Course"), ]


class OdoocmsStudentFeePreviousBalance(models.Model):
    _name = 'odoocms.student.fee.previous.balance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Student Fee Previous Balance"

    name = fields.Char('Name')
    student_id = fields.Many2one('odoocms.student', 'Student', tracking=True, index=True, ondelete='cascade')
    student_code = fields.Char('Student Code', tracking=True)
    amount = fields.Float('Amount', tracking=True)
    ledger_id = fields.Many2one('odoocms.student.ledger', 'Ledger Ref.', tracking=True, index=True)
    status = fields.Selection([('m', 'Student Matched'),
                               ('n', 'Student Not Matched')], string='Status', tracking=True)
    to_be = fields.Boolean('To Be', default=False, tracking=True)
    notes = fields.Char('Notes')
    date = fields.Date('Date', tracking=True)
    student_tags = fields.Char('Student Tags', compute='_compute_student_tags', store=True)
    included_invoice = fields.Boolean('Included In Invoice')
    institute_code = fields.Char(related='student_id.institute_id.code', string='Institute', store=True)

    @api.model
    def create(self, values):
        if not values.get('sequence', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.fee.previous.balance')
        result = super(OdoocmsStudentFeePreviousBalance, self).create(values)
        return result

    def action_create_ledger_entry(self):
        for rec in self:
            if rec.ledger_id:
                raise UserError(_('Its Ledger Entry is already created.'))
            if rec.student_id:
                vals = {
                    'student_id': rec.student_id.id,
                    'date': fields.Date.today(),
                    'credit': rec.amount,
                    'session_id': rec.student_id.session_id and rec.student_id.session_id.id or False,
                    'career_id': rec.student_id.career_id and rec.student_id.career_id.id or False,
                    'program_id': rec.student_id.program_id and rec.student_id.program_id.id or False,
                    'institute_id': rec.student_id.institute_id and rec.student_id.institute_id.id or False,
                    'discipline_id': rec.student_id.discipline_id and rec.student_id.discipline_id.id or False,
                    'term_id': rec.student_id.term_id and rec.student_id.term_id.id or False,
                    'semester_id': rec.student_id.semester_id and rec.student_id.semester_id.id or False,
                }
                ledger_rec = self.env['odoocms.student.ledger'].sudo().create(vals)
                rec.ledger_id = ledger_rec and ledger_rec.id or False
                # rec.to_be = False

    # Cron Job to assign the Student Id to records
    def cron_assign_student_id(self, nlimit=100):
        recs = self.env['odoocms.student.fee.previous.balance'].search([('to_be', '=', True)], limit=nlimit)
        if recs:
            for rec in recs:
                student_id = self.env['odoocms.student'].search([('code', '=', rec.student_code)])
                if student_id:
                    rec.write({'student_id': student_id.id,
                               'status': 'm',
                               'to_be': False})

    def update_arrears_ledger_amount(self):
        for rec in self:
            if rec.ledger_id:
                if not rec.ledger_id.invoice_id:
                    rec.ledger_id.write({'credit': rec.amount})
                if rec.ledger_id.invoice_id:
                    raise UserError(_('This Arrears Invoice is Generated.'))

    def delete_arrears_ledger_entry(self):
        for rec in self:
            if rec.ledger_id:
                if not rec.ledger_id.invoice_id:
                    ledger_rec = rec.ledger_id
                    rec.ledger_id = False
                    ledger_rec.sudo().unlink()
                if rec.ledger_id.invoice_id:
                    raise UserError(_('This Arrears Invoice is Generated.'))

    def unlink(self):
        for rec in self:
            rec.delete_arrears_ledger_entry()
        return super(OdoocmsStudentFeePreviousBalance, self).unlink()

    @api.depends('student_id', 'student_id.tag_ids')
    def _compute_student_tags(self):
        for rec in self:
            if rec.student_id and rec.student_id.tag_ids:
                student_groups = ''
                for tag in rec.student_id.tag_ids:
                    if tag.code:
                        student_groups = student_groups + tag.code + ", "
                rec.student_tags = student_groups
