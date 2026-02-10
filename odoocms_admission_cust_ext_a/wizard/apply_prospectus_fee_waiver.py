from odoo import models, fields, api
from odoo.exceptions import UserError

class ApplyProspectusFeeWaiverWizard(models.TransientModel):
    _name = "apply.prospectus.fee.waiver.wizard"
    _description = "Apply Prospectus Fee Waiver"

    waiver_type_id = fields.Many2one(
        "prospectus.fee.waiver.type",
        string="Prospectus Fee Waiver",
        required=True
    )

    application_id = fields.Many2one(
        "odoocms.application",
        string="Application",
    )

    def apply_waiver(self):
        self.ensure_one()

        app = self.application_id

        invoices = self.env["account.move"].sudo().search([
            ("challan_type", "=", "prospectus_challan"),
            ("application_id", "=", app.id),
            ("state", "=", "posted"),
            ("payment_state", "=", "not_paid"),
        ])
        if not invoices:
            raise UserError("Unpaid Prospectus Challan not found for this application.")
        for invoice in invoices:
            # Move to draft before editing
            if invoice.state == 'posted':
                invoice.button_draft()
            
            # Apply discount percentage
            invoice.line_ids.sudo().write({"discount": self.waiver_type_id.percentage})

            # Post again
            invoice.action_post()

        # Apply tags to the application
        if self.waiver_type_id.tag_ids:
            app.tag_ids |= self.waiver_type_id.tag_ids
        if self.waiver_type_id.percentage ==100:
        # Verify voucher
            app.with_context(self.env.context, skip_sms=True).verify_voucher()
            app.amount =0
            app.fee_voucher_verify_by =self.env.user.id

        # Close the wizard
        return {"type": "ir.actions.act_window_close"}
