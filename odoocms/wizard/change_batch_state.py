# -*- coding: utf-8 -*-
import pdb
from odoo import api, fields, models,_
from datetime import date
from odoo.exceptions import UserError, ValidationError


class OdooCMSChangeBatchState(models.Model):
	_name ='odoocms.batch.state.change'
	_description = 'Change Batch State'
				
	@api.model
	def _get_batches(self):
		if self.env.context.get('active_model', False) == 'odoocms.batch' and self.env.context.get('active_ids', False):
			return self.env.context['active_ids']
			
	batch_ids = fields.Many2many('odoocms.batch', 'state_change_batch_rel','state_change_id','batch_id',
		string='Batches', default=_get_batches, help="""Only selected Batches will be Processed.""")

	state = fields.Selection([('draft','Draft'),('active','Active'),('complete','Complete'),('closed','Closed'),('cancel','Cancel')],
		default='active', string='Status', help=
			"Draft: Before start of program session\n"
			"Active: Open for students enrollment and all academic activities\n"
			"Complete: Program session ends\n"
			"Closed: Period of time bar is over\n"
			"Cancel: Cancel to some reason or merged in other programs"
		)
	
	apply = fields.Boolean('Apply effect on Students', default=False)
	date_effective = fields.Date('Date Effective',default=date.today())
	description = fields.Text('Description')
	
	def change_batch_state(self):
		overdate_tag = self.env['odoocms.student.tag'].search([('time_lapsed','=',True)])
		for batch in self.batch_ids:
			old_state = batch.state
			batch.with_context({
					'date_effective':self.date_effective,
					'description': self.description,
					'method': 'State Wizard',
				}).write({
					'state': self.state,
				})
			
			msg = ("Date Effective=%s </br> Description: %s") % (self.date_effective, self.description)
			msg_subject = ("State Changed to %s", self.state.capitalize())
			
			if overdate_tag and self.apply and self.state in ('complete','closed','cancel'):
				msg = ("With Apply Tag to Students </br> Date Effective=%s </br> Description: %s") % (self.date_effective, self.description)
				for student in batch.student_ids.filtered(lambda l: l.state.name == 'Admitted'):
					tags = student.tag_ids + overdate_tag
					student.with_context({
						'date_effective': self.date_effective,
						'description': self.description,
						'method': 'Batch State',
					}).write({
						'tag_ids': [[6, 0, tags.ids]]
					})
			
			# odoobot_id = self.env['ir.model.data'].xmlid_to_res_id("base.partner_root")
			batch.message_post(body=msg, subject=msg_subject)
			
		return {'type': 'ir.actions.act_window_close'}



