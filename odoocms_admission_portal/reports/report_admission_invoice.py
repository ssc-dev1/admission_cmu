from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date, datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc
import time

from odoo import http
import logging
_logger = logging.getLogger(__name__)


class AdmissionInvoice(models.AbstractModel):
    _name = 'report.odoocms_admission_portal.report_admission_invoice'
    _description = 'Admission Online Invoice'

    @api.model
    def _get_report_values(self, docsid, data=None):
        application_ids = self.env['odoocms.application'].sudo().browse(docsid)

        register_id = application_ids.register_id
        preference_id = application_ids.preference_ids.search(
            [('preference', '=', 1), ('application_id', '=', application_ids.id)], limit=1)
        prospectus_fee = preference_id.program_id.prospectus_registration_fee
        disciplines = 0
        discipline = 0
        prefs = self.env['odoocms.application.preference'].sudo().search(
            [('application_id', '=', application_ids[0].id)])
        program_preferences_ordered = http.request.env['odoocms.application.preference'].sudo().search(
            [('application_id', '=', application_ids[0].id)], order='preference asc')

        # for program in preference_id.program_id:
        #     if program.signin_end_date:
        #         if program.signin_end_date >= date.today():
        #             return ('kjsadfjks')
        # context.update({
        #     program.id: program.name
        # })

        # selected_discipline = []
        # for program in program_preferences_ordered:
        #     selected_discipline += str(program.discipline_id.id)
        # selected_discipline = list(dict.fromkeys(selected_discipline))
        # for i in range(0, len(selected_discipline)):
        #     selected_discipline[i] = int(selected_discipline[i])
        # for pref in prefs:
        #     if pref.discipline_id.id != discipline:
        #         discipline = pref.discipline_id.id
        #         disciplines = disciplines + 1

        registration_fee_international = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.registration_fee_international')

        registration_fee = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.registration_fee')
        additional_fee = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.additional_fee')

        account_payable = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.account_payable')
        account_title = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.account_title')
        account_no = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.account_no')

        account_payable2 = http.request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.account_payable2')
        account_title2 = http.request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.account_title2')
        account_no2 = http.request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.account_no2')

        total_fee = 0
        # for rec in    :
        if application_ids[0].degree.code == 'DAECIVIL':
            choices = program_preferences_ordered.filtered(
                lambda l: l.discipline_id.code == 'TECH' or l.discipline_id.code == 'E')
            for ch in choices:
                if total_fee < 4000:
                    total_fee += int(float(registration_fee))
        else:
            total_fee = int(float(registration_fee))
        # if disciplines > 1:
        #     total_fee += int(float(additional_fee))
        docargs = {
            'application_ids': application_ids or False,
            'account_payable': account_payable or "",
            'account_payable2': account_payable2 or "",
            'registration_fee': prospectus_fee if prospectus_fee else registration_fee,
            'additional_fee': additional_fee or False,
            'total_fee': str(total_fee),
            'registration_fee_international': registration_fee_international or False,
            'account_title': account_title or "",
            'account_title2': account_title2 or "",
            'account_no': account_no or "",
            'account_no2': account_no2 or "",
            'today': date.today() or False,
        }
        # 'disciplines': disciplines,
        return docargs
