import pdb
from odoo import api, fields, models, _


class OdooCMSCancelRegistrationRequest(models.TransientModel):
	_name ='odoocms.cancel.registration'
	_description = 'Cancel Registration Wizard'
				
	@api.model	
	def _get_requests(self):
		if self.env.context.get('active_model', False) == 'odoocms.course.registration' and self.env.context.get('active_ids', False):
			active_ids = self.env.context['active_ids']
			return self.env['odoocms.course.registration'].browse(active_ids).filtered(lambda l: l.state in ('draft','submit')).ids
		
	request_ids = fields.Many2many('odoocms.course.registration', string='Students',
		help="""Only selected students will be Processed.""",default=_get_requests)

	def cancel_requests(self):
		for rec in self.request_ids:
			rec.action_cancel()
			
		if self.request_ids:
			reg_list = self.request_ids.mapped('id')
			return {
				'domain': [('id', 'in', reg_list)],
				'name': _('Canceled Registrations'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'odoocms.course.registration',
				'view_id': False,
				# 'context': {'default_class_id': self.id},
				'type': 'ir.actions.act_window'
			}

		return 1



