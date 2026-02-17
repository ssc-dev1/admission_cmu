import pdb
from datetime import datetime, date
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from odoo.osv import expression
from odoo.tools.safe_eval import safe_eval


class OdooCMSStudentTermDefer(models.Model):
	_name = "odoocms.student.term.defer"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Student Term Defer"
	_rec_name = 'student_id'
	
	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}
		
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student",states=READONLY_STATES)
	career_id = fields.Many2one('odoocms.career', string='Career/Degree Level', related='student_id.career_id', store=True)
	program_id = fields.Many2one('odoocms.program' ,string='Academic Program',related='student_id.program_id',store=True)
	batch_id = fields.Many2one('odoocms.batch' ,string='Batch',related='student_id.batch_id',store=True)
	batch_section_id = fields.Many2one('odoocms.batch.section',string='Batch Section', related='student_id.batch_section_id', store=True)

	current_term_id = fields.Many2one('odoocms.academic.term', string='Current Term', compute='_get_current_term', store=True)
	semester_id = fields.Many2one('odoocms.semester', string='Current Semester', compute='_get_current_term', store=True)
	term_seq = fields.Integer(related='current_term_id.number',store=True)
		
	term_id = fields.Many2one('odoocms.academic.term' ,string='Term to Defer',states=READONLY_STATES)
	reason = fields.Text(string='Reason',states=READONLY_STATES)
	bypass = fields.Boolean('ByPass Approval Process',states=READONLY_STATES)
		
	attachment = fields.Binary('Attachment')
	invoice_id = fields.Many2one('account.move', 'Invoice')
	# invoice_status = fields.Selection(string='Invoice Status',related='invoice_id.state', tracking=True)
		
	can_defer = fields.Boolean('Can Defer', compute='_can_defer', tracking=True)
	state = fields.Selection([('draft' ,'Draft'), ('submit' ,'Submitted'), ('approve' ,'Approved'), ('done' ,'Done'), ('cancel' ,'Canceled')]
		,default='draft' ,string="Status" ,tracking=True)
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_approve = fields.Date(string='Approve Date', readonly=True)

	@api.depends('student_id')
	def _get_current_term(self):
		for rec in self:
			current_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', rec.student_id.id)], order='number desc', limit=1)
			rec.current_term_id = current_term.term_id.id
			rec.semester_id = current_term.semester_id and current_term.semester_id.id or False

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.term.defer') or _('New')
		result = super().create(vals)
		return result

	def _can_defer(self):
		can_defer = False
		if self.state == 'approve':
			if self.invoice_id and self.invoice_status == 'paid':
				can_defer = True
			else:
				# sm_defer_receipt_type = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.sm_defer_receipt_type')
				#
				# if not sm_defer_receipt_type:
				# 	raise UserError('Please configure the Term Defer Receipt Type in Global Settings')
				# sm_defer_receipt_type = self.env['odoocms.receipt.type'].search([('id','=',sm_defer_receipt_type)])
				# if not sm_defer_receipt_type.fee_head_ids:
				# 	raise UserError('Please configure heads with Receipt Type.')
				#
				# fee_structure = self.env['odoocms.fee.structure'].search([
				# 	('academic_session_id','=',self.student_id.academic_session_id.id),
				# 	('career_id','=',self.student_id.career_id.id)
				# ])
				#
				# fee_amount = 0
				# if fee_structure and fee_structure.line_ids and fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id == sm_defer_receipt_type.fee_head_ids[0].id):
				# 	fee_amount = fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id == sm_defer_receipt_type.fee_head_ids[0].id).fee_amount
				# if fee_amount <= 0:
				# 	can_defer = True
				can_defer = True
		self.can_defer = can_defer

	def action_invoice(self):
		sm_defer_receipt_type = self.env['ir.config_parameter'].sudo().get_param('odoocms_fee.sm_defer_receipt_type')
		if not sm_defer_receipt_type:
			raise UserError('Please configure the Term Defer Receipt Type in Global Settings')
		sm_defer_receipt_type = self.env['odoocms.receipt.type'].search([('id','=',sm_defer_receipt_type)])
		if not sm_defer_receipt_type.fee_head_ids:
			raise UserError('Please configure heads with Receipt Type.')

		fee_structure = self.env['odoocms.fee.structure'].search([
			('academic_session_id','=',self.student_id.academic_session_id.id),
			('career_id','=',self.student_id.career_id.id)
		])

		fee_amount = 0
		if fee_structure and fee_structure.line_ids and fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id == sm_defer_receipt_type.fee_head_ids[0].id):
			fee_amount = fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id == sm_defer_receipt_type.fee_head_ids[0].id).fee_amount
		# sm_defer_receipt_type.fee_head_ids[0].

		if fee_amount > 0:
			view_id = self.env.ref('odoocms_fee.view_odoocms_generate_invoice_form')
			return {
				'name': _('Term Defer Invoice'),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'odoocms.generate.invoice',
				'view_id': view_id.id,
				'views': [(view_id.id, 'form')],
				'context': {
					'default_fixed_type': True,
					'default_receipt_type_ids': [(4, sm_defer_receipt_type.id, None)]},
				'target': 'new',
				'type': 'ir.actions.act_window'
			}
		return {'type': 'ir.actions.act_window_close'}

	def action_submit_portal(self):
		for rec in self:
			activity = self.env.ref('odoocms_registration.mail_act_term_defer')
			self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
			rec.state = 'submit'

	def action_submit(self):
		for rec in self:
			exist_recs = self.env['odoocms.student.term.defer'].search([('student_id','=',rec.student_id.id),('state','in',('submit','approve','done'))])
			if len(exist_recs) >= 2:
				raise UserError('Two Defered records already exist')
			
			if rec.bypass:
				rec.defer_term()
			else:
				activity = self.env.ref('odoocms_registration.mail_act_term_defer')
				self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
				rec.state = 'submit'

	def action_approve(self):
		for rec in self:
			rec.date_approve = date.today()
			rec.state = 'approve'

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'

	def defer_term(self):
		deferred_tag = self.env['odoocms.student.tag'].search([('name', '=', 'Deferred')])
		if not deferred_tag:
			values = {
				'name': 'Deferred',
				'code': 'deferred',
			}
			deferred_tag = self.env['odoocms.student.tag'].create(values)
			
		for rec in self:
			student_course = self.env['odoocms.student.course'].search([
				('student_id','=',rec.student_id.id),
				('term_id','=', rec.term_id.id),
				('course_type','in',('compulsory','elective','additional','alternate','minor',))
			])
			if student_course:
				student_course.active = False
				#student_course.unlink()
			rec.state = 'done'
			
			tags = rec.student_id.tag_ids + deferred_tag
			rec.student_id.write({
				'tag_ids': [[6, 0, tags.ids]]
			})
			# rec.term_id.term_type = 'defer'


class OdooCMSStudentTermResume(models.Model):
	_name = "odoocms.student.term.resume"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Student Term Resume"
		
	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}

	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student",states=READONLY_STATES)
	program_id = fields.Many2one(related='student_id.program_id',string='Academic Program')
	batch_id = fields.Many2one(related='student_id.batch_id',string='Class Batch')
	batch_section_id = fields.Many2one(related='student_id.batch_section_id',string='Batch Section', store=True)

	current_term_id = fields.Many2one('odoocms.academic.term', string='Current Term', compute='_get_current_term', store=True)
	semester_id = fields.Many2one('odoocms.semester', string='Current Semester', compute='_get_current_term', store=True)

	term_id = fields.Many2one('odoocms.academic.term', string='Term to Resume', states=READONLY_STATES)
	reason = fields.Text(string='Reason', states=READONLY_STATES)

	invoice_id = fields.Many2one('account.move', 'Invoice')
	# invoice_status = fields.Selection(string='Invoice Status', related='invoice_id.state', tracking=True)
	can_approve = fields.Boolean('Can Approve', compute='_can_approve', tracking=True)
		
	state = fields.Selection([('draft', 'Draft'), ('submit' ,'Submitted'), ('approve', 'Approved'), ('done', 'Done'), ('cancel', 'Canceled')]
		, default='draft', string="Status", tracking=True)
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_approve = fields.Date(string='Approve Date', readonly=True)

	@api.depends('student_id')
	def _get_current_term(self):
		for rec in self:
			current_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', rec.student_id.id)], order='number desc', limit=1)
			rec.current_term_id = current_term.term_id.id
			rec.semester_id = current_term.semester_id and current_term.semester_id.id or False

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.term.resume') or _('New')
		result = super().create(vals)
		return result

	def _can_approve(self):
		can_approve = False
		if self.state == 'submit':
			# if self.invoice_id and self.invoice_status == 'paid':
			can_approve = True
		self.can_approve = can_approve

	# Later on Will do same as done for defer
		
	# def action_invoice(self):
	# 	sm_resume_receipt_type = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.sm_resume_receipt_type')
	# 	if not sm_resume_receipt_type:
	# 		raise UserError('Please configure the Term Un-Defer Receipt Type in Global Settings')
	#
	# 	view_id = self.env.ref('odoocms_fee.view_odoocms_generate_invoice_form')
	# 	return {
	# 		'name': _('Term Un-Defer Invoice'),
	# 		'view_type': 'form',
	# 		'view_mode': 'form',
	# 		'res_model': 'odoocms.generate.invoice',
	# 		'view_id': view_id.id,
	# 		'views': [(view_id.id, 'form')],
	# 		'context': {
	# 			'default_fixed_type': True,
	# 			'default_receipt_type_ids': [(4, eval(sm_resume_receipt_type), None)]},
	# 		'target': 'new',
	# 		'type': 'ir.actions.act_window'
	# 	}

	def action_invoice(self):
		sm_resume_receipt_type = self.env['ir.config_parameter'].sudo().get_param('odoocms_registration.sm_resume_receipt_type')
		if not sm_resume_receipt_type:
			return {'type': 'ir.actions.act_window_close'}
		sm_resume_receipt_type = self.env['odoocms.receipt.type'].search([('id','=',sm_resume_receipt_type)])

		if not sm_resume_receipt_type.fee_head_ids:
			raise UserError('Please configure heads with Receipt Type.')

		fee_structure = self.env['odoocms.fee.structure'].search([
			('academic_session_id','=',self.student_id.academic_session_id.id),
			('career_id','=',self.student_id.career_id.id)
		])

		fee_amount = 0
		if fee_structure and fee_structure.line_ids and fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id == sm_resume_receipt_type.fee_head_ids[0].id):
			fee_amount = fee_structure.line_ids.filtered(lambda l: l.fee_head_id.id == sm_resume_receipt_type.fee_head_ids[0].id).fee_amount
		# sm_resume_receipt_type.fee_head_ids[0].

		if fee_amount > 0:
			view_id = self.env.ref('odoocms_fee.view_odoocms_generate_invoice_form')
			return {
				'name': _('Term Un-Defer Invoice'),
				'view_type': 'form',
				'view_mode': 'form',
				'res_model': 'odoocms.generate.invoice',
				'view_id': view_id.id,
				'views': [(view_id.id, 'form')],
				'context': {
					'default_fixed_type': True,
					'default_receipt_type_ids': [(4, sm_resume_receipt_type.id, None)]},
				'target': 'new',
				'type': 'ir.actions.act_window'
			}
		return {'type': 'ir.actions.act_window_close'}

	def action_submit(self):
		for rec in self:
			rec.date_approve = date.today()
			rec.state = 'submit'

	def resume_term(self):
		deferred_tag = self.env['odoocms.student.tag'].search([('name', '=', 'Deferred')])
		for rec in self:
			rec.state = 'done'
			tags = rec.student_id.tag_ids - deferred_tag
			rec.student_id.write({
				'tag_ids': [[6, 0, tags.ids]],
				'state': 'enroll',
			})


class OdooCMSTuitionFeeDefer(models.Model):
	_name = 'odoocms.tuition.fee.defer'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Fee Deferment Requests"

	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}

	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES)
	career_id = fields.Many2one('odoocms.career', string='Career/Degree Level', related='student_id.career_id', store=True)
	program_id = fields.Many2one('odoocms.program', string='Academic Program', related='student_id.program_id', store=True)
	batch_id = fields.Many2one('odoocms.batch', string='Batch', related='student_id.batch_id', store=True)
	batch_section_id = fields.Many2one('odoocms.batch.section', string='Batch Section', related='student_id.batch_section_id', store=True)

	current_term_id = fields.Many2one('odoocms.academic.term', string='Current Term', compute='_get_current_term', store=True)
	semester_id = fields.Many2one('odoocms.semester', string='Current Semester', compute='_get_current_term', store=True)
	term_seq = fields.Integer(related='current_term_id.number', store=True)

	term_id = fields.Many2one('odoocms.academic.term', string='Term to Defer', states=READONLY_STATES)
	reason = fields.Text(string='Reason', states=READONLY_STATES)
	bypass = fields.Boolean('ByPass Approval Process', states=READONLY_STATES)

	state = fields.Selection([
		('draft', 'Draft'), ('submit', 'Submitted'), ('approve', 'Approved'), ('reject', 'Rejected'), ('done', 'Done'), ('cancel', 'Canceled')],
		default='draft', string="Status", tracking=True)
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_approve = fields.Date(string='Approve Date', readonly=True)

	@api.depends('student_id')
	def _get_current_term(self):
		current_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', self.student_id.id)], order='number desc', limit=1)
		self.current_term_id = current_term.term_id.id
		self.semester_id = current_term.semester_id and current_term.semester_id.id or False

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.tuition.fee.defer') or _('New')
		result = super().create(vals)
		return result

	def action_invoice(self):
		return {'type': 'ir.actions.act_window_close'}

	def action_submit_portal(self):
		for rec in self:
			# activity = self.env.ref('odoocms_registration.mail_act_term_defer')
			# self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
			rec.state = 'submit'

	def action_submit(self):
		for rec in self:
			exist_recs = self.env['odoocms.tuition.fee.defer'].search([('student_id', '=', rec.student_id.id), ('state', 'in', ('submit', 'approve', 'done'))])
			if len(exist_recs) >= 2:
				raise UserError('Two records already exist')

			if rec.bypass:
				rec.defer_term()
			else:
				# activity = self.env.ref('odoocms_registration.mail_act_term_defer')
				# self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
				rec.state = 'submit'

	def action_approve(self):
		for rec in self:
			rec.date_approve = date.today()
			rec.state = 'approve'

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'

	def defer_term(self):
		b = 5


class OdooCMSStudentFeeRefund(models.Model):
	_name = 'odoocms.student.fee.refund'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Fee Refund Requests"

	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}

	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES)
	career_id = fields.Many2one('odoocms.career', string='Career/Degree Level', related='student_id.career_id', store=True)
	program_id = fields.Many2one('odoocms.program', string='Academic Program', related='student_id.program_id', store=True)
	batch_id = fields.Many2one('odoocms.batch', string='Batch', related='student_id.batch_id', store=True)
	batch_section_id = fields.Many2one('odoocms.batch.section', string='Batch Section', related='student_id.batch_section_id', store=True)
	attachment = fields.Binary('Attachment')

	current_term_id = fields.Many2one('odoocms.academic.term', string='Current Term', compute='_get_current_term', store=True)
	semester_id = fields.Many2one('odoocms.semester', string='Current Semester', compute='_get_current_term', store=True)
	term_seq = fields.Integer(related='current_term_id.number', store=True)

	term_id = fields.Many2one('odoocms.academic.term', string='Term to Defer', states=READONLY_STATES)
	reason = fields.Text(string='Reason', states=READONLY_STATES)
	bypass = fields.Boolean('ByPass Approval Process', states=READONLY_STATES)

	state = fields.Selection([
		('draft', 'Draft'), ('submit', 'Submitted'), ('approve', 'Approved'), ('reject', 'Rejected'), ('done', 'Done'), ('cancel', 'Canceled')],
		default='draft', string="Status", tracking=True)
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_approve = fields.Date(string='Approve Date', readonly=True)

	@api.depends('student_id')
	def _get_current_term(self):
		current_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', self.student_id.id)], order='number desc', limit=1)
		self.current_term_id = current_term.term_id.id
		self.semester_id = current_term.semester_id and current_term.semester_id.id or False

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.fee.refund') or _('New')
		result = super().create(vals)
		return result

	def action_invoice(self):
		return {'type': 'ir.actions.act_window_close'}

	def action_submit_portal(self):
		for rec in self:
			# activity = self.env.ref('odoocms_registration.mail_act_term_defer')
			# self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
			rec.state = 'submit'

	def action_submit(self):
		for rec in self:
			exist_recs = self.env['odoocms.tuition.fee.defer'].search([('student_id', '=', rec.student_id.id), ('state', 'in', ('submit', 'approve', 'done'))])
			if len(exist_recs) >= 2:
				raise UserError('Two records already exist')

			if rec.bypass:
				rec.defer_term()
			else:
				# activity = self.env.ref('odoocms_registration.mail_act_term_defer')
				# self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
				rec.state = 'submit'

	def action_approve(self):
		for rec in self:
			rec.date_approve = date.today()
			rec.state = 'approve'

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'

	def defer_term(self):
		b = 5


class OdooCMSFeeInstallment(models.Model):
	_name = 'odoocms.student.fee.installment'
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Fee Installment Requests"

	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}

	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES)
	career_id = fields.Many2one('odoocms.career', string='Career/Degree Level', related='student_id.career_id', store=True)
	program_id = fields.Many2one('odoocms.program', string='Academic Program', related='student_id.program_id', store=True)
	batch_id = fields.Many2one('odoocms.batch', string='Batch', related='student_id.batch_id', store=True)
	batch_section_id = fields.Many2one('odoocms.batch.section', string='Batch Section', related='student_id.batch_section_id', store=True)

	current_term_id = fields.Many2one('odoocms.academic.term', string='Current Term', compute='_get_current_term', store=True)
	semester_id = fields.Many2one('odoocms.semester', string='Current Semester', compute='_get_current_term', store=True)
	term_seq = fields.Integer(related='current_term_id.number', store=True)

	term_id = fields.Many2one('odoocms.academic.term', string='Term to Defer', states=READONLY_STATES)
	reason = fields.Text(string='Reason', states=READONLY_STATES)
	bypass = fields.Boolean('ByPass Approval Process', states=READONLY_STATES)

	state = fields.Selection([
		('draft', 'Draft'), ('submit', 'Submitted'), ('approve', 'Approved'), ('reject', 'Rejected'), ('done', 'Done'), ('cancel', 'Canceled')],
		default='draft', string="Status", tracking=True)
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_approve = fields.Date(string='Approve Date', readonly=True)

	@api.depends('student_id')
	def _get_current_term(self):
		current_term = self.env['odoocms.student.term'].sudo().search([('student_id', '=', self.student_id.id)], order='number desc', limit=1)
		self.current_term_id = current_term.term_id.id
		self.semester_id = current_term.semester_id and current_term.semester_id.id or False

	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.fee.installment') or _('New')
		result = super().create(vals)
		return result

	def action_invoice(self):
		return {'type': 'ir.actions.act_window_close'}

	def action_submit_portal(self):
		for rec in self:
			# activity = self.env.ref('odoocms_registration.mail_act_term_defer')
			# self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
			rec.state = 'submit'

	def action_submit(self):
		for rec in self:
			exist_recs = self.env['odoocms.tuition.fee.defer'].search([('student_id', '=', rec.student_id.id), ('state', 'in', ('submit', 'approve', 'done'))])
			if len(exist_recs) >= 2:
				raise UserError('Two records already exist')

			if rec.bypass:
				rec.defer_term()
			else:
				# activity = self.env.ref('odoocms_registration.mail_act_term_defer')
				# self.activity_schedule('odoocms_registration.mail_act_term_defer', user_id=activity._get_role_users(self.program_id))
				rec.state = 'submit'

	def action_approve(self):
		for rec in self:
			rec.date_approve = date.today()
			rec.state = 'approve'

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'

	def defer_term(self):
		b = 5


class OdooCMSWithDrawReason(models.Model):
	_name = "odoocms.drop.reason"
	_description = "Course Drop Reason"
	_inherit = ['mail.thread', 'mail.activity.mixin']

	name = fields.Char(string='name')
	description = fields.Text(string='Description Text', required = True)
	attendance = fields.Boolean('Attendance', default=False)
	finance = fields.Boolean('Finance', default=False)
		

class OdooCMSStudentCourse(models.Model):
	_inherit = 'odoocms.student.course'
		
	delete_id = fields.Many2one('odoocms.student.course.delete', 'Delete ID')
		
	def remove_attendance(self, component,date_effective):
		pass
		
		
class OdooCMSCourseDrop(models.Model):
	_name = "odoocms.student.course.drop"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Student Course Drop"
	_order = 'name desc'

	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}

	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student",tracking=True,states=READONLY_STATES)
	program_id = fields.Many2one(related='student_id.program_id',string='Academic Program',states=READONLY_STATES)
	batch_id = fields.Many2one(related='student_id.batch_id',string='Class Batch',states=READONLY_STATES)
	batch_section_id = fields.Many2one(related='student_id.batch_section_id',string='Batch Section',states=READONLY_STATES)
	term_id = fields.Many2one(related='batch_id.term_id',string='Academic Term',states=READONLY_STATES)
	semester_id  = fields.Many2one(related='student_id.semester_id',string='Current Semester',states=READONLY_STATES)
		
	registration_id  = fields.Many2one('odoocms.student.course',string='Withdraw/Drop Course',tracking=True,states=READONLY_STATES)
	description = fields.Text(string='Description',states=READONLY_STATES)
	reason_id  = fields.Many2one('odoocms.drop.reason',string='Reason',states=READONLY_STATES)
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_effective = fields.Date('Effective Date', default=date.today())
	date_approve = fields.Date(string='Approve Date', readonly=True)
	state = fields.Selection([
		('draft','Draft'),
		('submit','Submit'),
		('approve','Approved'),
		('cancel','Cancel')],default='draft',string="Status",tracking=True)
		
	override_min_limit = fields.Boolean('Override Minimum Limit?', default=False, states=READONLY_STATES, tracking=True)
	limit_error = fields.Boolean('Over Limit', default=False)
	limit_error_text = fields.Text(default='')
		
	@api.model
	def create(self, vals):
		if vals.get('name', _('New')) == _('New'):
			vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.course.drop') or _('New')
			result = super().create(vals)
		return result
		
	def action_submit(self):
		for rec in self:
			rec._min_register_limit()
			if self.limit_error:
				return
			rec.state = 'submit'
		
	def action_approve(self):
		for rec in self:
			self._min_register_limit()
			if rec.limit_error:
				return
			if rec.state == 'submit':
				if rec.term_id and rec.batch_id and rec.batch_id.can_apply('drop_f', rec.term_id, rec.date_effective, admin=True):
					rec.registration_id.write({
						'grade': 'F',
						'dropped': True,
						'state': 'done',
					})
				elif rec.term_id and rec.batch_id and rec.batch_id.can_apply('drop_w', rec.term_id, rec.date_effective, admin=True):
					rec.registration_id.write({
						'grade': 'W',
						'dropped': True,
						'state': 'done',
						'include_in_cgpa': False,
					})
				elif rec.term_id and rec.batch_id and rec.batch_id.can_apply('enrollment', rec.term_id, rec.date_effective, admin=True):
					rec.registration_id.write({
						'active': False,
						'dropped': True,
						'state': 'dropped',
						'dropped_date': datetime.now(),
					})
				else:
					raise UserError('Date Over for Course Drop!')
				
				for component in rec.registration_id.component_ids:
					rec.registration_id.remove_attendance(component, rec.date_effective)
					component.active = False
				
				rec.state ='approve'
			else:
				raise UserError('Request is not confirmed yet. Please Submit the request first!')

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'
		
	def _min_register_limit(self):
		registered_courses = self.env['odoocms.student.course'].search([
			('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id), ('grade', 'not in', ('W', 'F'))])
		
		min_credits = 0
		sum_credit = 0
		
		for course in registered_courses:
			sum_credit += course.primary_class_id.credits
			
		sum_credit -= self.registration_id.primary_class_id.credits
		
		# Allowed
		global_load = self.env['odoocms.student.registration.load'].search([
			('type', '=', self.term_id.type), ('default_global', '=', True)])
		if global_load:
			min_credits = global_load[0].min
		
		career_load = self.student_id.career_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if career_load:
			min_credits = career_load[0].min if career_load[0].min > 0 else min_credits
		
		batch_load = self.student_id.batch_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if batch_load:
			min_credits = batch_load[0].min if batch_load[0].min > 0 else min_credits
		
		program_load = self.student_id.program_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if program_load:
			min_credits = program_load[0].min if program_load[0].min > 0 else min_credits
		
		# tag_load = self.student_id.tag_ids.mapped('registration_load_ids').filtered(lambda l: l.type == self.term_id.type)
		# if tag_load:
		# 	min_credits = tag_load[0].min if tag_load[0].min > 0 else min_credits
		
		# domain_loads = self.env['odoocms.student.registration.load'].search([
		# 	('type', '=', self.term_id.type)]).filtered(lambda l: l.domain)
		# for domain_load in domain_loads:
		# 	domain = expression.AND([safe_eval(domain_load.domain), [('id', '=', self.student_id.id)]]) if domain_load.domain else []
		# 	domain_student = self.env['odoocms.student'].search(domain)
		# 	if domain_student:
		# 		min_credits = domain_load.min if domain_load.min > 0 else min_credits
		# 		break
				
		student_load = self.student_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if student_load:
			min_credits = student_load[0].min if student_load[0].min > 0 else min_credits
		
		if sum_credit < min_credits and not self.override_min_limit:
			self.limit_error = True
			self.limit_error_text = 'Registration of (%s) Credit Hours is not possible. Minimum Allowed limit: (%s) CH' % (sum_credit, min_credits)
		
		else:
			self.limit_error = False
			self.limit_error_text = ''
			

class OdooCMSCourseAddDrop(models.Model):
	_name = "odoocms.student.course.add.drop"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Student Course Add Drop"
	_order = 'name desc'
		
	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'done': [('readonly', True)],
		'cancel': [('readonly', True)],
	}
		
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	student_id = fields.Many2one('odoocms.student', string="Student", tracking=True, states=READONLY_STATES)
	program_id = fields.Many2one(related='student_id.program_id', string='Academic Program', states=READONLY_STATES)
	batch_id = fields.Many2one(related='student_id.batch_id', string='Class Batch', states=READONLY_STATES)
		
	term_id = fields.Many2one('odoocms.academic.term', string='Academic Term', states=READONLY_STATES)
		
	description = fields.Text(string='Description', states=READONLY_STATES)
	reason_id = fields.Many2one('odoocms.drop.reason', string='Reason', states=READONLY_STATES)
		
	drop_ids = fields.Many2many('odoocms.class.primary', 'rel_drop_course', 'request_id', 'course_id', string='Drop Courses', tracking=True, states=READONLY_STATES)
	add_ids = fields.Many2many('odoocms.class.primary', 'rel_add_course', 'request_id', 'course_id', string='Add Courses', tracking=True, states=READONLY_STATES)
	course_domain = fields.Many2many('odoocms.class.primary', 'rel_course_domain', 'request_id', 'course_id', compute='_get_courses_domain')
	drop_domain = fields.Many2many('odoocms.class.primary', 'rel_drop_domain', 'request_id', 'course_id', compute='_get_courses_domain')
	can_add = fields.Boolean(compute='_can_add', store=True)
		
	date_request = fields.Date('Request Date', default=date.today(), readonly=True)
	date_effective = fields.Date('Effective Date', default=date.today(), states=READONLY_STATES)
	date_approve = fields.Date(string='Approve Date', readonly=True)
	state = fields.Selection([
		('draft', 'Draft'),
		('submit', 'Submit'),
		('approve', 'Approved'),
		('cancel', 'Cancel')], default='draft', string="Status", tracking=True)
		
	override_limit = fields.Boolean('Override Limits?', default=False, states=READONLY_STATES, tracking=True)
	override_prereq = fields.Boolean('Override Pre-Requisite?', default=False, states=READONLY_STATES, tracking=True)
	limit_error = fields.Boolean('Over Limit', default=False)
	limit_error_text = fields.Text(default='')
		
	# Change tt_check to True
	@api.depends('student_id', 'term_id')
	def _get_courses_domain(self):
		self.course_domain = False
		self.drop_domain = False
		if self.student_id and self.term_id:
			classes = self.student_id.get_possible_classes(self.term_id, tt_check=self.student_id.batch_id.tt_check or False)  # [0]
			registered_classes = self.env['odoocms.student.course'].search([('student_id','=',self.student_id.id),('term_id','=',self.term_id.id)]).mapped('primary_class_id')
			possible_classes = classes['comp_class_ids'] + classes['elec_class_ids'] + \
				classes['repeat_class_ids'] + classes['improve_class_ids'] + \
				classes['additional_class_ids'] + classes['alternate_class_ids'] + \
				classes['minor_class_ids']
			
			#possible_classes -= registered_classes
			
			if possible_classes:
				course_domain = [(6, 0, possible_classes.ids)]
				self.course_domain = course_domain
			else:
				self.course_domain = False
			self.drop_domain = [(6, 0, registered_classes.ids)]
		
	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.course.add.drop') or _('New')
		result = super().create(vals)
		return result
		
	def action_submit(self):
		for rec in self:
			if rec.drop_ids and len(rec.drop_ids) != len(rec.drop_ids.mapped('course_id')):
				raise UserError('Same Course Added Twice')
			
			data = {
				'student_id': rec.student_id.id,
				'term_id': rec.term_id.id,
				'enrollment_type': 'enrollment',
				'source': 'portal',
				'new_courses': True,
				'override_max_limit': rec.override_limit,
				'override_prereq': rec.override_prereq,
				# 'add_drop_request_id': rec.id,
				'add_drop_request': True,
			}
			self.env['odoocms.course.registration'].create(data)
			
			# registered_courses = self.env['odoocms.student.course'].search([
			# 	('student_id', '=', self.student_id.id),
			# 	('term_id', '=', self.term_id.id),
			# 	('grade', 'not in', ('W', 'F')),
			# 	('primary_class_id', 'not in', self.drop_ids.ids)
			# ])
			#
			#
			# rec._min_register_limit()
			# if self.limit_error:
			# 	return
			rec.state = 'submit'
		
	@api.depends('term_id','batch_id','date_effective')
	def _can_add(self):
		for rec in self:
			if rec.term_id and rec.batch_id and rec.batch_id.can_apply('enrollment', rec.term_id, rec.date_effective, admin=True):
				rec.can_add = True
			else:
				rec.can_add = False
			
	def action_approve(self):
		for rec in self:
			# self._min_register_limit()
			# if rec.limit_error:
			# 	return
			if rec.state == 'submit':
				if rec.term_id and rec.batch_id and rec.batch_id.can_apply('enrollment', rec.term_id, rec.date_effective, admin=True):
					st_term = rec.student_id.get_student_term(rec.term_id)

					for primary_class in rec.drop_ids:
						course = self.env['odoocms.student.course'].search([
							('student_id', '=', self.student_id.id),
							('term_id', '=', self.term_id.id),
							('primary_class_id','=', primary_class.id)
						])
						course.write({
							'active': False,
							'dropped': True,
							'state': 'dropped',
							'dropped_date': datetime.now(),
						})
					for course in rec.add_ids:
						rec.student_id.register_courses(course, rec.term_id, st_term, rec.date_effective, 'compulsory')
						
				elif rec.term_id and rec.batch_id and rec.batch_id.can_apply('drop_f', rec.term_id, rec.date_effective, admin=True):
					rec.drop_ids.write({
						'grade': 'F',
						'dropped': True,
						'state': 'done',
					})
				elif rec.term_id and rec.batch_id and rec.batch_id.can_apply('drop_w', rec.term_id, rec.date_effective, admin=True):
					rec.drop_ids.write({
						'grade': 'W',
						'dropped': True,
						'state': 'done',
						'include_in_cgpa': False,
					})
				else:
					raise UserError('Date Over for Course Drop!')
				
				# for component in rec.registration_id.component_ids:
				# 	rec.registration_id.remove_attendance(component, rec.date_effective)
				# 	component.active = False
				
				rec.state = 'approve'
			else:
				raise UserError('Request is not confirmed yet. Please Submit the request first!')
		
	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'
		
	def _min_register_limit(self):
		registered_courses = self.env['odoocms.student.course'].search([
			('student_id', '=', self.student_id.id), ('term_id', '=', self.term_id.id), ('grade', 'not in', ('W', 'F'))])
		
		min_credits = 0
		sum_credit = 0
		
		for course in registered_courses:
			sum_credit += course.primary_class_id.credits
		
		sum_credit -= self.registration_id.primary_class_id.credits
		
		# Allowed
		global_load = self.env['odoocms.student.registration.load'].search([
			('type', '=', self.term_id.type), ('default_global', '=', True)])
		if global_load:
			min_credits = global_load[0].min
		
		career_load = self.student_id.career_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if career_load:
			min_credits = career_load[0].min if career_load[0].min > 0 else min_credits
		
		batch_load = self.student_id.batch_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if batch_load:
			min_credits = batch_load[0].min if batch_load[0].min > 0 else min_credits
		
		program_load = self.student_id.program_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if program_load:
			min_credits = program_load[0].min if program_load[0].min > 0 else min_credits
		
		# tag_load = self.student_id.tag_ids.mapped('registration_load_ids').filtered(lambda l: l.type == self.term_id.type)
		# if tag_load:
		# 	min_credits = tag_load[0].min if tag_load[0].min > 0 else min_credits
		
		domain_loads = self.env['odoocms.student.registration.load'].search([
			('type', '=', self.term_id.type)]).filtered(lambda l: l.domain)
		for domain_load in domain_loads:
			domain = expression.AND([safe_eval(domain_load.domain), [('id', '=', self.student_id.id)]]) if domain_load.domain else []
			domain_student = self.env['odoocms.student'].search(domain)
			if domain_student:
				min_credits = domain_load.min if domain_load.min > 0 else min_credits
				break
		
		student_load = self.student_id.registration_load_ids.filtered(lambda l: l.type == self.term_id.type)
		if student_load:
			min_credits = student_load[0].min if student_load[0].min > 0 else min_credits
		
		if sum_credit < min_credits and not self.override_min_limit:
			self.limit_error = True
			self.limit_error_text = 'Registration of (%s) Credit Hours is not possible. Minimum Allowed limit: (%s) CH' % (sum_credit, min_credits)
		
		else:
			self.limit_error = False
			self.limit_error_text = ''
			
			
class OdooCMSCourseDelete(models.Model):
	_name = "odoocms.student.course.delete"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_description = "Delete Students Course"
	_order = 'name desc'

	READONLY_STATES = {
		'submit': [('readonly', True)],
		'approve': [('readonly', True)],
		'cancel': [('readonly', True)],
	}
		
	name = fields.Char(string='Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
	date_request = fields.Date(string='Request Date', default= date.today(), readonly=True)
	date_effective = fields.Date(string='Effective Date', default= date.today())
	date_approve = fields.Date(string='Approve Date', readonly=True)
	description = fields.Text(string='Detailed Reason', required = True, states=READONLY_STATES)
		
	registration_ids = fields.Many2many('odoocms.student.course', 'student_course_delete_rel','request_id','course_id', states=READONLY_STATES)
	deleted_ids = fields.One2many('odoocms.student.course', 'delete_id', string='Deleted Courses', states=READONLY_STATES,
		domain=['|', ('active', '=', True), ('active', '=', False)], context={'active_test': False})
		
	state = fields.Selection([(
		'draft','Draft'),
		('submit','Submit'),
		('approve','Approved'),
		('cancel','Cancel'),],default='draft',string="Status",tracking=True)
		
	@api.model
	def create(self, vals):
		vals['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.course.delete') or _('New')
		result = super().create(vals)
		return result
		
	def action_submit(self):
		self.state = 'submit'
		
	def action_approve(self):
		self.state = 'approve'
		self.date_approve = date.today()
		
		message = "***"
		for reg in self.registration_ids:
			message += reg.primary_class_id.name or " " + "<br/>"
			for component in reg.component_ids:
				reg.sudo().remove_attendance(component, self.date_effective)
				component.active = False
			reg.active = False
			reg.delete_id = self.id

		message += ' Registration has been Deleted.***'
		self.state = 'approve'
		self.message_post(body=message)

	def action_cancel(self):
		for rec in self:
			rec.state = 'cancel'

		
class OdooCMSRequestStudentProfile(models.Model):
	_name = "odoocms.request.student.profile"
	_description = "Student Profile Change Request"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}

	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES)
	change_in = fields.Char(string='Change In', states=READONLY_STATES)
	old_info = fields.Char(string='Old Information', states=READONLY_STATES)
	new_info = fields.Char(string='New Information', states=READONLY_STATES)
	image_newspaper = fields.Binary(string='NewsPaper Image', attachment=True, states=READONLY_STATES)
	image_cnic = fields.Binary(string='CNIC Image', attachment=True, states=READONLY_STATES)
	state = fields.Selection([('draft','Draft'),('reject','Rejected'),('done','Done')], default ='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.student_id[self.change_in] = self.new_info
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestStudentSpecialization(models.Model):
	_name = "odoocms.request.student.specialization"
	_description = "Student Specialization Request"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'submit': [('readonly', True)],
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}

	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES, required=True)
	specialization_id = fields.Many2one('odoocms.specialization','Specialization', required=True)
	note = fields.Text('Note')
	state = fields.Selection([
		('draft','Draft'), ('submit','Submit'), ('reject','Rejected'), ('done','Done')
	], default ='draft', string='State')

	def action_submit(self):
		if self.state == 'draft':
			self.state = 'submit'
			
	def action_approve(self):
		if self.state == 'submit':
			self.student_id.specialization_id = self.specialization_id.id
			self.state = 'done'

	def action_reject(self):
		if self.state == 'submit':
			self.state = 'reject'
			
	def action_reset(self):
		if self.state in ('reject','submit'):
			self.state = 'draft'


class OdooCMSRequestStudentCertificate(models.Model):
	_name = "odoocms.request.student.certificate"
	_description = "Student Certificate Request"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}

	student_id = fields.Many2one(
		'odoocms.student', string="Student", states=READONLY_STATES)
	type_certificate = fields.Selection([
		('bona_fide', 'value'),
		('english_proficiency', 'English Proficiency'),
		('no_objection', 'NO Objection Certificate'),
		('character', 'Character'),
		('all', "All")
	], string='Type', states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	reason = fields.Text('Reason', states= READONLY_STATES)
	attachment = fields.Binary('Proof Of Attachment', states= READONLY_STATES)
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'),
	                         ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestStudentCorrection(models.Model):
	_name = "odoocms.request.name.correction"
	_description = "Student Name Correction"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}

	student_id = fields.Many2one('odoocms.student', string="Student",
                              states=READONLY_STATES)
	name = fields.Char('Name',required=True, states= READONLY_STATES)
	first_name = fields.Char('First Name',required=True, states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	last_name = fields.Char('Last Name',required=True, states= READONLY_STATES)
	father_name = fields.Char('Father Name',required=True, states= READONLY_STATES)
	attachment = fields.Binary('Upload Proof',required=True, states= READONLY_STATES)
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.student_id.name = self.name
			self.student_id.first_name = self.first_name
			self.student_id.last_name = self.last_name
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestWaiverFine(models.Model):
	_name = "odoocms.request.waiver.fine"
	_description = "Request Waiver Fine"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}

	student_id = fields.Many2one('odoocms.student', string="Student",
                              states=READONLY_STATES)
	amount = fields.Float('Amount Of Fine', states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	reason = fields.Text('Reason Why Fine Was Imposed', states= READONLY_STATES)
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestRegRestoration(models.Model):
	_name = "odoocms.request.registration.restoration"
	_description = "Request Restoration Registration"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES )
	date = fields.Date('date',default=fields.Date.today())
	reason = fields.Text('reason', states= READONLY_STATES)
	attachment = fields.Binary('Upload Proof Document', states= READONLY_STATES)
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestMedicalLeave(models.Model):
	_name = "odoocms.request.medical.leave"
	_description = "Request Restoration Registration"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES )
	days = fields.Integer('No of Days', states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	attachment = fields.Binary('Upload Certificate', states= READONLY_STATES)
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestCard(models.Model):
	_name = "odoocms.request.card"
	_description = "Request Card/Pass"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES )
	card_type = fields.Selection([
		('student_card', 'Student Card'),
		('library_card', 'Library Card'),
		('buss_pass', 'Buss Pass'),
	], string='Card Type', states= READONLY_STATES)
	attachment = fields.Binary('Proof Of Payment', states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestPlagiarismPerfoma(models.Model):
	_name = "odoocms.request.plagiarism.perfoma"
	_description = "Request Plagiarism Perfoma"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}
	student_id = fields.Many2one('odoocms.student', string="Student", states=READONLY_STATES )
	attachment = fields.Binary('Document To Check', states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


class OdooCMSRequestProgramChange(models.Model):
	_name = "odoocms.request.program.change"
	_description = "Request Program Change"
	_inherit = ['mail.thread', 'mail.activity.mixin']
	_rec_name = 'student_id'

	READONLY_STATES = {
		'done': [('readonly', True)],
		'reject': [('readonly', True)],
	}
	student_id = fields.Many2one('odoocms.student', string="Student", states= READONLY_STATES)
	program_id = fields.Many2one('odoocms.program', string='Program', states= READONLY_STATES)
	date = fields.Date('date',default=fields.Date.today())
	state = fields.Selection([('draft', 'Draft'), ('reject', 'Rejected'), ('done', 'Done')], default='draft', string='State')

	def action_approve(self):
		if self.state == 'draft':
			self.state = 'done'

	def action_reject(self):
		if self.state == 'draft':
			self.state = 'reject'


