import pdb

from odoo import http
import random
import string
from odoo.http import route, request, Controller
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.exceptions import UserError
import logging
import re
from odoo import _
import odoo
import werkzeug
import odoo.addons.web.controllers.main as main
import json
from odoo.addons.auth_signup.models.res_users import SignupError

_logger = logging.getLogger(__name__)


class AccountRegistration(Controller):

    # @route(['/web/login/', '/'], method='GET', type='http', auth="public", sitemap=False)
    # def login_signin(self, redirect=None, **kw):
    #     return http.local_redirect('/web/signin/')

    @route(['/web/signin/'], methods=['GET'], type='http', auth="public", sitemap=False)
    def index_signin(self, redirect=None, **kw):
        country_id = request.env['res.country'].sudo().search([])
        color_scheme = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme')
        color_scheme2 = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme2')
        length = 2
        all = string.digits
        captcha = "".join(random.sample(all, length))
        captcha1 = captcha[0]
        captcha2 = captcha[1]

        values = {
            'color_scheme': color_scheme,
            'color_scheme2': color_scheme2,
            'country_id': country_id,
            'company': request.env.company,
            'captcha': captcha1 + ' + ' + captcha2 + ' = ',
            'cap': int(captcha1) + int(captcha2)
        }
        if kw.get('signup') == 'True':
            request.session.logout(keep_db=True)
            values.update({
                'message': 'Login Details Sent By Email and Message'
            })
            return request.render('odoocms_admission_portal.account_registration_ucp', values)
        request.session.logout(keep_db=True)
        return request.render('odoocms_admission_portal.account_registration_ucp', values)

    @route(['/thankyou/signup'], methods=['GET'], type='http', auth="public", sitemap=False)
    def thankyou_signup(self):
        return request.render('odoocms_admission_portal.thankyou_signup_page')


class AdmissionSignUp(Home):

    @http.route('/web/admission/signup/', type='http', csrf=False, auth='public', website=True, sitemap=False)
    def web_auth_admission_signup(self, *args, **kw):

        if kw.get('cap') and kw.get('captcha'):
            if int(kw.get('cap')) != int(kw.get('captcha')):
                return json.dumps({
                    'error': 'captcha_error',
                    'error_detail': 'Your Answer is incorrect',
                })
        if kw.get('cnic'):
            bot_cnic = kw.get('cnic')
            if bot_cnic.isalpha() or bot_cnic.isalnum():
                return
        if kw.get('cnic') and not re.match("\d{5}-\d{7}-\d{1}", kw.get('cnic')):
            return json.dumps({
                'error': 'cnic_error',
                'error_detail': 'CNIC should be written as 99999-9999999-9'
            })
        qcontext = self.get_auth_signup_qcontext()
        country_id = request.env['res.country'].sudo().search([])
        color_scheme = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme')
        color_scheme2 = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme2')
        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                check_email = request.env['res.users'].sudo().search([('email', '=', kw.get('email'))])

                if check_email:
                    return json.dumps({
                        'error': 'email_error'
                    })
                    raise UserError('Email Already Registerd Please Signin')
                    # raise UserError('Email Already Registerd Please Signin')

                international_student = kw.get('international_student')
                country = 177
                phone = kw.get('phone_signup', '').replace('-', '')
                if international_student != 'national':
                    country = int(kw.get('country_id_signup')) if kw.get('country_id_signup', '').isnumeric() else 177
                    phone = kw.get('phone_signup_international','').replace('-', '')

                cnic = False

                if kw.get('cnic') != '':
                    cnic = kw.get('cnic') if kw.get('cnic').replace('-', '') else False
                length = 8
                all = string.ascii_letters + string.digits

                password = "".join(random.sample(all, length))
                application = request.env['odoocms.application'].sudo().create({
                    # 'register_id': admission_register.id,
                    'mobile': phone,
                    'applicant_type': international_student,
                    'nationality': country,
                    'email': kw.get('email'),
                    'first_name': kw.get('first_name'),
                    'password': password,
                    'last_name': kw.get('last_name'),
                    'step_no': 1,
                    'gender': kw.get('gender'),
                    'cnic': cnic,
                    'term_id':request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.admission_term_id')
                })

                qcontext.update({
                    'login': application.application_no,
                    'name': kw.get('first_name') + ' ' + kw.get('last_name'),
                    'password': password,
                    'phone': kw.get('phone'),
                    'country_id': country,
                    'confirm_password': password,
                })
                kw.update(qcontext)

                self.admission_signup(qcontext)
                application.user_id = request.env['res.users'].sudo().search(
                    [('login', '=', application.application_no)]).id
                user_created = application.user_id
                processing_fee = 0
                if user_created:
                    processing_fee = request.env['ir.config_parameter'].sudo().search([('key', '=', 'odoocms_admission_portal.registration_fee')])

                template = request.env.ref('odoocms_admission.mail_template_account_created').sudo()
                login_value = {
                    'processing_fee': processing_fee.value,
                    'applicant_name': application.name,
                    'email': kw.get('email'),
                    'company_name': request.env.company.name or "",
                    'company_website': request.env.company.website or "",
                    'company_email': request.env.company.admission_mail or "",
                    'company_phone': request.env.company.admission_phone or "",
                    'login': application.application_no,
                    'password': password
                }
                user = request.env['res.users'].sudo().search([('login', '=', application.application_no)])
                try:
                    template.with_context(login_value).send_mail(user.id, force_send=True)
                except ValueError:
                    pass

                # ****** SMS *****#
                # if application:
                #     company_name = request.env.company.name
                #     msg_txt = f'Dear {application.name},\nThank you for registering with {company_name}.Your Username: {application.application_no} and Password: {password}.\n Please check your email for your Login details and further instructions.'
                #     # msg_txt = f'Welcome To {request.env.company.name} \n Your Account Details At Admission Cust UserID: ' + application.application_no + " Password: " + password
                #     updated_mobile_no = phone.replace('-', '')
                #     updated_mobile_no = updated_mobile_no.replace(' ', '')
                #     updated_mobile_no = updated_mobile_no.lstrip('0')
                #     message = request.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.application', application.id)
                #     gateway_id = request.env['gateway_setup'].sudo().search([], order='id desc', limit=1)
                #     if gateway_id:
                #         try:
                #             request.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, application.id,'odoocms.application', gateway_id, application.name,'login','student',False,False,False)
                #         except ValueError:
                #             pass
                return json.dumps({
                    'error': 'noerror',
                    'signup': 'true',
                })

            except UserError as e:
                qcontext['error'] = e.name or e.value
            except (SignupError, AssertionError) as e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _(
                        "Another user is already registered using this email address.")
                else:
                    _logger.error("%s", e)
                    qcontext['error'] = _("Could not create a new account.")

        qcontext.update({
            'color_scheme': color_scheme,
            'color_scheme2': color_scheme2,
            'country_id': country_id,
            'company': request.env.company,
        })
        response = request.render('odoocms_admission_portal.account_registration_ucp', qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return json.dumps({
            'error': qcontext
        })

    def admission_signup(self, qcontext):
        if not qcontext.get('token'):
            # our custom function should not be called if user go for reset password. So, we have added this statement
            # """ Shared helper that creates a res.partner out of a token """
            values = {key: qcontext.get(key) for key in (
                'login', 'name', 'password', 'email', 'phone',)}
            if not values:
                raise UserError(_("The form was not properly filled in."))
            # get all user and check if the email already exist or not
            user = request.env["res.users"].sudo().search([])
            count = 0
            for rec in user:
                if (rec.login).upper() == (qcontext.get("login")).upper():
                    count += 1
            if values.get('password') != qcontext.get('confirm_password'):
                raise UserError(_("Passwords do not match; please retype them."))
            if count > 0:
                raise UserError(_("Another user is already registered with same ."))
            # elif request.env["res.users"].sudo().search([("email", "=", qcontext.get("email")), ("mobile", "=", qcontext.get("mobile"))]):
            #     raise UserError(
            #         _("Another user is already registered with same Email or Mobile."))
            self._signup_with_values(qcontext.get('token'), values)
            request.env.cr.commit()
        else:
            res = super(AdmissionSignUp, self).admission_signup(qcontext)
            # default will be called if you do have token---> means come here by clicking on reset password

    @http.route('/web/login/admission/', type='http', csrf=False, auth="public", sitemap=False)
    def web_login_admission(self, redirect=None, **kw):
        main.ensure_db()
        request.params['login_success'] = False
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect('/admission/application')
            # return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        country_id = request.env['res.country'].sudo().search([])
        values.update({
            'country_id': country_id,
        })
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            try:
                uid = request.session.authenticate(request.session.db, kw['login'], str(kw['password']).strip())
                request.params['login_success'] = True
                current_user = request.env['res.users'].search([('id', '=', uid)])

                student_application = request.env['odoocms.application'].sudo().search([('application_no', '=', current_user.login)])

                if student_application:
                    # raise UserError('Login Detail Send By Email')
                    # return request.redirect('/admission/application')
                    return request.redirect('/admission/student/dashboard')

                if request.env['res.users'].browse(request.uid).has_group('base.group_user'):
                    # redirect = '/web?' + request.httprequest.query_string
                    redirect = '/web'
                else:
                    redirect = '/admission/application/'

                return request.redirect(redirect)

            except odoo.exceptions.AccessDenied as e:
                # career_id = request.env['odoocms.admission.register'].sudo().search(
                #     [('state', '=', 'application')]).career_id
                country_id = request.env['res.country'].sudo().search([])
                color_scheme = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme')
                color_scheme2 = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme2')
                values.update({
                    'color_scheme': color_scheme,
                    'color_scheme2': color_scheme2,
                    'country_id': country_id,
                    'company': request.env.company
                })

                request.uid = old_uid
                if e.args == odoo.exceptions.AccessDenied().args:
                    values['error'] = _("Wrong login/password")
                else:
                    values['error'] = e.args[0]
        else:
            if 'error' in request.params and request.params.get('error') == 'access':
                values['error'] = _('Only employee can access this database. Please contact the administrator.')

        if 'login' not in values and request.session.get('auth_login'):
            values['login'] = request.session.get('auth_login')

        if not odoo.tools.config['list_db']:
            values['disable_database_manager'] = True

        # otherwise no real way to test debug mode in template as ?debug =>
        # values['debug'] = '' but that's also the fallback value when
        # missing variables in qweb
        if 'debug' in values:
            values['debug'] = True

        response = request.render('odoocms_admission_portal.account_registration_ucp', values)
        response.headers['X-Frame-Options'] = 'DENY'

        # website web_login function
        if not redirect and request.params['login_success']:
            if request.env['res.users'].browse(request.uid).has_group('base.group_user'):
                redirect = b'/web?' + request.httprequest.query_string
            else:
                redirect = '/admission/application/'

            return request.redirect(redirect)
            # return http.redirect_with_hash(redirect)

        # auth_signup web_login function
        response.qcontext.update(self.get_auth_signup_config())
        if request.httprequest.method == 'GET' and request.session.uid and request.params.get('redirect'):
            # Redirect if already logged in and redirect param is present
            redirect = '/admission/application/'
            return request.redirect(redirect)
            # return http.redirect_with_hash(request.params.get('redirect'))

        return response

    @http.route()
    def web_auth_reset_password(self, *args, **kw):
        if request.httprequest.method == 'POST':
            login=kw.get('login',False)
            if login:
                applicant = request.env['odoocms.application'].sudo().search(['|',('application_no','=',login),('email','=',login)])
                if applicant and kw.get('password',False):
                    applicant.reset_password = kw.get('password')
            
        return super(AdmissionSignUp,self).web_auth_reset_password()
