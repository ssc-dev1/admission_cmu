import pdb
from odoo import http, tools, _, SUPERUSER_ID
from odoo.http import content_disposition, Controller, request, route, dispatch_rpc
from odoo.addons.portal.controllers.web import Home
from odoo.addons.website.controllers.main import Website

class MyWebsite(Home):
    @http.route(website=True, auth="public", sitemap=False)
    def web_login(self, redirect=None, *args, **kw):
        ip_address = request.httprequest.environ['REMOTE_ADDR']
        check_ip = request.env['ip.address.login'].sudo().search([('ipaddress','=',ip_address)])

        response = super(MyWebsite, self).web_login(redirect=redirect, *args, **kw)
        if not redirect and request.params['login_success']:
            user = request.env['res.users'].browse(request.uid)
            if user.has_group('base.group_portal'):
                # if request.httprequest.method =='POST' and not check_ip:
                #     request.session.logout(keep_db=True)
                #     return request.redirect('/web/login')
                return request.redirect('/' + 'cbt' + '/home')
            redirect = b'/web?' + request.httprequest.query_string
            return request.redirect('/' + 'web')
            # return http.redirect_with_hash(redirect)

        # if user.has_group('base.group_portal') and user.user_type == 'faculty':
        # 	return request.redirect('/faculty/dashboard')
        # if user.has_group('base.group_portal') and user.user_type == 'student':
        # 	return request.redirect('/student/dashboard')
        # if user.has_group('base.group_portal') and user.user_type == 'employee':
        # 	return request.redirect('/employee/dashboard')
        # if user.has_group('base.group_portal') and user.user_type == 'external':
        # 	return request.redirect('/external/dashboard')

        # return http.redirect_with_hash(self._login_redirect(uid, redirect=redirect))

        # if request.env['res.users'].browse(request.uid).has_group('base.group_user'):
        # 	redirect = b'/web?' + request.httprequest.query_string
        # else:
        # 	redirect = '/my'
        # return http.redirect_with_hash(redirect)
        return response