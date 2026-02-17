# -*- coding: utf-8 -*-
from odoo import models, fields, api, exceptions, _
import logging

_logger = logging.getLogger(__name__)


class OdooCMSFeeReceiptDeletionLog(models.Model):
    _name = 'odoocms.fee.receipt.deletion.log'
    _inherit = ['odoocms.student.fee.public']
    _description = "Receipt Deletion Logs"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    move_id = fields.Many2one('account.move', 'Receipt')
    barcode = fields.Char('Barcode')
    number = fields.Char('Number')
    student_id = fields.Many2one('odoocms.student', 'Student Name')

    @api.model
    def create(self, values):
        res = super(OdooCMSFeeReceiptDeletionLog, self).create(values)
        if not res.sequence:
            res.name = self.env['ir.sequence'].next_by_code('odoocms.fee.receipt.deletion.log')
        return res


class OdooCMSStudentFeeLedgerDeletionLog(models.Model):
    _name = 'odoocms.student.fee.ledger.deletion.log'
    _inherit = ['odoocms.student.fee.public']
    _description = "Student Ledger Deletion Logs"

    name = fields.Char(string='Name')
    sequence = fields.Integer('Sequence')
    student_id = fields.Many2one('odoocms.student', string='Student')
    invoice_id = fields.Many2one('account.move', string='Student Invoice')
    ledger_id = fields.Many2one('odoocms.student.ledger', 'Ledger Ref')


class OdooCMSStudentLedgerChangesLog(models.Model):
    _name = 'odoocms.student.fee.ledger.changes.log'
    _inherit = ['odoocms.student.fee.public']
    _description = "Student Ledger Changes Logs"

    name = fields.Char(string='Name')
    sequence = fields.Integer('Sequence')
    student_id = fields.Many2one('odoocms.student', string='Student')
    invoice_id = fields.Many2one('account.move', string='Student Invoice')
    ledger_id = fields.Many2one('odoocms.student.ledger', 'Ledger')
    old_credit = fields.Float(string='Old Credit')
    old_debit = fields.Float(string='Old Debit')
    new_credit = fields.Float(string='New Credit')
    new_debit = fields.Float(string='New Debit')
    old_balance = fields.Char(string='Old Balance')
    new_balance = fields.Char(string='New Balance')


class OdooCMSFeePaymentRegisterDeletionLog(models.Model):
    _name = 'odoocms.fee.payment.register.deletion.log'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Fee Payment Register Deletion Logs"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    payment_register = fields.Char('Payment Register')

    @api.model
    def create(self, values):
        res = super(OdooCMSFeePaymentRegisterDeletionLog, self).create(values)
        if not res.sequence:
            res.name = self.env['ir.sequence'].next_by_code('odoocms.fee.payment.register.deletion.log')
        return res


class OdooCMSFeePaymentDeletionLog(models.Model):
    _name = 'odoocms.fee.payment.deletion.log'
    _inherit = ['odoocms.student.fee.public']
    _description = "Fee Payment Deletion Logs"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence')
    move_id = fields.Many2one('account.move', 'Receipt')
    barcode = fields.Char('Barcode')
    number = fields.Char('Number')
    student_id = fields.Many2one('odoocms.student', 'Student Name')
    payment_register = fields.Char('Payment Register')

    @api.model
    def create(self, values):
        res = super(OdooCMSFeePaymentDeletionLog, self).create(values)
        if not res.sequence:
            res.name = self.env['ir.sequence'].next_by_code('odoocms.fee.payment.deletion.log')
        return res
