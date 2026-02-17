import pdb
from odoo.addons.base_rest.components.service import to_bool, to_int
from odoo.addons.component.core import Component
from odoo.addons.base_rest.components.service import skip_secure_response, skip_secure_params
from datetime import date
import json
import logging
import decimal


_logger = logging.getLogger(__name__)


def roundhalfup(n, decimals=0):
    context = decimal.getcontext()
    context.rounding = decimal.ROUND_HALF_UP
    return float(round(decimal.Decimal(str(n)), decimals))


class InvoiceService(Component):
    _inherit = "base.rest.service"
    _name = "invoice.service"
    _usage = "invoice"
    _collection = "odoo.services"
    _description = """
        Invoice Services
    """

    def get(self, _id):
        return self._to_json(self._get(_id))

    @skip_secure_params
    @skip_secure_response
    def inquiry(self, **params):
        param_body = json.dumps(params, indent=4)
        p_ChallanNumber = params['p_ChallanNumber']
        # For Admission DB request
        # if p_ChallanNumber[0:5] == '14599':
        #     ret_response = self.inquiry_redirect_ucp(params)
        #     return ret_response
        # elif p_ChallanNumber[0:5] in {'25599', '94299'}:
        #     ret_response = self.inquiry_redirect_cust(params)
        #     return ret_response
        # else:
        user_id = self.env['res.users'].sudo().search([('login', '=', params['p_UserName']), ('secret', '=', params['p_Password'])])
        if user_id:
            challan = self.env["odoocms.fee.barcode"].sudo().search([('name', '=', params['p_ChallanNumber'])])
            if challan:
                challan_date = challan.date_due or date.today()
                if challan.date_due and date.today() > challan.date_due:
                    data = {
                        'ReturnValue': '9',
                    }
                    response_body = json.dumps(data, indent=4)
                    write_data = {
                        'name': 'payment',
                        'param_body': param_body,
                        'response_body': response_body,
                    }
                    self.env['odoocms.api.log'].sudo().create(write_data)
                    return data

                if challan.student_id.state in ('defferred', 'suspended'):
                    data = {
                        'ReturnValue': '10',
                    }
                    response_body = json.dumps(data, indent=4)
                    write_data = {
                        'name': 'payment',
                        'param_body': param_body,
                        'response_body': response_body,
                    }
                    self.env['odoocms.api.log'].sudo().create(write_data)
                    return data

                # ***** Paid Challan *****#
                if challan.state == 'paid':
                    data = {
                        'ReturnValue': '4',
                    }
                    response_body = json.dumps(data, indent=4)
                    write_data = {
                        'name': 'payment',
                        'param_body': param_body,
                        'response_body': response_body,
                    }
                    self.env['odoocms.api.log'].sudo().create(write_data)
                    return data

                data = {
                    'p_StudentName': challan.student_id.name,
                    'p_Amount': int(roundhalfup(challan.amount_residual)),
                    'p_BillingMonth': challan.date.strftime("%Y-%m"),
                    'p_DueDate': challan_date.strftime("%Y-%m-%d"),
                    'p_ReferenceNo': challan.student_id.code,
                    'p_CompanyName': challan.student_id.campus_id.company_id.name,
                    'p_CampusName': challan.student_id.program_id.institute_id.name,
                    'p_CustomerCode': challan.student_id.program_id and challan.student_id.program_id.institute_id.customer_code or '',
                    'p_ChallanNumber': challan.name,
                    'ReturnValue': '0',
                }
                response_body = json.dumps(data, indent=4)
                write_data = {
                    'name': 'payment',
                    'param_body': param_body,
                    'response_body': response_body,
                }
                self.env['odoocms.api.log'].sudo().create(write_data)
            else:
                invoice = self.env["account.move"].sudo().search([('move_type', '=', 'out_invoice'),
                                                                  ('old_challan_no', '=', params['p_ChallanNumber'])])
                if invoice:
                    inv_date = invoice.invoice_date_due or date.today()
                    if invoice.expiry_date and date.today() > invoice.expiry_date:
                        data = {
                            'ReturnValue': '9',
                        }
                        response_body = json.dumps(data, indent=4)
                        write_data = {
                            'name': 'payment',
                            'param_body': param_body,
                            'response_body': response_body,
                        }
                        self.env['odoocms.api.log'].sudo().create(write_data)
                        return data

                    # ***** CLOSED_ACCOUNT *****#
                    # id->10---Description->CLOSED_ACCOUNT---Long Description->Closed Account Status
                    if invoice.student_id.state in ('defferred', 'suspended'):
                        data = {
                            'ReturnValue': '10',
                        }
                        response_body = json.dumps(data, indent=4)
                        write_data = {
                            'name': 'payment',
                            'param_body': param_body,
                            'response_body': response_body,
                        }
                        self.env['odoocms.api.log'].sudo().create(write_data)
                        return data

                    # ***** Paid Challan *****#
                    if invoice.payment_state in ('in_payment', 'paid'):
                        data = {
                            'ReturnValue': '4',
                        }
                        response_body = json.dumps(data, indent=4)
                        write_data = {
                            'name': 'payment',
                            'param_body': param_body,
                            'response_body': response_body,
                        }
                        self.env['odoocms.api.log'].sudo().create(write_data)
                        return data

                    data = {
                        'p_StudentName': (invoice.student_id and invoice.student_id.name) or
                            (invoice.partner_id and invoice.partner_id.name) or
                            (invoice.application_id and invoice.application_id.name) or '',
                        'p_Amount': int(invoice.amount_total),
                        'p_BillingMonth': invoice.invoice_date.strftime("%Y-%m"),
                        'p_DueDate': inv_date.strftime("%Y-%m-%d"),
                        'p_ReferenceNo': (invoice.student_id and invoice.student_id.code) or (invoice.application_id and invoice.application_id.application_no) or '',
                        'p_CompanyName': invoice.company_id and invoice.company_id.name or '',
                        'p_CampusName': (invoice.student_id and invoice.student_id.program_id.institute_id.name) or
                                        (invoice.application_id.prefered_program_id and invoice.application_id.prefered_program_id and invoice.application_id.prefered_program_id.institute_id.name) or '',
                        # 'p_CustomerCode': invoice.student_id.program_id and invoice.student_id.program_id.institute_id.customer_code or '',
                        'p_CustomerCode': '',
                        'p_ChallanNumber': invoice.old_challan_no,
                        'ReturnValue': '0',
                    }
                    response_body = json.dumps(data, indent=4)
                    write_data = {
                        'name': 'payment',
                        'param_body': param_body,
                        'response_body': response_body,
                    }
                    self.env['odoocms.api.log'].sudo().create(write_data)

                else:   # ***** INCORRECT_CHALLAN_NO *****#
                    data = {
                        'ReturnValue': '3',
                    }
                    response_body = json.dumps(data, indent=4)
                    write_data = {
                        'name': 'payment',
                        'param_body': param_body,
                        'response_body': response_body,
                    }
                    self.env['odoocms.api.log'].sudo().create(write_data)

        else:   # Invalid User + Password
            data = {
                'ReturnValue': '2',
            }
            response_body = json.dumps(data, indent=4)
            write_data = {
                'name': 'payment',
                'param_body': param_body,
                'response_body': response_body,
            }
            self.env['odoocms.api.log'].sudo().create(write_data)

        return data

    @skip_secure_params
    @skip_secure_response
    def payment(self, **params):
        _logger.exception("########################challan payment API is called###############################")
        param_body = json.dumps(params, indent=4)
        try:

            p_ChallanNumber = params['p_ChallanNumber']
            # For Admission Challans
            # if p_ChallanNumber[0:5] == '14599':
            #     ret_response = self.payment_redirect_ucp(params)
            #     return ret_response
            # elif p_ChallanNumber[0:5] in {'25599', '94299'}:
            #     ret_response = self.payment_redirect_cust(params)
            #     return ret_response
            # # For Regular Semester Fee
            # else:
            tran_auth_id = False
            journal_id = False
            challan = False
            user_id = self.env['res.users'].sudo().search([('login', '=', params['p_UserName']), ('secret', '=', params['p_Password'])])

            invoice = self.env["odoocms.fee.barcode"].sudo().search([('name', '=', p_ChallanNumber)])
            if invoice:
                if params['p_TransactionId']:
                    tran_auth_id = self.env["odoocms.fee.barcode"].sudo().search([('transaction_id', '=', params['p_TransactionId'])])
                    challan = True

            if not invoice:
                invoice = self.env["account.move"].sudo().search([('move_type', '=', 'out_invoice'), ('old_challan_no', '=', p_ChallanNumber)])
                if params['p_TransactionId']:
                    tran_auth_id = self.env["account.move"].sudo().search([('transaction_id', '=', params['p_TransactionId'])])

            if invoice and invoice.company_id and user_id:
                journal_id = self.env['account.journal'].sudo().search([('company_id', '=',invoice.company_id.id), ('api_user', '=', params['p_UserName'])])

            # ***** Already Paid *****#
            if invoice and ((not challan and invoice.payment_date) or (challan and invoice.date_payment)):
                data = {
                    'ReturnValue': '4',
                    'p_ChallanNumber': p_ChallanNumber,
                }
                self.create_unconfirmed_bank_paid_record(params, '4')
                response_body = json.dumps(data, indent=4)
                write_data = {
                    'name': 'payment',
                    'param_body': param_body,
                    'response_body': response_body,
                }
                self.env['odoocms.api.log'].sudo().create(write_data)
                return data

            # ***** Transaction Already Exists *****#
            elif tran_auth_id:
                data = {
                    'ReturnValue': '11',
                    'p_ChallanNumber': p_ChallanNumber,
                }
                self.create_unconfirmed_bank_paid_record(params, '11')
                response_body = json.dumps(data, indent=4)
                write_data = {
                    'name': 'payment',
                    'param_body': param_body,
                    'response_body': response_body,
                }
                self.env['odoocms.api.log'].sudo().create(write_data)
                return data

            # ***** INVALID_AMOUNT *****#
            elif invoice and ((not challan and not invoice.amount_total == params['p_Amount']) or (challan and not int(roundhalfup(invoice.amount_residual)) == params['p_Amount'])):
                data = {
                    'ReturnValue': '5',
                    'p_ChallanNumber': p_ChallanNumber,
                }
                self.create_unconfirmed_bank_paid_record(params, '5')
                response_body = json.dumps(data, indent=4)
                write_data = {
                    'name': 'payment',
                    'param_body': param_body,
                    'response_body': response_body,
                }
                self.env['odoocms.api.log'].sudo().create(write_data)
                return data

            # ***** Invoice Available *****#
            elif invoice:
                if not challan:
                    order_data = {
                        # 'paid_amount': int(params['p_Amount']),
                        'payment_date': params['tran_date'],
                        'paid_time': params['tran_time'],
                        'transaction_id': params['p_TransactionId'],
                        'payment_state': 'paid',
                        # 'bank_ref': '123456'
                    }
                elif challan:
                    order_data = {
                        # 'paid_amount': int(params['p_Amount']),
                        'date_payment': params['tran_date'],
                        'paid_time': params['tran_time'],
                        'transaction_id': params['p_TransactionId'],
                        'state': 'paid',
                        # 'bank_ref': '123456'
                    }
                if not journal_id:
                    journal_id = self.env['account.journal'].sudo().search([('company_id', '=',invoice.company_id.id), ('type', '=', 'bank')], order='id asc', limit=1)
                amount = float(params['p_Amount'])
                payment_obj = self.env['odoocms.fee.payment'].sudo()
                if not challan:
                    payment_rec = payment_obj.fee_payment_record(params['tran_date'], p_ChallanNumber, amount, journal_id, invoice_id=invoice)
                    payment_rec.sudo().action_post_fee_payment()
                elif challan:
                    payment_rec = payment_obj.fee_payment_record(params['tran_date'], p_ChallanNumber, amount, journal_id, challan_id=invoice)
                    payment_rec.sudo().action_post_fee_payment()

                if challan:
                    order_data['payment_id'] = payment_rec.id
                invoice.sudo().write(order_data)

                data = {
                    'ReturnValue': '0',
                    'p_ChallanNumber': p_ChallanNumber,
                }
                response_body = json.dumps(data, indent=4)
                write_data = {
                    'name': 'payment',
                    'param_body': param_body,
                    'response_body': response_body,
                }
                self.env['odoocms.api.log'].sudo().create(write_data)
                return data

            # ***** INCORRECT_CHALLAN_NO *****#
            data = {
                'ReturnValue': '3',
            }
            self.create_unconfirmed_bank_paid_record(params, '3')
            response_body = json.dumps(data, indent=4)
            write_data = {
                'name': 'payment',
                'param_body': param_body,
                'response_body': response_body,
            }
            self.env['odoocms.api.log'].sudo().create(write_data)
            return data
        except Exception as e:
            write_data = {
                'name': 'payment',
                'param_body': param_body,
                'response_body': e,
            }
            self.env['odoocms.api.log'].sudo().create(write_data)
            _logger.exception("Error while challan payment: %s", e)

    # def inquiry(self, **params):
    #     param_body = json.dumps(params, indent=4)
    #     data = {
    #         'response_Code': '1'
    #     }
    #     user_id = self.env['res.users'].sudo().search([('login', '=', params['p_UserName']), ('secret', '=', params['p_Password'])])
    #     if user_id:
    #         invoice = self.env["account.move"].sudo().search([('old_challan_no', '=', params['p_ChallanNumber'])])
    #         if invoice:
    #             inv_date = invoice.invoice_date_due or date.today()
    #             # ***** INACTIVE ACCOUNT *****#
    #             # id->9---Description->INACTIVE_ACCOUNT---Long Description->Inactive Account Status
    #             if invoice.expiry_date and date.today() > invoice.expiry_date:
    #                 data = {
    #                     'ReturnValue': '9',
    #                 }
    #                 response_body = json.dumps(data, indent=4)
    #                 write_data = {
    #                     'name': 'payment',
    #                     'param_body': param_body,
    #                     'response_body': response_body,
    #                 }
    #                 self.env['odoocms.api.log'].sudo().create(write_data)
    #
    #                 return data
    #
    #             # ***** CLOSED_ACCOUNT *****#
    #             # id->10---Description->CLOSED_ACCOUNT---Long Description->Closed Account Status
    #             if invoice.student_id.state in ('defferred', 'suspended'):
    #                 data = {
    #                     'ReturnValue': '10',
    #                 }
    #                 response_body = json.dumps(data, indent=4)
    #                 write_data = {
    #                     'name': 'payment',
    #                     'param_body': param_body,
    #                     'response_body': response_body,
    #                 }
    #                 self.env['odoocms.api.log'].sudo().create(write_data)
    #                 return data
    #
    #             # ***** Paid Challan *****#
    #             if invoice.payment_state in ('in_payment', 'paid'):
    #                 data = {
    #                     'ReturnValue': '4',
    #                 }
    #                 response_body = json.dumps(data, indent=4)
    #                 write_data = {
    #                     'name': 'payment',
    #                     'param_body': param_body,
    #                     'response_body': response_body,
    #                 }
    #                 self.env['odoocms.api.log'].sudo().create(write_data)
    #                 return data
    #
    #             data = {
    #                 'p_StudentName': (invoice.student_id and invoice.student_id.name) or
    #                                  (invoice.partner_id and invoice.partner_id.name) or
    #                                  (invoice.application_id and invoice.application_id.name) or '',
    #                 'p_Amount': int(invoice.amount_total),
    #                 'p_BillingMonth': invoice.invoice_date.strftime("%Y-%m"),
    #                 'p_DueDate': inv_date.strftime("%Y-%m-%d"),
    #                 'p_ReferenceNo': (invoice.student_id and invoice.student_id.code) or (invoice.application_id and invoice.application_id.application_no) or '',
    #                 'p_CompanyName': invoice.company_id and invoice.company_id.name or '',
    #                 'p_CampusName': (invoice.student_id and invoice.student_id.program_id.institute_id.name) or
    #                                 (invoice.application_id.prefered_program_id and invoice.application_id.prefered_program_id and invoice.application_id.prefered_program_id.institute_id.name) or '',
    #                 # 'p_CustomerCode': invoice.student_id.program_id and invoice.student_id.program_id.institute_id.customer_code or '',
    #                 'p_CustomerCode': '',
    #                 'p_ChallanNumber': invoice.old_challan_no,
    #                 'ReturnValue': '0',
    #             }
    #             response_body = json.dumps(data, indent=4)
    #             write_data = {
    #                 'name': 'payment',
    #                 'param_body': param_body,
    #                 'response_body': response_body,
    #             }
    #             self.env['odoocms.api.log'].sudo().create(write_data)
    #             return data
    #         else:
    #             # ***** INCORRECT_CHALLAN_NO *****#
    #             data = {
    #                 'ReturnValue': '3',
    #             }
    #             response_body = json.dumps(data, indent=4)
    #             write_data = {
    #                 'name': 'payment',
    #                 'param_body': param_body,
    #                 'response_body': response_body,
    #             }
    #             self.env['odoocms.api.log'].sudo().create(write_data)
    #             return data
    #
    #     else:
    #         # Invalid User + Password
    #         data = {
    #             'ReturnValue': '2',
    #         }
    #         response_body = json.dumps(data, indent=4)
    #         write_data = {
    #             'name': 'payment',
    #             'param_body': param_body,
    #             'response_body': response_body,
    #         }
    #         self.env['odoocms.api.log'].sudo().create(write_data)
    #         return data
    #     return data

    # def payment(self, **params):
    #     param_body = json.dumps(params, indent=4)
    #     tran_auth_id = False
    #     journal_id = False
    #     user_id = self.env['res.users'].sudo().search([('login', '=', params['p_UserName']),
    #                                                    ('secret', '=', params['p_Password'])
    #                                                    ])
    #     if user_id:
    #         journal_id = self.env['account.journal'].sudo().search([('api_user', '=', params['p_UserName'])])
    #
    #     invoice = self.env["account.move"].sudo().search([('old_challan_no', '=', params['p_ChallanNumber'])])
    #     if params['p_TransactionId']:
    #         tran_auth_id = self.env["account.move"].sudo().search([('transaction_id', '=', params['p_TransactionId'])])
    #
    #     # ***** Already Paid *****#
    #     if invoice and invoice.payment_date:
    #         data = {
    #             'ReturnValue': '4',
    #             'p_ChallanNumber': params['p_ChallanNumber'],
    #         }
    #         self.create_unconfirmed_bank_paid_record(params, '4')
    #
    #         response_body = json.dumps(data, indent=4)
    #         write_data = {
    #             'name': 'payment',
    #             'param_body': param_body,
    #             'response_body': response_body,
    #         }
    #         self.env['odoocms.api.log'].sudo().create(write_data)
    #         return data
    #
    #     # ***** Transaction Already Exists *****#
    #     elif tran_auth_id:
    #         data = {
    #             'ReturnValue': '11',
    #             'p_ChallanNumber': params['p_ChallanNumber'],
    #         }
    #         self.create_unconfirmed_bank_paid_record(params, '11')
    #         response_body = json.dumps(data, indent=4)
    #
    #         write_data = {
    #             'name': 'payment',
    #             'param_body': param_body,
    #             'response_body': response_body,
    #         }
    #         self.env['odoocms.api.log'].sudo().create(write_data)
    #         return data
    #
    #     # ***** INVALID_AMOUNT *****#
    #     elif invoice and not invoice.amount_total == params['p_Amount']:
    #         data = {
    #             'ReturnValue': '5',
    #             'p_ChallanNumber': params['p_ChallanNumber'],
    #         }
    #         self.create_unconfirmed_bank_paid_record(params, '5')
    #         response_body = json.dumps(data, indent=4)
    #
    #         write_data = {
    #             'name': 'payment',
    #             'param_body': param_body,
    #             'response_body': response_body,
    #         }
    #         self.env['odoocms.api.log'].sudo().create(write_data)
    #         return data
    #
    #     # ***** Invoice Available *****#
    #     elif invoice:
    #         order_data = {
    #             # 'paid_amount': int(params['p_Amount']),
    #             'payment_date': params['tran_date'],
    #             'paid_time': params['tran_time'],
    #             'transaction_id': params['p_TransactionId'],
    #             'payment_state': 'paid',
    #             # 'bank_ref': '123456'
    #         }
    #         if not journal_id:
    #             journal_id = self.env['account.journal'].sudo().search([('type', '=', 'bank')], order='id asc', limit=1)
    #         amount = float(params['p_Amount'])
    #         p_ChallanNumber = params['p_ChallanNumber']
    #         payment_obj = self.env['odoocms.fee.payment'].sudo()
    #         payment_rec = payment_obj.fee_payment_record(invoice, p_ChallanNumber, journal_id, params['tran_date'])
    #         payment_rec.sudo().action_post_fee_payment()
    #         invoice.sudo().write(order_data)
    #         data = {
    #             'ReturnValue': '0',
    #             'p_ChallanNumber': params['p_ChallanNumber'],
    #         }
    #         response_body = json.dumps(data, indent=4)
    #
    #         write_data = {
    #             'name': 'payment',
    #             'param_body': param_body,
    #             'response_body': response_body,
    #         }
    #         self.env['odoocms.api.log'].sudo().create(write_data)
    #         return data
    #
    #     # ***** INCORRECT_CHALLAN_NO *****#
    #     data = {
    #         'ReturnValue': '3',
    #     }
    #     # Remarked For admission
    #     # self.create_unconfirmed_bank_paid_record(params, '3')
    #     response_body = json.dumps(data, indent=4)
    #     write_data = {
    #         'name': 'payment',
    #         'param_body': param_body,
    #         'response_body': response_body,
    #     }
    #     self.env['odoocms.api.log'].sudo().create(write_data)
    #     return data

    def _get(self, _id):
        return self.env["nrlp"].sudo().browse(_id)

    def _validator_return_get(self):
        res = self._validator_create()
        res.update({"id": {"type": "integer", "required": True, "empty": False}})
        return res

    def _validator_payment(self):
        return {
            "p_ChallanNumber": {"type": "string", "required": True, "empty": False},
            "p_UserName": {"type": "string", "required": True, "empty": False},
            "p_Password": {"type": "string", "required": True, "empty": False},
            "p_TransactionId": {"type": "string", "required": True, "empty": False},
            "p_Amount": {"type": "integer", "required": True, "empty": False},
            "tran_date": {"type": "string", "required": True, "empty": False},
            "tran_time": {"type": "string", "required": True, "empty": False},
            "bank_name": {"type": "string", "required": False, "empty": True},
            # "reserved": {"type": "string", "nullable": False},
        }

    def _validator_return_payment(self):
        res = {
            "ReturnValue": {"type": "string", "nullable": True},
            "p_ChallanNumber": {"type": "string", "nullable": True},
            "reserved": {"type": "string", "nullable": True},
        }
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

    def create_unconfirmed_bank_paid_record(self, params, ret_value):
        journal_id = False
        user_id = self.env['res.users'].sudo().search([('login', '=', params['p_UserName']),
                                                       ('secret', '=', params['p_Password'])])
        invoice = self.env["account.move"].sudo().search([('old_challan_no', '=', params['p_ChallanNumber'])])
        if user_id:
            journal_id = self.env['account.journal'].sudo().search([('api_user', '=', params['p_UserName']),('company_id','=',invoice.company_id.id)])
        nw_data_values = {
            'name': params['p_ChallanNumber'],
            'type': ret_value,
            'invoice_id': invoice and invoice.id or False,
            'challan_amount': invoice and invoice.amount_total or 0,
            'received_amount': params['p_Amount'],
            'bank': params['p_UserName'],
            'journal_id': journal_id and journal_id.id or False,
            'transaction_id': params['p_TransactionId'],
            'transaction_date': params['tran_date'],
            'transaction_time': params['tran_time'],
        }
        if ret_value == '4':
            nw_data_values['processed'] = True
        self.env['odoocms.unconfirmed.paid.bank.challan'].sudo().create(nw_data_values)
