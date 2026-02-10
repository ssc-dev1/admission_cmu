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

    # -------------------------
    # Helper: company-wise checks
    # -------------------------
    def _company_checks_ok(self, application, merit_rec=None, program=None):
        """
        Returns (ok: bool, reason: str) according to company toggles:
          - Merit       -> require a selected merit line (prefer wizard's merit list)
          - Documents   -> require fee_voucher_state == 'verify' AND
                           (verification_status == 'verified' OR all academic docs verified)
          - Scholarship -> require scholarship_id
        Only the toggled-on checks are enforced.
        """
        company = self.env.company

        # Merit check (if enabled)
        if getattr(company, 'challan_check_merit_list', False):
            ml_domain = [('applicant_id', '=', application.id), ('selected', '=', True)]
            if merit_rec:
                ml_domain.append(('merit_reg_id', '=', merit_rec.id))
            merit_line = self.env['odoocms.merit.register.line'].sudo().search(ml_domain, limit=1)
        if not merit_line:
                return (False, "Merit not found/selected")
        if getattr(company, 'challan_check_offer_letter', False):
                exists = self.env['ucp.offer.letter'].sudo().search_count([
                    ('applicant_id', '=', application.id)
                ])
                if not exists:
                    raise UserError(_("The offer letter must be sent to the applicant before proceeding."))

        # Document check (if enabled)
        if getattr(company, 'challan_check_document_verification', False):
            voucher_ok = (getattr(application, 'fee_voucher_state', False) == 'verify')
            status_ok = (getattr(application, 'verification_status', '') == 'verified')
            docs_ok = all(x.doc_state in ('yes', 'reg_verified') for x in application.applicant_academic_ids)
            if not (voucher_ok and (status_ok or docs_ok)):
                return (False, "Documents not verified")

        # Scholarship check (if enabled)
        if getattr(company, 'challan_check_scholarship', False):
            if not application.scholarship_id:
                return (False, "Scholarship missing")

        return (True, "OK")

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
        if not self.lines:
            return
        for line in self.lines.filtered(lambda a: not a.main_challan):
            app = line.application_id

            ok, reason = self._company_checks_ok(app, merit_rec=line.merit_id, program=line.program_id)
            if ok:
                # Mark as verified in the log list
                new_rec = self.env['invoice.list'].sudo().create({
                    'applicant_id': app.id,
                    'document_state': 'Verified',
                    'date_generated': fields.Date.today(),
                    'merit_id': line.merit_id.id if line.merit_id else False,
                    'program_id': line.program_id.id if line.program_id else False,
                    'generate_invoice_id': self.id,
                })
                # Create challan(s)
                try:
                    main_challan = app.sudo().action_create_admission_invoice(bypass_check=True)
                except TypeError:
                    main_challan = app.sudo().action_create_admission_invoice()

                # Handle tuple return (main, second) vs single
                main = main_challan[0] if isinstance(main_challan, (list, tuple)) else main_challan

                new_rec.write({'invoice_id': main.id if main else False})
                line.write({
                    'invoice_generated': True,
                    'state': 'invoice',
                    'main_challan': main.id if main else False,
                })
            else:
                # Not verified per enabled checks → log it
                self.env['invoice.list'].sudo().create({
                    'applicant_id': app.id,
                    'document_state': 'Not Verified',
                    'date_generated': fields.Date.today(),
                    'merit_id': line.merit_id.id if line.merit_id else False,
                    'program_id': line.program_id.id if line.program_id else False,
                })

        if self.lines and all([ln.invoice_generated for ln in self.lines]):
            self.state = 'invoice'

    def generate_admission_invoices_detail(self):
        for rec in self:
            domain = [
                ('merit_reg_id', '=', rec.merit_id.id),
                ('program_id', '=', rec.program_id.id),
                ('selected', '=', True)
            ]
            applicants = self.env['odoocms.merit.register.line'].search(domain)
            if not applicants:
                continue

            # Filter applicants by company toggles and absence of an existing challan
            eligible = []
            for ml in applicants:
                app = ml.applicant_id
                if app.admission_inv_id:
                    continue
                ok, _ = rec._company_checks_ok(app, merit_rec=rec.merit_id, program=rec.program_id)
                if ok:
                    eligible.append(ml)

            for applicant in eligible:
                app = applicant.applicant_id
                scholarship_percentage = 0.0
                already_exits = self.env['generate.invoice.line'].search([
                    ('application_id', '=', app.id),
                    ('parent_id', '=', rec.id)
                ])
                if already_exits:
                    raise UserError(_('Application %s already exist') % app.application_no)

                # Fee preview math
                credit_hrs, program_batch = rec.get_courses_cnt(rec.merit_id, rec.program_id)
                fee_amount = credit_hrs * program_batch.per_credit_hour_fee if program_batch else 0.0

                scholarship_amount = 0.0
                if app.scholarship_id and app.scholarship_id.line_ids:
                    scholarship_percentage = app.scholarship_id.line_ids[0].percentage
                    scholarship_amount = round(fee_amount * (scholarship_percentage / 100.0), 2)

                adm_fee = program_batch.admission_fee if program_batch else 0.0
                net_amount = fee_amount + adm_fee - scholarship_amount

                data_values = {
                    'merit_id': rec.merit_id.id,
                    'program_id': rec.program_id.id,
                    'company_id': rec.company_id.id,
                    'application_id': app.id,
                    'credit_hrs': credit_hrs,
                    'credit_hrs_fee': program_batch.per_credit_hour_fee if program_batch else 0.0,
                    'parent_id': rec.id,
                    'fee_amount': fee_amount,
                    'admission_amount': adm_fee,
                    'scholarship_amount': scholarship_amount,
                    'net_amount': net_amount,
                    'state': 'detail',
                    'scholarship_id': app.scholarship_id.id if app.scholarship_id else False,
                    'scholarship_percentage': scholarship_percentage,
                    'doc_verify': True,
                }
                self.env['generate.invoice.line'].sudo().create(data_values)
                rec.state = 'detail'
    def get_courses_cnt(self, merit_register_id, program_id):
        credit_hrs = 0
        program_batch = self.env['odoocms.batch'].search([('program_id', '=', program_id.id),
                                                          ('session_id', '=', merit_register_id.register_id.academic_session_id.id),
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
