# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class RefundReuest(models.Model):
    _name = 'refund.request'
    _description = 'Applications Request for Refund'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('odoocms.student',required=True)
    request_date = fields.Date(string='Request Date')
    refund_amount= fields.Integer(string='Refund Amount',required=True)
    description = fields.Text('Description')


class AdjustmentReuest(models.Model):
    _name = 'adjustment.request'
    _description = 'Applications Request for Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    student_id = fields.Many2one('odoocms.student',required=True)
    request_date = fields.Date(string='Request Date')
    adjustment_amount= fields.Integer(string='Adjustment Amount',required=True)
    description = fields.Text('Description')