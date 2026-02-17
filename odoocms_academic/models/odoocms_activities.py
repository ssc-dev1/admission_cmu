from odoo import fields, models, api, _
import pdb


class OdooCMSClass(models.Model):
	_inherit = 'odoocms.class'

	submission_ids = fields.One2many('odoocms.class.submission', 'class_id', 'Course Submissions')


class OdooCMSSubmissionAttachment(models.Model):
	_name ='odoocms.class.submission.attachment'
	_description = 'Submission Attachment'
	
	submission_id = fields.Many2one('odoocms.class.submission', string='submission')
	attachment = fields.Binary('Attachment' ,attachment=True)
	file_name = fields.Char('File Name')
	status = fields.Boolean('Status', default=True)


class OdooCMSClassSubmission(models.Model):
	_name = 'odoocms.class.submission'
	_description = 'class Submission'
	
	class_id = fields.Many2one('odoocms.class', string='Class')
	name = fields.Char('name')
	description = fields.Html('Description')
	start_date = fields.Datetime('Start Date')
	end_date = fields.Datetime(string='End Date')
	status = fields.Boolean('Status', default=True)
	lab_ids = fields.Many2many('odoocms.lab', string='Labs for Submission')
	attachment_ids = fields.One2many('odoocms.class.submission.attachment', 'submission_id', string='Attachment')
	student_submission_ids = fields.One2many('odoocms.class.submission.student', 'submission_id', 'Students Submissions')
	company_id = fields.Many2one('res.company', string='Company', related='class_id.company_id', store=True)


class OdooCMSClassSubmissionStudentAttachment(models.Model):
	_name = 'odoocms.class.submission.student.attachment'
	_description = 'class Submission Student'
	
	submission_student_id = fields.Many2one('odoocms.class.submission.student', string='Submission Student')
	attachment = fields.Binary('Attachment')
	file_name = fields.Char('File Name')


class OdooCMSClassSubmissionStudent(models.Model):
	_name = 'odoocms.class.submission.student'
	_description = 'class Submission Student'
	
	submission_id = fields.Many2one('odoocms.class.submission', 'Submission')
	class_id = fields.Many2one('odoocms.class', related='submission_id.class_id', store=True, string='Class/Section')
	student_id = fields.Many2one('odoocms.student', 'Student')
	attachment_ids = fields.One2many('odoocms.class.submission.student.attachment', 'submission_student_id', string='Attachment')
	lab_ip_id = fields.Many2one('odoocms.lab.ip', 'Lab IP')
	lab_id = fields.Many2one('odoocms.lab', related='lab_ip_id.lab_id', store=True, string='Lab')
	ipaddress = fields.Char('IP Address')
	date_submit = fields.Datetime('Submit Time')
	company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')