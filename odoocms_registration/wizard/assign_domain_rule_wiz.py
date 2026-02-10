import pdb

from odoo import api, fields, models,_
import math


class OdooCMSAssignDomainRuleWiz(models.TransientModel):
	_name ='odoocms.assign.domain.rule.wiz'
	_description = 'Assign Domain Rule Wizard'
	
	term_id = fields.Many2one('odoocms.academic.term','Term')
	enroll_domain = fields.Char('Enrollment Domain')
	primary_class_ids = fields.Many2many('odoocms.class.primary',string="Classes")

	def assign_domain_rule(self):
		for primary_class_id in self.primary_class_ids:
			primary_class_id.enroll_domain = self.enroll_domain
		
		return {'type': 'ir.actions.act_window_close'}



