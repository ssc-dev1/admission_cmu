
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
import pdb

import logging
_logger = logging.getLogger(__name__)


class OdooCMSCareer(models.Model):
    _inherit = "odoocms.career"

    improve_course_limit = fields.Integer('Repeat-Improvement Course Limit', help="How many time a student can repeat course for improvement.", default=1000)


class OdooCMSInstitute(models.Model):
    _inherit = "odoocms.institute"

    def registration_stat(self):
        # [data] = False
        datas = {
            'ids': [],
            'model': 'odoocms.institute',
            # 'form': data
        }
        return self.env.ref('odoocms_registration.action_report_registration_stat').with_context(landscape=False).report_action(self, data=datas, config=False)


