# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from datetime import date
from odoo.exceptions import UserError



class OdooCMSApplicationTagChange(models.Model):
    _name = 'odoocms.application.tag.change'
    _description = 'Change Application Tag'

    # === LOAD ACTIVE APPLICATIONS EXACTLY LIKE STUDENT WIZARD ===
    @api.model
    def _get_applications(self):
        if (
            self.env.context.get('active_model') == 'odoocms.application'
            and self.env.context.get('active_ids')
        ):
            return self.env.context['active_ids']

    application_ids = fields.Many2many(
        'odoocms.application',
        'tag_change_application_rel',
        'tag_change_id',
        'application_id',
        string='Applications',
        default=_get_applications,
        help="Only selected applications will be processed."
    )

    action = fields.Selection([
        ('add', 'Add'),
        ('remove', 'Remove')
    ], required=True)

    tag_id = fields.Many2one(
        'odoocms.student.tag',
        string='Tag',
        required=True,
        domain="[]",
    )


    date_effective = fields.Date(
        'Date Effective',
        default=date.today()   # ✔ Same as your working wizard
    )

    description = fields.Text('Description', required=True)

    # === APPLY TAGS SAME WAY AS STUDENT WIZARD ===
    def change_application_tag(self):
        if not self.application_ids:
            raise UserError("No applications selected.")

        if not self.tag_id:
            raise UserError("Please select a tag.")

        for app in self.application_ids:

            if self.action == 'add':
                tags = app.tag_ids + self.tag_id
            else:
                tags = app.tag_ids - self.tag_id

            app.with_context({
                'date_effective': self.date_effective,
                'description': self.description,
                'method': 'Application Tag Wizard',
            }).write({
                'tag_ids': [(6, 0, tags.ids)]
            })

        return {'type': 'ir.actions.act_window_close'}
