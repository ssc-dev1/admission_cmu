import pdb

from odoo import api, fields, models,_
import math


class OdooCourseDrop(models.Model):
	_name ='odoocms.course.drop'
	_description = 'Course Drop'
	
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
	                   states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	
	class_id = fields.Many2one('odoocms.class.primary', string='Class to Drop', readonly=True, states={'draft': [('readonly', False)]})
	dropped_class = fields.Char('Dropped Class')
	batch_id = fields.Many2one('odoocms.batch','Batch', readonly=True, states={'draft': [('readonly', False)]})
	term_id = fields.Many2one('odoocms.academic.term','Term', readonly=True, states={'draft': [('readonly', False)]})
	
	student_ids = fields.Many2many('odoocms.student','course_drop_student_rel','drop_id','student_id','Students'
	    , readonly=True, states={'draft': [('readonly', False)]})
	state = fields.Selection([('draft','Draft'),('submit','Submit'),('done','Done'),('cancel','Cancel')], 'Status', default='draft')
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

	def action_submit(self):
		if self.name == _('New'):
			self.name = self.env['ir.sequence'].next_by_code('odoocms.course.drop') or _('New')
		self.state = 'submit'
		
	def action_cancel(self):
		self.state = 'submit'
		
	def action_draft(self):
		self.state = 'draft'
		
	def fetch_students(self):
		if self.class_id and self.class_id.registration_ids:
			self.student_ids = [(5,0,0),(6,0,self.class_id.registration_ids.mapped('student_id').ids)]
			
	def drop_course(self):
		self.dropped_class = self.class_id.code or '' + '-' + self.class_id.name
		for student in self.student_ids:
			registration = student.enrolled_course_ids.filtered(lambda l: l.term_id.id == self.term_id.id and l.primary_class_id.id == self.class_id.id)
			if registration:
				
				# Have to handle fee
				registration.unlink()
		
		self.class_id.timetable_ids.unlink()
		self.class_id.unlink()
		self.state = 'done'
		


