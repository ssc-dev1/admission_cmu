# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import json


class ShowStudentFeeChallansWiz(models.TransientModel):
    _name = 'show.student.fee.challans.wiz'
    _description = """This Wizard will Show Selected Challans"""

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term, )

    student_id_domain = fields.Char(compute="_compute_student_id_domain", readonly=True, store=False)
    student_id = fields.Many2one('odoocms.student', 'Registration No')

    @api.depends('term_id')
    def _compute_student_id_domain(self):
        std_list = []
        if self.term_id:
            students = self.env['account.move'].search([('term_id', '=', self.term_id.id),
                                                        ]).mapped('student_id')
            std_list = students.ids
        self.student_id_domain = json.dumps([('id', 'in', std_list)])

    def action_submit_challan_form(self):
        if not self.student_id:
            raise UserError(_("Please Select Registration No"))
        dom = [('student_id', '=', self.student_id.id),
               ('term_id', '=', self.term_id.id)
               ]
        moves = self.env['account.move'].search(dom)
        if moves:
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', moves.ids)],
                'name': _('Student Challans'),
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
