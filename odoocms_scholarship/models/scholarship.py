
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class OdooCMSScholarshipType(models.Model):
    _name = 'odoocms.scholarship.type'
    _description = 'Scholarship Type'
    
    name = fields.Char('Name', size=64, required=True)
    amount = fields.Integer('Amount')
    
    @api.constrains('amount')
    def check_amount(self):
        if self.amount <= 0:
            raise ValidationError(_('Amount cannot be Negative.'))


class OdooCMSScholarshipDonor(models.Model):
    _name = 'odoocms.scholarship.donor'
    _description = 'Scholarship Donor'
    
    name = fields.Char('Name', required=True)
    scholarship_no = fields.Integer('No. of Scholarships')
    scholarship_amount = fields.Integer('Scholarships Amount')
    academic_calendar_id = fields.Many2one('odoocms.academic.calendar', 'Academic Calendar')
    description = fields.Text('Description')


class OdooCMSScholarship(models.Model):
    _name = 'odoocms.scholarship'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Scholarship'

    name = fields.Char('Name', size=64, required=True)
    student_id = fields.Many2one('odoocms.student', 'Student', required=True)
    type_id = fields.Many2one('odoocms.scholarship.type', 'Type', required=True)
    type_amount = fields.Integer(related='type_id.amount',string="Scholarship Amount", store=True, tracking=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'),
         ('reject', 'Reject')], 'State', default='draft', readonly=True,
        index=True, tracking=True)
    program_id = fields.Many2one('odoocms.program', 'Program', required=True, states={'confirm': [('readonly', True)]})
    batch_id = fields.Many2one('odoocms.batch', 'Batch', required=True, states={'confirm': [('readonly', True)]})

    @api.onchange('type_id')
    def _onchange_vehicle(self):
        self.type_amount = self.type_id.amount

    # @api.one
    def act_confirm(self):
        self.state = 'confirm'

    # @api.one
    def act_reject(self):
        self.state = 'reject'
