import pdb
from odoo import api, fields, models, _


class FeeDefaulterReport(models.AbstractModel):
    _name = 'report.odoocms_fee_ucp.fee_defaulter_report'
    _description = 'Fee Defaulter Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        data_lines = []
        term_rec = self.env['odoocms.academic.term']
        label = 'Main'
        faculty_ids = data.get('form', {}).get('faculty_ids') or self.env['odoocms.institute'].search([]).ids
        term_id = data.get('form', {}).get('term_id') and data['form']['term_id'][0] or False
        if term_id:
            term_rec = self.env['odoocms.academic.term'].browse(term_id)

        label_id = data.get('form', {}).get('label_id') and data['form']['label_id'][0] or False
        if label_id:
            label_rec = self.env['account.payment.term.label'].browse(label_id)
            label = label_rec.name

        exclude_due_date = data.get('form', {}).get('exclude_due_date')
        exclude_withdraw_students = data.get('form', {}).get('exclude_withdraw_students')

        dom = [('label_id', '=', label_id), ('term_id', '=', term_id), ('state', 'not in', ('paid','cancel')),('amount_residual','>',0)]
        if exclude_due_date:
            dom.append(('date_due', '<', fields.Date.today()))
        if exclude_withdraw_students:
            dom.append(('student_id.state', '!=', 'withdraw'))

        if faculty_ids:
            for faculty_id in faculty_ids:
                faculty_rec = self.env['odoocms.institute'].sudo().browse(faculty_id)
                defaulter_lines = self.env['odoocms.fee.barcode'].sudo().search(dom + [('institute_id', '=', faculty_id)], order='student_id')
                if defaulter_lines:
                    line = ({
                        'faculty_name': faculty_rec.name,
                        'faculty_code': faculty_rec.code,
                        'lines': defaulter_lines,
                    })
                    data_lines.append(line)
        report = self.env['ir.actions.report']._get_report_from_name('odoocms_fee_ucp.fee_defaulter_report')
        docargs = {
            'doc_ids': docsid,
            'doc_model': report.model,
            'data': data['form'],
            'company_rec': self.env.company,
            'term': term_rec,
            'label': label,
            'data_lines': data_lines,
            'total_amount': 0,
            'total_fine_amount': 0,
        }
        return docargs
