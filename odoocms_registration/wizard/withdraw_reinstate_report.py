from odoo import fields, models, api, _
from odoo.exceptions import UserError


class WithdrawReinstateWizard(models.TransientModel):
    _name = 'withdraw.reinstate.wizard'
    _description = 'Withdraw Reinstate Report'
    
    start_date = fields.Date('Start Date',required=True)
    end_date = fields.Date('End Date',required=True)
    program_id = fields.Many2one('odoocms.program', string='Program',)
    # batch_id = fields.Many2one('odoocms.batch', string='Batched',required=True)
    type = fields.Selection([
        ('withdraw', 'Withdraw'),
        ('reinstate', 'Reinstate'),
    ], string='Report Type',required=True)
    
    def print_report(self):
        datas={
            'start_date': self.start_date,
            'end_date': self.end_date,
            'type': self.type,
            'program_id': self.program_id.id if self.program_id else False,
        }        
        return self.env.ref('odoocms_registration.action_course_withdraw_reinstate_report').with_context(landscape=False).report_action(self,data=datas)
