import pdb
from odoo import api, fields, models, tools
from dateutil.relativedelta import relativedelta
from odoo.http import request


class ResUsers(models.Model):
    _inherit = 'res.users'

    def send_user_login_sms(self):
        # Simple ---> User AQEEL.AHMED logged in to UCP Portal from IP.10.10.5.105 at Wed Apr 19 10:12:50 PKT 2023
        ip_address = request.httprequest.environ['REMOTE_ADDR']
        current_datetime = ttime = fields.datetime.now() + relativedelta(hours=5)
        text = f"User {self.name.upper()} logged into CMS from {ip_address} at {current_datetime.strftime('%a %b %Y %H:%M:%S')}"

        message = self.env['send_sms'].sudo().render_template(text, 'res.users', self.id)
        gatewayurl_id = self.env['gateway_setup'].sudo().search([('id', '=', 1)])
        mobile_no = None
        mobile_network = None
        send_to = None
        department_id = None
        institute_id = None
        sms_nature = 'login'
        sms_type = None

        if self.faculty_staff_id and self.faculty_staff_id.mobile_phone:
            mobile_no = self.faculty_staff_id.mobile_phone.lstrip('0')
            if mobile_no.startswith("92"):
                mobile_no = mobile_no[2:]
            mobile_network = self.faculty_staff_id.employee_id.mobile_network
            send_to = self.faculty_staff_id.name
            department_id = self.faculty_staff_id.employee_id.department_id
            institute_id = self.faculty_staff_id.institute
            sms_type = 'faculty'
        elif self.emp_id and self.emp_id.mobile_phone:
            mobile_no = self.emp_id.mobile_phone.lstrip('0')
            if mobile_no.startswith("92"):
                mobile_no = mobile_no[2:]
            mobile_network = self.emp_id.mobile_network
            send_to = self.emp_id.name
            department_id = self.emp_id.department_id
            sms_type = 'staff'

        if mobile_no:
            sms_data_values = {
                'model_id': 'res.users',
                'res_id': self.id,
                'mobile_no': mobile_no,
                'message_id': message,
                'gateway_id': gatewayurl_id and gatewayurl_id.id or False,
                'send_to': send_to,
                'sms_nature': sms_nature,
                'type': sms_type,
                'department_id': department_id and department_id.id or False,
                'institute_id': institute_id and institute_id.id or False,
                'mobile_network': mobile_network,
            }
            self.env['send_sms.cron'].sudo().create(sms_data_values)


# ******************************************************************
# ret = self.env['send_sms'].sudo().send_sms_link(message, mobile_no, self.id, 'res.users', gatewayurl_id, self.faculty_staff_id.name, 'login', 'faculty',  self.faculty_staff_id.employee_id.department_id, self.faculty_staff_id.institute, mobile_network)
# ret = self.env['send_sms'].sudo().send_sms_link(message, mobile_no, self.id, 'res.users', gatewayurl_id, self.emp_id.name, 'login', 'staff', self.emp_id.department_id, False, mobile_network)
