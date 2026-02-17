# -*- coding: utf-8 -*-
import pdb
from datetime import date
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError, UserError


import logging

_logger = logging.getLogger(__name__)


class OdooCMSGenerateInvoice(models.TransientModel):
    _name = 'odoocms.generate.invoice'
    _description = 'Generate Invoice'

    @api.model
    def _get_students(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        tag_ids = self.env['odoocms.student.tag'].search([('graduate_line', '=', True)])
        domain = [('id', 'in', active_ids), ('state', 'in', ('enroll', 'defer', 'transferred'))]
        if tag_ids:
            domain.append(('tag_ids', 'not in', tag_ids.ids))
        student_ids = self.env['odoocms.student'].search(domain)
        if student_ids:
            return student_ids and student_ids.ids or []

    @api.model
    def _get_registrations(self):
        if self.env.context.get('active_model', False) == 'odoocms.course.registration' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    @api.model
    def _get_defer_requests(self):
        if self.env.context.get('active_model', False) == 'odoocms.student.term.defer' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    @api.model
    def _get_resume_requests(self):
        if self.env.context.get('active_model', False) == 'odoocms.student.term.resume' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    student_ids = fields.Many2many('odoocms.student', 'generate_invoice_student_rel', 'invoice_id', 'student_id', string='Students',
        help="""Invoices for Only selected Students will be Generated.""", default=_get_students)
    reg_ids = fields.Many2many('odoocms.course.registration', 'generate_invoice_course_registration_rel', 'invoice_id', 'course_reg_id', string="Registrations",
        help="""Invoices for Only selected Registrations will be Generated.""", default=_get_registrations)
    defer_ids = fields.Many2many('odoocms.student.term.defer', 'generate_invoice_term_defer_rel', 'invoice_id', 'term_defer_id', string="Defer Requests",
        help="""Invoices for Only selected Requests will be Generated.""", default=_get_defer_requests)
    resume_ids = fields.Many2many('odoocms.student.term.resume', 'generate_invoice_term_resume_rel', 'invoice_id', 'term_resume_id', string="Resume Requests",
        help="""Invoices for Only selected Requests will be Generated.""", default=_get_resume_requests)

    receipt_type_ids = fields.Many2many('odoocms.receipt.type', 'generate_invoice_receipt_type_rel', 'invoice_id', 'receipt_type_id', string='Receipt For')
    semester_required = fields.Boolean('Semester Required?', default=False)
    override_amount = fields.Boolean('Override Amount?', default=False)

    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    date_due = fields.Date('Due Date', default=(fields.Date.today() + relativedelta(days=7)))
    payment_term_id = fields.Many2one('account.payment.term', string='Payment Terms', check_company=True)

    fixed_type = fields.Boolean('Fixed Receipt Type', default=False)
    registration_id = fields.Many2one('odoocms.student.course', 'Subject')

    hostel_challan_months = fields.Integer('Challan Months', default=6)

    tag = fields.Char('Tag', help='Batch Number etc...', default=lambda self: self.env['ir.sequence'].next_by_code('odoocms.student.invoice'), copy=False, readonly=True)
    reference = fields.Char('Reference')

    description_id = fields.Many2one('odoocms.fee.description', 'Fee Description')
    comment = fields.Html('Description of Invoice', help='Description of Invoice')

    override_line = fields.One2many('odoocms.invoice.amount.override', 'invoice_id', 'Override Lines')
    rechecking_subject = fields.Integer('Rechecking Subjects')
    rechecking_id = fields.Char('Rechecking reference')
    description_sub = fields.Char(string='Description')
    charge_annual_fee = fields.Boolean('Charge Annual Fee', default=False)
    apply_taxes = fields.Boolean('Apply Taxes', default=False)

    check_student_tags = fields.Many2many('odoocms.student.tag', 'generate_invoice_check_student_tags_rel', 'wiz_id', 'tag_id', 'Check Student Tags')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.onchange('description_id')
    def onchange_description_id(self):
        if self.description_id:
            self.comment = self.description_id.description
        else:
            self.comment = ''

    # @api.onchange('term_id')
    # def onchange_academic_term_id(self):
    # if self.term_id:
    # 	planning_line = False
    # 	if self.academic_term_id.planning_ids:
    # 		planning_line = self.term_id.planning_ids.filtered(
    # 			lambda l: l.type == 'duesdate') # and student.batch_id.department_id in (l.department_ids)
    # 		if not planning_line:
    # 			planning_line = self.term_id.planning_ids.filtered(lambda l: l.type == 'withdraw' and len(l.department_ids) == 0)
    #
    # 	if planning_line:
    # 		self.date_due = planning_line.date_end
    # 	else:
    # self.date_due = fields.Date.today() + relativedelta(days=7)

    @api.onchange('receipt_type_ids')
    def onchange_receipt_type(self):
        self.semester_required = any([receipt.semester_required for receipt in self.receipt_type_ids])
        self.override_amount = any([receipt.override_amount for receipt in self.receipt_type_ids])
        if self.override_amount:
            for receipt in self.receipt_type_ids.filtered(lambda l: l.override_amount == True):
                for head in receipt.fee_head_ids:
                    values = {
                        'fee_head_id': head.id,
                        'fee_head': head.id,
                        'fee_amount': head.lst_price,
                        'note': 'Test',
                    }
                    self.update({
                        'override_line': [(0, 0, values)],
                    })
                # return {'value': {'field': value}}
        for receipt in self.receipt_type_ids:
            if receipt.comment and not self.comment:
                self.comment = receipt.comment

    def generate_invoice_action(self):
        invoices = self.env['account.move']
        values = {
            'tag': self.tag,
            'reference': self.reference,
            'description': self.comment,
            'date': date.today(),
        }
        invoices_group = self.env['account.move.group'].create(values)
        for student in self.student_ids:
            _logger.info('Student ID %r , Student Code %r', student.id, student.code)
            if self.term_id:
                canceled_invoice_domain = [('student_id', '=', student.id), ('term_id', '=', self.term_id.id), ('state', '=', 'cancel')]
                canceled_invoices = self.env['account.move'].search(canceled_invoice_domain)
                if canceled_invoices:
                    canceled_invoices_reg_domain = [('student_id', '=', student.id), ('term_id', '=', self.term_id.id),('state','!=','cancel'),('invoice_id','in',canceled_invoices.ids)]
                    self.env['odoocms.course.registration'].search(canceled_invoices_reg_domain).invoice_id = False

            term_id = self.term_id
            if not term_id:
                term_id = student.get_student_term(self.term_id, False).term_id

            reg_invoice = self.env['ir.config_parameter'].sudo().get_param('aarsol.reg_invoice','True')
            domain = [('student_id', '=', student.id), ('term_id', '=', term_id.id),('state','!=','cancel')]
            registration_requests = self.env['odoocms.course.registration'].search(domain, order='id')
            if registration_requests and reg_invoice == 'True':
                for registration_request in registration_requests:
                    if registration_request.state == 'draft':
                        registration_request.state = 'submit'
                    student_invoice = registration_request.student_id.generate_registration_invoice(registration_request, receipt_type_ids=self.receipt_type_ids,payment_term_id=self.payment_term_id,date_due=self.date_due)
                    if student_invoice:
                        invoices += student_invoice

                # for student_invoice in student_invoices:
                #     if student_invoice.amount_total == 0:
                #         if not registration_request.state == 'approve':
                #             registration_request.sudo().action_approve()
                #             student_invoice.write({'payment_state': 'paid'})

            else:
                domain = [('student_id', '=', student.id), ('term_id', '=', self.term_id.id), ('state', '!=', 'cancel'), ('receipt_type_ids', 'in', self.receipt_type_ids.mapped('id'))]
                if self.env['account.move'].search(domain):
                    continue

                invoices += student.generate_challan_without_registration(term_id, receipt_type_ids=self.receipt_type_ids,payment_term_id=self.payment_term_id,date_due=self.date_due)

            # invoices += student.generate_invoice_old(
            #     semester=term_id, receipts=self.receipt_type_ids,
            #     date_due=self.date_due, comment=self.comment, tag=self.tag, override_line=self.override_line, reg=False,
            #     invoice_group=invoices_group, registration_id=self.registration_id, charge_annual_fee=self.charge_annual_fee, apply_taxes=self.apply_taxes)

        gr_flag = True  # SARFRAZ
        if not gr_flag:
            for reg in self.reg_ids:
                invoices += reg.student_id.generate_invoice_old(
                    semester=self.term_id, receipts=self.receipt_type_ids, date_due=self.date_due,
                    comment=self.comment, tag=self.tag, override_line=self.override_line, reg=reg,
                    invoice_group=invoices_group)

        for reg in self.defer_ids:
            invoices += reg.student_id.generate_invoice_old(
                semester=self.term_id, receipts=self.receipt_type_ids, date_due=self.date_due,
                comment=self.comment, tag=self.tag, override_line=self.override_line, reg=reg,
                invoice_group=invoices_group)

        for reg in self.resume_ids:
            invoices += reg.student_id.generate_invoice_old(
                semester=self.term_id, receipts=self.receipt_type_ids, date_due=self.date_due,
                comment=self.comment, tag=self.tag, override_line=self.override_line, reg=reg,
                invoice_group=invoices_group, charge_annual_fee=self.charge_annual_fee, apply_taxes=self.apply_taxes)

        if invoices:
            invoice_list = invoices.mapped('id')
            form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', invoice_list)],
                'name': _('Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                    (form_view and form_view.id or False, 'form'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}

    # Temporary Used for the Spring 2021 Hostel Fee Generation
    def generate_hostel_invoice(self):
        due_date = False
        invoices = self.env['account.move']
        values = {
            'tag': self.tag,
            'reference': self.reference,
            'description': self.comment,
            'date': date.today(),
        }

        invoices_group = self.env['account.move.group'].create(values)
        for student in self.student_ids:
            term_id = self.term_id
            if not term_id:
                term_id = student.term_id

            status, invoice = student.generate_hostel_invoice(description_sub=self.description_sub, semester=term_id, receipts=self.receipt_type_ids,date_due=self.date_due, comment=self.comment, tag=self.tag, invoice_group=invoices_group, registration_id=self.registration_id)
            if status:
                invoices += invoice
            else:
                raise UserError("Student %s: Msg: %s" % (student.code,invoice))
        if invoices:
            invoice_list = invoices.mapped('id')
            form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', invoice_list)],
                'name': _('Hostel Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                    (form_view and form_view.id or False, 'form'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}

    # Ad Hoc Charges Fee Generation
    def generate_ad_hoc_charges_invoice_wiz(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids')
        student_ids = False
        if self.env.context.get('active_model', False) == 'odoocms.student' and self.env.context.get('active_ids', False):
            student_ids = self.env['odoocms.student'].browse(self.env.context.get('active_ids'))
        due_date = False
        invoices = self.env['account.move']
        values = {
            'tag': self.tag,
            'reference': self.reference,
            'description': self.comment,
            'date': date.today(),
        }
        invoices_group = self.env['account.move.group'].create(values)
        for student in student_ids:
            term_id = self.term_id
            if not term_id:
                term_id = student.term_id

            invoices += student.generate_ad_hoc_charges_invoice(
                description_sub=self.description_sub, semester=term_id, receipts=self.receipt_type_ids,
                date_due=self.date_due, comment=self.comment, tag=self.tag, invoice_group=invoices_group, registration_id=self.registration_id)
        if invoices:
            invoice_list = invoices.mapped('id')
            form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
            tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
            return {
                'domain': [('id', 'in', invoice_list)],
                'name': _('Ad Hoc Charges Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.move',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                    (form_view and form_view.id or False, 'form'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}


class OdooCMSInvoiceAmountOverride(models.TransientModel):
    _name = 'odoocms.invoice.amount.override'
    _description = 'Invoice Amount Override'

    fee_head_id = fields.Many2one('odoocms.fee.head', string='Fee')
    fee_head = fields.Integer()
    fee_amount = fields.Float('Amount')
    payment_type = fields.Selection(string='Payment Type', related="fee_head_id.payment_type")
    fee_description = fields.Text('Description', related='fee_head_id.description_sale')
    note = fields.Char('Note')
    invoice_id = fields.Many2one('odoocms.generate.invoice', 'Invoice')


