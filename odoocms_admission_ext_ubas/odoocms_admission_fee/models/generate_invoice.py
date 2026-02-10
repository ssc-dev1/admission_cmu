# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError
import pdb


class GenerateInvoice(models.Model):
    _name = 'generate.invoice'
    _description = 'Generate Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', index=True, compute='_compute_name', store=True)
    sequence = fields.Integer('Sequence')
    merit_id = fields.Many2one('odoocms.merit.registers', "Merit List", required=True, tracking=True, index=True)
    program_id = fields.Many2one('odoocms.program', related='merit_id.program_id', string="Program", store=True, index=True)
    invoice_ids = fields.One2many('invoice.list', 'invoice_id', 'Invoices')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    state = fields.Selection([('draft', 'Draft'),
                              ('detail', 'Detail Generated'),
                              ('invoice', 'Invoice Generated'),
                              ('cancel', 'Cancel')
                              ], default='draft', string='Status', tracking=True, index=True)

    date = fields.Date('Date', default=fields.Date.today())
    lines = fields.One2many('generate.invoice.line', 'parent_id', 'Lines')

    total_applicants = fields.Integer('Total Applicants', compute='_compute_total_amount', store=True)
    total_amount = fields.Float('Total Amount', compute='_compute_total_amount', store=True)
    total_admission_amount = fields.Float('Total Admission Amount', compute='_compute_total_amount', store=True)
    total_scholarship_amount = fields.Float('Total Scholarship Amount', compute='_compute_total_amount', store=True)
    net_receivable = fields.Float('Net Receivable', compute='_compute_total_amount', store=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.model
    def create(self, values):
        res = super(GenerateInvoice, self).create(values)
        return res

    def unlink(self):
        for rec in self:
            if rec.state in ('draft', 'cancel'):
                raise UserError(_("You cannot Delete this Record"))
        super(GenerateInvoice, self).unlink()

    @api.onchange('merit_id')
    def onchange_merit_id(self):
        for rec in self:
            return {'domain': {'program_id': [('id', 'in', rec.merit_id.program_ids.program_id.ids)]}}

    @api.depends('program_id', 'merit_id')
    def _compute_name(self):
        for rec in self:
            name = ''
            if rec.program_id and rec.merit_id:
                rec.name = rec.merit_id.register_id.term_id.name + '/' + rec.program_id.code
            else:
                rec.name = ''

    @api.depends('lines')
    def _compute_total_amount(self):
        for rec in self:
            fee_amt = 0
            adm_amt = 0
            scholarship_amt = 0
            net_amt = 0
            rec.total_applicants = len(rec.lines)
            for line in rec.lines:
                fee_amt += line.fee_amount
                adm_amt += line.admission_amount
                scholarship_amt += line.scholarship_amount
                net_amt += line.net_amount

            rec.total_amount = fee_amt
            rec.total_admission_amount = adm_amt
            rec.total_scholarship_amount = scholarship_amt
            rec.net_receivable = net_amt

    def generate_admission_invoices(self):
        if self.lines:
            for line in self.lines.filtered(lambda a: not a.main_challan):
                check_application = line.application_id
                # For CUST
                # if check_application.fee_voucher_state == 'verify' and check_application.applicant_academic_ids.filtered(lambda x: x.doc_state == 'yes'):

                # Changed For UCP
                if check_application.fee_voucher_state == 'verify' and all(x.doc_state == 'yes' for x in check_application.applicant_academic_ids) and check_application.scholarship_id:
                    new_rec = self.env['invoice.list'].sudo().create({
                        'applicant_id': check_application.id,
                        'document_state': 'Verified',
                        'date_generated': fields.Date.today(),
                        'merit_id': line.merit_id and line.merit_id.id or False,
                        'program_id': line.program_id and line.program_id.id or False,
                        'generate_invoice_id': self.id,
                    })
                    main_challan = check_application.sudo().action_create_admission_invoice()
                    new_rec.write({
                        'invoice_id': main_challan and main_challan.id or False
                    })
                    line.write({
                        'invoice_generated': True,
                        'state': 'invoice',
                        'main_challan': main_challan and main_challan.id or False,
                    })

                elif check_application.fee_voucher_state != 'verify' or check_application.applicant_academic_ids.filtered(
                        lambda x: x.doc_state != 'yes'):
                    self.env['invoice.list'].sudo().create({
                        'applicant_id': check_application.id,
                        'document_state': 'Not Verified',
                        'date_generated': fields.Date.today(),
                        'merit_id': line.merit_id and line.merit_id.id or False,
                        'program_id': line.program_id and line.program_id.id or False,
                    })
            if all([ln.invoice_generated for ln in self.lines]):
                self.state = 'invoice'

    def generate_admission_invoices_detail(self):
        for rec in self:
            applicants = self.env['odoocms.merit.register.line'].search([('merit_reg_id', '=', rec.merit_id.id),
                                                                         ('program_id', '=', rec.program_id.id),
                                                                         ('selected', '=', True)])
            if applicants:
                for applicant in applicants.filtered(lambda a: all(x.doc_state == 'yes' for x in a.applicant_id.applicant_academic_ids) and a.applicant_id.scholarship_id):
                    scholarship_percentage = 0
                    already_exits = self.env['generate.invoice.line'].search([('application_id', '=', applicant.applicant_id.id),
                                                                              ('parent_id', '=', rec.id)
                                                                              ])
                    if already_exits:
                        raise UserError(_('Application %s already exist') % applicant.applicant_id.application_no)
                    scholarship_amount = 0
                    credit_hrs, program_batch = self.get_courses_cnt(rec.merit_id, rec.program_id)
                    fee_amount = credit_hrs * program_batch.per_credit_hour_fee
                    if applicant.applicant_id.scholarship_id:
                        scholarship_percentage = applicant.applicant_id.scholarship_id.line_ids[0].percentage
                        scholarship_amount = round(fee_amount * (scholarship_percentage / 100), 2)
                    net_amount = fee_amount + program_batch.admission_fee - scholarship_amount

                    data_values = {
                        'merit_id': rec.merit_id.id,
                        'program_id': rec.program_id.id,
                        'company_id': rec.company_id.id,
                        'application_id': applicant.applicant_id.id,
                        'credit_hrs': credit_hrs,
                        'credit_hrs_fee': program_batch.per_credit_hour_fee,
                        'parent_id': rec.id,
                        'fee_amount': fee_amount,
                        'admission_amount': program_batch.admission_fee,
                        'scholarship_amount': scholarship_amount,
                        'net_amount': net_amount,
                        'state': 'detail',
                        'scholarship_id': applicant.applicant_id.scholarship_id and applicant.applicant_id.scholarship_id.id or False,
                        'scholarship_percentage': scholarship_percentage,
                        'doc_verify': True,
                    }
                    self.env['generate.invoice.line'].sudo().create(data_values)
                    rec.state = 'detail'

    def get_courses_cnt(self, merit_register_id, program_id):
        credit_hrs = 0
        program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id),
                                                          ('session_id', '=', merit_register_id.register_id.academic_session_id.id),
                                                          ('term_id', '=', merit_register_id.register_id.term_id.id),
                                                          ('career_id', '=', merit_register_id.register_id.career_id.id)])
        if program_batch:
            study_scheme_id = program_batch.study_scheme_id
            first_semester_study_scheme_lines = study_scheme_id.line_ids.filtered(lambda a: a.semester_id.number == 1)
            for first_semester_study_scheme_line in first_semester_study_scheme_lines:
                credit_hrs += first_semester_study_scheme_line.credits
        return credit_hrs, program_batch


class GenerateInvoiceLine(models.Model):
    _name = 'generate.invoice.line'
    _description = 'Generate Invoice Line Detail'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', index=True, compute='_compute_name', store=True)
    sequence = fields.Integer('Sequence')
    merit_id = fields.Many2one('odoocms.merit.registers', "Merit List", required=True, tracking=True, index=True)
    program_id = fields.Many2one('odoocms.program', "Program", required=True, tracking=True, index=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    application_id = fields.Many2one('odoocms.application', 'Application')
    applicant_name = fields.Char(related='application_id.name', string='Applicant Name', store=True)
    doc_verify = fields.Boolean(string='Doc Verify')

    parent_id = fields.Many2one('generate.invoice', 'Parent', ondelete='cascade', index=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('detail', 'Detail Generated'),
                              ('invoice', 'Invoice Generated'),
                              ('cancel', 'Cancel')
                              ], default='draft', string='Status', tracking=True, index=True)

    credit_hrs = fields.Integer('Credit Hrs')
    credit_hrs_fee = fields.Float('Credit Hrs Fee')
    fee_amount = fields.Float('Fee Amount')
    admission_amount = fields.Float('Admission Amount')
    scholarship_amount = fields.Float('Scholarship Amount')
    net_amount = fields.Float('Net Receivable')
    main_challan = fields.Many2one('account.move', 'Main Challan')
    second_challan = fields.Many2one('account.move', 'Second Challan')
    date = fields.Date('Date', default=fields.Date.today())
    invoice_generated = fields.Boolean('Invoice Generated', default=False)

    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Scholarship')
    scholarship_percentage = fields.Float('Scholarship %')
