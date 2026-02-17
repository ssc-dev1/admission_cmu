# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class OdooCMSCourseRegistration(models.Model):
    _inherit = 'odoocms.course.registration'

    invoice_id = fields.Many2one('account.move','Invoice', index=True)
    pass_term = fields.Boolean('Pass', default=False)

    def compute_registration_fee(self):
        for rec in self:
            rec.student_id._compute_registration_fee(rec)

    def cron_compute_registration_fee(self, limit=100):
        regs = self.env['odoocms.course.registration'].search([('to_be','=',True)], limit=limit)
        for reg in regs:
            _logger.warning("Registration Fee: %s, %s" % (reg.id, reg.student_id.code,))
            reg.compute_registration_fee()
            reg.to_be = False

    def cron_submit(self, limit=100):
        regs = self.env['odoocms.course.registration'].search([('to_be','=',True)], limit=limit)
        for reg in regs:
            _logger.warning("Generating Fee: %s, %s" % (reg.id, reg.student_id.code,))
            reg.action_submit()
            reg.to_be = False

    def action_submit(self, web=False):
        res = super().action_submit()
        if res and res == 'Submitted Successfully':  # not web and
            st_term = self.student_id.get_student_term(self.term_id)
            invoice_generate_at_registration_submit = self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.invoice_generate_at_registration_submit','False')
            if invoice_generate_at_registration_submit in ('True','Yes','1') and not self.invoice_id and self.line_ids and not self.env.context.get('no_invoice',False):
                self.student_id.generate_registration_invoice(self)
        return res

    def action_reset_draft(self):
        invoice = self.invoice_id
        if invoice:
            if invoice.payment_state in ('in_payment', 'paid'):
                raise UserError(_('Invoices Linked With this Registration are Paid'))

            # Have to check the relation of challan with others line also
            challan_ids = self.env['odoocms.fee.barcode'].search([('res_id', 'in', invoice.line_ids.ids)])
            challan_ids.sudo().unlink()

            invoice.sudo().with_context(force_delete=True).unlink()
        super().action_reset_draft()

    def action_cancel(self):
        for rec in self:
            rec.line_ids.state = 'cancel'
            rec.state = 'cancel'

            invoices = self.env['account.move'].search([('registration_id', '=', rec.id)])
            if invoices:
                if invoices.filtered(lambda a: a.payment_state in ('in_payment', 'paid')):
                    raise UserError(_('Invoices Linked With this Registration are Paid'))
                for invoice in invoices.filtered(lambda a: a.payment_state not in ('in_payment', 'paid')):
                    invoice.line_ids.mapped('challan_id').unlink()
                    invoice.sudo().unlink()

                audit_line = self.env['odoocms.student.term.audit'].search([('student_id', '=', rec.student_id.id)])
                audit_line._get_amount()
                audit_line._compute_gross()
                audit_line._get_tuition_diff()


class OdooCMSCourseRegistrationLine(models.Model):
    _inherit = 'odoocms.course.registration.line'

    price_unit = fields.Float('Unit Price')
    discount = fields.Float('Discount')
