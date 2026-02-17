# -*- coding: utf-8 -*-
import pdb
from datetime import date
from odoo import api, fields, models, _


class OdooCMSGenerateInvoice(models.TransientModel):
    _inherit = 'odoocms.generate.invoice'

    def generate_hostel_invoice(self):
        due_date = False
        hostel_challan_months = self.hostel_challan_months
        invoices = self.env['account.move']
        values = {
            'tag': self.tag,
            'reference': self.reference,
            'description': self.comment,
            'date': date.today(),
        }

        invoices_group = self.env['account.move.group'].create(values)
        for student in self.student_ids:
            term_id = self.term_id
            if not term_id:
                term_id = student.term_id

            invoice_id = student.generate_hostel_invoice(description_sub=self.description_sub, semester=term_id, receipts=self.receipt_type_ids, date_due=self.date_due, comment=self.comment, tag=self.tag, invoice_group=invoices_group, registration_id=self.registration_id, hostel_challan_months=hostel_challan_months)

            invoices += invoice_id
            invoice_id.generate_challan_barcode(student, 'Hostel')

        if invoices:
            invoice_list = invoices.mapped('id')
            form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', invoice_list)],
                'name': _('Hostel Invoices'),
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
