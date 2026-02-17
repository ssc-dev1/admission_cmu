import pdb

from odoo import http
import random
import string
from odoo.http import route, request, Controller
from odoo.addons.web.controllers.main import ensure_db, Home
from odoo.exceptions import UserError
import logging
from odoo import _
import odoo
import werkzeug
import odoo.addons.web.controllers.main as main
import json
from odoo.addons.auth_signup.models.res_users import SignupError
from urllib.parse import urlparse

_logger = logging.getLogger(__name__)

# url = 'https://www.ubas.edu.pk'

class AccountRegistration(Controller):

    @route(['/web/signin', '/web/signin/'], methods=['GET'], type='http', auth="public", sitemap=False)
    def index_signin(self, redirect=None, **kw):
        test_url = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.url',False)
        url = test_url or request.httprequest.url_root
        # url = 'https://admission.ubas.edu.pk'
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        _logger.warning("URL: %s, Domain=%s" % (url, domain))
        website_id = request.env['website'].sudo().search([('domain', '=', domain)])
        _logger.warning("Website: %s" % (website_id and website_id.id or 'Not Found'))
        #company_id = website_id.company_id
        company_id = request.env['res.company'].sudo().browse(5)

        # company_name = domain.split('.')[1]
        company_name = company_id.short_name
        template_name = 'odoocms_admission_ext_ubas.account_registration_' + company_name
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        operation = random.choice(['+', '*', '-'])
        country_id = request.env['res.country'].sudo().search([])
        color_scheme = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme')
        color_scheme2 = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme2')
        values = {
            'color_scheme': color_scheme,
            'color_scheme2': color_scheme2,
            'country_id': country_id,
            'company': company_id,
            'num1': num1,
            'num2': num2,
            'operation': operation,
        }
        if kw.get('signup') == 'True':
            request.session.logout(keep_db=True)
            # db_select = '/web/signin?db=%s' % request._cr.dbname
            # return http.local_redirect(db_select)
            values.update({
                'message': 'Login Details Sent By Email and Message'
            })
            return request.render(template_name, values)
        request.session.logout(keep_db=True)
        return request.render(template_name, values)
        
    @route(['/thankyou/signup'], methods=['GET'], type='http', auth="public", sitemap=False)
    def thankyou_signup(self):
        test_url = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.url', False)
        url = test_url or request.httprequest.url_root

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        website_id = request.env['website'].sudo().search([('domain', '=', domain)])
        #company_id = website_id.company_id
        company_id = request.env['res.company'].sudo().browse(5)

        values = {
            'company': company_id
        }
        return request.render('odoocms_admission_ext_ubas.thankyou_signup_page',values)


class AdmissionSignUp(Home):
    @http.route('/web/admission/signup/', type='http', csrf=False, auth='public', website=True, sitemap=False)
    def web_auth_admission_signup(self, *args, **kw):
        test_url = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.url', False)
        url = test_url or request.httprequest.url_root
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        website_id = request.env['website'].sudo().search([('domain', '=', domain)])
        #company_id = website_id.company_id
        company_id = request.env['res.company'].sudo().browse(5)

        # company_name = domain.split('.')[1]
        company_name = company_id.short_name
        template_name = 'odoocms_admission_ext_ubas.account_registration_' + company_name

        qcontext = self.get_auth_signup_qcontext()
        country_id = request.env['res.country'].sudo().search([])
        color_scheme = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme')
        color_scheme2 = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme2')

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        user_num1=int(kw.get('num1'))
        user_num2=int(kw.get('num2'))
        user_answer=0
        if kw.get('operation') == '+':
            correct_answer = user_num1 + user_num2
        elif kw.get('operation')  == '*':
            correct_answer = user_num1 * user_num2
        elif kw.get('operation')  == '-':
            correct_answer = user_num1 - user_num2
        num1 = random.randint(1, 9)
        num2 = random.randint(1, 9)
        operation = random.choice(['+', '*', '-'])
        if kw.get('math_captcha_answer') :
            user_answer = kw.get('math_captcha_answer')
            if str(user_answer) != str(correct_answer):
                return json.dumps({
                    'error': 'captcha_exp',
                    'error_detail': "The math problem was solved incorrectly. Please try again.",
                    'csrf_token': request.csrf_token(),
                    'num1': num1,
                    'num2': num2,
                    'operation': operation,
                    })
        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                check_email = request.env['res.users'].sudo().search([('email', '=', kw.get('email'))])

                if check_email:
                    return json.dumps({
                        'error': 'email_error',
                        'num1': num1,
                        'num2': num2,
                        'operation': operation,
                    })

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
                application_data = {
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
                    'term_id': request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.admission_term_id'),
                    'company_id': company_id.id
                }
                application = request.env['odoocms.application'].sudo().create(application_data)

                qcontext.update({
                    'login': application.application_no,
                    'name': kw.get('first_name') + ' ' + kw.get('last_name'),
                    'password': password,
                    'phone': kw.get('phone'),
                    'country_id': country,
                    'confirm_password': password,
                    'website_id': website_id.id,
                    'company_ids': company_id.ids,
                    'company_id': company_id.id,
                })
                
                kw.update(qcontext)
                self.admission_signup(qcontext)

                application.user_id = request.env['res.users'].sudo().search([('login', '=', application.application_no)]).id
                user_created = application.user_id

                processing_fee = 0
                if user_created:
                    processing_fee = request.env['ir.config_parameter'].sudo().search([('key', '=', 'odoocms_admission_portal.registration_fee')])

                mail_server_id = request.env['ir.mail_server'].sudo().search([('company_id', '=', company_id.id)])
                # template = request.env.ref('odoocms_admission.mail_template_account_created').sudo()
                template = request.env['mail.template'].sudo().search([('name','=','Account Created'),('mail_server_id','=',mail_server_id.id)])

                login_value = {
                    'processing_fee': processing_fee.value,
                    'applicant_name': application.name,
                    'company':company_id,
                    'email': kw.get('email'),
                    'company_name': company_id.name or "",
                    'company_website': company_id.website or "",
                    'company_email': company_id.admission_mail or "",
                    'company_phone': company_id.admission_phone or "",
                    'login': application.application_no,
                    'password': password
                }
                user = request.env['res.users'].sudo().search([('login', '=', application.application_no)])

                partner = request.env["res.partner"].sudo().search([('email' , '=' , kw.get('email'))])
                partner.company_id = user.company_id.id


                email_from = company_id.admission_mail
                try:
                    template.with_context(login_value, email_from=email_from,allowed_company_ids=[5, 2, 4], company =company_id).send_mail(user.id, force_send=True)
                except Exception as e:
                    print(e)
                    pass

                #****** SMS *****
                if application:
                    company_name = company_id.name
                    msg_txt = f'Dear {application.name},\nThank you for registering with {company_name}.Your Username: {application.application_no} and Password: {password}.\n Please check your email for your Login details and further instructions.'
                    # msg_txt = f'Welcome To {request.env.company.name} \n Your Account Details At Admission Cust UserID: ' + application.application_no + " Password: " + password
                    updated_mobile_no = phone.replace('-', '')
                    updated_mobile_no = updated_mobile_no.replace(' ', '')
                    updated_mobile_no = updated_mobile_no.lstrip('0')
                    message = request.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.application', application.id)
                    gateway_id = request.env['gateway_setup'].sudo().search([('company_id','=',company_id.id)], order='id desc', limit=1)
                    if gateway_id:
                        try:
                            request.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, application.id,'odoocms.application', gateway_id, application.name,'login','student',False,False,False)
                        except UserError as e:
                            print(e)
                            pass
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
            'company': company_id.id,
            # 'company': request.env.company,
            
        })
        response = request.render(template_name, qcontext)
        response.headers['X-Frame-Options'] = 'DENY'
        return json.dumps({
            'error': qcontext
        })

    def admission_signup(self, qcontext):
        if not qcontext.get('token'):
            # our custom function should not be called if user go for reset password. So, we have added this statement
            # """ Shared helper that creates a res.partner out of a token """
            values = {key: qcontext.get(key) for key in ('login', 'name', 'password', 'email', 'phone', 'company_id','company_ids','website_id')}
            
            if not values:
                raise UserError(_("The form was not properly filled in."))
            # get all user and check if the email already exist or not
            user = request.env["res.users"].sudo().search([('login' , 'ilike' , values['login'])])
            count = 0
            # for rec in user:
            #     if (rec.login).upper() == (qcontext.get("login")).upper():
            #         count += 1
            # if values.get('password') != qcontext.get('confirm_password'):
            #     raise UserError(
            #         _("Passwords do not match; please retype them."))
            if user:
                raise UserError(_("Another user is already registered with same ."))
            # elif request.env["res.users"].sudo().search([("email", "=", qcontext.get("email")), ("mobile", "=", qcontext.get("mobile"))]):
            #     raise UserError(
            #         _("Another user is already registered with same Email or Mobile."))


            ctx = request.env.context.copy()
            ctx.update({
                'allowed_company_ids': values.get('company_ids'),
                'company_ids': values.get('company_ids'),
                'company_id': values.get('company_id'),
                'website_id': values.get('website_id'),
            })
            request.env.context = ctx
            self._signup_with_values(qcontext.get('token'), values)
            request.env.cr.commit()
        else:
            res = super(AdmissionSignUp, self).admission_signup(qcontext)
            # default will be called if you do have token---> means come here by clicking on reset password

    @http.route('/web/login/admission/', type='http', csrf=False, auth="public", sitemap=False)
    def web_login_admission(self, redirect=None, **kw):
        main.ensure_db()
        request.params['login_success'] = False
        test_url = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.url', False)
        url = test_url or request.httprequest.url_root
        # url = 'https://admission.ubas.edu.pk'

        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        website_id = request.env['website'].sudo().search([('domain', '=', domain)])
        #company_id = website_id.company_id
        company_id = request.env['res.company'].sudo().browse(5)

        # company_name = domain.split('.')[1]
        company_name = company_id.short_name
        template_name = 'odoocms_admission_ext_ubas.account_registration_' + company_name
        if request.httprequest.method == 'GET' and redirect and request.session.uid:
            return request.redirect('/admission/application')
            # return http.redirect_with_hash(redirect)

        if not request.uid:
            request.uid = odoo.SUPERUSER_ID

        values = request.params.copy()
        country_id = request.env['res.country'].sudo().search([])
        
        values.update({
            'country_id': country_id,
            'company': company_id,
        })
        try:
            values['databases'] = http.db_list()
        except odoo.exceptions.AccessDenied:
            values['databases'] = None

        if request.httprequest.method == 'POST':
            old_uid = request.uid
            # company check on login to verify user using same company login
            company_check = request.env['res.users'].sudo().search([('login', '=', kw['login']), ('password' , '=' , str(kw['password']).strip()) , ('company_id' , '=' , company_id.id)])
            # company_check = True
            # pdb.set_trace()
            if company_check:
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

                    # redirect = '/admission/application/'
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
                        # 'company': request.env.company
                        # 'company': company_id.id
                    })

                    request.uid = old_uid
                    if e.args == odoo.exceptions.AccessDenied().args:
                        values['error'] = _("Wrong login/password")
                    else:
                        values['error'] = e.args[0]
            else:
                values['error'] = _("Wrong login/password")
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

        response = request.render(template_name, values)
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
