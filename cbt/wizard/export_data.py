# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ExportDataWizard(models.TransientModel):
	_name = "export.data.wizard"
	_description = "Export Data Wizard"

	@api.model
	def get_default_export_id(self):
		if self._context.get('active_model', False)=='cbt.export' and self._context.get('active_id', False):
			return self.env['cbt.export'].browse(self._context.get('active_id', False))

	export_id = fields.Many2one('cbt.export', 'Export ID', default=get_default_export_id)
	user_id = fields.Char('User ID')
	password = fields.Char('Password')
	admin_pass = fields.Char('Admin Password')
	
	def export_cbt_data(self):
		if self.export_id:
			self.export_id.message_post(body=_("Export Process run by %(name)s .", name=self.env.user.name))
			self.export_id.export_cbt_data(self.user_id,self.password, self.admin_pass)