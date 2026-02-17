
import pdb
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc
import time
import logging

_logger = logging.getLogger(__name__)

from io import StringIO
import io

try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')

try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')

try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class ExportResultWizard(models.TransientModel):
	_name = "export.result.wizard"

	paper_id = fields.Many2one('cbt.paper.generator', 'Generated Paper', required=True)

	def make_excel(self):
		workbook = xlwt.Workbook(encoding="utf-8")
		worksheet = workbook.add_sheet("Participants Result")
		style_title = xlwt.easyxf(
			"font:height 350; font: name Liberation Sans, bold on,color black; align: horiz center, vert center; borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
		style_table_header = xlwt.easyxf(
			"font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center, vert center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour silver_ega;")
		style_table_header2 = xlwt.easyxf(
			"font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour sea_green;alignment: wrap True;")
		style_table_header3 = xlwt.easyxf(
			"font:height 200; font: name Liberation Sans, bold on,color black; align: horiz center;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour ivory;alignment: wrap True;")

		style_table_totals = xlwt.easyxf(
			"font:height 150; font: name Liberation Sans, bold on,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour cyan_ega;")
		style_date_col = xlwt.easyxf(
			"font:height 180; font: name Liberation Sans,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour white;")
		style_date_col2 = xlwt.easyxf(
			"font:height 180; font: name Liberation Sans,color black; align: horiz left;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour white;")
		style_table_totals2 = xlwt.easyxf(
			"font:height 200; font: name Liberation Sans, bold on,color black; align: horiz right;borders: left thin, right thin, top thin, bottom thin;pattern: pattern solid, fore_colour ivory;")

		worksheet.write(0, 0, 'CNIC', style=style_table_header2)
		worksheet.write(0, 1, 'Subjects', style=style_table_header2)
		worksheet.write(0, 2, 'Score', style=style_table_header2)
		worksheet.write(0, 3, 'Total Score', style=style_table_header2)


		row = 1
		subjects = self.env['cbt.paper.subject.score'].search([
			('conduct.paper_id.main_paper_id.generator_id', '=', self.paper_id.id)])
		for subject in subjects:
			worksheet.write(row, 0, subject.conduct.paper_id.participant_id.login)
			worksheet.write(row, 1, subject.subject_id.name)
			worksheet.write(row, 2, subject.score)
			worksheet.write(row, 3, subject.total_score)

			row = int(row) + 1


		file_data = io.BytesIO()
		workbook.save(file_data)
		wiz_id = self.env['cbt.result.save.wizard'].create({
			'data': base64.encodestring(file_data.getvalue()),
			'name': 'cbtResult.xls'
		})

		return {
			'type': 'ir.actions.act_window',
			'name': 'CBT Result Report Form',
			'res_model': 'cbt.result.save.wizard',
			'view_mode': 'form',
			'view_type': 'form',
			'res_id': wiz_id.id,
			'target': 'new'
		}

class Cbt_Result_save_wizard(models.TransientModel):
		_name = "cbt.result.save.wizard"
		_description = 'CBT Result Save Wizard'

		name = fields.Char('filename', readonly=True)
		data = fields.Binary('file', readonly=True)


