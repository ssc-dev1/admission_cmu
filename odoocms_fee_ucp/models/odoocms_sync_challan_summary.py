# -*- coding: utf-8 -*-
import pdb
from odoo import api, fields, models, tools, _
import pyodbc
import logging

_logger = logging.getLogger(__name__)


class OdoocmsSyncChallanSummary(models.Model):
    _name = 'odoocms.sync.challan.summary'
    _description = 'Sync Challan Summary '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence')
    date = fields.Date('Date', tracking=True)
    total_challan = fields.Float('Total Challan')
    total_amount = fields.Float('Total Amount')
    lines = fields.One2many('odoocms.sync.challan.summary.line', 'summary_id', 'Summary Detail')

    @api.model
    def create(self, values):
        result = super(OdoocmsSyncChallanSummary, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.sync.challan.summary')
        return result

    def action_create_challan_sync_summary(self, dt):
        if not dt:
            dt = fields.Date.today()
        sync_pool_lines = self.env['odoocms.fee.sync.pool'].sudo().search([('date', '=', dt), ('summary_id', '=', False)])
        challan_amt = 0
        if sync_pool_lines:
            summary_data_dict = {
                'date': fields.Date.today(),
                'total_challan': len(sync_pool_lines),
            }
            summary_rec = self.env['odoocms.sync.challan.summary'].sudo().create(summary_data_dict)

            self.env.cr.execute("""select count(*) as cnt,sum(total_payable) as amt,date,challan_type,institute_id from odoocms_fee_sync_pool where date='%s' and summary_id is null group by date,challan_type,institute_id order by institute_id;""" % dt)
            query_results = self.env.cr.dictfetchall()
            for query_result in query_results:
                challan_amt += query_result['amt']
                summary_line_dict = {
                    'date': dt,
                    'summary_id': summary_rec.id,
                    'institute_id': query_result['institute_id'],
                    'challan_type': query_result['challan_type'],
                    'challan_count': query_result['cnt'],
                    'challan_amount': query_result['amt'],
                }
                self.env['odoocms.sync.challan.summary.line'].sudo().create(summary_line_dict)
            summary_rec.write({'total_amount': challan_amt})
            sync_pool_lines.write({'summary_id': summary_rec.id})


class OdoocmsSyncChallanSummaryLine(models.Model):
    _name = 'odoocms.sync.challan.summary.line'
    _description = 'Sync Challan Summary Detail '
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence')
    date = fields.Date('Date', tracking=True)
    summary_id = fields.Many2one('odoocms.sync.challan.summary', 'Summary Ref')
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')
    challan_type = fields.Selection([('main_challan', 'Main Challan'),
                                     ('2nd_challan', '2nd Challan'),
                                     ('admission', 'New Admission'),
                                     ('admission_2nd_challan', 'Admission 2nd Challan'),
                                     ('add_drop', 'Add Drop'),
                                     ('prospectus_challan', 'Prospectus Challan'),
                                     ('hostel_fee', 'Hostel Fee'),
                                     ('misc_challan', 'Misc Challan'),
                                     ('installment', 'Installment')
                                     ], string='Challan Type', tracking=True)
    challan_count = fields.Float('Cnt')
    challan_amount = fields.Float('Amount')

    @api.model
    def create(self, values):
        result = super(OdoocmsSyncChallanSummaryLine, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.sync.challan.summary.line')
        return result
