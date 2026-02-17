from odoo import fields, models, _, api
from datetime import datetime

class AdmissionDocuments(models.Model):
    _name = 'applicant.academic.detail'
    _description = 'Applicant Document Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'application_id'

    application_id = fields.Many2one('odoocms.application', string='Applicant', ondelete='cascade',tracking=True)
    applicant = fields.Char(related='application_id.name', string='Applicant Name', store=True)
    program_id = fields.Many2one('odoocms.program', string='Program',tracking=True)
    institute_id = fields.Many2one(related='application_id.prefered_program_id.institute_id',store=True )
    program_name = fields.Char(related='application_id.prefered_program', string='Program',store=True)
    fee_voucher_state = fields.Selection(related='application_id.fee_voucher_state', string='Fee Status', store=True)
    voucher_verified_date = fields.Date(related='application_id.voucher_verified_date',store=True)
    father_name = fields.Char('Father Name',related='application_id.father_name')
    father_cnic = fields.Char('Father CNIC',related='application_id.father_cnic')
    reference_no = fields.Char(related='application_id.application_no', string='Reference No', store=True)
    cnic = fields.Char(string='CNIC', related='application_id.cnic')
    cnic_attachment = fields.Binary(string='CNIC Attachment', related='application_id.cnic_front')
    board = fields.Char(string='Board')

    institute = fields.Char(string='Last Institute')
    passport = fields.Char(string='Passport', related='application_id.passport')
    passport_attachment = fields.Binary(string='Passport Attachment', related='application_id.pass_port')
    mobile = fields.Char(string='Mobile', related='application_id.mobile')
    last_year_slip = fields.Binary('Last Year Roll No Slip')
    gender = fields.Selection(string='Gender', required=False, related='application_id.gender')
    domicile = fields.Char(string='Domicile', related='application_id.domicile_id.name')
    application_state = fields.Selection(string='Application Status', related='application_id.state')
    domicile_attachment = fields.Binary(string='Domicile Attachment', related='application_id.domicile')
    application_submit_date = fields.Datetime(string='Application Submit Date', related='application_id.application_submit_date')
    nationality = fields.Char(string='Nationality', related='application_id.nationality.name')
    doc_state = fields.Selection(
        [('yes', 'Verified'), ('no', 'UnVerified'), ('rejected', 'Rejected'),
         ('reg_verified', 'Registration Verified'), ('reg_reject', 'Registration Reject')],
        string='Verified?', default="no", tracking=True)
    doc_verify = fields.Boolean(default=False,tracking=True)
    reg_verify = fields.Boolean(default=False,tracking=True)
    degree_name = fields.Many2one('odoocms.admission.degree',tracking=True)
    degree_level_id = fields.Many2one('odoocms.admission.education',tracking=True)
    group_specialization = fields.Many2one('applicant.academic.group',tracking=True)
    # application_id = fields.Many2one('odoocms.application')
    applicant_subject_id = fields.One2many('applicant.subject.details', 'applicant_academic_id')
    roll_no = fields.Char(string='Roll No')
    sec_year_roll_no = fields.Char(string='Second Year Roll No',tracking=True)
    result_status = fields.Selection(
        string='Result Status',
        selection=[('complete', 'Complete'),
                   ('waiting', 'Waiting'), ],
        required=False,tracking=True )

    obt_marks = fields.Integer('Obtained Marks',tracking=True)
    total_marks = fields.Integer('Total Marks',tracking=True)
    obtained_cgpa = fields.Float('Obtained CGPA',tracking=True)
    total_cgpa = fields.Float('Total CGPA',tracking=True)
    cgpa_check = fields.Boolean('Cgpa Check',default=False,tracking=True)
    cgpa_percentage = fields.Float('Cgpa Percentage',compute='_get_cgpa_percentage',store=True)
    
    percentage = fields.Float('Percentage',tracking=True)
    attachment = fields.Binary(string='Degree Attachment View', attachment=True,tracking=True)
    degree_attachment = fields.Binary('Degree Attachment Download', related='attachment')
    year = fields.Char(string='Passing Year',tracking=True)
    hope_certificate = fields.Image('Hope Certificate View', attachment=True,tracking=True)
    hope_certificate_attachment = fields.Image('Hope Certificate Download', related='hope_certificate')
    
    document_verified_date = fields.Date('Document Verified Date',tracking=True)
    user_verify_id = fields.Many2one('res.users', string='Verify By.')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    def action_document_verified(self):
        self.doc_verify = True
        for rec in self:
            rec.document_verified_date = datetime.today().date()
            rec.user_verify_id = self.env.user.id
            rec.doc_state = 'yes'

    def action_document_unverified(self):
        self.doc_verify = True
        for rec in self:
            rec.doc_state = 'no'

    def registration_verified(self):
        self.reg_verify = True
        for rec in self:
            rec.doc_state = 'reg_verified'

    def registration_unverified(self):
        self.reg_verify = True
        for rec in self:
            rec.doc_state = 'reg_reject'

    def action_document_rejected(self):
        self.doc_verify = True
        for rec in self:
            rec.doc_state = 'rejected'

    @api.depends('application_id')
    def _get_program(self):
        for rec in self:
            rec.program_id = False
            if len(rec.application_id.preference_ids)>0:
                rec.program_id = rec.application_id.preference_ids[0].program_id

    @api.depends('obtained_cgpa','obt_marks','total_marks','total_cgpa','cgpa_check')
    def _get_cgpa_percentage(self):
        for rec in self:
            rec.cgpa_percentage = 0
            if rec.obtained_cgpa>0:
                cgpa_percentage = (rec.obtained_cgpa/4)*100 
                rec.cgpa_percentage = cgpa_percentage
                rec.percentage = cgpa_percentage
    
    @api.onchange('obt_marks','total_marks')
    def academic_marks(self):
        if self.obt_marks and self.total_marks and self.obt_marks <= self.total_marks:
            self.percentage = (self.obt_marks/self.total_marks)*100
    
