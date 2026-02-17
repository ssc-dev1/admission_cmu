# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ChallanRollbackWiz(models.TransientModel):
    _name = 'challan.rollback.wiz'
    _description = 'Challan Roll Back Wizard'

    @api.model
    def _get_invoices(self):
        if self.env.context.get('active_model', False)=='account.move' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    invoice_ids = fields.Many2many('account.move', 'challan_rollback_wiz_invoice_rel1', 'rollback_id', 'move_id', string='Invoices', default=_get_invoices)
    set_to_be = fields.Boolean('Set To Be', default=False)
    set_student_to_be = fields.Boolean('Set Student To Be', default=False)
    auto_delete = fields.Boolean('Auto Delete', default=True)

    def action_challan_rollback(self):
        for rec in self:
            if rec.invoice_ids:
                rec.invoice_ids.write({'payment_state': 'not_paid', 'state': 'draft', 'posted_before': False})
            if rec.set_to_be:
                rec.invoice_ids.write({'to_be': True})
            if rec.set_student_to_be:
                students = self.env['odoocms.student'].search([('to_be', '=', True)])
                students.write({'to_be': False})
                inv_students = rec.invoice_ids.mapped('student_id')
                inv_students.write({'to_be': True})
            if rec.auto_delete:
                for invoice in rec.invoice_ids:
                    invoice.sudo().with_context(force_delete=True).unlink()
        return {'type': 'ir.actions.act_window_close'}
