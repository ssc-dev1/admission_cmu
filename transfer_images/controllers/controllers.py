# -*- coding: utf-8 -*-
# from odoo import http


# class Kobotest(http.Controller):
#	@http.route('/kobotest/kobotest', auth='public')
#	def index(self, **kw):
#		return "Hello, world"

#	@http.route('/kobotest/kobotest/objects', auth='public')
#	def list(self, **kw):
#		return http.request.render('kobotest.listing', {
#			'root': '/kobotest/kobotest',
#			'objects': http.request.env['kobotest.kobotest'].search([]),
#		})
#	@http.route('/kobotest/kobotest/objects/<model("kobotest.kobotest"):obj>', auth='public')
#	def object(self, obj, **kw):
#		return http.request.render('kobotest.object', {
#		'object': obj
#		})
