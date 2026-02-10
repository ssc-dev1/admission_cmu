
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import pdb

import logging
_logger = logging.getLogger(__name__)

READONLY_STATES = {
    'draft': [('readonly', False)],
    'current': [('readonly', True)],
    'lock': [('readonly', True)],
    'submit': [('readonly', True)],
    'disposal': [('readonly', True)],
    'approval': [('readonly', True)],
    'done': [('readonly', True)],
}

READONLY_STATES2 = {
    'draft': [('readonly', False)],
    'current': [('readonly', False)],
    'lock': [('readonly', True)],
    'submit': [('readonly', True)],
    'disposal': [('readonly', True)],
    'approval': [('readonly', True)],
    'done': [('readonly', True)],
}


class OdooCMSGradeHisto(models.Model):
    _name = 'odoocms.grade.histo'
    _description = 'Histogram Grades'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'high_per desc'
    
    name = fields.Char('Grade Name')
    low_per = fields.Float('Per. From')
    high_per = fields.Float('Per. Below')
    cnt = fields.Integer('Count')
    grade_class_id = fields.Many2one('odoocms.class.grade', 'Grade Class')
    batch_id = fields.Many2one('odoocms.batch', 'Program Batch', related='grade_class_id.batch_id', store=True)
    event = fields.Selection([('mid','Mid'),('final','Final')], string='Event', default='final')
    company_id = fields.Many2one('res.company', string='Company', related='grade_class_id.company_id', store=True)


class OdooCMSGrade(models.Model):
    _name = 'odoocms.grade'
    _description = 'CMS Grades'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char('Name')
    domain = fields.Char('Domain')
    term_domain = fields.Char('Term Domain')
    sequence = fields.Integer('Sequence',default=10)
    line_ids = fields.One2many('odoocms.grade.line', 'grade_id', 'Grade Lines', copy=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSGradeLine(models.Model):
    _name = 'odoocms.grade.line'
    _description = 'CMS Grades Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'high_per desc'
    
    name = fields.Char('Grade Name')
    remarks = fields.Char('Academic Standing')
    low_per = fields.Float('Per. From')
    high_per = fields.Float('Per. Below')
    grade_id = fields.Many2one('odoocms.grade', 'Grade')
    # batch_id = fields.Many2one('odoocms.batch', 'Program Batch', related='grade_class_id.batch_id', store=True)


