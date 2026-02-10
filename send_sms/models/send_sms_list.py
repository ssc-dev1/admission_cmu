from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

import pdb


class SendSMSSList(models.Model):
    _name = "send.sms.list"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Send SMS To List"

    @api.model
    def get_default_gateway_id(self):
        gateway_rec = self.env['gateway_setup'].search([], order='id asc', limit=1)
        return gateway_rec and gateway_rec.id or False

    name = fields.Char(string='Name')
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Date('Date', default=lambda self: fields.Date.context_today(self), tracking=True, index=True)
    type = fields.Selection([('employee', 'Employee'),
                             ('student', 'Student'),
                             ], string='Type', tracking=True, index=True)

    gateway_id = fields.Many2one('gateway_setup', required=True, string='SMS Gateway', tracking=True, default=get_default_gateway_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    sms_body = fields.Text('Body')
    mobile_no_list = fields.Text('Mobile No List')
    sms_length = fields.Integer('Message Length', compute='compute_message_length', store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('sent', 'Sent'),
                              ('cancel', 'Cancelled')
                              ], string='Status', default='draft', index=True)

    @api.model
    def create(self, values):
        record = super(SendSMSSList, self).create(values)
        if not record.name:
            record.name = self.env['ir.sequence'].next_by_code('send.sms.list')
        return record

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('you can delete only Draft Entries '))
        record = super(SendSMSSList, self).unlink()
        return record

    def action_cancel(self):
        self.lines.write({'state': 'cancel'})
        self.state = 'cancel'

    def action_turn_to_draft(self):
        records_to_update = self.filtered(lambda r: r.state == 'cancel')
        records_to_update.write({'state': 'draft'})

    def action_send_list_sms(self):
        mobile_no_list = self.mobile_no_list.split(",")
        if mobile_no_list:
            for mobile_no in mobile_no_list:
                updated_mobile_no = mobile_no.replace('-', '')
                updated_mobile_no = updated_mobile_no.replace(' ', '')
                updated_mobile_no = updated_mobile_no.lstrip('0')
                updated_mobile_no = updated_mobile_no.lstrip('mobile_no')
                message = self.env['send_sms'].sudo().render_template(self.sms_body, 'send.sms.employee', self.id)
                sms_data_values = {
                    'model_id': 'send.sms.list',
                    'res_id': self.id,
                    'mobile_no': updated_mobile_no,
                    'message_id': message,
                    'gateway_id': self.gateway_id and self.gateway_id.id or False,
                    'send_to': '',
                    'sms_nature': 'other',
                    'type': 'student',
                    'department_id': False,
                    'institute_id': False,
                    'mobile_network': '',
                }
                self.env['send_sms.cron'].sudo().create(sms_data_values)

        self.state = 'sent'

    # def action_send_list_sms(self):
    #     mobile_no_list = self.mobile_no_list.split()
    #     if mobile_no_list:
    #         for mobile_no in mobile_no_list:
    #             institute_id = False
    #             # ***** For Employee *****#
    #             if self.type == 'employee':
    #                 employee_id = self.env['hr.employee'].search([('mobile_phone', '=', mobile_no)], order='id desc', limit=1)
    #                 if employee_id:
    #                     track_type = 'staff'
    #                     faculty_staff = self.env['odoocms.faculty.staff'].search([('employee_id', '=', employee_id.id)])
    #                     if faculty_staff:
    #                         institute_id = faculty_staff.institute
    #                         track_type = 'faculty'
    #
    #                     updated_mobile_no = mobile_no.replace('-', '')
    #                     updated_mobile_no = updated_mobile_no.replace(' ', '')
    #                     updated_mobile_no = updated_mobile_no.lstrip('0')
    #                     updated_mobile_no = updated_mobile_no.lstrip('mobile_no')
    #                     message = self.env['send_sms'].sudo().render_template(self.sms_body, 'send.sms.employee', self.id)
    #                     mobile_network = employee_id.mobile_network
    #                     self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, employee_id.id, 'hr.employee', self.gateway_id, employee_id.name,
    #                                                               'other', track_type, employee_id.department_id, institute_id, mobile_network)
    #             # ***** For Student ****#
    #             elif self.type == 'student':
    #                 mobile_network = ''
    #                 student_id = self.env['odoocms.student'].search([('sms_mobile', '=', mobile_no)], order='id desc', limit=1)
    #                 if student_id:
    #                     updated_mobile_no = mobile_no.replace('-', '')
    #                     updated_mobile_no = updated_mobile_no.replace(' ', '')
    #                     updated_mobile_no = updated_mobile_no.lstrip('0')
    #                     updated_mobile_no = updated_mobile_no.lstrip('mobile_no')
    #                     if updated_mobile_no[0:2] == "92":
    #                         updated_mobile_no = mobile_no[2:]
    #                     message = self.env['send_sms'].sudo().render_template(self.sms_body, 'send.sms.employee', self.id)
    #                     self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, student_id.id, 'odoocms.student', self.gateway_id, student_id.name,
    #                                                               'other', 'student', False, student_id.institute_id, mobile_network)
    #         self.state = 'sent'

    @api.depends('sms_body')
    def compute_message_length(self):
        self.sms_length = len(self.sms_body) if self.sms_body else 0
