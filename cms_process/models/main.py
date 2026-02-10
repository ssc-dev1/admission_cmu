from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval
from odoo.osv import expression
import decimal
from datetime import date, datetime
import pytz
import pdb


def roundhalfup(n, decimals=0):
	context = decimal.getcontext()
	context.rounding = decimal.ROUND_HALF_UP
	return float(round(decimal.Decimal(str(n)), decimals))


def check_student_survey(self, student):
	# KarachiTz = pytz.timezone("Asia/Karachi")
	# current_time = datetime.now(KarachiTz)
	current_time = datetime.now()

	survey_input_ids = self.env['survey.user_input'].sudo().search([('student_id', '=', student.id)])
	for survey in survey_input_ids:
		if (not student.survey_bypass and not survey.survey_id.no_block and survey.state in ('new', 'skip', 'in_progress')) and survey.survey_id.session_state == 'in_progress' \
				and survey.survey_id.start_date <= current_time and survey.survey_id.end_date >= current_time:
			return '/student/qa/feedback'
	return False


def check_faculty_survey(self, faculty_staff):
	# KarachiTz = pytz.timezone("Asia/Karachi")
	# current_time = datetime.now(KarachiTz)
	current_time = datetime.now()

	survey_input_ids = self.env['survey.user_input'].sudo().search([('faculty_staff_id', '=', faculty_staff.id)])
	for survey in survey_input_ids:
		if (not survey.survey_id.no_block) and survey.state in ('new','skip','in_progress') and survey.survey_id.session_state == 'in_progress' \
				and survey.survey_id.start_date <= current_time and survey.survey_id.end_date >= current_time:
			return '/faculty/survey'
		return False


def get_current_term(self):
	term_id = self.env['odoocms.academic.term'].sudo().search([
		('current', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='number desc', limit=1)
	if not term_id:
		term = self.env['ir.config_parameter'].sudo().get_param('odoocms.current_term')
		if term:
			term_id = self.env['odoocms.academic.term'].sudo().browse(term_id)
	else:
		term = term_id and term_id.id or False
	return term_id, term

def get_registration_term(self):
	term_id = self.env['odoocms.academic.term'].sudo().search([
			('enrollment_active', '=', True),'|',('company_id','=',self.env.company.id),('company_id','=',False)], order='number desc', limit=1)
	term = term_id and term_id.id or False
	return term_id, term


def get_grade_rec(self, program_id, term_id, course_id):
	grade_rec = self.env['odoocms.grade'].sudo()
	if course_id.grade_id:
		grade_rec = course_id.grade_id
	elif self._name == 'odoocms.class.grade' and self.grade_method_id:
		grade_rec = self.grade_method_id.grade_id
	else:
		for grade in self.env['odoocms.grade'].sudo().search(['|',('company_id','=',self.env.company.id),('company_id','=',False)], order='sequence'):
			domain = expression.AND([safe_eval(grade.domain), [('id', '=', program_id.id)]]) if grade.domain else []
			program = self.env['odoocms.program'].sudo().search(domain)
			if program:
				term_domain = expression.AND([safe_eval(grade.term_domain), [('id', '=', term_id.id),'|',('company_id','=',self.env.company.id),('company_id','=',False)]]) if grade.term_domain else []
				term = self.env['odoocms.academic.term'].sudo().search(term_domain)
				if term:
					grade_rec = grade
					break
	return grade_rec

def get_curve_grade(self, grade_method_id, marks):
	grade_rec = grade_method_id
	# marks = roundhalfup(marks, 0)

	grade_line = grade_rec.line_ids.filtered(lambda g: g.low_per <= marks <= g.high_per)
	return grade_line and grade_line[0] or False


def get_absolute_grade(self, program_id, term_id, marks, course_id):
	grade_rec = get_grade_rec(self,program_id,term_id, course_id)
	marks = roundhalfup(marks, 0)

	grade_line = grade_rec.line_ids.filtered(lambda g: g.low_per <= marks <= g.high_per)
	return grade_line and grade_line[0] or False


def get_grade_master(self, term_id=None, batch_id=None):
	grade_master_id = False
	if term_id:
		grade_master_id = term_id.grade_master_id
	if not grade_master_id and batch_id:
		grade_master_id = batch_id.grade_master_id
	if not grade_master_id:
		grade_master_ids = self.env['odoocms.grade.gpa.master'].sudo().search(['|',('company_id','=',self.env.company.id),('company_id','=',False)])
		if len(grade_master_ids) == 1:
			grade_master_id = grade_master_ids[0]
		else:
			grade_master_ids = self.env['odoocms.grade.gpa.master'].sudo().search([
				('date_from', '<=', term_id.term_lines[0].date_start),
				'|',('date_to','=',False),('date_to', '>=', term_id.term_lines[0].date_end),'|',('company_id','=',self.env.company.id),('company_id','=',False)
			], order='date_from desc', limit=1)
			if grade_master_ids:
				grade_master_id = grade_master_ids[0]
	return grade_master_id


def get_grade_gpa_rec(self, grade, term_id=None, batch_id=None):
	grade_master_id = get_grade_master(self, term_id, batch_id)
	if not grade_master_id:
		raise UserError('GPA Master Setting is not properly configured.')
	
	grade_rec = self.env['odoocms.grade.gpa'].search([
		('master_id', '=', grade_master_id.id), ('name', '=', grade),'|',('company_id','=',self.env.company.id),('company_id','=',False)
	])
	if not grade_rec:
		raise UserError('GPA Setting is not properly configured. for %s-%s' % (grade_master_id.name, grade))
	return grade_rec