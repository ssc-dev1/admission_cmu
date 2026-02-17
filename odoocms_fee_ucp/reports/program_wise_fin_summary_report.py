import pdb
from odoo import api, fields, models, _
from odoo.http import request

import logging

_logger = logging.getLogger(__name__)


class ProgramFinSummaryReport(models.AbstractModel):
    _inherit = 'report.odoocms_fee.program_wise_fin_summary_report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        company_id = data.get('form', {}).get('company_id', self.env.company.id)[0]
        institute_ids = data.get('form', {}).get('institute_ids') or self.env['odoocms.institute'].search([]).ids
        program_ids = data.get('form', {}).get('program_ids') or self.env['odoocms.program'].search([]).ids
        term_ids = data.get('form', {}).get('term_ids') or self.env['odoocms.academic.term'].search([]).ids

        main_challan = data.get('form', {}).get('main_challan', False)
        second_challan = data.get('form', {}).get('second_challan', False)
        admission_challan = data.get('form', {}).get('admission_challan', False)
        admission_2nd_challan = data.get('form', {}).get('admission_2nd_challan', False)
        add_drop_challan = data.get('form', {}).get('add_drop_challan', False)
        prospectus_challan = data.get('form', {}).get('prospectus_challan', False)
        hostel_challan = data.get('form', {}).get('hostel_challan', False)
        misc_challan = data.get('form', {}).get('misc_challan', False)

        challan_type = []
        if main_challan:
            challan_type.append(('main_challan'))
        if second_challan:
            challan_type.append(('2nd_challan'))
        if admission_challan:
            challan_type.append(('admission'))
        if admission_2nd_challan:
            challan_type.append(('admission_2nd_challan'))
        if add_drop_challan:
            challan_type.append(('add_drop'))
        if prospectus_challan:
            challan_type.append(('prospectus_challan'))
        if hostel_challan:
            challan_type.append(('hostel_fee'))
        if misc_challan:
            challan_type.append(('misc_challan'))

        dom = [
            ('institute_id', 'in', institute_ids),
            ('program_id', 'in', program_ids),
            ('term_id', 'in', term_ids),
            ('payment_state', '=', 'not_paid'),
            ('company_id', '=', company_id)
        ]
        if challan_type:
            dom.append(('challan_type', 'in', challan_type))
        invoices = self.env['account.move'].search(dom, order='student_code,institute_id,program_id')
        report = self.env['ir.actions.report']._get_report_from_name('odoocms_fee.program_wise_fin_summary_report')
        docargs = {
            'doc_ids': [],
            'doc_model': report.model,
            'data': data['form'],
            'invoice': invoices or [],
            'company': request.env.company
        }
        return docargs
