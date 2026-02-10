from odoo import models, fields

class ProspectusFeeWaiverType(models.Model):
    _name = "prospectus.fee.waiver.type"
    _description = "Prospectus Fee Waiver Type"

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    percentage = fields.Float(string="Waiver %")

    # FIXED: use a unique relation table
    tag_ids = fields.Many2many(
        'odoocms.student.tag',
        'prospectus_fee_waiver_tag_rel',
        'waiver_id',                       
        'tag_id',                   
        string='Group/Tag'
    )


class OdoocmsApplication(models.Model):
    _inherit = "odoocms.application"

    tag_ids = fields.Many2many(
        'odoocms.student.tag',
        'application_tag_rel',
        'application_id',
        'tag_id',
        string='Tags'
    )

    def open_fee_waiver_wizard(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Apply Prospectus Fee Waiver",
            "res_model": "apply.prospectus.fee.waiver.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_application_id": self.id},
        }
