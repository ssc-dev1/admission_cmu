# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdooCMSFeeWaiverType(models.Model):
    _inherit = 'odoocms.fee.waiver.type'

    type = fields.Selection([('waiver', 'ScholarShip'), ('scholarship', 'ScholarShip-II')
                             ], default='waiver', string='Type', tracking=True)
    scholarship_category_id = fields.Many2one('odoocms.fee.scholarship.category', 'Scholarship Category', index=True, tracking=True)
    auto_type = fields.Selection([('auto', 'Auto'), ('non_auto', 'Non Auto'),
                                  ], default='auto', string='Auto/Non Auto', tracking=True)


class OdooCMSFeeWaiver(models.Model):
    _inherit = 'odoocms.fee.waiver'

    scholarship_category_id = fields.Many2one('odoocms.fee.scholarship.category', related='waiver_type.scholarship_category_id', string='Scholarship Category', store=True, tracking=True)
    is_special = fields.Boolean('Is Special', default=False, tracking=True)

    @api.onchange('waiver_type')
    def onchange_scholarship_type(self):
        for rec in self:
            if rec.waiver_type:
                rec.name = rec.waiver_type.name
                rec.code = rec.waiver_type.code


# ***** This Model is Being Added on the Request of MIS Manager UCP *****#
# ***** Before That you have already Scholarship Type for that Purpose *****#
# ***** But They Will Generate/Create one Type For each its Line item *****#
# ***** So Scholarship Category Will be Top upper layer *****#
class OdooCMSFeeScholarshipCategory(models.Model):
    _name = 'odoocms.fee.scholarship.category'
    _description = 'Scholarship Categories'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    progress_base = fields.Boolean('Progress Based', default=False)
    advance_enrollment = fields.Boolean('Apply on Advance Registration', default=False)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('unique_scholarship_category', 'unique(name)', "Duplicate Record are not Allowed."),
    ]

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'

    @api.model
    def create(self, values):
        result = super(OdooCMSFeeScholarshipCategory, self).create(values)
        return result

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError('You Cannot delete this Record, This Record is not in the Draft State.')
            return super(OdooCMSFeeScholarshipCategory, self).unlink()
