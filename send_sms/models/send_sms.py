import logging
from odoo import http
from odoo.http import request, serialize_exception as _serialize_exception, content_disposition
from odoo import api, fields, models, tools, _
import datetime
from werkzeug import urls
import functools
import urllib
import requests
import re
import pdb
import threading

_logger = logging.getLogger(__name__)
try:
    from jinja2.sandbox import SandboxedEnvironment

    mako_template_env = SandboxedEnvironment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="${",
        variable_end_string="}",
        comment_start_string="<%doc>",
        comment_end_string="</%doc>",
        line_statement_prefix="%",
        line_comment_prefix="##",
        trim_blocks=True,  # do not output newline after blocks
        autoescape=True,  # XML/HTML automatic escaping
    )
    mako_template_env.globals.update({
        'str': str,
        'quote': urls.url_quote,
        'urlencode': urls.url_encode,
        'datetime': datetime,
        'len': len,
        'abs': abs,
        'min': min,
        'max': max,
        'sum': sum,
        'filter': filter,
        'reduce': functools.reduce,
        'map': map,
        'round': round,

        'relativedelta': lambda *a, **kw: relativedelta.relativedelta(*a, **kw),
    })
except ImportError:
    _logger.warning("jinja2 Not Available, Templating Features Will Not Work!")


class SendSMS(models.Model):
    _name = "send_sms"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "Send SMS"

    name = fields.Char(required=True, string='Name')
    gateway_id = fields.Many2one('gateway_setup', required=True, string='SMS Gateway')
    model_id = fields.Many2one('ir.model', string='Applies to', help="The kind of document with with this template can be used")
    sms_to = fields.Char(string='To (Mobile)', help="To mobile number (placeholders may be used here)")
    sms_html = fields.Text('Body')
    ref_ir_act_window = fields.Many2one('ir.actions.act_window', 'Sidebar action', readonly=True, copy=False, help="Sidebar action to make this template available on records " "of the related document model")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.model
    def send_sms(self, template_id, record_id):
        sms_rendered_content = self.env['send_sms'].render_template(template_id.sms_html, template_id.model_id.model, record_id)
        rendered_sms_to = self.env['send_sms'].render_template(template_id.sms_to, template_id.model_id.model, record_id)
        self.send_sms_link(sms_rendered_content, rendered_sms_to, record_id, template_id.model_id.model, template_id.gateway_id)

    def send_sms_link(self, sms_rendered_content, rendered_sms_to, record_id, model, gateway_url_id, send_to, sms_nature, type, department_id, institute_id, mobile_network):
        # sms_rendered_contents = sms_rendered_content.encode('ascii', 'ignore')
        sms_rendered_content_msg = urllib.parse.quote_plus(sms_rendered_content)
        if rendered_sms_to:
            rendered_sms_to = re.sub(r' ', '', rendered_sms_to)
            if '+' in rendered_sms_to:
                rendered_sms_to = rendered_sms_to.replace('+', '')
            if '-' in rendered_sms_to:
                rendered_sms_to = rendered_sms_to.replace('-', '')

        if rendered_sms_to:
            send_url = gateway_url_id.gateway_url
            if mobile_network:
                send_link = send_url.replace('{mobile}', rendered_sms_to).replace('{message}', sms_rendered_content_msg).replace('{op}', mobile_network)
            else:
                send_link = send_url.replace('{mobile}', rendered_sms_to).replace('{message}', sms_rendered_content_msg)
            try:
                response = requests.request("POST", url=send_link).text
            except Exception as e:
                return e
            self.env['sms_track'].sms_track_create(record_id, sms_rendered_content, rendered_sms_to, response, model, gateway_url_id.id, send_to, sms_nature, type, department_id, institute_id, mobile_network)
            if model not in ('gateway_setup', 'res.users'):
                self.env['mail.message'].create({
                    # 'author_id': http.request.env.user.partner_id.id,
                    'author_id': self.env.user.partner_id.id,
                    'date': datetime.datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
                    'model': model,
                    'res_id': record_id,
                    'message_type': 'email',
                    'body': '<b>SMS: </b>' + sms_rendered_content,
                })
            return next((char for char in response if char.isdigit()), '')

    def render_template(self, template, model, res_id):
        template = mako_template_env.from_string(tools.ustr(template))
        user = self.env.user
        record = self.env[model].browse(res_id)
        variables = {'user': user}
        variables['object'] = record
        try:
            render_result = template.render(variables)
        except Exception:
            _logger.error("Failed to render template %r using values %r" % (template, variables))
            render_result = u""
        if render_result == u"False":
            render_result = u""

        return render_result

    def create_action(self):
        action_obj = self.env['ir.actions.act_window'].sudo()
        view = self.env.ref('send_sms.sms_compose_wizard_form')

        button_name = _('SMS Send (%s)') % self.name
        action = action_obj.create({
            'name': button_name,
            'type': 'ir.actions.act_window',
            'res_model': 'sms.compose',
            'context': "{'default_template_id' : %d, 'default_use_template': True}" % (self.id),
            'view_mode': 'form,tree',
            'view_id': view.id,
            'target': 'new',
            'binding_model_id': self.model_id.id,
        })
        self.write({
            'ref_ir_act_window': action.id,
        })
        return True

    def unlink_action(self):
        for template in self:
            if template.ref_ir_act_window:
                template.ref_ir_act_window.sudo().unlink()
        return True


class SendSMSCron(models.Model):
    _name = "send_sms.cron"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = "SMS Cron"

    name = fields.Char('Name')
    model_id = fields.Char('Model', readonly=True)
    response_id = fields.Char('Response', readonly=True)
    message_id = fields.Text('Messages', readonly=True)
    gateway_id = fields.Many2one('gateway_setup', string='GateWay', readonly=True)

    mobile_no = fields.Char('Mobile No.', readonly=True)
    send_to = fields.Char('Send To')
    date = fields.Date('Date', default=lambda self: fields.Date.context_today(self))

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
    mobile_network = fields.Selection([('Moblink', 'Moblink'),
                                       ('warid', 'Warid'),
                                       ('telenor', 'Telenor'),
                                       ('ufone', 'Ufone'),
                                       ('zong', 'Zong')
                                       ], string='Mobile Network')

    department_id = fields.Many2one('hr.department', 'Department')
    institute_id = fields.Many2one('odoocms.institute', 'Faculty')

    sms_track_id = fields.Many2one('sms_track', 'SMS History Ref')
    res_id = fields.Integer()
    sent = fields.Boolean('Sent', default=False)
    delivered_datetime = fields.Datetime('Delivered Date Time')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id)

    @api.model
    def create(self, values):
        record = super(SendSMSCron, self).create(values)
        if not record.name:
            record.name = self.env['ir.sequence'].next_by_code('send_sms.cron')
        return record

    def send_user_login_sms(self, nlimit=100):
        recs = self.env['send_sms.cron'].sudo().search([('sent', '=', False)], order='id asc', limit=nlimit)
        for rec in recs:
            self.env['send_sms'].sudo().send_sms_link(rec.message_id, rec.mobile_no, rec.res_id, rec.model_id, rec.gateway_id, rec.send_to,
                                                      rec.sms_nature, rec.type, rec.department_id or False, rec.institute_id or False, rec.mobile_network)
            rec.write({'sent': True, 'delivered_datetime': fields.Datetime.now()})
            self._cr.commit()

    def send_sms(self, nlimit=10):
        messages = self.env['send_sms.cron'].search([('status', '=', False)], limit=nlimit)
        for message in messages:
            try:
                # self.env['send_sms'].send_sms(message.template_id, message.res_id)
                response = self.env['send_sms'].send_sms_link(message.message_id,
                                                              message.mobile_no,
                                                              message.res_id,
                                                              message.model_id,
                                                              message.gateway_id if message.gateway_id else False,
                                                              message.send_to,
                                                              message.sms_nature,
                                                              message.type,
                                                              message.department_id.id if message.department_id else False,
                                                              message.institute_id.id if message.institute_id else False,
                                                              message.mobile_network)
            except Exception as e:
                return e
            message.sent = True
            message.status = response if response in ['0', '1', '2', '4'] else ''
            self._cr.commit()
    def send_custom_sms(self, nlimit=100):
        recs = self.env['send_sms.cron'].sudo().search([('sent', '=', False),('model_id','=','student.sms.wizard')], order='id asc', limit=nlimit)
        for rec in recs:
            try:
                response=self.env['send_sms'].sudo().send_sms_link(rec.message_id, rec.mobile_no, rec.res_id, rec.model_id, rec.gateway_id, rec.send_to,
                                                          rec.sms_nature, rec.type, rec.department_id or False, rec.institute_id or False, rec.mobile_network)
                rec.write({'sent': True, 'delivered_datetime': fields.Datetime.now()})
                self._cr.commit()
            except Exception as e:
                return e
            rec.sent = True
            rec.status = response if response in ['0', '1', '2', '4'] else ''
            self._cr.commit()