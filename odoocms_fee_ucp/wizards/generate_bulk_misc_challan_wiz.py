# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class GenerateBulkMiscChallanWiz(models.TransientModel):
    _name = 'generate.bulk.misc.challan.wiz'
    _description = 'Generate Bulk Misc Challan'

    @api.model
    def _get_misc_charges(self):
        if self.env.context.get('active_model', False)=='odoocms.fee.additional.charges' and self.env.context.get('active_ids', False):
            recs = self.env['odoocms.fee.additional.charges'].search([('id', 'in', self.env.context['active_ids']), ('state', '=', 'draft')])
            return recs and recs.ids or []

    misc_charges = fields.Many2many('odoocms.fee.additional.charges', 'generate_bulk_misc_challan_rel1', 'wizard_id', 'additional_charges_id',
                                    string='Misc Charges', help="""Only selected Records will be Processed.""", default=_get_misc_charges)

    def action_generate_bulk_misc_challan(self):
        misc_invoices = self.env['account.move']
        if self.misc_charges:
            for rec in self.misc_charges:
                rec.action_create_misc_challan()
                misc_invoices += rec.receipt_id

        if misc_invoices:
            invoice_list = misc_invoices.mapped('id')
            form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', invoice_list)],
                'name': _('Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                    (form_view and form_view.id or False, 'form'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
