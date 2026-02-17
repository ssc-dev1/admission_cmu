import pdb
import time
import datetime
from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class SuccessMessageWizard(models.TransientModel):
    _name = 'success.message.wizard'
    _description = "Show Message"

    message = fields.Text('Message', required=True)

    def action_close(self):
        return {'type': 'ir.actions.act_window_close'}
