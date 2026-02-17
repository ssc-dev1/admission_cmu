from odoo.http import route, request, Controller
import json
from werkzeug.datastructures import FileStorage
import base64

class DashboardStudentAdmission (Controller):
    @route(['/admission/student/dashboard'], methods=['GET'], type='http', auth="user")
    def admission_student_dashboard(self, **kw):
        company = request.env.company
        user = request.env.user
        application_id = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', user.login)])
        admit_card = request.env['applicant.entry.test'].sudo().search(
            [('student_id', "=", application_id.id), ('active', '=', True),('paper_status', 'not in', ('missed','passed','failed')),
             ('slot_type', '=', 'test')])
        test_letter = request.env['applicant.entry.test'].sudo().search(
            [('student_id', "=", application_id.id), ('active', '=', True), ('paper_status', '=', False),
             ('slot_type', '=', 'interview')])

        merit_id = request.env['odoocms.merit.registers'].sudo().search(
            [('register_id', '=', application_id.register_id.id), ('publish_merit', '=', True)])
        merit_student = request.env['odoocms.merit.register.line'].sudo().search(
            [('applicant_id.application_no', '=', user.login), ('merit_reg_id', 'in', merit_id.ids), ('selected', '=', True)])
        pending_request = request.env['odoocms.program.transfer.request'].sudo().search(
            [('applicant_id', '=', application_id.id), ('state', '=', 'draft')])
        
        last_request = request.env['odoocms.program.transfer.request'].sudo().search(
            [('applicant_id', '=', application_id.id), ('state', '!=', 'draft')],limit=1,order='id desc')
        offer_letter = request.env['ucp.offer.letter'].sudo().search(
            [('applicant_id', '=', application_id.id)], limit=1)
        
        domain = [('student_id', '=', application_id.student_id.id),('label_id.type','=','admission'),('show_on_portal','=',True)]
        fee_invoice = request.env['odoocms.fee.barcode'].sudo().search(domain, limit=1,order='id desc')
        color_scheme = request.env['ir.config_parameter'].sudo().get_param('odoocms_admission_portal.color_scheme')

        context = {
            'color_scheme':color_scheme,
            'fee_invoice': fee_invoice,
            'company': company,
            'merit_student': merit_student,
            'is_blacklisted': True if offer_letter.is_blacklisted else False,
            'pending_request': pending_request,
            'last_request': last_request,
            'admit_card': admit_card,
            'test_letter':test_letter,
            'user': user,
            'application_id': application_id,
        }
        return request.render('odoocms_admission_portal.admission_student_dashboard_ucp', context)

    @route(['/program/transfer/'], methods=['GET'], csrf=False, type='http', auth="user")
    def program_transfer_request(self, **kw):
        application_id = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)])
        try:
            program_transfer_from = kw.get('program_transfer_from')
            program_transfer_to = kw.get('program_transfer_to')        
            pretest_id = kw.get('pretest_id','')   
            pending_request = request.env['odoocms.program.transfer.request'].sudo().search([('applicant_id', '=', application_id.id),('state', '=','draft')])
            if not pending_request:
                pretest_card= kw.get('pre_test_card','')
                if type(kw.get('pre_test_card','')) == FileStorage:
                    pretest_card =  base64.b64encode(kw.get('pre_test_card').read())
                program_transfer_request = request.env['odoocms.program.transfer.request'].sudo().create({
                    'applicant_id': application_id.id,
                    'pretest_id': pretest_id,
                    'current_program': program_transfer_to,
                    'pretest_card':pretest_card,
                    'previous_program': program_transfer_from,
                    'pre_test_marks':kw.get('pre_test_marks',''),
                })
            if pending_request: 
                pretest_card= kw.get('pre_test_card','')
                if type(kw.get('pre_test_card','')) == FileStorage:
                    pretest_card =  base64.b64encode(kw.get('pre_test_card').read())
                if pending_request.state == 'draft':
                    pending_request.unlink()    
                    program_transfer_request = request.env['odoocms.program.transfer.request'].sudo().create({
                        'applicant_id': application_id.id,
                        'pretest_id': pretest_id,
                        'pretest_card':pretest_card,
                        'pre_test_marks':kw.get('pre_test_marks',''),
                        'current_program': program_transfer_from,
                        'previous_program': program_transfer_to,
                    })

            return json.dumps({
                'status': 'noerror',
            })

        except Exception as e:
            return json.dumps({
                'msg': f'{e}',
                # 'application_state': application_id.state,
                'status': 'error',
            })

    
    @route(['/change/password'], methods=['POST'],csrf=False, type='http', auth="user")
    def change_password(self, **kw):
        try:
            password=kw.get('password')
            password2=kw.get('password2')
            if password == password2:
                user=request.env['res.users'].sudo().browse(request.env.user.id)
                user.password=password                
                return json.dumps(
                {    'status':'noerror',
                    'msg':'Password Change Successfully',
                })
            return json.dumps(
            {    'status':'noerror',
                'msg':'Password and Confirm Password Not Same',
            })
        except Exception as e:
            return json.dumps(
            {    'status':'error',
                'msg':f'{e}',
            })
        
