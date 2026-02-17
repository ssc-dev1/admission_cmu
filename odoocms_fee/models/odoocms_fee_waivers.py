# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

payment_types = [
    ('admissiontime', 'Admission Time'),
    ('permonth', 'Per Month'),
    ('peryear', 'Per Year'),
    ('persemester', 'Per Semester'),
    ('persubject', 'Per Subject'),
    ('percredit','Per Credit'),
    ('onetime', 'One Time')
]


class OdooCMSFeeWaiverType(models.Model):
    _name = 'odoocms.fee.waiver.type'
    _description = 'Fee Waiver Types'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Title", tracking=True)
    code = fields.Char("Code", tracking=True)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', default=True, tracking=True)
    type = fields.Selection([('waiver', 'Waivers'), ('scholarship', 'ScholarShip')], default='waiver', string='Type', tracking=True)
    waiver_ids = fields.One2many('odoocms.fee.waiver', 'waiver_type', 'Linked Waives')
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'


class OdooCMSFeeWaiver(models.Model):
    _name = 'odoocms.fee.waiver'
    _description = 'Fee Waiver'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence')
    code = fields.Char('Code', tracking=True)
    tag_id = fields.Many2one('odoocms.student.tag', 'Tag', tracking=True)
    waiver_type = fields.Many2one('odoocms.fee.waiver.type', 'Waiver Type', tracking=True, ondelete="restrict")

    session_id = fields.Many2one('odoocms.academic.session', tracking=True)
    line_ids = fields.One2many('odoocms.fee.waiver.line', 'waiver_id', 'Waiver Lines')
    domain = fields.Char('Domain Rule')
    student_ids = fields.Many2many('odoocms.student', 'student_waiver_rel', 'waiver_id', 'student_id', 'Students')
    type = fields.Selection(string='Type', related='waiver_type.type', store=True, tracking=True, index=True)
    donor_id = fields.Many2one('odoocms.fee.donors', 'Donor', tracking=True, index=True)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    to_be = fields.Boolean('To Be', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    # This field required for UCP
    amount = fields.Float('Amount')

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'


class OdooCMSFeeWaiverLine(models.Model):
    _name = 'odoocms.fee.waiver.line'
    _description = 'Fee Waiver Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'fee_head_id'

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    category_id = fields.Many2one('odoocms.fee.category', string='Fee Category', required=True)
    fee_head_id = fields.Many2one('odoocms.fee.head', string='Fee Head', required=True, tracking=True)
    waiver_type = fields.Selection([('fixed', 'Fixed'),
                                    ('percentage', 'Percentage'),
                                    ('remaining', 'Remaining Amount'),
                                    ], 'Type', default='fixed')
    percentage = fields.Float('Discount (%)', required=True, tracking=True)
    amount = fields.Float('Amount', tracking=True)
    payment_type = fields.Selection(string='Payment Type', related="fee_head_id.payment_type")

    fee_description = fields.Text('Description', related='fee_head_id.description_sale')
    note = fields.Char('Note', tracking=True)
    waiver_id = fields.Many2one('odoocms.fee.waiver', 'Waiver', ondelete="cascade")
    company_id = fields.Many2one('res.company', string='Company', related='waiver_id.company_id', store=True)

    _sql_constraints = [('feehead_waiver', 'unique(fee_head_id,waiver_id)', "Another Fee Line already exists with this Head and Waiver!")]

    @api.model
    def create(self, values):
        res = super(OdooCMSFeeWaiverLine, self).create(values)
        res.name = self.env['ir.sequence'].next_by_code('odoocms.fee.waiver.line')
        body = 'Fee Head Added: %s' % res.fee_head_id.name
        # res.waiver_id.message_post(body=body)
        return res

    def write(self, values):
        res = super(OdooCMSFeeWaiverLine, self).write(values)
        for rec in self:
            body = 'Fee Head Modified: %s - %s' % (rec.fee_head_id.name, rec.percentage)
            # rec.waiver_id.message_post(body=body)
        return res

    def unlink(self):
        for rec in self:
            body = 'Fee Head Removed: %s - %s' % (rec.fee_head_id.name, rec.percentage)
            # rec.waiver_id.message_post(body=body)
        return super(OdooCMSFeeWaiverLine, self).unlink()


class OdooCMSStudentFeeWaiver(models.Model):
    _name = 'odoocms.student.fee.waiver'
    _description = 'Student Fee Waiver'

    name = fields.Char('Name')
    student_id = fields.Many2one('odoocms.student', 'Student')
    invoice_id = fields.Many2one('account.move', 'Invoice')
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    term_code = fields.Char('Term Code', related='term_id.code', store=True)
    semester_id = fields.Many2one('odoocms.semester', 'Semester')
    waiver_type = fields.Selection([('fixed', 'Fixed'),
                                    ('percentage', 'Percentage'),
                                    ('remaining', 'Remaining Amount'),
                                    ], 'Type', default='fixed')
    amount = fields.Float('Amount')
    amount_percentage = fields.Char('Value')
    waiver_line_id = fields.Many2one('odoocms.fee.waiver.line', 'Waiver Line')
    company_id = fields.Many2one('res.company', string='Company', related='student_id.company_id', store=True)

    def create(self, values):
        result = super().create(values)
        if not result.name:
            result.name = result.student_id.name + ' Scholarship For ' + result.term_id.name
        return result
