import pdb
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component
from odoo.addons.base_rest.components.service import skip_secure_response, skip_secure_params


class MobileService(Component):
    _inherit = "base.rest.service"
    _name = "mobile.service"
    _usage = "mobile"
    _collection = "aarsol.services"
    _description = """
        AARSOL Services
    """

    def get(self, _id):
        return self._to_json(self._get(_id))

    @skip_secure_params
    @skip_secure_response
    def login(self, **params):
        data = {}
        # student_id = self.env['odoocms.student'].sudo().search([('code', '=', 'L1F15BBAM0305')])
        student_id = self.env['odoocms.student'].sudo().search([('code', '=', params['reg_no']), ('secret', '=', params['secret'])])
        return data

    @skip_secure_params
    @skip_secure_response
    def profile(self, **params):
        data = {}
        # student_id = self.env['odoocms.student'].sudo().search([('code', '=', 'L1F15BBAM0305')])
        student_id = self.env['odoocms.student'].sudo().search([('code', '=', params['reg_no']), ('secret', '=', params['secret'])])
        if student_id:
            data = {
                'Name': student_id.name,
                'RegNo': student_id.code,
                'Gender': student_id.gender,
                'CNIC': student_id.cnic,
                'FatherName': student_id.father_name,
                'Email': student_id.notification_email or '',
                'Mobile': student_id.sms_mobile and student_id.sms_mobile or '',
                'DOB': student_id.date_of_birth and student_id.date_of_birth or '',
                'DegreeLevel': student_id.career_id.name,
                'Program': student_id.program_id.code,
                'GradePoints': student_id.grade_points,
                'AttemptedCredits': student_id.attempted_credits,
                'TotalCredits': student_id.credits,
                'EarnedCredits': student_id.earned_credits,
                'CGPA': student_id.cgpa,
                'Scholarship': student_id.scholarship_id.name
            }
        return data

    @skip_secure_params
    @skip_secure_response
    def invoices(self, **params):
        invoices_data = []
        student_id = self.env['odoocms.student'].sudo().search([('code', '=', params['reg_no']), ('secret', '=', params['secret'])])
        if student_id:
            invoices = self.env['account.move'].sudo().search([('student_id', '=', student_id.id)], order='id asc')
            if invoices:
                for invoice in invoices:
                    invoice_line_data = {
                        'InvoiceDate': invoice.invoice_date.strftime('%d-%m-%Y'),
                        'DueDate': invoice.invoice_date_due and invoice.invoice_date_due.strftime('%d-%m-%Y') or '-',
                        'TermName': invoice.term_id and invoice.term_id.name or '-',
                        'TermCode': invoice.term_id and invoice.term_id.code or '-',
                        'ChallanType': dict(invoice.fields_get(allfields=['challan_type'])['challan_type']['selection'])[invoice.challan_type],
                        'ChallanID': invoice.old_challan_no,
                        'AdmissionFee': invoice.admission_fee or '-',
                        'Scholarship': invoice.waiver_percentage or '-',
                        'TuitionFee': invoice.tuition_fee or '-',
                        'HostelFee': invoice.hostel_fee or '-',
                        'MiscFee': invoice.misc_fee,
                        'FineAmount': invoice.fine_amount,
                        'TaxAmount': invoice.tax_amount,
                        'TotalAmount': invoice.amount_total_signed,
                        'Status': dict(invoice.fields_get(allfields=['payment_state'])['payment_state']['selection'])[invoice.payment_state],
                    }
                    invoices_data.append(invoice_line_data)
        return invoices_data

    @skip_secure_params
    @skip_secure_response
    def results(self, **params):
        result_data = []
        student_id = self.env['odoocms.student'].sudo().search([('code', '=', params['reg_no']), ('secret', '=', params['secret'])])
        if student_id:
            student_terms = self.env['odoocms.student.term'].sudo().search([('student_id', '=', student_id.id)], order='id asc')
            if student_terms:
                for student_term in student_terms:
                    result_line = {
                        'TermName': student_term.term_id and student_term.term_id.name or '-',
                        'TermCode': student_term.term_id and student_term.term_id.code or '-',
                        'GradePoints': student_term.grade_points,
                        'CumulativeGP': student_term.cgp or '-',
                        'AttemptedCH': student_term.attempted_credits or '-',
                        'EarnedCH': student_term.earned_credits or '-',
                        'CumulativeCH': student_term.ecch or '-',
                        'SGPA': student_term.sgpa,
                        'CGPA': student_term.cgpa,
                    }
                    result_data.append(result_line)
        return result_data

    @skip_secure_params
    @skip_secure_response
    def timetable(self, **params):
        timetabledata = []
        makeup_classes = []
        student_id = self.env['odoocms.student'].sudo().search([('code', '=', params['reg_no']), ('secret', '=', params['secret'])])
        if student_id:
            timetable = self.env['odoocms.timetable.schedule'].sudo().get_timetable(student_id, False, False)
            date = datetime.now()
            month = date.strftime("%B")
            week = date.strftime("%w")

            for schedule in timetable:
                for day in timetable[schedule]:
                    data = {
                        'day_code': day['day_code'],
                        'subject': str(day['subject_code'])[:35] + '..' if len(day['subject_code']) > 35 else day['subject_code'],
                        'subject_name': str(day['subject_name'])[:35] + '..' if len(day['subject_name']) > 35 else day['subject_name'],
                        'component': day['component'],
                        'time_from': day['time_from'],
                        'faculty': day['faculty'],
                        'time_to': day['time_to'],
                        'room': day['room']
                    }
                    timetabledata.append(data)

            date_today = date.today()
            date_seven = date.today() + relativedelta(days=6)

            makeup_roasters = self.env['odoocms.class.attendance'].sudo().search([
                ('date_class', '>=', date_today), ('date_class', '<=', date_seven),
                ('makeup_class', '=', 'True'), ('makeup_approved', '=', True),
                ('state', '!=', 'cancel')])

            for roaster in makeup_roasters:
                classes = roaster.attendance_lines.filtered(lambda l: l.student_id.id == student_id.id)
                if classes:
                    makeup_classes.append(roaster)
        return_data = {'timetabledata': timetabledata, 'makeup_classes': makeup_classes}
        return return_data

    def _get(self, _id):
        return self.env["nrlp"].sudo().browse(_id)

    def _validator_return_get(self):
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res

    def _validator_create(self):
        res = {
            "p_ChallanNumber": {"type": "string", "required": True, "empty": False},
            "customer_name": {"type": "string", "required": True, "empty": False},
            "amount": {"type": "float", "nullable": False},
        }
        return res

    def _validator_return_create(self):
        return self._validator_return_get()

    def _validator_inquiry(self):
        res = {
            "p_ChallanNumber": {"type": "string", "required": True, "empty": False},
            "p_UserName": {"type": "string", "required": True, "empty": False},
            "p_Password": {"type": "string", "required": True, "empty": False},
            # "bank_name": {"type": "string", "required": True, "empty": False},
            # "reserved": {"type": "string", "nullable": False},
        }
        return res

    def _validator_return_inquiry(self):
        res = {
            "p_StudentName": {"type": "string", "nullable": True},
            "p_Amount": {"type": "integer", "empty": False},
            "p_BillingMonth": {"type": "string", "nullable": True},
            "p_DueDate": {"type": "string", "nullable": True},
            "p_ReferenceNo": {"type": "string", "nullable": True},
            "p_CompanyName": {"type": "string", "nullable": True},
            "p_CampusName": {"type": "string", "nullable": True},
            "p_CustomerCode": {"type": "string", "nullable": True},
            "tran_auth_Id": {"type": "string", "nullable": True},
            "p_ChallanNumber": {"type": "string", "nullable": True},
            "ReturnValue": {"type": "string", "nullable": True},
        }
        return res

    def _to_json(self, order):
        res = {
            "id": order.id,
            "consumer_number": order.consumer_number,
            "customer_name": order.customer_name,
            "amount": order.amount,
        }
        return res
