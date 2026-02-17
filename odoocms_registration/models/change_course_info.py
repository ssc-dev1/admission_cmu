import pdb

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from ...cms_process.models import main as main


class OdooCMSChangeCourseInfo(models.Model):
	_name ='odoocms.change.course.info'
	_description = 'Change Course Info'
	_order = 'name desc, id desc'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	
	@api.model
	def _get_term(self):
		term_id, term = main.get_current_term(self)
		return term
	
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	term_id = fields.Many2one('odoocms.academic.term','Term', required=True ,readonly=True, states={'draft': [('readonly', False)]}, default=_get_term)
	course_id = fields.Many2one('odoocms.course', 'Course', required=True ,readonly=True, states={'draft': [('readonly', False)]})
	course_name = fields.Boolean('Course Name',default=False, readonly=True, states={'draft': [('readonly', False)]})
	course_code = fields.Boolean('Course Code',default=False, readonly=True, states={'draft': [('readonly', False)]})
	composition = fields.Boolean('Course Composition',default=False, readonly=True, states={'draft': [('readonly', False)]})
	
	new_course_name = fields.Text('New Name',readonly=True, states={'draft': [('readonly', False)]})
	new_course_code = fields.Text('New Code',readonly=True, states={'draft': [('readonly', False)]})
	component_lines = fields.One2many('odoocms.change.course.info.component', 'change_id', string='Course Components',readonly=True, states={'draft': [('readonly', False)]})
	credits = fields.Float('Credit Hours', compute='_compute_credits', store=True)
	state = fields.Selection([('draft', 'Draft'), ('done', 'Done'), ('cancel', 'Cancel')], 'Status', default='draft')
	
	class_ids = fields.Many2many('odoocms.class.primary',readonly=True, states={'draft': [('readonly', False)]})
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

	@api.model
	def create(self, vals):
		if vals.get('name', 'New') == 'New':
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.change.course.info') or 'New'
		result = super().create(vals)
		return result
	
	def get_classes(self):
		domain = [
			('term_id', '=', self.term_id.id),
			('course_id', '=', self.course_id.id),
		]
		classes = self.env['odoocms.class.primary'].search(domain)
		self.class_ids = [(6, 0, classes.ids)]
		
	def action_confirm(self):
		if not self.class_ids:
			raise UserError('No Class is selected for change of Info')
		
		for primary_class in self.class_ids:
			if self.course_name or self.course_code:
				if self.course_name:
					primary_class.course_name = self.new_course_name
				if self.course_code:
					primary_class.course_code = self.new_course_code
				primary_class._get_code()
				
				if primary_class.grade_class_id:
					primary_class.grade_class_id._get_code()
				for component_class in primary_class.class_ids:
					component_class._get_code()
			
			if self.composition:
				if len(self.component_lines) != len(primary_class.class_ids) or len(primary_class.class_ids) > 1:
					raise UserError('Composition Lines for %s Mismatch')
				primary_class.class_ids[0].component = self.component_lines[0].component
				primary_class.class_ids[0].weightage = self.component_lines[0].weightage

			for registration in primary_class.registration_ids:
				if self.course_name:
					registration.course_name = self.new_course_name
				if self.course_code:
					registration.course_code = self.new_course_code
				
				if self.composition:
					for component in registration.component_ids:
						component.weightage = self.component_lines[0].weightage
					
					for component_class in primary_class.class_ids:
						for rec in self.env['odoocms.class.attendance'].search([('class_id', '=', component_class.id),('att_marked','=',True)]):
							rec.apply_policy()
							rec.policy = False
							rec.to_be = False
							
		self.state = 'done'
		
	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'
			
	def action_reset_draft(self):
		for rec in self:
			rec.state = 'draft'
			
					
class OdooCMSChangeCourseInfoComponent(models.Model):
	_name = 'odoocms.change.course.info.component'
	_description = 'CMS Change Course Info Component'
	
	change_id = fields.Many2one('odoocms.change.course.info', ondelete='cascade')
	component = fields.Selection([
		('lab', 'Lab'),
		('lecture', 'Lecture'),
		('studio', 'Studio'),
	], string='Component', required=True)
	weightage = fields.Float(string='Credit Hours', default=3.0, help="Weightage for this Course")
	
	_sql_constraints = [
		('unique_course_info_component', 'unique(change_id,component)', "Component already exists in Course"), ]
	
	@api.constrains('weightage')
	def check_weightage(self):
		for rec in self:
			if rec.weightage < 0:
				raise ValidationError('Weightage must be Positive')

		
		



