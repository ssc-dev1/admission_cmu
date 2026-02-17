from odoo.fields import Datetime
from odoo import fields, models, _, api
from odoo.exceptions import AccessError, UserError

class OdooCmsMeritRegisterLine(models.Model):
    _inherit = 'odoocms.merit.register.line'

    bs_percentage = fields.Float(string='BS Percentage', compute='_get_bs_percentage', store=True)
    offer_send_status = fields.Boolean(string="Offer Send Status", default=False)


    def _get_bs_percentage(self):
        for rec in self:
            applicant_marks = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)])
            for degree in applicant_marks.applicant_academic_ids:
                if degree.degree_name.year_age == 16:
                    rec.bs_percentage = degree.percentage
