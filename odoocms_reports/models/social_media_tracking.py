from odoo import models, fields, api
from odoo.tools.misc import xlsxwriter
import base64
import io
from datetime import datetime, date
import asyncio

class SocialMediaTracking(models.Model):
    _inherit = 'social.media.tracking'

    # @api.model
    # def get_sms_report_rpc(self, from_date, to_date, report_type, group_by):
    #     loop = asyncio.get_event_loop()
    #     result = loop.run_until_complete(self.get_sms_report(from_date, to_date, report_type, group_by))
    #     return result
    @api.model
    def get_social_media_tracking_report(self, from_date, to_date, report_type, group_by):
        query = self._build_query(report_type, group_by)
        self.env.cr.execute(query, (from_date, to_date))
        data =  self.env.cr.dictfetchall()
        columns = self._get_columns(data)
        keys = self._get_keys(data)
        return data, columns, keys

    def _build_query(self, report_type, group_by):
        if report_type == 'summary':
            query = """

                    WITH unique_clicks AS (
                        SELECT DISTINCT ON (email, platform, click_time) email, platform, click_time
                        FROM social_media_tracking
                        WHERE date(click_date) >= %s AND date(click_date) <= %s
                    ),
                    record_counts AS (
                        SELECT email, COUNT(*) AS visit_count
                        FROM unique_clicks
                        GROUP BY email
                    )
                    SELECT visit_count, COUNT(*) AS number_of_email
                    FROM record_counts
                    GROUP BY visit_count
                    ORDER BY visit_count;

            """
        else:
            if group_by == 'none':
                query = """

                    SELECT DISTINCT ON (smt.email, smt.platform, smt.click_time) 
                        smt.id, ap.application_no, smt.click_date, smt.email, smt.platform, smt.template
                    FROM social_media_tracking smt
                    JOIN odoocms_application ap ON ap.email = smt.email
                    WHERE date(smt.click_date) >= %s AND date(smt.click_date) <= %s;
                """
            elif group_by == 'email':
                query = """
                WITH unique_clicks AS (
                    SELECT DISTINCT ON (email, platform, click_time) email, platform, click_time
                    FROM social_media_tracking
                    WHERE date(click_date) >= %s AND date(click_date) <= %s
                ),
                click_counts AS (
                    SELECT email, platform, COUNT(*) AS count
                    FROM unique_clicks
                    GROUP BY email, platform
                )
                SELECT sc.email, cc.platform, cc.count
                FROM social_media_tracking AS sc
                INNER JOIN click_counts AS cc ON sc.email = cc.email AND sc.platform = cc.platform
                GROUP BY sc.email, cc.platform, cc.count
                ORDER BY sc.email DESC;
                """
            elif group_by == 'date':
                query = """
                WITH UniqueClicks AS (
                    SELECT DISTINCT ON (email, platform, click_time) email, click_date, platform, click_time
                    FROM social_media_tracking
                    WHERE date(click_date) >= %s AND date(click_date) <= %s
                )
                SELECT click_date, platform, COUNT(email) AS no_of_email_sent
                FROM UniqueClicks
                GROUP BY click_date, platform
                ORDER BY click_date DESC;
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

    
    @api.model
    def generate_excel_report(self, from_date, to_date, report_type, group_by):
            data, columns, keys = self.get_social_media_tracking_report(from_date, to_date, report_type, group_by)
            output = io.BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            sheet = workbook.add_worksheet('Social Media Tracking Report')
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

            workbook.close()
            output.seek(0)
            file_content = output.read()
            output.close()
            file_base64 = base64.b64encode(file_content)
            filename = f'social_media_tracking_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
            return filename, file_base64
