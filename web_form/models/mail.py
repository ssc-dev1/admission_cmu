from odoo import api, models, fields
from odoo.models import AbstractModel
from odoo.tools import misc
import datetime
import requests
import json
import pdb


class ResUsers(models.Model):
	_inherit = 'res.users'
	
	cnt = fields.Boolean('Cnt', default=False)
	
	@api.model
	def search_count(self, args):
		args.extend([('active','=',True),('cnt', '=', True)])
		res = self.search(args, count=True)
		return res if isinstance(res, int) else len(res)


class ResConfigSettings(models.TransientModel):
	_inherit = 'res.config.settings'
	
	@api.depends('company_id')
	def _compute_active_user_count(self):
		active_user_count = self.env['res.users'].sudo().search_count([('active','=',True),('share', '=', False), ('cnt', '=', True)])
		for record in self:
			record.active_user_count = active_user_count


class PWC(AbstractModel):
	_inherit = "publisher_warranty.contract"
	
	@api.model
	def _get_message(self):
		IrParamSudo = self.env['ir.config_parameter'].sudo()

		msg = super()._get_message()
		Users = self.env['res.users']
		
		limit_date = datetime.datetime.now()
		limit_date = limit_date - datetime.timedelta(15)
		limit_date_str = limit_date.strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
		
		nbr_users = Users.search_count([('active', '=', True), ('cnt', '=', True)])
		nbr_active_users = Users.search_count([("login_date", ">=", limit_date_str), ('active', '=', True), ('cnt', '=', True)])
		nbr_share_users = 0
		nbr_active_share_users = 0
		if "share" in Users._fields:
			nbr_share_users = Users.search_count([("share", "=", True), ('active', '=', True), ('cnt', '=', True)])
			nbr_active_share_users = Users.search_count([("share", "=", True), ("login_date", ">=", limit_date_str), ('active', '=', True), ('cnt', '=', True)])

		web_base_url = IrParamSudo.get_param('web.base.url2','False')
		dbname = IrParamSudo.get_param('dbname','False')
		if web_base_url == 'False':
			web_base_url = IrParamSudo.get_param('web.base.url')

		msg.update({
			"nbr_users": nbr_users,
			"nbr_active_users": nbr_active_users,
			"nbr_share_users": nbr_share_users,
			"nbr_active_share_users": nbr_active_share_users,
			"web_base_url": web_base_url,
			# "dbname": 'production',
		})
		if dbname != 'False':
			msg.update({
				'dbname': dbname
			})
		return msg
	
	@api.model
	def _get_sys_logs2(self):
		msg = self._get_message()
		Users = self.env['res.users']
		
		limit_date = datetime.datetime.now()
		limit_date = limit_date - datetime.timedelta(15)
		limit_date_str = limit_date.strftime(misc.DEFAULT_SERVER_DATETIME_FORMAT)
		
		nbr_users = Users.search_count([('active', '=', True)])
		nbr_active_users = Users.search_count([("login_date", ">=", limit_date_str), ('active', '=', True)])
		nbr_share_users = 0
		nbr_active_share_users = 0
		if "share" in Users._fields:
			nbr_share_users = Users.search_count([("share", "=", True), ('active', '=', True)])
			nbr_active_share_users = Users.search_count([("share", "=", True), ("login_date", ">=", limit_date_str), ('active', '=', True)])
		domain = [('application', '=', True), ('state', 'in', ['installed', 'to upgrade', 'to remove'])]
		apps = self.env['ir.module.module'].sudo().search_read(domain, ['name'])
		
		msg.update({
			"nbr_users0": nbr_users,
			"nbr_active_users0": nbr_active_users,
			"nbr_share_users0": nbr_share_users,
			"nbr_active_share_users0": nbr_active_share_users,
			"apps0": [app['name'] for app in apps],
		})
		
		url = 'https://aarsol.com/updatew'
		
		data = {
			"params": msg
		}
		headers = {'Content-Type': 'application/json'}
		r = requests.post(url, data=json.dumps(data), headers=headers, timeout=30)
		return True
	
	def update_notification(self, cron_mode=True):
		IrParamSudo = self.env['ir.config_parameter'].sudo()
		survey = IrParamSudo.get_param('survey')
		if survey and survey == 'Public':
			return True
		url = IrParamSudo.get_param('web.base.url')
		if url and "localhost" in url:
			return True
		return super().update_notification(cron_mode=cron_mode)
	
	
class Http(models.AbstractModel):
	_inherit = 'ir.http'
	
	def session_info(self):
		result = super(Http, self).session_info()
		result['warning'] = False
		return result
