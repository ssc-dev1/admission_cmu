from dateutil.relativedelta import relativedelta
from odoo import models, fields

class OdooCMSAdmissionRegister(models.Model):
    _inherit = 'odoocms.admission.register'

    # Toggle + template field live in MIS now
    enable_welcome_letter = fields.Boolean(
        string='Enable Welcome Letter',
        default=False,
        tracking=True,
        help="If enabled, the Welcome Letter template/tab is available",
    )
    welcome_letter = fields.Html('Welcome Letter')
