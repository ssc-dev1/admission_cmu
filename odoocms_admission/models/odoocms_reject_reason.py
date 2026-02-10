from odoo import fields, models, _, api
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval
import pdb
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

from odoo.tools.safe_eval import safe_eval
from odoo import tools
import pdb
import logging

_logger = logging.getLogger(__name__)


class OdooCMSApplicationRejectReason(models.Model):
    _name = 'odoocms.application.reject.reason'
    _description = 'Reject Reasons'

    name = fields.Char(string="Reason", required=True, help="Possible Reason for rejecting the Applications")
    code = fields.Char(string='Code')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

