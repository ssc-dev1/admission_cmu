# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class OdooCmsStudentFeeLedgerUpdate(models.TransientModel):
    _name = 'odoocms.student.fee.ledger.update'
    _description = 'Student Fee Ledger Update'

    @api.model
    def _get_student_id(self):
        if self.env.context.get('active_model', False)=='odoocms.student' and self.env.context.get('active_id', False):
            return self.env.context['active_id']

    student_id = fields.Many2one('odoocms.student', string='Student', default=_get_student_id)
    ledger_id = fields.Many2one('odoocms.student.ledger', string='Student Ledger')
    old_debit = fields.Float('Old Debit')
    old_credit = fields.Float('Old Credit')
    new_debit = fields.Float('New Debit')
    new_credit = fields.Float('New Credit')

    @api.onchange('ledger_id')
    def onchange_ledger_id(self):
        for rec in self:
            rec.old_debit = rec.ledger_id.debit
            rec.old_credit = rec.ledger_id.credit

    def action_update_student_ledger(self):
        if not self.env.user.login=='admin':
            raise UserError(_('This action is allowed for this User.'))

        if self.student_id and self.ledger_id:
            self.ledger_id.credit = self.new_credit
            self.ledger_id.debit = self.new_debit
        else:
            raise UserError(_("Please Select the Student And Ledger Entry to Update."))
        return {'type': 'ir.actions.act_window_close'}
