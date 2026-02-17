from odoo.fields import Datetime
from odoo import fields, models, _, api


class OdooCMSProgramInherit(models.Model):
    _inherit = 'odoocms.program'
    _description = 'Programs'


    enable_shifts = fields.Boolean(string='Enable Shifts', default=False)
    morning = fields.Boolean(string='Morning', default=False)
    evening = fields.Boolean(string='Evening', default=False)
    weekend = fields.Boolean(string='Weekend', default=False)

    def get_enabled_shifts(self):
        """
        Return list of tuples (value, label) for enabled shifts on this program.
        Example: [('morning','Morning'), ('evening','Evening')]
        """
        self.ensure_one()
        choices = []
        if not self.enable_shifts:
            return choices
        if self.morning:
            choices.append(('morning', 'Morning'))
        if self.evening:
            choices.append(('evening', 'Evening'))
        if self.weekend:
            choices.append(('weekend', 'Weekend'))
        return choices




class OdoocmsApplication(models.Model):
    _inherit = 'odoocms.application'

    shift = fields.Selection([
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('weekend', 'Weekend'),
    ], string="Shift", default=False, tracking=True)




class OdoocmsStudent(models.Model):
    _inherit = 'odoocms.student'

    shift = fields.Selection([
        ('morning', 'Morning'),
        ('evening', 'Evening'),
        ('weekend', 'Weekend'),
    ], string="Shift", default=False, tracking=True)
