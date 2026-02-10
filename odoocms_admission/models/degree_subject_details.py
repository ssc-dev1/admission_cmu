from odoo import fields, models, _, api


class AdmissionDocuments(models.Model):
    _name = 'applicant.subject.details'
    _description = 'Applicant Degree Subject Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Many2one('applicant.academic.subjects')
    total_marks = fields.Char(string='Total Marks')
    obtained_marks = fields.Char(string='Obtained Marks')
    # percentage = fields.Char(string='Percentage')
    applicant_academic_id = fields.Many2one('applicant.academic.detail')
