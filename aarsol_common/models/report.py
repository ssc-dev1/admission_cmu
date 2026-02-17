from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _
import pdb


class ReportAction(models.Model):
	_inherit = 'ir.actions.report'
	
	report_type = fields.Selection(selection_add=[
		('qweb-xls', 'XLS'),
		('qweb-ppt', 'PPT'),
		('qweb-pptp', 'PPT-PDF'),
		('qweb-doc', 'DOC'),
		('qweb-docp', 'DOC-PDF'),
		("fillpdf", "PDF Fill"),
	], ondelete={
			'qweb-xls': 'set default',
			'qweb-ppt': 'set default',
			'qweb-pptp': 'set default',
			'qweb-doc': 'set default',
			'qweb-docp': 'set default',
			'fillpdf': 'set default',
		 }
	)
	
	# ttype = fields.Selection(selection_add=[
	# 	('serialized', 'serialized'),
	# ], ondelete={'serialized': 'cascade'})
	
	# report_type = fields.Selection([
	# 	('qweb-html', 'HTML'),
	# 	('qweb-pdf', 'PDF'),
	# 	('qweb-text', 'Text'),
	# 	('qweb-xls', 'XLS'),
	# 	('qweb-ppt', 'PPT'),
	# 	('qweb-pptp', 'PPT-PDF'),
	# 	('qweb-doc', 'DOC'),
	# 	('qweb-docp', 'DOC-PDF'),
	# 	("fillpdf", "PDF Fill"),
	# ], required=True, default='qweb-pdf',
	# 	help='The type of the report that will be rendered, each one having its own'
	# 		 ' rendering method. HTML means the report will be opened directly in your'
	# 		 ' browser PDF means the report will be rendered using Wkhtmltopdf and'
	# 		 ' downloaded by the user.')
	
	def render_xlsx(self, docids, data):
		report_model_name = 'report.{}'.format(self.report_name)
		report_model = self.env.get(report_model_name)
		if report_model is None:
			raise UserError(_('%s model was not found' % report_model_name))
		return report_model.with_context({'active_model': self.model}).create_xlsx_report(docids, data)

	def _get_report_from_name(self, report_name):
		res = super(ReportAction, self)._get_report_from_name(report_name)
		if res:
			return res
		report_obj = self.env['ir.actions.report']
		qwebtypes = ['qweb-xls', 'qweb-ppt', 'qweb-pptp', 'qweb-doc', 'qweb-docp', 'fillpdf']
		conditions = [('report_type', 'in', qwebtypes), ('report_name', '=', report_name)]
		context = self.env['res.users'].context_get()
		return report_obj.with_context(context).search(conditions, limit=1)
	
	def render_qweb_xls(self, docids, data=None):
		"""This method generates and returns xls version of a report."""
		# If the report is using a custom model to render its html, we must use it. otherwise, fallback on the generic html rendering.
		report_model_name = 'report.{}'.format(self.report_name)
		report_model = self.env.get(report_model_name)
		
		if report_model is not None:
			data = report_model.make_excel(data)
		else:
			docs = self.env[self.model].browse(docids)
			data = {
				'doc_ids': docids,
				'doc_model': self.model,
				'docs': docs,
			}
			return self.render_template(self.report_name, data)
		return data
	
	def render_qweb_ppt(self, docids, data=None):
		"""This method generates and returns ppt version of a report."""
		# If the report is using a custom model to render its html, we must use it. otherwise, fallback on the generic html rendering.
		report_model_name = 'report.{}'.format(self.report_name)
		report_model = self.env.get(report_model_name)
		
		if report_model is not None:
			data = report_model.make_ppt(data)
		else:
			docs = self.env[self.model].browse(docids)
			data = {
				'doc_ids': docids,
				'doc_model': self.model,
				'docs': docs,
			}
			return docs.ppt5()
		return data
	
	def render_qweb_doc(self, docids, data=None):
		
		"""This method generates and returns ppt version of a report."""
		# If the report is using a custom model to render its html, we must use it. otherwise, fallback on the generic html rendering.
		# report_model_name = 'report.%s' % self.report_name
		# report_model = self.env.get(report_model_name)
		
		# if report_model is not None:
		# 	data = report_model.make_ppt(data)
		# else:
		# docs = self.env[self.model].browse(docids)
		# data = {
		# 	'doc_ids': docids,
		# 	'doc_model': self.model,
		# 	'docs': docs,
		# }
		# return docs.gen_transcript()
		# return data
		
		
		report_model_name = 'report.{}'.format(self.report_name)
		report_model = self.env.get(report_model_name)
		if report_model is None:
			raise UserError(_('%s model was not found' % report_model_name))
		return report_model.with_context({'active_model': self.model}).create_doc_report(docids, data)