# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class OdooCMSFeeStructureStudent(models.Model):
    _name = 'odoocms.fee.structure.student'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Structure Student'

    category_id = fields.Many2one('odoocms.fee.category', string='Category', required=True)
    fee_head_id = fields.Many2one('odoocms.fee.head', string='Fee', required=True)
    fee_type = fields.Selection([('fixed', 'Fixed'),
                                 ('percentage', 'Percentage')
                                 ], 'Type', default='fixed')
    amount = fields.Float('Amount', tracking=True)
    percentage = fields.Float('Percentage', )
    percentage_of = fields.Many2one('odoocms.fee.structure.head.line', '% Of')

    payment_type = fields.Selection(string='Payment Type', related="fee_head_id.payment_type")
    fee_description = fields.Text('Description', related='fee_head_id.description_sale')
    note = fields.Char('Note')
    student_id = fields.Many2one('odoocms.student', 'Student')

    _sql_constraints = [('feehead_student', 'unique(fee_head_id,student_id)', "Another Fee Line already exists with this Head and Student!"), ]

    @api.onchange('student_id', 'fee_head_id')
    def onchange_fee_head(self):
        if self.student_id and self.fee_head_id:
            fee_structure = self.env['odoocms.fee.structure'].search(
                [('session_id', '=', self.student_id.session_id.id)])
            fee_line = fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id==self.fee_head_id.id)
            # Now Search from Head Line
            if fee_line:
                self.amount = fee_line.amount  # or percentage
