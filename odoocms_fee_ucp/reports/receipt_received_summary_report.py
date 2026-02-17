# -*- coding: utf-8 -*-
import pdb
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class ReceiptReceivedSummaryReport(models.AbstractModel):
    _inherit = 'report.odoocms_fee.receipt_received_summary_report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        form = data.get('form', {})
        date_from = form.get('date_from', False)
        date_to = form.get('date_to', False)
        company_id = form.get('company_id', self.env.company.id)
        institute_ids = form.get('institute_ids') or self.env['odoocms.institute'].search([]).ids
        journal_ids = form.get('journal_ids') or self.env['account.journal'].search([('type', '=', 'bank')]).ids
        date_wise_amount = []
        current_user = self.env.user
        totals = {'total_received_amount': 0,
                  'total_received_inv': 0,
                  'total_abb_inv': 0,
                  'total_abb_amt': 0,
                  'total_bal_inv': 0,
                  'total_bal_amt': 0,
                  'total_bipl_inv': 0,
                  'total_bipl_amt': 0,
                  'total_dib_inv': 0,
                  'total_dib_amt': 0,
                  'total_fbl_inv': 0,
                  'total_fbl_amt': 0,
                  'total_hbl_inv': 0,
                  'total_hbl_amt': 0,
                  'total_tmf_inv': 0,
                  'total_tmf_amt': 0,
                  'total_bop_inv': 0,
                  'total_bop_amt': 0,
                  }

        if date_from and date_to:
            date_from = fields.Date.from_string(date_from)
            date_to = fields.Date.from_string(date_to)
            if date_from > date_to:
                raise ValidationError(_('Start Date must be Anterior to End Date'))
            else:
                start_date = date_from
                while start_date <= date_to:
                    abb_inv = 0
                    abb_amt = 0
                    bal_inv = 0
                    bal_amt = 0
                    bipl_inv = 0
                    bipl_amt = 0
                    dib_inv = 0
                    dib_amt = 0
                    fbl_inv = 0
                    fbl_amt = 0
                    hbl_inv = 0
                    hbl_amt = 0
                    tmf_inv = 0
                    tmf_amt = 0
                    bop_inv = 0
                    bop_amt = 0

                    abb_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'ABB')])
                    if abb_payment_recs:
                        abb_inv = len(abb_payment_recs)
                        abb_amt += sum([abb_payment_rec.received_amount for abb_payment_rec in abb_payment_recs])

                    bal_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'BAL')])
                    if bal_payment_recs:
                        bal_inv = len(bal_payment_recs)
                        bal_amt += sum([bal_payment_rec.received_amount for bal_payment_rec in bal_payment_recs])

                    bipl_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'BIPL')])
                    if bipl_payment_recs:
                        bipl_inv = len(bipl_payment_recs)
                        bipl_amt += sum([bal_payment_rec.received_amount for bal_payment_rec in bal_payment_recs])

                    dib_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'DIB')])
                    if dib_payment_recs:
                        dib_inv = len(dib_payment_recs)
                        dib_amt += sum([dib_payment_rec.received_amount for dib_payment_rec in dib_payment_recs])

                    fbl_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'FBL')])
                    if fbl_payment_recs:
                        fbl_inv = len(fbl_payment_recs)
                        fbl_amt += sum([fbl_payment_rec.received_amount for fbl_payment_rec in fbl_payment_recs])

                    hbl_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'HBL')])
                    if hbl_payment_recs:
                        hbl_inv = len(hbl_payment_recs)
                        hbl_amt += sum([hbl_payment_rec.received_amount for hbl_payment_rec in hbl_payment_recs])

                    tmf_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'TMF')])
                    if tmf_payment_recs:
                        tmf_inv = len(tmf_payment_recs)
                        tmf_amt += sum([tmf_payment_rec.received_amount for tmf_payment_rec in tmf_payment_recs])

                    bop_payment_recs = self.env['odoocms.fee.payment'].search([
                        ('journal_id', 'in', journal_ids),
                        ('invoice_id.institute_id', 'in', institute_ids),
                        ('date', '=', start_date),
                        ('journal_id.bank_id.bic', '=', 'BOP')])
                    if bop_payment_recs:
                        bop_inv = len(bop_payment_recs)
                        bop_amt += sum([bop_payment_rec.received_amount for bop_payment_rec in bop_payment_recs])

                    received_amount = abb_amt + bal_amt + bipl_amt + dib_amt + fbl_amt + hbl_amt + tmf_amt + bop_amt
                    received_inv = abb_inv + bal_inv + bipl_inv + dib_inv + fbl_inv + hbl_inv + tmf_inv + bop_inv
                    line = {
                        "date": start_date.strftime('%d-%m-%Y'),
                        "abb_inv": abb_inv,
                        "abb_amt": abb_amt,
                        "bal_inv": bal_inv,
                        "bal_amt": bal_amt,
                        "bipl_inv": bipl_inv,
                        "bipl_amt": bipl_amt,
                        "dib_inv": dib_inv,
                        "dib_amt": dib_amt,
                        "fbl_inv": fbl_inv,
                        "fbl_amt": fbl_amt,
                        "hbl_inv": hbl_inv,
                        "hbl_amt": hbl_amt,
                        "tmf_inv": tmf_inv,
                        "tmf_amt": tmf_amt,
                        "bop_inv": bop_inv,
                        "bop_amt": bop_amt,
                        "received_amount": received_amount,
                        "received_inv": received_inv,
                    }
                    date_wise_amount.append(line)
                    start_date += relativedelta(days=1)

                    totals['total_received_amount'] += received_amount
                    totals['total_received_inv'] += received_inv
                    totals['total_abb_inv'] += abb_inv
                    totals['total_abb_amt'] += abb_amt
                    totals['total_bal_inv'] += bal_inv
                    totals['total_bal_amt'] += bal_amt
                    totals['total_bipl_inv'] += bipl_inv
                    totals['total_bipl_amt'] += bipl_amt
                    totals['total_dib_inv'] += dib_inv
                    totals['total_dib_amt'] += dib_amt
                    totals['total_fbl_inv'] += fbl_inv
                    totals['total_fbl_amt'] += fbl_amt
                    totals['total_hbl_inv'] += hbl_inv
                    totals['total_hbl_amt'] += hbl_amt
                    totals['total_tmf_inv'] += tmf_inv
                    totals['total_tmf_amt'] += tmf_amt
                    totals['total_bop_inv'] += bop_inv
                    totals['total_bop_amt'] += bop_amt

        report = self.env['ir.actions.report']._get_report_from_name('odoocms_fee.receipt_received_summary_report')
        docargs = {
            'doc_ids': [],
            'doc_model': report.model,
            'data': data['form'],
            'date_wise_amount': date_wise_amount or False,
            'date_from': date_from.strftime("%d-%m-%Y") or False,
            'date_to': date_to.strftime("%d-%m-%Y") or False,
            'company': current_user.company_id or False,
            'totals': totals,
        }
        return docargs
