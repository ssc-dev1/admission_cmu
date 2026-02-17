from odoo import models, fields, api

class OdoocmsApplication(models.Model):
    _inherit = 'odoocms.application'

    def action_export_pictures(self):
        """
        Action method to export profile pictures of selected candidates.
        Creates a URL that triggers the download controller.
        """
        if not self:
            return {'type': 'ir.actions.act_window_close'}

        record_ids = ",".join(str(r) for r in self.ids)
        # Use a relative URL so the request stays on the current host / subdomain,
        # avoiding cross-domain login redirects when using multiple admission portals.
        full_url = f"/download/export_applicant_images?record_ids={record_ids}"

        return {
            'type': 'ir.actions.act_url',
            'url': full_url,
            'target': 'new',
        }


    def action_export_all_docs(self):
        """
        Action method to export all documents of selected candidates.
        Creates a URL that triggers the download controller for all documents.
        """
        if not self:
            return {'type': 'ir.actions.act_window_close'}

        record_ids = ",".join(str(r) for r in self.ids)
        # Same logic as pictures: keep it relative to avoid switching domains.
        full_url = f"/download/export_applicant_all_documents?record_ids={record_ids}"

        return {    
            'type': 'ir.actions.act_url',
            'url': full_url,
            'target': 'new',
        }
        
