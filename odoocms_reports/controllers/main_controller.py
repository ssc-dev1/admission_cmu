
from distutils.command.check import check

import werkzeug
from odoo import http, _, SUPERUSER_ID
from odoo.http import route, request, Controller, content_disposition
from odoo.exceptions import UserError, ValidationError
from datetime import date, datetime
import json
from odoo.addons.auth_signup.models.res_users import SignupError 
    
    

class MainControllerOdoocmsReports(Controller):
    
    @http.route('/admission/terms/', csrf=False, type='http', auth='public', website=True, methods=['POST'])
    def get_terms(self, **kw):
        pass