# -*- coding: utf-8 -*-
import pdb
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import json
import logging

_logger = logging.getLogger(__name__)


class OdooCMSAssessmentTemplate(models.Model):
	_name = 'odoocms.assessment.template'
	_description = 'Assessment Template'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_order = 'sequence'
	
	sequence = fields.Integer('Sequence')
	name = fields.Char('Template Name', copy=False)
	code = fields.Char('Template Code', copy=False)
	component = fields.Selection([
		('lab', 'Lab'),
		('lecture', 'Lecture'),
		('studio', 'Studio'),
	], string='Component', required=True)
	institute_id = fields.Many2one('odoocms.institute','Faculty/Institute')
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSClassGenerator(models.Model):
	_name = 'odoocms.class.generator'
	_description = 'Class Generator'
	_order = 'name desc, id desc'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	
	@api.model
	def _get_institute(self):
		institute_ids = self.env['odoocms.institute'].search([])
		institute_id = False
		if len(institute_ids) == 1:
			institute_id = institute_ids[0].id
		return institute_id
	
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	generator_type = fields.Selection([('scheme', 'Study Scheme'), ('faculty', 'Faculty')], string='Generator Type', default='scheme', required=True)
	term_id = fields.Many2one('odoocms.academic.term','Academic Term')
	institute_id = fields.Many2one('odoocms.institute','Institute', default=_get_institute)
	department_id = fields.Many2one('odoocms.department','Department/Center')
	program_id = fields.Many2one('odoocms.program','Program')
	batch_ids = fields.Many2many('odoocms.batch', string='Batches')
	course_id = fields.Many2one('odoocms.course','Course')
	course_ids = fields.Many2many('odoocms.course', string='Courses')
	
	can_generate = fields.Boolean(compute='_can_generate',store=True)
	state = fields.Selection([('draft','Draft'),('done','Done'),('cancel','Cancel')],'Status',default='draft')
	type = fields.Selection([('compulsory','Core Course'),('gen_elective','General Elective'),('elective','Elective'),('specialization','Specialization')],'Courses Type',default='compulsory')
	class_type = fields.Selection([('regular','Regular'),('special','Special/Summer')],'Class Type',default='regular')
	offer_for = fields.Selection([('new','New Students'), ('ongoing','On Going Students'),('both','Both')],'Offer For', default='both')
	course_domain = fields.Char(compute='_compute_course_domain', readonly=True, store=False)
	
	section_pattern = fields.Many2one('odoocms.section.pattern','Section Pattern')
	lec_assessment_template_id = fields.Many2one('odoocms.assessment.template','Lecture Template')
	lab_assessment_template_id = fields.Many2one('odoocms.assessment.template','Lab Template')
	
	line_ids = fields.One2many('odoocms.class.generator.line', 'generator_id', 'Lines')
	primary_class_ids = fields.One2many('odoocms.class.primary','generator_id','Primary Classes')
	
	section_strength = fields.Integer('Section Strength', default=45)
	restrict = fields.Selection([('no','No Restrict'),('section','Section'),('program','Program'),('institute','Faculty')], 'Restrict To', default='no')
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.class.generator') or _('New')
		result = super().create(vals)
		return result
	
	@api.depends('program_id', 'department_id')
	def _compute_course_domain(self):
		for rec in self:
			rec.course_domain = json.dumps([(1, '=', 1)])
		# 	course_ids = self.env['odoocms.course.program'].search([('program_id', '=', rec.program_id.id), ('can_offer', '=', True)])
		# 	rec.course_domain = json.dumps([('id', 'in', course_ids.mapped('course_id').ids)])
			
	@api.depends('line_ids')
	def _can_generate(self):
		if self.line_ids:
			self.can_generate = True
		else:
			self.can_generate = False
			
	def _get_section_count(self, batch):
		if batch:
			batch_strength = self.env['odoocms.student'].search_count([('batch_id', '=', batch.id),('state','in',('draft','enroll'))])
			if batch.section_ids:
				section_count = len(batch.section_ids)
			elif batch.sections and batch.sections > 0:
				section_count = batch.sections
			else:
				section_count = round((batch_strength / (self.section_strength or 45)), 0) or 1
		else:
			batch_strength = (self.section_strength or 45)
			section_count = 1
		return batch_strength, section_count
	
	def add_course(self):
		batch = len(self.batch_ids) > 0 and self.batch_ids[0] or False
		course_data = []
		for course_id in self.course_ids:    #+ self.course_id:
			batch_strength, section_count = self._get_section_count(batch)
			
			data = {
				'name': course_id.name,
				'code': course_id.code,
				'batch_id': batch and batch.id or False,
				'program_id': self.program_id and self.program_id.id or False,
				'department_id': self.department_id.id,
				'institute_id': self.institute_id.id,
				'career_id': self.program_id.career_id.id,
				'course_id': course_id.id,
				'count': section_count,
				'batch_strength': batch_strength,
				'strength': (self.section_strength or 45),
				'type': self.type if self.generator_type == 'scheme' else False,
				'class_type': self.class_type if self.generator_type == 'scheme' else False,
				'scheme_line_id': False,
			}
			course_data.append((0, 0, data))

			# Add CO-REQ
			if course_id.coreq_course and course_id.coreq_course not in self.course_ids:
				data = {
					'name': course_id.coreq_course.name,
					'code': course_id.coreq_course.code,
					'batch_id': batch and batch.id or False,
					'program_id': self.program_id and self.program_id.id or False,
					'department_id': self.department_id.id,
					'institute_id': self.institute_id.id,
					'career_id': self.program_id.career_id.id,
					'course_id': course_id.coreq_course.id,
					'count': section_count,
					'batch_strength': batch_strength,
					'strength': (self.section_strength or 45),
					'type': self.type if self.generator_type == 'scheme' else False,
					'class_type': self.class_type if self.generator_type == 'scheme' else False,
					'scheme_line_id': False,
				}
				course_data.append((0, 0, data))
				
		self.line_ids = course_data
		self.course_ids = False
		# self.course_id = False
		
	def fetch_scheme_courses(self):
		#classes = [[5]]
		classes = []
		for batch in self.batch_ids:
			# term_scheme = self.env['odoocms.term.scheme'].search(
			# 	[('session_id', '=', batch.session_id.id), ('term_id', '=', batch.term_id.id)])
			# if not term_scheme:
			# 	raise ValidationError('Term Scheme is not defined for %s and %s' % (batch.session_id.name, batch.term_id.name,))
			scheme_lines = self.env['odoocms.study.scheme.line']
			if self.type in ('compulsory','specialization','gen_elective'): # Get all compulsory courses of specific term
				scheme_lines = batch.study_scheme_id.line_ids.filtered(
					lambda l: l.term_id.id == self.term_id.id and l.course_type == self.type)
			else: # Get all courses of specific time from study scheme
				scheme_lines = batch.study_scheme_id.line_ids.filtered(
					lambda l: l.term_id.id == self.term_id.id and l.course_type == self.type)
				if not scheme_lines:
					placeholder_lines = batch.study_scheme_id.line_ids.filtered(
						lambda l: l.term_id.id == self.term_id.id and l.course_type == 'placeholder')
					if placeholder_lines:
						scheme_lines = batch.study_scheme_id.line_ids.filtered(
							lambda l: l.course_type == self.type and l.credits in placeholder_lines.mapped('credits'))
				
			for scheme_line in scheme_lines:
				exists = self.line_ids.filtered(lambda l: l.code == scheme_line.course_id.code and l.batch_id.id == batch.id and l.department_id.id == self.department_id.id)
				if not exists:
					batch_strength = self.env['odoocms.student'].search_count([('batch_id', '=', batch.id),('state','in',('draft','enroll'))])
					existing_sections = self.env['odoocms.class.primary'].search_count([
						('batch_id','=', batch.id),('term_id','=',self.term_id.id),('study_scheme_line_id','=',scheme_line.id)
					])
					if batch.section_ids:
						section_count = max(len(batch.section_ids) - existing_sections,0)
					elif batch.sections and batch.sections > 0:
						section_count = max(batch.sections - existing_sections,0)
					else:
						section_count = max((round(batch_strength / (self.section_strength or 45),0) or 1) - existing_sections,0)
					data = {
						'name': scheme_line.course_id.name,
						'code': scheme_line.course_id.code,
						'batch_id': batch.id,
						'program_id': self.program_id and self.program_id.id or False,
						'department_id': self.department_id.id,
						'institute_id': self.department_id.institute_id.id,
						'career_id': batch.career_id.id,
						'course_id': scheme_line.course_id.id,
						'scheme_line_id': scheme_line.id,
						'generate_count': existing_sections,
						'count': section_count,
						'batch_strength': batch_strength,
						'strength': (self.section_strength or 45),
						'type': self.type,
						'class_type': self.class_type,
					}
					classes.append((0, 0, data))
		
		if len(classes) > 0:
			self.line_ids = classes
	
	def add_classes(self, term_id, class_code, class_name, line, term_section=None, section_name=None, batch_term=None, batch_section=None):
		# There is Primary Class for each Section x Course
		batch_term_section_id = None
		if batch_term and batch_section:
			batch_term_section_id = self.env['odoocms.batch.term.section'].search([('batch_term_id','=',batch_term.id),('name', '=', batch_section.name)])
			if not batch_term_section_id:
				data = {
					'name': batch_section.name,
					'code': batch_term.code + '-' + batch_section.name, #batch_term.batch_id.code + '-' + batch_section.name,
					'batch_term_id': batch_term.id,
				}
				batch_term_section_id = self.env['odoocms.batch.term.section'].create(data)
		
		primary_class_id = self.env['odoocms.class.primary'].search([('code', '=', class_code)])
		SL = line.scheme_line_id or None
		if not primary_class_id:
			class_ids = []
			allowed_institute_ids = []
			grade_class_id = self.env['odoocms.class.grade'].search([('code', '=', class_code)])
			if not grade_class_id:
				grade_method = False
				if line.batch_id:
					if line.batch_id.grade_method_id:
						grade_method = line.batch_id.grade_method_id.id
					else:
						grade_method = line.batch_id.program_id.grade_method_id and line.batch_id.program_id.grade_method_id.id
				elif SL:
					grade_method = SL.grade_method_id and SL.grade_method_id.id or False
				else:
					grade_method = line.program_id.grade_method_id and line.program_id.grade_method_id.id or False

				grade_class_data = {
					'name': class_name,
					'code': class_code,
					'course_id': line.course_id.id,
					'batch_id': line.batch_id and line.batch_id.id or False,
					'career_id': line.career_id and line.career_id.id or False,
					'program_id': line.program_id and line.program_id.id or False,
					'department_id': line.department_id and line.department_id.id or False,
					'term_id': term_id.id,
					'grade_method_id': grade_method,
					'study_scheme_id': line.batch_id and line.batch_id.study_scheme_id.id or False,
					'study_scheme_line_id': SL and SL.id or False,
					'batch_term_id': batch_term and batch_term.id or False,
				}
				_logger.info('Generating Grading Class: %s' % (grade_class_data['code']))
				grade_class_id = self.env['odoocms.class.grade'].create(grade_class_data)

			credits = 0
			components = SL and SL.component_lines or line.course_id.component_lines
			for component in components:
				assessment_template_id = False
				if component.component == 'lecture' and self.lec_assessment_template_id:
					assessment_template_id = self.lec_assessment_template_id.id
				elif component.component == 'lab' and self.lab_assessment_template_id:
					assessment_template_id = self.lab_assessment_template_id.id
					
				class_data = {
					'name': class_name,
					'code': class_code + '-' + component.component,
					'component': component.component,
					'weightage': component.weightage,
					'contact_hours': component.contact_hours,
					'batch_section_id': (term_section and term_section.id or False) if self.generator_type == 'scheme' and not section_name else False,  # check section_name
					'batch_term_section_id': batch_term_section_id and batch_term_section_id.id or False,
					'assessment_template_id': assessment_template_id,
				}
				if line.batch_id:
					class_data = line.batch_id.component_hook(class_data, SL)
				credits += component.weightage
				class_ids.append((0, 0, class_data))
			
			data = {
				'name': class_name,
				'code': class_code,
				'class_type': 'special' if self.generator_type == 'faculty' else line.class_type,
				'session_id': line.batch_id and line.batch_id.session_id.id or False,
				'batch_id': line.batch_id and line.batch_id.id or False,
				'batch_term_section_id': batch_term_section_id and batch_term_section_id.id or False,
				'batch_section_id': (batch_section and batch_section.id or False) if self.generator_type == 'scheme' and not section_name else False, # Check name
				'term_id': term_id.id,
				'program_id': line.program_id and line.program_id.id or False,
				'department_id': line.department_id and line.department_id.id or False,
				'study_scheme_id': line.batch_id and line.batch_id.study_scheme_id.id or False,
				'study_scheme_line_id': SL and SL.id or False,
				'course_id': line.course_id.id,
				'career_id': line.program_id.career_id.id,
				'strength': line.strength or self.section_strength or 45,
				'class_ids': class_ids,
				'grade_class_id': grade_class_id.id,
				'credits': credits,
				'major_course': SL and SL.major_course or line.course_id.major_course or False,
				'self_enrollment': SL and SL.self_enrollment or line.course_id.self_enrollment or False,
				'generator_id': self.id,
				'course_code': SL and SL.course_code and SL.course_code or line.course_id.code,
				'course_name': SL and SL.course_name and SL.course_name or line.course_id.name,
				'offer_for': self.offer_for,
				'allowed_institute_ids': [(6, 0, [self.institute_id.id] if self.restrict == 'institute' else [])],
				'allowed_program_ids': [(6, 0, [self.program_id.id] if self.restrict == 'program' and self.program_id else [])],
				'own_section': True if self.restrict == 'section' else False,
			}
			primary_class_id = self.env['odoocms.class.primary'].create(data)
		return primary_class_id
		
	def action_generate(self):
		primary_class_ids = self.env['odoocms.class.primary']
		for line in self.line_ids:
			# Scheme
			batch = line.batch_id
			if batch:
				batch_term = self.env['odoocms.batch.term'].search(
					[('batch_id', '=', batch.id), ('term_id', '=', self.term_id.id)])
				if not batch_term:
					batch_term_data = {
						'name': batch.code + '-' + self.term_id.code,
						'code': batch.code + '-' + self.term_id.code,
						'batch_id': batch.id,
						'term_id': self.term_id.id,
					}
					batch_term_data = batch.batch_term_hook(batch_term_data)
					batch_term = self.env['odoocms.batch.term'].create(batch_term_data)
				
				SL = line.scheme_line_id
				# cnt = 1
				if batch.section_ids and len(batch.section_ids) == line.count:
					for batch_section in batch.section_ids:
						# if cnt > line.count:
						# 	break
						# cnt = cnt + 1
						class_code = (SL and SL.course_code and SL.course_code or line.course_id.code) \
							+ '-' + self.term_id.short_code + '-' + batch_section.code
						class_name = SL and SL.course_name and SL.course_name or line.course_id.name
						
						primary_class_ids += self.add_classes(self.term_id, class_code, class_name, line, batch_section=batch_section, batch_term=batch_term)
				else:
					if not self.section_pattern:
						raise UserError('Please select the Section Pattern before generating the Classes')
					
					section_pattern = self.section_pattern.line_ids.sorted(key=lambda r: r.sequence, reverse=False)
					for x in range(1+line.generate_count, line.count + line.generate_count + 1):
						section_name = chr(64 + x)
						batch_section = False
						if section_pattern and len(section_pattern) >= x:
							section_name = section_pattern[x-1].name
							batch_section = section_pattern[x-1]
						class_code = (SL and SL.course_code and SL.course_code or line.course_id.code) \
						             + '-' + self.term_id.short_code + '-' + self.institute_id.code + '-' + section_name
						class_name = SL and SL.course_name and SL.course_name or line.course_id.name
						primary_class_ids += self.sudo().add_classes(self.term_id, class_code, class_name, line, section_name=section_name, batch_term=batch_term,batch_section=batch_section)
			
			
			# Faculty
			else:
				section_pattern = self.section_pattern.line_ids.sorted(key=lambda r: r.sequence, reverse=False)
				SL = line.scheme_line_id or False
				for x in range(1+line.generate_count, line.count + line.generate_count + 1):
					section_name = chr(64 + x)
					batch_section = False
					if section_pattern and len(section_pattern) >= x:
						section_name = section_pattern[x - 1].name
						batch_section = section_pattern[x - 1]
						
					class_code = (SL and SL.course_code and SL.course_code or line.course_id.code) \
						+ '-' + self.term_id.short_code + '-' + self.institute_id.code + '-' + section_name
					class_name = SL and SL.course_name and SL.course_name or line.course_id.name
					primary_class_ids += self.sudo().add_classes(self.term_id, class_code, class_name, line, section_name=section_name, batch_section=batch_section)
			
		self.state = 'done'
		if primary_class_ids:
			class_list = primary_class_ids.mapped('id')
			return {
				'domain': [('id', 'in', class_list)],
				'name': _('Classes'),
				'view_type': 'form',
				'view_mode': 'tree,form',
				'res_model': 'odoocms.class.primary',
				'view_id': False,
				'type': 'ir.actions.act_window'
			}
		
	def action_reject(self):
		self.state = 'cancel'
		
	def action_reset_draft(self):
		self.state = 'draft'


class OdooCMSClassGeneratorLine(models.Model):
	_name = 'odoocms.class.generator.line'
	_description = 'Class Generator Lines'
	
	generator_id = fields.Many2one('odoocms.class.generator','Generator')
	batch_id = fields.Many2one('odoocms.batch','Batch')
	program_id = fields.Many2one('odoocms.program','Program')
	department_id = fields.Many2one('odoocms.department','Department/Center')
	institute_id = fields.Many2one('odoocms.institute','Institute')
	career_id = fields.Many2one('odoocms.career','career')
	name = fields.Char('Name')
	code = fields.Char('Code')
	scheme_line_id = fields.Many2one('odoocms.study.scheme.line','Course Offer')
	course_id = fields.Many2one('odoocms.course','Catalogue Course')
	generate_count = fields.Integer('Existing Count',help='Already Generated Sections Count')
	count = fields.Integer('New Count',help='New Required Sections')
	strength = fields.Integer('Section Strength')
	batch_strength = fields.Integer('Batch Strength')
	
	type = fields.Selection([('compulsory', 'Core Course'), ('gen_elective', 'General Elective'),('elective', 'Elective'),('specialization','Specialization')], 'Courses Type', default='compulsory')
	class_type = fields.Selection([('regular', 'Regular'), ('special', 'Special/Summer')], 'Class Type', default='regular')
	generator_type = fields.Selection(related='generator_id.generator_type', string='Generator Type', store=True)
	company_id = fields.Many2one('res.company', string='Company', related='generator_id.company_id', store=True)

	@api.onchange('strength')
	def onchange_strength(self):
		for rec in self:
			if rec.strength and rec.batch_strength:
				rec.count = max((round(rec.batch_strength / (rec.strength or 45),0) or 1) - rec.generate_count,0)
				
