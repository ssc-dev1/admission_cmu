# -*- coding: utf-8 -*-
import logging
import pdb
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class OdooCMSFeePaymentRegister(models.Model):
    _inherit = 'odoocms.fee.payment.register'

    payment_mismatch_ids = fields.One2many('odoocms.fee.payments.amount.mismatch', 'payment_register_id', 'Amount Mismatch Detail')
    total_amount_mismatch_receipts = fields.Float('Amount Mismatch Receipts', compute='compute_total_amount_mismatch_receipt', store=True, tracking=True)

    def action_confirm_registration(self, payment, invoice):
        fee_charge_term = int(self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.fee_charge_term'))
        fee_charge_term_rec = self.env['odoocms.academic.term'].browse(fee_charge_term)
        # *****  Registration Approval *****#
        registration_id = invoice.registration_id
        if not registration_id:
            registration_id = self.env['odoocms.course.registration'].sudo().search([('student_id', '=', invoice.student_id.id),
                                                                                     ('term_id', '=', fee_charge_term_rec.id),
                                                                                     ('state', '!=', 'approved')
                                                                                     ], order='id desc', limit=1)
        if registration_id and invoice.challan_type in ('main_challan', 'add_drop', 'admission'):
            registration_id.sudo().action_approve()

        # ***** # Prospectus Fee Handling *****#
        # if invoice.narration == 'Prospectus Fee':
        #     application_id = self.env['odoocms.application'].search([('prospectus_inv_id', '=', invoice.id)])
        #     if application_id:
        #         application_id.write({'fee_voucher_state': 'verify'})

        # ***** # Admission Fee Handling *****#
        # if invoice.is_admission_fee:
        #     student = invoice.application_id.sudo().create_student()
        #     if student:
        #         payment.write({'student_id': student.id})
        #         if not invoice.student_id:
        #             invoice.write({'student_id': student.id, })
        #         if invoice.batch_id:
        #             reg_no = invoice.batch_id.program_id.campus_id.code + invoice.batch_id.session_id.code + invoice.batch_id.program_id.code + self.env['ir.sequence'].next_by_code('student.reg.no.seq')
        #             student.write({'code': reg_no,
        #                            'id_number': reg_no
        #                            })
        #         invoice.application_id.sudo().new_student_registration()
        #         payment_ledger_recs = self.env['odoocms.student.ledger'].search([('invoice_id', '=', invoice.id),
        #                                                                          ('debit', '>', 0)
        #                                                                          ])
        #         if payment_ledger_recs:
        #             payment_ledger_recs.write({
        #                 'student_id': student.id,
        #                 'id_number': student.code
        #             })
        #         invoice.application_id.admission_link_invoice_to_student()

        # ***** Reinstate with Drap Courses@06-06-2023 *****#
        # ***** # Handling Withdrawn Courses, Search Out Withdraw Courses *****#
        if invoice.challan_type in ('2nd_challan', 'installment'):
            reason_id = self.env['odoocms.drop.reason'].search([('finance', '=', True)], limit=1)
            if reason_id:
                withdraw_courses = payment.student_id.course_ids.filtered(lambda a: a.state == "withdraw" and a.withdraw_reason == reason_id)
                if withdraw_courses:
                    withdraw_courses.write({'state': 'current',
                                            'withdraw_date': False,
                                            'withdraw_reason': False,
                                            'grade': False,
                                            })
        # added@11042023
        invoice.write({
            'confirmation_date': fields.Date.today(),
        })

    @api.depends('payment_mismatch_ids')
    def compute_total_amount_mismatch_receipt(self):
        for rec in self:
            rec.total_amount_mismatch_receipts = rec.total_amount_mismatch_receipts and len(rec.total_amount_mismatch_receipts.ids) or 0.0


# ***** This Class Will Handle all the Records Whose Total Amount and Receive Amount not Matched. ****#
class OdoocmsFeePaymentsAmountMismatch(models.Model):
    _name = 'odoocms.fee.payments.amount.mismatch'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Payments Amount Mismatch'

    name = fields.Char('Name')
    barcode = fields.Char('Challan#')
    payment_register_id = fields.Many2one('odoocms.fee.payment.register', 'Payment Register', index=True, ondelete='cascade', auto_join=True)
    invoice_id = fields.Many2one('account.move', 'Invoice')
    invoice_amount = fields.Float('Invoice Amount')
    payment_amount = fields.Float('Payment Amount')
    diff_amount = fields.Float('Diff Amount')
    state = fields.Selection([('Draft', 'Draft'),
                              ('Posted', 'Posted'),
                              ('Cancel', 'Cancel')], string='Status', default='Draft')
    notes = fields.Char('Notes')

    @api.model
    def create(self, values):
        result = super(OdoocmsFeePaymentsAmountMismatch, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.fee.payments.amount.mismatch')
        return result
