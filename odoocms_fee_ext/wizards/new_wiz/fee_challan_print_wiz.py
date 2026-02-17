# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import json


class FeeChallanPrintFormWiz(models.TransientModel):
    _name = 'fee.challan.print.form.wiz'
    _description = """This Wizard will Show the Selected Challan"""

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    challan_type = fields.Selection([('main_challan', 'Main Challan'),
                                     ('2nd_challan', '2nd Challan'),
                                     ('admission', 'New Admission'),
                                     ('admission_2nd_challan', 'Admission 2nd Challan'),
                                     ('add_drop', 'Add Drop'),
                                     ('prospectus_challan', 'Prospectus Challan'),
                                     ('hostel_fee', 'Hostel Fee'),
                                     ('misc_challan', 'Misc Challan'),
                                     ('installment', 'Installment')
                                     ], default='main_challan', string='Challan Type')

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    registration_no = fields.Char('Reg#')

    student_id_domain = fields.Char(compute="_compute_student_id_domain", readonly=True, store=False)
    student_id = fields.Many2one('odoocms.student', 'Student')

    challan_no_domain = fields.Char(compute="_compute_challan_no_domain", readonly=True, store=False)
    challan_no = fields.Many2one('account.move', 'Challans#')
    installment_no = fields.Integer('Installment No')

    @api.depends('challan_type', 'term_id')
    def _compute_student_id_domain(self):
        std_list = []
        if self.term_id and self.challan_type:
            students = self.env['account.move'].search([('term_id', '=', self.term_id.id),
                                                        ('challan_type', '=', self.challan_type)
                                                        ]).mapped('student_id')
            std_list = students.ids
        self.student_id_domain = json.dumps([('id', 'in', std_list)])

    @api.depends('student_id', 'term_id', 'challan_type', 'installment_no')
    def _compute_challan_no_domain(self):
        challan_list = []
        self.challan_no = False
        if self.term_id and self.challan_type and self.student_id:
            if self.challan_type == 'installment' and self.installment_no > 0:
                challan_no = self.env['account.move'].search([('term_id', '=', self.term_id.id),
                                                              ('challan_type', '=', self.challan_type),
                                                              ('student_id', '=', self.student_id.id),
                                                              ('installment_no', '=', str(self.installment_no))])
            else:
                challan_no = self.env['account.move'].search([('term_id', '=', self.term_id.id),
                                                              ('challan_type', '=', self.challan_type),
                                                              ('student_id', '=', self.student_id.id)])
            challan_list = challan_no.ids
        self.challan_no_domain = json.dumps([('id', 'in', challan_list)])

    def action_open_print_challan_form(self):
        moves = self.env['account.move']
        if self.challan_no:
            moves += self.challan_no
        else:
            if not self.student_id and not self.registration_no:
                raise UserError(_("Please Select Student ID or Student Registration No"))
            student_id = self.student_id
            if not self.student_id and self.registration_no:
                student_id = self.env['odoocms.student'].search([('code', '=', self.registration_no)])
            if not student_id:
                raise UserError(_('Student not Found'))
            dom = [('student_id', '=', student_id.id), ('term_id', '=', self.term_id.id), ('challan_type', '=', self.challan_type)]
            if self.installment_no:
                dom.append(('installment_no', '=', str(self.installment_no)))

            # if self.challan_type:
            #     if self.challan_type == 'main_challan':
            #         dom.append(('challan_type', 'in', ['main_challan', 'admission']))
            #     elif self.challan_type == 'installment':
            #         dom.append(('challan_type', 'in', ['2nd_challan', 'admission_2nd_challan']))
            #     elif self.challan_type == 'add_drop':
            #         dom.append(('challan_type', '=', 'add_drop'))

            challan_ids = self.env['account.move'].search(dom)
            moves += challan_ids

        if moves:
            challan_list = moves.mapped('id')
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', challan_list)],
                'name': _('Challan Print Form'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
