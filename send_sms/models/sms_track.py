import pdb
from odoo import api, fields, models, tools


class sms_track(models.Model):
    _name = "sms_track"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "SMS Tracking"

    name = fields.Char('Name')
    model_id = fields.Char('Model', readonly=True)
    mobile_no = fields.Char('Mobile No.', readonly=True)
    response_id = fields.Char('Response', readonly=True)
    message_id = fields.Text('Messages', readonly=True)
    gateway_id = fields.Many2one('gateway_setup', string='GateWay', readonly=True)
    send_to = fields.Char('Send To')
    status = fields.Selection([('0', 'Invalid Parameters'),
                               ('1', 'Successfully Delivered'),
                               ('2', 'Parameter Missing'),
                               ('4', 'Account Expired'),
                               ], string='Status', compute="_compute_status", store=True)

    sms_nature = fields.Selection([('login', 'Login'),
                                   ('other', 'Other')
                                   ], string='Nature')

    type = fields.Selection([('faculty', 'Faculty'),
                             ('staff', 'Staff'),
                             ('student', 'Student'),
                             ], string="Type")

    department_id = fields.Many2one('hr.department', 'Department')
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')
    date = fields.Date('Date', default=fields.Date.today())
    mobile_network = fields.Selection([('Moblink', 'Moblink'),
                                       ('warid', 'Warid'),
                                       ('telenor', 'Telenor'),
                                       ('ufone', 'Ufone'),
                                       ('zong', 'Zong')
                                       ], string='Mobile Network')
    sms_cron_id = fields.Many2one('send_sms.cron', 'SMS Cron Ref')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.model
    def sms_track_create(self, record_id, sms_rendered_content, rendered_sms_to, response, model, gateway_id, send_to, sms_nature, type, department_id, institute_id, mobile_network):
        value = {
            'name': self.env['ir.sequence'].next_by_code('sms_track'),
            'send_to': send_to,
            'sms_nature': sms_nature,
            'type': type,
            'department_id': department_id and department_id.id or False,
            'institute_id': institute_id and institute_id.id or False,
            'model_id': model,
            'mobile_no': rendered_sms_to,
            'mobile_network': mobile_network,
            'message_id': sms_rendered_content,
            'response_id': response,
            'gateway_id': gateway_id,
        }
        track_id = self.create(value)

    @api.depends('response_id')
    def _compute_status(self):
        for rec in self:
            if rec.response_id:
                response = next((char for char in rec.response_id if char.isdigit()), '')
                if response == '-1' or response not in ('0','1','2','3','4'):
                    rec.status = '0'
                else:
                    rec.status = str(int(response))
