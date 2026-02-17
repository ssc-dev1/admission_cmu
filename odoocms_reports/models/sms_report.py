from odoo import models, fields, api
from odoo.tools.misc import xlsxwriter
import base64
import io
from datetime import datetime, date
import asyncio

class sms_track(models.Model):
    _inherit = "sms_track"

    # @api.model
    # def get_sms_report_rpc(self, from_date, to_date, report_type, group_by):
    #     loop = asyncio.get_event_loop()
    #     result = loop.run_until_complete(self.get_sms_report(from_date, to_date, report_type, group_by))
    #     return result
    @api.model
    def get_sms_report(self, from_date, to_date, report_type, group_by):
        company_id =self.env.company.id
        query = self._build_query(report_type, group_by)
        self.env.cr.execute(query, (from_date, to_date,))
        data =  self.env.cr.dictfetchall()
        columns = self._get_columns(data)
        keys = self._get_keys(data)
        sms_list = self.env['sms_track'].sudo().search([('date', '>=', from_date), ('date', '<=', to_date)]).mapped('message_id')
        sms_count_as_per_alphabets = self._get_sms_count_as_per_alphabets(sms_list)
        return data, columns, keys, sms_count_as_per_alphabets

    def _build_query(self, report_type, group_by):
        if report_type == 'summary':
            query = """
                WITH record_counts AS (
                    SELECT mobile_no, COUNT(*) AS sms_frequency
                    FROM sms_track
                    WHERE date(date) >= %s AND date(date) <= %s 
                    GROUP BY mobile_no
                )
                SELECT sms_frequency, COUNT(*) AS number_of_mobile_no
                FROM record_counts
                GROUP BY sms_frequency
                ORDER BY sms_frequency;
            """
        else:
            if group_by == 'none':
                query = """
                    SELECT id, date, mobile_no, status, model_id, send_to, status, sms_nature, type
                    FROM sms_track
                    WHERE date(date) >= %s AND date(date) <= %s
                    ORDER BY date DESC 
                """
            elif group_by == 'number':
                query = """
                    SELECT MAX(sms_track.id) AS id, subquery.count, MAX(sms_track.date) AS date, sms_track.mobile_no, 
                        MAX(sms_track.status) AS status, MAX(sms_track.model_id) AS model_id, MAX(sms_track.send_to) AS send_to,
                        MAX(sms_track.status) AS status, MAX(sms_track.sms_nature) AS sms_nature, MAX(sms_track.type) AS type
                    FROM sms_track
                    INNER JOIN (
                        SELECT mobile_no, COUNT(*) AS count 
                        FROM sms_track 
                        WHERE date(date) >= %s AND date(date) <= %s 
                        GROUP BY mobile_no
                    ) AS subquery ON sms_track.mobile_no = subquery.mobile_no
                    GROUP BY subquery.count, sms_track.mobile_no
                    ORDER BY subquery.count DESC;
                """
            elif group_by == 'date':
                query = """
                    SELECT date(date), count(*) as no_of_sms_sent
                    FROM sms_track
                    WHERE date(date) >= %s AND date(date) <= %s
                    GROUP BY date(date)
                    ORDER BY date(date) DESC 
                """
        return query

    def _get_columns(self, data):
        def format_key(key):
            return ' '.join(word.capitalize() for word in key.split('_'))
        if not data:
            return []
        keys = data[0].keys()
        columns = [format_key(key) for key in keys]
        return columns

    def _get_keys(self, data):
        if data and data[0]:
            keys = data[0].keys()
            keys = list(keys)
            return keys
        return []


    def _get_sms_count_as_per_alphabets(self, messages):
        message_count = 0
        message_length_limit = 160
        for message in messages:
            message_length = len(message)
            full_messages, remainder = divmod(message_length, message_length_limit)
            message_count += full_messages
            if remainder > 0:
                message_count += 1
        return message_count

    
    @api.model
    def generate_excel_report(self, from_date, to_date, report_type, group_by):
            data, columns, keys, sms_count_as_per_alphabets = self.get_sms_report(from_date, to_date, report_type, group_by)
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('SMS Report')
            date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
            for col_num, column_title in enumerate(columns):
                sheet.write(0, col_num, column_title)
                sheet.set_column(col_num, col_num, 15)
            for row_num, row_data in enumerate(data, start=1):
                for col_num, key in enumerate(keys):
                    cell_value = row_data[key]
                    if isinstance(cell_value, str):
                        try:
                            cell_value = datetime.strptime(cell_value, '%Y-%m-%d').date()
                        except ValueError:
                            pass
                    if isinstance(cell_value, date):
                        sheet.write_datetime(row_num, col_num, cell_value, date_format)
                    else:
                        sheet.write(row_num, col_num, cell_value)

            last_row = len(data) + 1
            sheet.write(last_row, 0, 'Total SMS Count As Per Alphabets:')
            sheet.write(last_row, 1, sms_count_as_per_alphabets)
            workbook.close()
            output.seek(0)
            file_content = output.read()
            output.close()
            file_base64 = base64.b64encode(file_content)
            filename = f'SMS_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            return filename, file_base64
