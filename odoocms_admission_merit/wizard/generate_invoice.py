import pdb
from odoo import fields, models, _, api
from odoo.exceptions import ValidationError
from datetime import datetime, date


class GenerateInvoiceWizard(models.TransientModel):
    _name = 'generate.invoice.wizard'
    _description = 'Generate Invoice Wizard'

    merit_id = fields.Many2one('odoocms.merit.registers', string='Merit', required=True)
    program_id = fields.Many2one('odoocms.program', string='Program', required=True)
    invoice_ids = fields.One2many('invoice.list', 'invoice_gen_id', 'Invoices')

    @api.onchange('merit_id')
    def onchange_merit_id(self):
        for rec in self:
            return {'domain': {'program_id': [('id', 'in', rec.merit_id.program_ids.program_id.ids)]}}

    def generate_admission_invoices(self):
        invoice_list = self.env['invoice.list'].search([])
        invoice_list.unlink()
        
        # Get company configuration for challan checks
        company = self.env.company
        
        for merit_line in self.merit_id.merit_register_ids.filtered(lambda x: x.selected==True):
            check_application = merit_line.applicant_id
            
            # Document Verification Check (only if enabled in company config)
            doc_verified = True
            if company.challan_check_document_verification:
                doc_verified = all(x.doc_state == 'yes' for x in check_application.applicant_academic_ids)
            
            # Scholarship Check (only if enabled in company config) 
            scholarship_assigned = True
            if company.challan_check_scholarship:
                scholarship_assigned = bool(check_application.scholarship_id)
            
            # Merit List Check (only if enabled in company config)
            merit_check_passed = True
            if company.challan_check_merit_list:
                merit_check_passed = merit_line.selected == True
            
            # Generate invoice if all enabled checks pass
            if doc_verified and scholarship_assigned and merit_check_passed:
                list = self.env['invoice.list'].sudo()
                list.create({
                    'applicant_id': check_application.id,
                    'document_state': 'Verified',
                })
                check_application.action_create_admission_invoice()

            else:
                list = self.env['invoice.list'].search([])
                list.create({
                    'applicant_id': check_application.id,
                    'document_state': 'Not Verified',
                })
