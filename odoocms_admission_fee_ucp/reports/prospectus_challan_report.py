# -*- coding: utf-8 -*-
import pdb

from odoo import api, fields, models, _


class ProspectusChallanReport(models.AbstractModel):
    _name = 'report.odoocms_admission_fee_ucp.prospectus_challan_report'
    _description = 'Prospectus Challan Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        form_data = data.get('form', {})
        date_from = form_data.get('date_from')
        date_to = form_data.get('date_to')
        source = form_data.get('source')
        program_id = form_data.get('program_id', False)

        term_id = self.env['odoocms.admission.register'].search([('state','=','application')], order='create_date desc', limit=1).term_id

        domain = [('voucher_verified_date', '>=', date_from),
                  ('voucher_verified_date', '<=', date_to),
                  ('prospectus_inv_id', '!=', False)]

        if source and not source == 'all':
            domain.append(('fee_voucher_verify_source', '=', source))
        if program_id:
            domain.append(('prefered_program_id', '=', program_id[0]))

        lines = self.env['odoocms.application'].sudo().search(domain, order='voucher_verified_date')
        report = self.env['ir.actions.report']._get_report_from_name('odoocms_admission_fee_ucp.prospects_challan_report')
        docargs = {
            'doc_ids': [],
            'doc_model': report.model,
            'data': data,
            'company': self.env.company or False,
            'company_name': self.env.company.name,
            'lines': lines,
            'term_id': term_id,
            'faculty_summary_lines': self.get_faculty_summary(lines),
            'deo_summary_lines': self.get_deo_summary(lines),
        }
        return docargs

    def get_faculty_summary(self, lines):
        summary_lines = []
        if lines:
            self.env.cr.execute("""select count(*) as cnt,sum(amount) as amount,faculty_code as faculty from odoocms_application where id in %s group by faculty_code;""" % (tuple(lines.ids),))
            query_result = self.env.cr.dictfetchall()
            if query_result:
                for result in query_result:
                    summary_line = {
                        'faculty': result['faculty'],
                        'cnt': result['cnt'],
                        'amount': result['amount'],
                    }
                    summary_lines.append(summary_line)
        return summary_lines

    def get_deo_summary(self, lines):
        deo_lines = []
        if lines:
            self.env.cr.execute("""select count(*) as cnt,sum(amount) as amount,fee_voucher_verify_by as deo from odoocms_application where id in %s group by fee_voucher_verify_by;""" % (tuple(lines.ids),))
            query_result = self.env.cr.dictfetchall()
            if query_result:
                for result in query_result:
                    deo_name = ''
                    if not result['deo']:
                        deo_name = 'Auto Bank'
                    else:
                        user_rec = self.env['res.users'].browse(result['deo'])
                        if user_rec:
                            deo_name = user_rec.login.split('@')[0]
                    deo_line = {
                        'deo': deo_name,
                        'cnt': result['cnt'],
                        'amount': result['amount'],
                    }
                    deo_lines.append(deo_line)
        return deo_lines
