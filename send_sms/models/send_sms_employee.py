from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

import pdb


class SendSMSEmployee(models.Model):
    _name = "send.sms.employee"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Send SMS To Employee"

    @api.model
    def get_default_gateway_id(self):
        gateway_rec = self.env['gateway_setup'].search([], order='id asc', limit=1)
        return gateway_rec and gateway_rec.id or False

    name = fields.Char(string='Name')
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Date('Date', default=lambda self: fields.Date.context_today(self), tracking=True, index=True)
    type = fields.Selection([('all', 'All Active Employee'),
                             ('faculty', 'Faculty/Teachers'),
                             ('staff', 'Admin Staff'),
                             ], default='all', string='Type', tracking=True, index=True)
    sub_type = fields.Selection([('visiting', 'Visiting'),
                                 ('permanent', 'Permanent'),
                                 ('both', 'Both'),
                                 ], string='Sub Type', tracking=True)

    department_ids = fields.Many2many('hr.department', 'send_sms_employee_department_rel1', 'send_sms_employee_id', 'department_id', 'Departments')
    employee_ids = fields.Many2many('hr.employee', 'send_sms_employee_employee_rel1', 'send_sms_employee_id', 'employee_id', 'Departments')

    excluded_department_ids = fields.Many2many('hr.department', 'send_sms_employee_excluded_department_rel1', 'send_sms_employee_id', 'excluded_department_id', 'Excluded Departments')
    excluded_employee_ids = fields.Many2many('hr.employee', 'send_sms_employee_excluded_employee_rel1', 'send_sms_employee_id', 'excluded_employee_id', 'Excluded Departments')

    gateway_id = fields.Many2one('gateway_setup', required=True, string='SMS Gateway', tracking=True, default=get_default_gateway_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    sms_body = fields.Text('Body')
    sms_length = fields.Integer('Message Length', compute='compute_message_length', store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('detail', 'Detail Generated'),
                              ('sent', 'Sent'),
                              ('cancel', 'Cancelled')
                              ], string='Status', default='draft', index=True)
    lines = fields.One2many('send.sms.employee.line', 'employee_send_sms_id', 'Lines')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, values):
        record = super(SendSMSEmployee, self).create(values)
        if not record.name:
            record.name = self.env['ir.sequence'].next_by_code('send.sms.employee')
        return record

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('you can delete only Draft Entries '))
        record = super(SendSMSEmployee, self).unlink()
        return record

    def action_cancel(self):
        self.lines.write({'state': 'cancel'})
        self.state = 'cancel'

    def action_turn_to_draft(self):
        if self.state == 'detail':
            self.sudo().lines.unlink()
        records_to_update = self.filtered(lambda r: r.state in ('cancel', 'detail'))
        records_to_update.write({'state': 'draft'})

    def action_generate_detail(self):
        employee_ids = self.env['hr.employee']
        if self.employee_ids:
            employee_ids = self.employee_ids

        if not self.employee_ids:
            dom = [('state', '=', 'active'), ('company_id', '=', self.company_id.id)]
            if self.type == 'faculty':
                dom.append(('employee_type_id.name', '=', 'Academic'))
                if self.sub_type == 'permanent':
                    dom.append(('employment_nature', 'in', ('permanent', 'contract')))
                elif self.sub_type == 'visiting':
                    dom.append(('employment_nature', '=', 'visiting'))
            elif self.type == 'staff':
                dom.append(('employee_type_id.name', '=', 'Non Academic'))

            if self.department_ids:
                dom.append(('department_id', 'in', self.department_ids.ids))
            if self.excluded_department_ids:
                dom.append(('department_id', 'not in', self.excluded_department_ids.ids))
            if self.excluded_employee_ids:
                dom.append(('id', 'not in', self.excluded_employee_ids.ids))
            employee_ids = self.env['hr.employee'].sudo().search(dom)

        if employee_ids:
            for employee_id in employee_ids.filtered(lambda a: a.mobile_phone):
                already_exists = self.env['send.sms.employee.line'].sudo().search([('employee_id', '=', employee_id.id), ('employee_send_sms_id', '=', self.id)])
                if not already_exists:
                    faculty_staff = self.env['odoocms.faculty.staff'].search([('employee_id', '=', employee_id.id)])
                    mobile_no = employee_id.mobile_phone.replace('-', '')
                    mobile_no = mobile_no.replace(' ', '')
                    mobile_no = mobile_no.lstrip('0')
                    mobile_no = mobile_no.lstrip('mobile_no')
                    if mobile_no[0:2] == "92":
                        mobile_no = mobile_no[2:]
                    track_type = 'staff'
                    if faculty_staff:
                        track_type = 'faculty'
                    emp_values = {
                        'employee_id': employee_id.id,
                        'employee_code': employee_id.code,
                        'employee_name': employee_id.name,
                        'department_id': employee_id.department_id and employee_id.department_id.id or False,
                        'job_id': employee_id.job_id and employee_id.job_id.id or False,
                        'mobile_no': mobile_no,
                        'date': fields.Date.context_today(self),
                        'employee_send_sms_id': self.id,
                        'institute_id': faculty_staff.institute.id if faculty_staff else False,
                        'state': 'detail',
                        'employee_type': track_type,
                    }
                    self.env['send.sms.employee.line'].sudo().create(emp_values)
            self.state = 'detail'

    def action_employee_sms(self):
        message = self.env['send_sms'].sudo().render_template(self.sms_body, 'send.sms.employee', self.id)
        for line in self.lines.filtered(lambda a: not a.sent):
            mobile_network = line.employee_id.mobile_network
            self.env['send_sms'].sudo().send_sms_link(message, line.mobile_no, line.employee_id.id, 'hr.employee', line.employee_send_sms_id.gateway_id, line.employee_name,
                                                      'other', line.employee_type, line.department_id, line.institute_id, mobile_network)
            line.write({'sent': True, 'state': 'sent'})
        if all([ln.sent for ln in self.lines]):
            self.state = 'sent'

    @api.depends('sms_body')
    def compute_message_length(self):
        self.sms_length = len(self.sms_body) if self.sms_body else 0


class SendSMSEmployeeLines(models.Model):
    _name = "send.sms.employee.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Send SMS To Employee Detail"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    employee_id = fields.Many2one('hr.employee', tracking=True)
    employee_name = fields.Char('Employee Name')
    employee_code = fields.Char('Employee Code')
    department_id = fields.Many2one('hr.department', 'Department')
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')
    job_id = fields.Many2one('hr.job', 'Designation')
    mobile_no = fields.Char('Mobile No')
    date = fields.Date('Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('detail', 'Detail Generated'),
                              ('sent', 'Sent'),
                              ('cancel', 'Cancelled')
                              ], string='Status', default='draft', index=True)
    sent = fields.Boolean('Sent', default=False)
    employee_send_sms_id = fields.Many2one('send.sms.employee', 'Employee SMS Ref', index=True, ondelete='cascade')
    sms_track_id = fields.Many2one('sms_track', 'SMS Track')
    employee_type = fields.Selection([('faculty', 'Faculty'),
                                      ('staff', 'Staff'),
                                      ], string="Type")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)
