from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError

import pdb


class SendSMSStudent(models.Model):
    _name = "send.sms.student"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Send SMS To Students"

    @api.model
    def get_default_gateway_id(self):
        gateway_rec = self.env['gateway_setup'].search([], order='id asc', limit=1)
        return gateway_rec and gateway_rec.id or False

    name = fields.Char(string='Name')
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Date('Date', default=lambda self: fields.Date.context_today(self), tracking=True, index=True)
    type = fields.Selection([('all', 'All'),
                             ('enroll', 'Admitted'),
                             ('alumni', 'Alumni'),
                             ('deferred', 'Deferred'),
                             ], default='enroll', string='Type', tracking=True, index=True)

    batch_ids = fields.Many2many('odoocms.batch', 'send_sms_student_batch_rel1', 'send_sms_student_id', 'batch_id', 'Batches')
    program_ids = fields.Many2many('odoocms.program', 'send_sms_student_program_rel1', 'send_sms_student_id', 'program_id', 'Programs')
    session_ids = fields.Many2many('odoocms.academic.session', 'send_sms_student_session_rel1', 'send_sms_student_id', 'session_id', 'Sessions')
    institute_ids = fields.Many2many('odoocms.institute', 'send_sms_student_institute_rel1', 'send_sms_student_id', 'institute_id', 'Faculties')
    student_ids = fields.Many2many('odoocms.student', 'send_sms_student_student_rel1', 'send_sms_student_id', 'student_id', 'Students')

    excluded_batch_ids = fields.Many2many('odoocms.batch', 'send_sms_student_excluded_batch_rel1', 'send_sms_student_id', 'excluded_batch_id', 'Excluded Batches')
    excluded_program_ids = fields.Many2many('odoocms.program', 'send_sms_student_excluded_program_rel1', 'send_sms_student_id', 'excluded_program_id', 'Excluded Programs')
    excluded_session_ids = fields.Many2many('odoocms.academic.session', 'send_sms_student_excluded_session_rel1', 'send_sms_student_id', 'excluded_session_id', 'Excluded Sessions')
    excluded_institute_ids = fields.Many2many('odoocms.institute', 'send_sms_student_excluded_institute_rel1', 'send_sms_student_id', 'excluded_institute_id', 'Excluded Faculties')
    excluded_student_ids = fields.Many2many('odoocms.student', 'send_sms_student_excluded_student_rel1', 'send_sms_student_id', 'excluded_student_id', 'Excluded Students')

    gateway_id = fields.Many2one('gateway_setup', required=True, string='SMS Gateway', tracking=True, default=get_default_gateway_id)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    sms_body = fields.Text('Body')
    sms_length = fields.Integer('Message Length', compute='compute_message_length', store=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('detail', 'Detail Generated'),
                              ('sent', 'Sent'),
                              ('cancel', 'Cancelled')
                              ], string='Status', default='draft', index=True)
    lines = fields.One2many('send.sms.student.line', 'student_send_sms_id', 'Lines')

    @api.model
    def create(self, values):
        record = super(SendSMSStudent, self).create(values)
        if not record.name:
            record.name = self.env['ir.sequence'].next_by_code('send.sms.student')
        return record

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('you can delete only Draft Entries '))
        record = super(SendSMSStudent, self).unlink()
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
        student_ids = self.env['odoocms.student']
        if self.student_ids:
            student_ids = self.student_ids

        if not self.student_ids:
            dom = [('state', '=', self.type)]
            if self.batch_ids:
                dom.append(('batch_id', 'in', self.batch_ids.ids))
            if self.program_ids:
                dom.append(('program_id', 'in', self.program_ids.ids))
            if self.session_ids:
                dom.append(('session_id', 'in', self.session_ids.ids))
            if self.institute_ids:
                dom.append(('institute_id', 'in', self.institute_ids.ids))

            # Excluded
            if self.excluded_batch_ids:
                dom.append(('batch_id', 'not in', self.excluded_batch_ids.ids))
            if self.excluded_program_ids:
                dom.append(('program_ids', 'not in', self.excluded_program_ids.ids))
            if self.excluded_session_ids:
                dom.append(('session_id', 'not in', self.excluded_session_ids.ids))
            if self.excluded_institute_ids:
                dom.append(('institute_ids', 'not in', self.excluded_institute_ids.ids))
            if self.excluded_student_ids:
                dom.append(('id', 'not in', self.excluded_student_ids.ids))
            student_ids = self.env['odoocms.student'].sudo().search(dom)

        if student_ids:
            for student_id in student_ids.filtered(lambda a: a.sms_mobile):
                already_exists = self.env['send.sms.student.line'].sudo().search([('student_id', '=', student_id.id), ('student_send_sms_id', '=', self.id)])
                if not already_exists:
                    mobile_no = student_id.sms_mobile.replace('-', '')
                    mobile_no = mobile_no.replace(' ', '')
                    mobile_no = mobile_no.lstrip('0')
                    mobile_no = mobile_no.lstrip('mobile_no')
                    if mobile_no[0:2] == "92":
                        mobile_no = mobile_no[2:]

                    student_values = {
                        'student_id': student_id.id,
                        'student_code': student_id.code,
                        'student_name': student_id.name,
                        'batch_id': student_id.batch_id and student_id.batch_id.id or False,
                        'institute_id': student_id.institute_id and student_id.institute_id.id or False,
                        'program_id': student_id.program_id and student_id.program_id.id or False,
                        'mobile_no': mobile_no,
                        'date': fields.Date.context_today(self),
                        'student_send_sms_id': self.id,
                        'state': 'detail',
                    }
                    self.env['send.sms.student.line'].sudo().create(student_values)
            self.state = 'detail'

    def action_student_sms(self):
        message = self.env['send_sms'].sudo().render_template(self.sms_body, 'send.sms.student', self.id)
        for line in self.lines.filtered(lambda a: not a.sent):
            mobile_network = ''
            self.env['send_sms'].sudo().send_sms_link(message, line.mobile_no, line.student_id.id, 'odoocms.student', line.student_send_sms_id.gateway_id, line.student_name,
                                                      'other', 'student', False, line.institute_id, mobile_network)
            line.write({'sent': True, 'state': 'sent'})
        if all([ln.sent for ln in self.lines]):
            self.state = 'sent'

    @api.depends('sms_body')
    def compute_message_length(self):
        self.sms_length = len(self.sms_body) if self.sms_body else 0


class SendSMSStudentLines(models.Model):
    _name = "send.sms.student.line"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Send SMS To Student Detail"

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    student_id = fields.Many2one('odoocms.student', tracking=True)
    student_name = fields.Char('Student Name')
    student_code = fields.Char('Student Code')
    batch_id = fields.Many2one('odoocms.batch', 'Batch')
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')
    program_id = fields.Many2one('odoocms.program', 'Program')
    mobile_no = fields.Char('Mobile No')
    date = fields.Date('Date')
    state = fields.Selection([('draft', 'Draft'),
                              ('detail', 'Detail Generated'),
                              ('sent', 'Sent'),
                              ('cancel', 'Cancelled')
                              ], string='Status', default='draft', index=True)
    sent = fields.Boolean('Sent', default=False)
    student_send_sms_id = fields.Many2one('send.sms.student', 'Student SMS Ref', index=True, ondelete='cascade')
    sms_track_id = fields.Many2one('sms_track', 'SMS Track')
