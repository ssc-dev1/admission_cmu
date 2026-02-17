import pdb

from odoo import api, fields, models,_
import math


class OdooCMSAssignTeacherWiz(models.TransientModel):
	_name ='odoocms.assign.teacher.wiz'
	_description = 'Assign Teachers Wizard'

	batch_id = fields.Many2one('odoocms.batch','Batch')
	term_id = fields.Many2one('odoocms.academic.term','Term')

	def assign_teacher(self):
		self.env['odoocms.class.faculty'].search([]).unlink()
		
		class_ids = self.env['odoocms.class'].search([('term_id','=',self.term_id.id), ('batch_id','=',self.batch_id.id)])
		class_ids.write({
			'faculty_staff_id': False
		})
		self.env.cr.commit()
		
		
		primary_class_ids = class_ids.mapped('primary_class_id')
		course_ids = primary_class_ids.mapped('course_id')
		for course_id in course_ids:
			sections = class_ids.filtered(lambda l: l.course_id.id == course_id.id).sorted(key=lambda r: r.section_name, reverse=False)
			available_teachers = course_id.faculty_staff_ids
			course_tags = course_id.tag_ids.ids
			faculty_tags = self.env['odoocms.faculty.staff'].search([('state','in',('active','notice_period')),('course_tag_ids', 'in', course_tags)])
			
			already_assigned = self.env['odoocms.class.faculty'].search([]).mapped('faculty_staff_id')
			possible_teachers = list(set(available_teachers + faculty_tags - already_assigned))
			per_teacher = max(math.ceil(len(sections) / len(possible_teachers)),4)
			i = j = 0
			for section in sections:
				if i >= per_teacher:
					j += 1
					i = 0
				
				data = {
					'faculty_staff_id': possible_teachers[j].id,
					'class_id': section.id,
					'role_id': 2,
				}
				self.env['odoocms.class.faculty'].create(data)
				i += 1
		
		return {'type': 'ir.actions.act_window_close'}



