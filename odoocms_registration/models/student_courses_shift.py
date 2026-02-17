import pdb
from odoo.exceptions import ValidationError, UserError
from odoo import api, fields, models,_


class OdooStudentCoursesShift(models.Model):
	_name ='odoocms.student.courses.shift'
	_description = 'Student Courses Shift'
	
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
	                   states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	
	student_id = fields.Many2one('odoocms.student', string='Student', readonly=True, states={'draft': [('readonly', False)]})
	batch_id = fields.Many2one('odoocms.batch','Batch', related='student_id.batch_id', store=True)
	program_id = fields.Many2one('odoocms.program','Program', related='student_id.program_id', store=True)
	term_id = fields.Many2one('odoocms.academic.term','Term', readonly=True, states={'draft': [('readonly', False)]})
	from_section = fields.Many2one('odoocms.batch.term.section', 'From Section', readonly=True, states={'draft': [('readonly', False)]})
	to_section = fields.Many2one('odoocms.batch.term.section', 'To Section', readonly=True, states={'draft': [('readonly', False)]})
	class_ids = fields.Many2many('odoocms.class.primary','course_shift_class_rel','shift_id','primary_class_id','Courses to Shift'
	    , readonly=True, states={'draft': [('readonly', False)]})
	new_class_ids = fields.Many2many('odoocms.class.primary','course_shift_new_class_rel','shift_id','primary_class_id','Courses Shifted to'
	    , readonly=True, states={'draft': [('readonly', False)]})
	state = fields.Selection([('draft','Draft'),('submit','Submit'),('done','Done'),('cancel','Cancel')], 'Status', default='draft')
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

	def action_submit(self):
		if self.from_section == self.to_section:
			raise UserError('Please select two different Sections')
		
		if self.name == _('New'):
			self.name = self.env['ir.sequence'].next_by_code('odoocms.student.courses.shift') or _('New')
		self.state = 'submit'
		
	def action_cancel(self):
		self.state = 'submit'
		
	def action_draft(self):
		self.state = 'draft'
		
	def fetch_courses(self):
		if self.from_section == self.to_section:
			raise UserError('Please select two different Sections')
			
		class_ids = self.env['odoocms.class.primary']
		new_class_ids = self.env['odoocms.class.primary']
		for primary_class in self.student_id.enrolled_course_ids.filtered(lambda l: l.term_id.id == self.term_id.id).mapped('primary_class_id'):
			if primary_class in self.from_section.primary_class_ids:
				class_ids += primary_class
		if class_ids:
			for primary_class in class_ids:
				new_class = self.to_section.primary_class_ids.filtered(lambda l: l.course_id.id == primary_class.course_id.id)
				new_class_ids += new_class
			self.class_ids = [(5,0,0),(6,0,class_ids.ids)]
			self.new_class_ids = [(5,0,0),(6,0,new_class_ids.ids)]
			
	def shift_courses(self):
		if self.from_section == self.to_section:
			raise UserError('Please select two different Sections')
		
		registration_ids = self.env['odoocms.student.course']
		for primary_class in self.class_ids:
			registration = self.student_id.enrolled_course_ids.filtered(lambda l: l.term_id.id == self.term_id.id and l.primary_class_id.id == primary_class.id)
			if registration:
				new_class_primary = self.new_class_ids.filtered(lambda l: l.course_id.id == registration.course_id.id)
				if new_class_primary:
					for component in registration.component_ids:
						new_class = new_class_primary.class_ids.filtered(lambda m: m.component == component.class_id.component)
						if new_class:
							component.class_id = new_class.id
					
					registration.primary_class_id = new_class_primary.id
					registration_ids += registration
		
		self.state = 'done'
		if registration_ids:
			reg_list = registration_ids.mapped('id')
			return {
				'domain': [('id', 'in', reg_list)],
				'name': _('Student Courses'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'odoocms.student.course',
				'view_id': False,
				# 'context': {'default_class_id': self.id},
				'type': 'ir.actions.act_window'
			}


class OdooStudentCourseShift(models.Model):
	_name = 'odoocms.student.course.shift'
	_description = 'Student Course Shift'

	name = fields.Char('Reference', required=True, copy=False, readonly=True,
		states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))

	term_id = fields.Many2one('odoocms.academic.term', 'Term', readonly=True, states={'draft': [('readonly', False)]})
	remarks = fields.Char('Remarks', readonly=True, states={'draft': [('readonly', False)]})
	line_ids = fields.One2many('odoocms.student.course.shift.line','shift_id','Lines')
	state = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('done', 'Done'), ('cancel', 'Cancel')], 'Status', default='draft')
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

	def action_submit(self):
		if self.name == _('New'):
			self.name = self.env['ir.sequence'].next_by_code('odoocms.student.course.shift') or _('New')
		self.state = 'submit'

	def action_cancel(self):
		self.state = 'submit'

	def action_draft(self):
		self.state = 'draft'

	def shift_courses(self):
		registration_ids = self.env['odoocms.student.course']
		for line in self.line_ids:
			if line.to_section:
				for course_component in line.course_id.component_ids:
					new_component = line.to_section.class_ids.filtered(lambda m: m.component == course_component.class_id.component)
					if new_component:
						course_component.class_id = new_component.id

				line.course_id.primary_class_id = line.to_section.id
				registration_ids += line.course_id

		self.state = 'done'
		if registration_ids:
			reg_list = registration_ids.mapped('id')
			return {
				'domain': [('id', 'in', reg_list)],
				'name': _('Student Courses'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'odoocms.student.course',
				'view_id': False,
				'type': 'ir.actions.act_window'
			}


class OdooStudentCourseShiftLine(models.Model):
	_name = 'odoocms.student.course.shift.line'
	_description = 'Student Course Shift Line'

	shift_id = fields.Many2one('odoocms.student.course.shift', 'Shift ID')
	student_id = fields.Many2one('odoocms.student', 'Student')
	course_id = fields.Many2one('odoocms.student.course', 'Course')
	from_section = fields.Many2one('odoocms.class.primary', 'From Section')
	to_section = fields.Many2one('odoocms.class.primary', 'To Section')

	@api.onchange('course_id')
	def onchange_course(self):
		if self.course_id:
			self.from_section = self.course_id.primary_class_id.id
			course_id = self.course_id.primary_class_id.course_id
			courses = self.env['odoocms.class.primary'].search([('term_id','=',self.shift_id.term_id.id),('course_id','=',course_id.id)]) - self.from_section
			domain = [('id', 'in', courses.ids)]
			return {
				'domain': {
					'to_section': domain
				},
			}
