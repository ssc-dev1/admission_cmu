from odoo import http, _, SUPERUSER_ID
from odoo.http import route, request, Controller, content_disposition
from odoo.exceptions import UserError, ValidationError
from werkzeug.datastructures import FileStorage
from datetime import date, datetime
import json
import base64
import pdb


class RegisterApplication(Controller):

    def _show_report_admit(self, model, report_type, report_ref, download=False):

        if report_type not in ('html', 'pdf', 'text'):
            raise UserError(_("Invalid report type: %s") % report_type)

        report_sudo = request.env.ref(report_ref).with_user(SUPERUSER_ID)

        if not isinstance(report_sudo, type(request.env['ir.actions.report'])):
            raise UserError(
                _("%s is not the reference of a report") % report_ref)

        method_name = '_render_qweb_%s' % (report_type)
        report = getattr(report_sudo, method_name)(
            [model.id], data={'report_type': report_type})[0]
        reporthttpheaders = [
            ('Content-Type', 'application/pdf' if report_type == 'pdf' else 'text/html'),
            ('Content-Length', len(report)),
        ]
        # if report_type == 'pdf' and download:
        #     # filename = "letter.pdf"
        #     reporthttpheaders.append(
        #         ('Content-Disposition', 'content_disposition(filename)'))
        return request.make_response(report, headers=reporthttpheaders)

    @route('/next/education/step/', type='http', auth='user', methods=['POST'], csrf=False)
    def save_education_application(self, **kw):
        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)], limit=1)
        try:
            if request.httprequest.method == 'POST':
                form_data = {}
            if kw.get('step_name') == 'education_step_submit':
                education_criteria = 'no'
                preferences_allowed = 0
                
                applicant_education_year = max(
                    [int(year.year_age) for year in application.applicant_academic_ids.degree_name])

                register_id = request.env['odoocms.admission.register'].sudo().search([('state', '=', 'application'), ('min_edu_year', '<=', applicant_education_year), ('company_id', '=' , request.env.user.company_id.id)])
                if register_id:
                    register_id_max = max(
                        [rec.min_edu_year for rec in register_id])
                    register_id = register_id.filtered(
                        lambda x: x.min_edu_year == register_id_max)[0]
                    application.register_id = register_id

                preferences_allowed = ''
                if application.register_id:
                    if (applicant_education_year >= application.register_id.min_edu_year or 0) and len(
                            application.applicant_academic_ids) >= 2:

                        if application.step_no <= int(kw.get('step_no')):
                            application.step_no = application.step_no + 1
                        education_criteria = 'yes'
                        preferences_allowed = int(
                            application.register_id.preferences_allowed)
                if application.register_id:
                    preferences_allowed = application.register_id.preferences_allowed

                return json.dumps({
                    'education_criteria': education_criteria,
                    'preferences_allowed': preferences_allowed,
                    # 'academic_data': context_academic_data,
                    # 'preferences_allowed': preferences_allowed,
                    'msg': 'Education Details Saved',
                    'step_no': application.step_no,
                    'application_state': application.state,
                    'status': 'noerror'
                })
        except Exception as e:

            return json.dumps({
                'msg': f'Error! {e}',
                'status': 'error',
                'step_no': application.step_no,
                'application_state': application.state,
            })

    @route('/admission/application/save/', type='http', auth='user', methods=['POST'], csrf=False)
    def save_application(self, **kw):
        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)], limit=1)
        try:
            if request.httprequest.method == 'POST':
                form_data = {}

                if kw.get('step_name') == 'personal':
                    # for persnol detail form
                    try:
                        dob = datetime.strptime(
                            kw.get('date_of_birth'), '%m/%d/%Y')
                    except:
                        dob = ''

                    personal_detail = {
                        'last_school_attend': kw.get('last_institute_attend', ''),
                        'advertisement': kw.get('advertisement', ''),
                        'first_name': kw.get('first_name', ''),
                        'middle_name': kw.get('middle_name', ''),
                        'last_name': kw.get('last_name', ''),
                        'gender': kw.get('gender', ''),
                        'date_of_birth': dob,
                        'program_migration': True if kw.get('program_migration') == 'on' else False,
                        'migration_type': kw.get('migration_type',''),
                        'migration_university': kw.get('migration_university',''),
                        'current_registration_no': kw.get('current_registration_no',''),
                        'last_studied_semester': kw.get('last_studied_semester',''),
                        'last_obtained_cgpa': kw.get('last_obtained_cgpa',''),
                        'blood_group': kw.get('blood_group', ''),
                        'father_name': kw.get('father_name', ''),
                        'father_cnic': kw.get('father_cnic', '').replace('-', ''),
                        'father_status': kw.get('father_status', ''),
                        'mother_name': kw.get('mother_name', ''),
                        'mother_cnic': kw.get('mother_cnic', '').replace('-', ''),
                        'sisters': kw.get('sisters', ''),
                        'brothers': kw.get('brothers', ''),
                        'mother_status': kw.get('mother_status', ''),
                        'religion_id': kw.get('religion_id', ''),
                        'nationality': kw.get('nationality', ''),
                    }

                    if int(kw.get('nationality', '')) == 177:
                        personal_detail.update({
                            'cnic': kw.get('cnic', '').replace('-', ''),
                            'province_id': kw.get('province_id', ''),
                            'domicile_id': kw.get('domicile_id', ''),

                        })
                    if int(kw.get('nationality')) != 177:
                        personal_detail.update({
                            'passport': kw.get('passport', ''),
                            'province2': kw.get('province2', ''),

                        })

                    # update family details
                    if personal_detail.get('father_status') == 'alive':
                        personal_detail.update({
                            'father_cell': kw.get('father_cell', '').replace('-', ''),
                            'father_education': kw.get('father_education', ''),
                            'father_profession': kw.get('father_profession', ''),
                        })
                    if personal_detail.get('mother_status') == 'alive':
                        personal_detail.update({
                            'mother_cell': kw.get('mother_cell', '').replace('-', ''),
                            'mother_education': kw.get('mother_education', ''),
                            'mother_profession': kw.get('mother_profession', ''),
                        })

                    form_data.update(
                        {k: v for k, v in personal_detail.items() if v != '' and v != '0'})
                    application.write(form_data)
                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1

                    return json.dumps({'msg': 'Personal Details Updated', 'step_no': application.step_no,
                                       'application_state': application.state,
                                       'status': 'noerror', })

                if kw.get('step_name') == 'contact':
                    contact_detail = {
                        'email': kw.get('email', ''),
                        'phone': kw.get('phone', ''),
                        'mobile': kw.get('mobile', '').replace('-', ''),
                        'country_id': kw.get('country_id', ''),
                        'street': kw.get('street', ''),
                        'street2': kw.get('street2', ''),
                        'zip': kw.get('zip', ''),
                    }

                    if int(kw.get('country_id', 1)) == 177:
                        city = kw.get('city', '')
                    if int(kw.get('country_id', 1)) != 177:
                        city = kw.get('city_foreign', '')

                    contact_detail.update({'city': city})

                    if kw.get('is_same_address') == 'on':
                        contact_detail.update({
                            'is_same_address': True,
                            'per_country_id': int(kw.get('per_country_id')) if kw.get('per_country_id', '').isnumeric() else '',
                            'per_street': kw.get('street', ''),
                            'per_street2': kw.get('street2', ''),
                            'per_city': city,
                            'per_zip': kw.get('zip', ''),
                        })
                    if kw.get('is_same_address') != 'on':
                        contact_detail.update({
                            'per_country_id': int(kw.get('per_country_id')) if kw.get('per_country_id').isnumeric() else '',
                            'per_street': kw.get('per_street', ''),
                            'per_street2': kw.get('per_street2', ''),
                            'per_city': kw.get('per_city', ''),
                            'per_zip': kw.get('per_zip', ''),
                        })

                        if int(kw.get('per_country_id', 1)) == 177:
                            per_city = kw.get('per_city', '')
                        if int(kw.get('per_country_id', 1)) != 177:
                            per_city = kw.get('per_city_foreign', '')
                        contact_detail.update({'per_city': per_city})

                    form_data.update(
                        {k: v for k, v in contact_detail.items() if v != ''})
                    application.write(form_data)
                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1

                    return json.dumps({'msg': f'Contact Details Updated', 'step_no': application.step_no,
                                       'application_state': application.state,
                                       'status': 'noerror', })

                if kw.get('step_name') == 'guardian':
                    guardian_detail = {
                        'guardian_name': kw.get('guardian_name', ''),
                        'guardian_cell': kw.get('guardian_cell', '').replace('-', ''),
                        'guardian_cnic': kw.get('guardian_cnic', '').replace('-', ''),
                        'guardian_relation': kw.get('guardian_relation', ''),
                        'guardian_income': kw.get('guardian_income', ''),
                        'guardian_address': kw.get('guardian_address', ''),
                        'guardian_education': kw.get('guardian_education', ''),
                        'guardian_profession': kw.get('guardian_profession', ''),
                        'fee_payer_name': kw.get('fee_payer_name', ''),
                        'fee_payer_cnic': kw.get('fee_payer_cnic', '').replace('-', ''),
                    }

                    form_data.update(
                        {k: v for k, v in guardian_detail.items() if v != ''})
                    application.write(form_data)
                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1

                    return json.dumps({'msg': f'Guardian Details Updated', 'step_no': application.step_no,
                                       'application_state': application.state,
                                       'status': 'noerror', })

                if kw.get('step_name') == 'education':
                    alevel = False
                    # checking olevel degree if candidate added alevel
                    if application.applicant_academic_ids:
                        check_olevel = application.applicant_academic_ids.filtered(
                            lambda x: x.degree_name.code == 'olevel')
                        degree_name_id = int(kw.get('degree')) if kw.get('degree').isnumeric() else ''
                        if degree_name_id != '':
                            degree = request.env['odoocms.admission.degree'].sudo().search(
                                [('id', '=', degree_name_id) , ('company_id', '=', request.env.user.company_id.id) ])
                            if str(degree.name).lower().replace('-', '').replace(' ', '') == 'alevel':
                                alevel = True
                                if not check_olevel:
                                    return json.dumps({
                                        'msg': f'For A-level Secondary Education Must be in O-level',
                                        'status': 'error'
                                    })

                    # raise error if same level degree is added
                    education_checked_py =kw.get('update_education_check', '').isnumeric()
                    equivelant_degree =request.env['applicant.academic.detail'].sudo().search([('degree_level_id','=',int(kw.get('degree'))),('application_id','=',application.id)])
                    if equivelant_degree:
                        education_checked_py=1
                    if education_checked_py :

                        if int(kw.get('update_education_check')) != 1:
                            if int(kw.get('degree_level')) in [rec.degree_level_id.id for rec in application.applicant_academic_ids]:
                                return json.dumps({
                                    'msg': f'Equivalent Degree Already Added',
                                    'status': 'error'
                                })
                            degree_name_id = int(kw.get('degree')) if kw.get(
                                'degree').isnumeric() else ''
                            if degree_name_id != '':
                                degree_year = request.env['odoocms.admission.degree'].sudo().search(
                                    [('id', '=', degree_name_id), ('company_id', '=', request.env.user.company_id.id)]).year_age
                                if degree_year in [rec.degree_name.year_age for rec in application.applicant_academic_ids]:
                                    return json.dumps({
                                        'msg': f'Equivalent Degree Already Added',
                                        'status': 'error'
                                    })
                                if (degree_year > 13 and  degree_year < 18)and len(application.applicant_academic_ids) < 2:
                                    return json.dumps({
                                        'msg': f'Please add lower degrees first (HSSC)',
                                        'status': 'error'
                                    })
                                if (degree_year > 16 )and len(application.applicant_academic_ids) < 3:
                                    return json.dumps({
                                        'msg': f'Please add lower degrees first.(SSC,HSSC,16 Years)',
                                        'status': 'error'
                                    })
                                if (application.applicant_academic_ids.filtered(lambda x:x.result_status != 'complete')):
                                    return json.dumps({
                                        'msg': f'You cannot add further academic records.',
                                        'status': 'error'
                                    })
                        # if candidate update education the previous record deleted
                        if int(kw.get('update_education_check')) == 1:
                            education_checked = application.applicant_academic_ids.filtered(
                                lambda x: x.degree_level_id.id == int(kw.get('degree_level')))
                            if education_checked:
                                education_checked.sudo().unlink()
                            if application.state == 'draft':
                                application.step_no = 4
                                application.preference_ids.sudo().unlink()
                    # raiseerrror if secondry education is not added first
                    if not application.applicant_academic_ids:
                        degree_name_id = int(kw.get('degree')) if kw.get(
                            'degree').isnumeric() else ''
                        if degree_name_id != '':
                            degree_year = request.env['odoocms.admission.degree'].sudo().search([('id', '=', degree_name_id), ('company_id', '=', request.env.user.company_id.id)]).year_age
                            if degree_year > 10:
                                return json.dumps({
                                    'msg': f'Please First Add Secondary Education!',
                                    'status': 'error'
                                })

                    academic_data = {
                        'doc_state': 'no',
                        'degree_level_id': int(kw.get('degree_level', '')) if kw.get('degree_level', '').isnumeric() else '',
                        'degree_name': int(kw.get('degree', '')) if kw.get('degree', '').isnumeric() else '',
                        'group_specialization': int(kw.get('specialization', '')) if kw.get('specialization', '').isnumeric() else '',
                        'total_marks': kw.get('total_marks', ''),
                        'obt_marks': kw.get('obtained_marks', ''),
                        'total_cgpa': kw.get('total_cgpa', ''),
                        'obtained_cgpa': kw.get('obtained_cgpa', ''),
                        'percentage': kw.get('percentage', ''),
                        'roll_no': kw.get('roll_no', ''),
                        'application_id': application.id,
                        'board': kw.get('board', ''),
                        'year': kw.get('passing_year'),
                        'institute': kw.get('institute', ''),
                    }

                    if type(float(kw.get('obtained_cgpa', 0.0))) == float and float(kw.get('obtained_cgpa', 0.0)) >= 1:
                        academic_data.update({
                            'cgpa_check': True
                        })

                    if kw.get('result_status') or alevel:
                        academic_data.update({
                            'result_status': 'complete' if alevel else kw.get('result_status', '')
                        })

                    if type(kw.get('degree_file')) == FileStorage:
                        academic_data.update({
                            'attachment': base64.b64encode(kw.get('degree_file').read())
                        })

                    if type(kw.get('last_year_slip_file')) == FileStorage:
                        academic_data.update({
                            'last_year_slip': base64.b64encode(kw.get('last_year_slip_file').read())
                        })

                    form_data.update(
                        {k: v for k, v in academic_data.items() if v != ''})
                    academic_add = application.applicant_academic_ids.create(form_data)
                    request.env.cr.commit()

                    # updating subject_marks
                    if kw.get('subject_marks'):
                        subject_marks = json.loads(kw.get('subject_marks'))
                        if subject_marks != {}:
                            for k, v in subject_marks.items():
                                v = json.loads(v)
                                data_subject = {
                                    'name': int(k),
                                    'total_marks': int(v['subj_total_marks']),
                                    'obtained_marks': int(v['subj_marks']),
                                    'applicant_academic_id': academic_add.id,
                                }
                                academic_add.applicant_subject_id.create(data_subject)

                    # this dict will reponse back
                    context_academic_data = []
                    for rec in application.applicant_academic_ids:
                        context_academic_data.append({
                            'id': rec.id,
                            'degree_level': rec.degree_level_id.name or '',
                            'degree_level_id': rec.degree_level_id.id or '',
                            'degree_name': rec.degree_name.name or '',
                            'degree_name_id': rec.degree_name.id or '',
                            'specialization': rec.group_specialization.name or '',
                            'specialization_id': rec.group_specialization.id or '',
                            'passing_year': rec.year or '',
                            'subjects_marks': [{'name': rec2.name.name, 'id': rec2.name.id, 'total_marks': rec2.total_marks, 'obtained_marks': rec2.obtained_marks} for rec2 in rec.applicant_subject_id if rec.applicant_subject_id],
                            'state': rec.result_status or 'complete',
                            'total_marks': rec.total_marks or '',
                            'obtained_marks': rec.obt_marks or '',
                            'total_cgpa': rec.total_cgpa or '',
                            'obtained_cgpa': rec.obtained_cgpa or '',
                            'percentage': rec.percentage if rec.percentage > 0 else rec.obtained_cgpa,
                            'institue': rec.institute or '',
                            'board_roll_no': rec.roll_no or '',
                            'board': rec.board or '',
                            'sec_year_roll_no': rec.sec_year_roll_no or '',
                        })

                    education_criteria = 'no'
                    preferences_allowed = 0
                    applicant_education_year = max(
                        [int(year.year_age) for year in application.applicant_academic_ids.degree_name])

                    register_id = request.env['odoocms.admission.register'].sudo().search(
                        [('state', '=', 'application'), ('min_edu_year', '<=', applicant_education_year), ('company_id', '=', request.env.user.company_id.id)])
                    if register_id:
                        register_id_max = max(
                            [rec.min_edu_year for rec in register_id])
                        register_id = register_id.filtered(
                            lambda x: x.min_edu_year == register_id_max)[0]
                        application.register_id = register_id

                    preferences_allowed = ''
                    if application.register_id:
                        if (applicant_education_year >= application.register_id.min_edu_year or 0) and len(application.applicant_academic_ids) >= 2:
                            #application.step_no = application.step_no
                            if application.step_no <= int(kw.get('step_no')):
                                # application.step_no = application.step_no + 1
                                # application.step_no = application.step_no
                                application.step_no = application.step_no
                            education_criteria = 'yes'
                            preferences_allowed = int(
                                application.register_id.preferences_allowed)
                    if application.register_id:
                        preferences_allowed = application.register_id.preferences_allowed

                    return json.dumps({
                        'education_criteria': education_criteria,
                        'preferences_allowed': preferences_allowed,
                        'academic_data': context_academic_data,
                        'msg': 'Education Details Updated',
                        'step_no': application.step_no,
                        'application_state': application.state,
                        'status': 'noerror',

                    })

                if kw.get('step_name') == 'document':

                    cnic_file = kw.get('cnic_file')
                    cnic_back_file = kw.get('cnic_back_file')
                    domicile_file = kw.get('domicile_file')
                    passport_file = kw.get('passport')

                    document_data = {}
                    if application.applicant_type == 'national':
                        if type(cnic_file) == FileStorage:
                            document_data.update({
                                'cnic_front': base64.b64encode(cnic_file.read()) or '',
                            })
                        if type(cnic_back_file) == FileStorage:
                            document_data.update({
                                'cnic_back': base64.b64encode(cnic_back_file.read()) or '',
                            })
                        if type(domicile_file) == FileStorage:
                            document_data.update({
                                'domicile': base64.b64encode(domicile_file.read()) or '',
                            })
                    if application.applicant_type == 'international':
                        if type(passport_file) == FileStorage:
                            document_data.update({
                                'pass_port': base64.b64encode(passport_file.read()) or '',
                            })

                    form_data.update(
                        {k: v for k, v in document_data.items() if v != ''})

                    application.sudo().write(form_data)
                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1
                    return json.dumps({'msg': 'Documents Details Updated', 'step_no': application.step_no, 'application_state': application.state,'status': 'noerror', })

                if kw.get('step_name') == 'fee_voucher':
                    if kw.get('step_skip') and kw.get('step_skip') == 'yes':
                        if application.step_no <= int(kw.get('step_no')):
                            application.step_no = application.step_no + 1
                        return json.dumps({
                            'msg': 'Fee Voucher Details Updated',
                            'step_no': application.step_no,
                            'application_state': application.state,
                            'status': 'noerror',
                        })

                    # 'fee_voucher_state': 'upload',
                    voucher_image = kw.get('voucher_image')
                    voucher_data = {
                        'voucher_number': kw.get('voucher_number', ''),
                        'voucher_date': datetime.strptime(kw.get('voucher_date'), '%Y-%m-%d') or '',
                    }
                    if application.fee_voucher_state in ['no', 'download']:
                        voucher_data.update({
                            'fee_voucher_state': 'upload0',
                        })
                    if type(voucher_image) == FileStorage:
                        voucher_data.update({
                            'voucher_image': base64.b64encode(voucher_image.read()) or '',
                        })
                    form_data.update(
                        {k: v for k, v in voucher_data.items() if v != ''})
                    application.write(form_data)
                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1

                    return json.dumps({'msg': 'Fee Voucher Details Updated', 'step_no': application.step_no,
                                       'application_state': application.state,
                                       'status': 'noerror', })

                if kw.get('step_name') == 'program_transfer':
                    try:
                        if not kw.get('new_selected_program'):
                            if application.step_no <= int(kw.get('step_no')):
                                application.step_no = application.step_no + 1
                                return json.dumps({
                                    'msg': 'Skiped!',
                                    'step_no': application.step_no,
                                    'application_state': application.state,
                                    'status': 'noerror',
                                })

                        pending_request = request.env['odoocms.program.transfer.request'].sudo().search(
                            [('applicant_id', '=', application.id)])
                        if pending_request and pending_request.state == 'draft':
                            return json.dumps({
                                'msg': 'Already Pending Request!',
                                'step_no': application.step_no,
                                'application_state': application.state,
                                'status': 'noerror',
                            })

                        if not pending_request:
                            program_transfer_request = request.env['odoocms.program.transfer.request'].sudo().create({
                                'applicant_id': application.id,
                                'current_program': int(kw.get('new_selected_program')),
                                'previous_program': int(kw.get('current_program')),
                            })

                        if application.step_no <= int(kw.get('step_no')):
                            application.step_no = application.step_no + 1
                        return json.dumps({
                            'msg': 'Program Trasferred Request Created!',
                            'step_no': application.step_no,
                            'application_state': application.state,
                            'status': 'noerror',
                        })

                    except Exception as e:
                        return json.dumps({
                            'msg': f'{e}',
                            'step_no': application.step_no,
                            'application_state': application.state,
                            'status': 'error',
                        })

                if kw.get('step_name') == 'preference':
                    if kw.get('pre_test_marks', '').isnumeric() and kw.get('pre_test_id',False):
                        preTest = application.pre_test_id.search([('id','=',int(kw.get('pre_test_id')))])
                        if preTest and preTest.pre_test_total_marks < int(kw.get('pre_test_marks', '')):
                            return json.dumps({
                                    'msg': 'Invalid Pre Test Marks!',
                                    'status': 'error'
                                })
                    if application.career_id.code == 'PHD' and application.statement_purpose is False:
                        return json.dumps({
                                    'msg': 'Please First Add Statement OF Purpose!',
                                    'status': 'error'
                                })

                    if application.preference_ids:
                        application.preference_ids.unlink()
                    data_kw = kw.copy()
                    data_kw.pop('pre_test_marks')
                    data_kw.pop('step_name')
                    data_kw.pop('pre_test_attachment')
                    data_kw.pop('step_no')
                    data_kw.pop('pre_test_id')
                    # data_kw.pop('work_experience')
                    # data_kw.pop('phd_proposal')
                    data_kw.pop('test_center_id')
                    data_kw.pop('shift_choice')
                    for k, v in data_kw.items():
                        request.env['odoocms.application.preference'].sudo().create({
                            'preference': int(k),
                            'program_id': int(v),
                            'application_id': application.id,
                        })
                    preference = request.env['odoocms.application.preference'].sudo().search(
                        [('application_id', '=', application.id)])
                    # application.work_experience =kw.get('work_experience') or ''
                    # application.phd_proposal =kw.get('phd_proposal') or ''
                    if kw.get('shift_choice'):
                        application.shift = kw.get('shift_choice') or False
                    application.test_center_id =int(kw.get('test_center_id')) or 1

                    if kw.get('pre_test_marks', '').isnumeric() and kw.get('pre_test_marks', '') != 0:

                        if type(kw.get('pre_test_attachment')) == FileStorage:
                            application.pre_test_attachment = base64.b64encode(
                                kw.get('pre_test_attachment').read())

                        application.pre_test_marks = int(
                            kw.get('pre_test_marks'))
                        # application.phd_proposal =kw.get('phd_proposal')
                        # application.pre_test_id = preference.filtered(
                        #     lambda x: x.preference == 1).program_id.pre_test_ids.id

                        application.pre_test_id = int(kw.get('pre_test_id'))

                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1
                    return json.dumps({'msg': 'Preferences Details Updated', 'step_no': application.step_no,
                                       'application_state': application.state,
                                       'status': 'noerror', })

                if kw.get('step_name') == 'scholarship':
                    need_based_scholarship_applied = kw.get('need_based_scholarship_applied', 'False') == 'True'

                    need_base = {
                        'need_based_scholarship_applied': need_based_scholarship_applied,
                        'guardian_occupation': kw.get('guardian_occupation_scho', ''),
                        'guardian_monthly_income': kw.get('guardian_monthly_income', ''),
                        'family_member': kw.get('family_member_scho', ''),
                        'guardian_job_status': kw.get('job_status_scho', ''),
                        'residential_status': kw.get('residential_status', ''),
                    }

                    pgc = {
                        'previous_school_attend': kw.get('previous_school_attend_scho', ''),
                        'pgc_registration_no': kw.get('pgc_registration_number_scho', ''),
                    }
                    if kw.get('pgc_institute'):
                        pgc.update({'pgc_institute_id': int(kw.get('pgc_institute')) if kw.get('pgc_institute', '').isnumeric() else '',})
                    form_data.update(
                        {k: v for k, v in need_base.items() if v != '' and v != '0'})
                    form_data.update(
                        {k: v for k, v in pgc.items() if v != '' and v != '0'})

                    application.write(form_data)

                    if application.step_no <= int(kw.get('step_no')):
                        application.step_no = application.step_no + 1

                    return json.dumps({'msg': f'Scholarship Details Updated', 'step_no': application.step_no,
                                       'application_state': application.state,
                                       'status': 'noerror', })

        except Exception as e:

            return json.dumps({
                'msg': f'Error! {e}',
                'status': 'error',
                'step_no': application.step_no,
                'application_state': application.state,
            })

    @route('/test/slot/', type='http', auth='user', methods=['POST'], csrf=False)
    def test_slot(self, **kw):
        '''return the slot of test centere if available'''
        try:
            center_id = int(kw.get('test_center_id'))
            center_slot = request.env['odoocms.admission.test.center'].sudo().search(
                [('id', '=', center_id)]).time_ids.filtered(lambda x: x.active_time)
            slot_data = []
            for slot in center_slot:
                slot_data.append(
                    {'id': slot.id, 'name': str(slot.date) if slot.date else '' + ' ' + str(slot.time) if slot.time else ''})

            record = {
                'status': "noerror",
                'slots_data': slot_data}

            return json.dumps(record)
        except Exception as e:
            return json.dumps({
                'Error': '%s' % e
            })

    @route('/province/domicile/', type='http', auth='user', methods=['POST'], csrf=False)
    def province_domicile(self, **kw):
        """
        This Function is used for geting the domiciles of specific province(given through ajax request)

        Returns:
            list-of-dict: status and list of domiciles
        """
        try:
            province_id = int(kw.get('province_id'))

            domiciles = request.env['odoocms.domicile'].sudo().search(
                [('province_id', '=', province_id)])
            domicile_data = []
            for domicile in domiciles:
                domicile_data.append(
                    {'id': domicile.id, 'name': domicile.name})
            record = {
                'status_is': "noerror",
                'domiciles': domicile_data, }
            return json.dumps(record)
        except Exception as e:
            return json.dumps({
                'Error': '%s' % e
            })

    @route('/degree/level/degree/', type='http', auth='user', methods=['POST'], csrf=False)
    def degree_level_degree(self, **kw):

        try:

            degree_id = int(kw.get('degree_id'))
            application = request.env['odoocms.application'].sudo().search(
                [('application_no', '=', request.env.user.login)])
            check_olevel = application.applicant_academic_ids.filtered(
                lambda x: x.degree_name.code == 'olevel')

            degrees = request.env['odoocms.admission.education'].sudo().search([('id', '=', degree_id), ('company_id', '=', request.env.user.company_id.id)]).degree_ids
            degrees = degrees.sorted(lambda d: d.name.lower())

            # degree_get = request.env['odoocms.admission.degree'].sudo().search([
            #     ('id', '=', degree_id), ('company_id', '=', request.env.user.company_id)])

            degree_data = []
            for degree in degrees:
                if degree_id != '':
                    if str(degree.name).lower().replace('-', '').replace(' ', '') == 'alevel':
                        if check_olevel:
                            degree_data.append(
                                {'id': degree.id, 'code': degree.code, 'name': degree.name})
                        else:
                            degree_data.append(
                                {'id': degree.id, 'code': degree.code, 'name': degree.name})
                            # pass
                    elif str(degree.name).lower().replace('-', '').replace(' ', '') != 'alevel':
                        degree_data.append(
                            {'id': degree.id, 'code': degree.code, 'name': degree.name})

            record = {
                'status': "noerror",
                'degrees': degree_data, }
            return json.dumps(record)
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'Error': '%s' % e
            })

    @route('/degree/specializations/subjects/', type='http', auth='user', methods=['POST'], csrf=False)
    def degree_specializations_subject(self, **kw):

        try:
            specialization_id = int(kw.get('specialization_id'))
            specilizations_subject = request.env['applicant.academic.group'].sudo().search(
                [('id', '=', specialization_id),('active','=',True),('company_id', '=', request.env.user.company_id.id)]).academic_subject_ids
            specilizations_subject = specilizations_subject.sorted(lambda s: s.name.lower())
            specialization_subject_data = []
            for subject in specilizations_subject:
                specialization_subject_data.append(
                    {'id': subject.id, 'name': subject.name})
            record = {
                'status': "noerror",
                'specializations_subject': specialization_subject_data, }
            return json.dumps(record)
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'Error': '%s' % e,
            })

    @route('/descipline/program/', type='http', auth='user', methods=['POST'], csrf=False)
    def descipline_program(self, **kw):
        try:
            descipline_code = kw.get('descipline_id')
            programs = request.env['odoocms.discipline'].sudo().search(
                [('code', '=', descipline_code), ]).program_ids
            programs = programs.sorted(lambda p: p.name.lower())
            program_data = []
            for program in programs:
                program_data.append({
                    'code': program.code,
                    'program': program.name,
                })
            record = {
                'status_is': 'noerror',
                'program': program_data,
            }
            return json.dumps(record)
        except Exception as e:
            return json.dumps({
                'Error': '%s' % e
            })

    @route('/education/update/', type='http', auth='user', methods=['POST'], csrf=False)
    def update_education(self, **kw):
        try:
            if request.httprequest.method == 'POST':
                application = request.env['odoocms.application'].sudo().search(
                    [('application_no', '=', request.env.user.login)], limit=1)
                academic_education = {k: v for k, v in kw.items() if v != ''}
                academic_education['application_id'] = int(
                    kw.get('application_id'))
                request.env['applicant.academic.detail'].sudo().create(
                    academic_education)
                return json.dumps({
                    'is_success': 'yes'
                })
        except Exception as e:
            return json.dumps({
                'is_success': 'no',
                'exception': f'Error! {e}'
            })

    @route('/profile/image/update/', type='http', auth='user', methods=['POST'], csrf=False)
    def profile_image_update(self, **kw):
        try:
            application = request.env['odoocms.application'].sudo().search(
                [('application_no', '=', request.env.user.login)], limit=1)
            if request.httprequest.method == 'POST':
                image = kw.get('image_file')
                application.write({
                    'image': base64.b64encode(image.read()),
                })
                return json.dumps({
                    'msg': f'Profle Picture Updated!!',
                    'status': 'noerror',
                })
        except Exception as e:
            return json.dumps({
                'msg': f'Error!',
                'status': 'error',
                'step_no': application.step_no,
                'application_state': application.state,
            })
            
    @route('/statement/purpose/update/', type='http', auth='user', methods=['POST'], csrf=False)
    def statement_of_purpose(self, **kw):
        try:
            application = request.env['odoocms.application'].sudo().search(
                [('application_no', '=', request.env.user.login)], limit=1)
            if request.httprequest.method == 'POST':
                statement_purpose = kw.get('statement_purpose')
                application.write({
                    'statement_purpose': base64.b64encode(statement_purpose.read()),
                })
                return json.dumps({
                    'msg': f'Statement Of Purpose Uploaded!!',
                    'status': 'noerror',
                })
        except Exception as e:
            return json.dumps({
                'msg': f'Error!',
                'status': 'error',
                'step_no': application.step_no,
                'application_state': application.state,
            })

    @route('/apply/application/', csrf=False, type="http", methods=['GET'], auth="user")
    def apply_application(self, **kw):
        current_user = request.env.user
        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', current_user.login)])
        check_matric = application.applicant_academic_ids.filtered(
            lambda x: x.degree_name.year_age == 10)
        check_fsc = application.applicant_academic_ids.filtered(
            lambda x: x.degree_name.year_age == 12)
        check_preference = application.preference_ids

        if not check_matric:
            return json.dumps({
                'msg': f'Secondary School Education Is Mandatory Please Add!',
                'step_no': application.step_no,
                'application_state': application.state,
                'status': 'error',

            })

        if not check_preference:
            return json.dumps({
                'msg': f'Please Add Preference',
                'step_no': application.step_no,
                'application_state': application.state,
                'status': 'error',

            })
        if not check_fsc:
            return json.dumps({
                'msg': f'Higher Education Is Mandatory Please Add!',
                'step_no': application.step_no,
                'application_state': application.state,
                'status': 'error',
            })
        # app_id.action_create_prospectus_invoice()
        #
        # rec.fee_receipt_no = app_id.voucher_number
        # rec.amount = app_id.amount
        # user = self.env['res.users'].sudo().search(
        #     [('login', '=', app_id.application_no)])
        if not application.fee_voucher_state == 'verify':
            application.sudo().action_create_prospectus_invoice()
        elif application.fee_voucher_state == 'verify':
            application.sudo().assign_test_date()
        application.voucher_number = application.prospectus_inv_id and application.prospectus_inv_id.barcode or ''
        application.amount = application.prospectus_inv_id.amount_total
        if application.state == 'draft':
            application.state = 'submit'
            application.application_submit_date = datetime.now()
            if application.program_migration:
                application.migration_state = 'draft'
            # if application.step_no <= int(kw.get('step_no')):
            application.step_no = application.step_no + 1
            # template = request.env.ref('odoocms_admission.mail_template_admission_form_submit').sudo()
            # pass_val = {

            #     'company_name': request.env.company.name,
            #     'company_website': request.env.company.website,
            #     'company_email': request.env.company.admission_mail,
            #     'company_phone': request.env.company.admission_phone,
            #     'processing_fee': application.amount,
            #     'email':application.email
            # }
            # mail_server_id = request.env['ir.mail_server'].sudo().search([('company_id', '=', application.company_id.id)])
            # email_from = application.company_id.admission_mail
            # template.with_context(pass_val, mail_server_id=mail_server_id.id, email_from=email_from).send_mail(current_user.id, force_send=True)

            return json.dumps({
                'msg': f'Application Submitted!',
                'step_no': application.step_no,
                'application_state': application.state,
                'status': 'noerror',

            })
        else:
            return json.dumps({
                'msg': f'Application Already Submitted!',
                'status': 'error',
                'step_no': application.step_no,
                'application_state': application.state,

            })

    @route('/delete/education/', csrf=False, type="http", methods=['POST', 'GET'], auth="user")
    def delete_education(self, **kw):
        current_user = request.env.user
        application_id = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', current_user.login)], limit=1)

        edu_id = kw.get('edu_id')
        application_id.applicant_academic_ids.sudo().search(
            [('id', '=', edu_id)]).unlink()
        preferences_allowed = 0
        # pdb.set_trace()
        # if len(application_id.applicant_academic_ids) > 0:
        #     applicant_education_year = max(
        #         [int(year.year_age) for year in application_id.applicant_academic_ids.degree_name])
        #     register_id = request.env['odoocms.admission.register'].sudo().search(
        #         [('state', '=', 'application'), ('min_edu_year', '<=', applicant_education_year)])
        
        #     if register_id:
        #         register_id_max = max(
        #             [rec.min_edu_year for rec in register_id])
        #         register_id = register_id.filtered(
        #             lambda x: x.min_edu_year == register_id_max)
        #         application_id.register_id = register_id
        #         preferences_allowed = int(
        #             application_id.register_id.preferences_allowed)
        application_id.preference_ids.unlink()
        
        # pdb.set_trace()
        # template = request.env['odoocms.application.steps'].sudo().search(
        #     [('template', '=', 'Educations')], limit=1)

        application_id.step_no = 4

        return json.dumps({
            'status': 'noerror',
            'preferences_allowed': preferences_allowed,
            'msg': f'Education Removed!',

        })

    @route('/prepare/admission/invoice/', csrf=False, type="http", methods=['GET'], auth="user")
    def prepare_admission_invoice(self, **kw):
        current_user = request.env.user
        application_id = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', current_user.login)])

        disciplines = 0
        discipline = 0
        prefs = request.env['odoocms.application.preference'].sudo().search(
            [('application_id', '=', application_id.id)])

        first_preference = prefs.filtered(lambda x: x.preference == 1)
        seat_avail_program = first_preference.program_id
        for program in seat_avail_program:
            if program.signin_end_date:
                if program.signin_end_date <= date.today():
                    data = json.dumps({
                        'error': 'unavailable',
                    })

                    return data

        program_preferences_ordered = http.request.env['odoocms.application.preference'].sudo().search(
            [('application_id', '=', application_id.id)], order='preference asc')
        selected_discipline = []
        for program in program_preferences_ordered:
            selected_discipline += str(program.discipline_id.id)
        selected_discipline = list(dict.fromkeys(selected_discipline))
        for i in range(0, len(selected_discipline)):
            selected_discipline[i] = (selected_discipline[i])
        for pref in prefs:
            if pref.discipline_id.id != discipline:
                discipline = pref.discipline_id.id
                disciplines = disciplines + 1

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

        account_payable2 = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.account_payable2')
        account_title2 = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.account_title2')
        account_no2 = http.request.env['ir.config_parameter'].sudo(
        ).get_param('odoocms_admission_portal.account_no2')

        total_fee = 0
        # for rec in selected_discipline:
        if application_id.degree.code == 'DAECIVIL':
            choices = program_preferences_ordered.filtered(
                lambda x: x.discipline_id.code == 'TECH' or x.discipline_id.code == 'E')
            for ch in choices:
                if total_fee < 4000:
                    total_fee += int(float(registration_fee))
        else:
            total_fee = int(float(registration_fee))
        # if disciplines > 1:
        #     total_fee += int(float(additional_fee))

        docargs = {
            'is_dual_nationality': application_id.is_dual_nationality or application_id.overseas or application_id.nationality.id != 177,
            'student_name': application_id.first_name + ' ' + application_id.last_name,
            'father_name': application_id.father_name,
            'cnic': application_id.cnic,
            'account_payable': account_payable or "",
            'account_payable2': account_payable2 or "",
            'registration_fee': registration_fee or False,
            'additional_fee': additional_fee or False,
            'fee_voucher_state': application_id.fee_voucher_state or False,
            'total_fee': str(total_fee),
            'total_fee_word': application_id.amount_to_text(float(total_fee)),
            'registration_fee_international': registration_fee_international or False,
            'total_fee_word_international': application_id.amount_to_text(float(registration_fee_international)),
            'account_title': account_title or " ",
            'account_title2': account_title2 or " ",
            'account_no': account_no or "",
            'account_no2': account_no2 or "",
            'disciplines': disciplines,
            'today': date.today().strftime('%Y/%d/%m') or False,
        }
        if application_id.fee_voucher_state in ('no', 'download'):
            application_id.fee_voucher_state = 'download'
        docargs.update({'fee_voucher_state': 'download'})

        data = json.dumps(docargs)
        return data

    @route('/prepare/preference/', csrf=False, type="http", methods=['GET'], auth="user")
    def prepare_preference(self, **kw):
        try:
            # pdb.set_trace()
            application = request.env['odoocms.application'].sudo().search([('application_no', '=', request.env.user.login)], limit=1)
            register_id = application.register_id
            dob_min = register_id.dob_min
            dob_max = register_id.dob_max
            applicant_dob = application.date_of_birth
            if dob_min and dob_max and applicant_dob and (applicant_dob < dob_max or applicant_dob > dob_min):
                return json.dumps({
                'status': 'error',
                'error': f'age_error',
            })
            academic_info = application.applicant_academic_ids
            specialization_edu = academic_info.filtered(
                lambda x: x.group_specialization)
            non_specialization_edu = academic_info.filtered(
                lambda x: not x.group_specialization)
            general_offered_program = request.env['odoocms.degree'].sudo().search(
                [('career_id', '=', application.register_id.career_id.id)])

            offered_porgram = []
            for rec in specialization_edu:
                if not rec.cgpa_check:
                    offering = general_offered_program.filtered(lambda x: x.degree_id.id == rec.degree_name.id).filtered(
                        lambda x: x.specialization_id.id == rec.group_specialization.id).filtered(lambda x: x.eligibilty_percentage <= rec.percentage and x.eligibilty_per >= rec.percentage)
                if rec.cgpa_check:
                    offering = general_offered_program.filtered(lambda x: x.degree_id.id == rec.degree_name.id).filtered(
                        lambda x: x.specialization_id.id == rec.group_specialization.id).filtered(lambda x: x.eligibilty_cgpa <= rec.obtained_cgpa and x.eligibilty_cgp >= rec.obtained_cgpa)
                if offering:
                    offered_porgram.append(offering.id)

            if non_specialization_edu:
                for rec in non_specialization_edu:
                    if not rec.cgpa_check:
                        offering2 = general_offered_program.filtered(lambda x: x.degree_id.id == rec.degree_name.id).filtered(
                            lambda x: x.eligibilty_percentage <= rec.percentage and x.eligibilty_per >= rec.percentage)
                    if rec.cgpa_check:
                        offering2 = general_offered_program.filtered(lambda x: x.degree_id.id == rec.degree_name.id).filtered(
                            lambda x: x.eligibilty_cgpa <= rec.obtained_cgpa).filtered(lambda x: x.eligibilty_cgp >= rec.obtained_cgpa)
                    if offering2:
                        offered_porgram.append(offering2.id)

            offered = request.env['odoocms.degree'].sudo().browse(
                offered_porgram)
            register_offered_program = application.register_id.program_ids.ids
            context = {}
            pre_test_context = {}
            # pre_test_list = {}
            # checking signin and signup date for eligibile program
            for rec in offered:
                for program in rec.program_ids:
                    if program.id and program.offering and program.id in register_offered_program:
                        pre_test_list = {}
                        if program.signup_end_date:
                            if program.signup_end_date >= date.today():

                                if program.signin_end_date:
                                    if program.signin_end_date <= date.today():
                                        context.update({
                                            program.id: program.name
                                        })
                                        if len(program.pre_test_ids) > 0:
                                            pre_test_context.update({
                                                program.id: {
                                                    }
                                            })
                                            for rec in program.pre_test_ids:
                                                pre_test_list.update({
                                                        rec.id: rec.name
                                                })
                                            pre_test_context.update({
                                                program.id: pre_test_list
                                            })
                                if not program.signin_end_date:
                                    context.update({
                                        program.id: program.name
                                    })
                                    if len(program.pre_test_ids) > 0:
                                        pre_test_context.update({
                                            program.id: {
                                            }
                                        })
                                        for rec in program.pre_test_ids:
                                            pre_test_list.update({
                                                rec.id: rec.name
                                            })
                                        pre_test_context.update({
                                            program.id: pre_test_list
                                        })


                                    #
                                    # pre_test_context.update({
                                    #     program.id: {
                                    #         program.pre_test.id: program.pre_test.name} if program.pre_test else False
                                    # })

                        if not program.signup_end_date:
                            if program.signin_end_date:
                                if program.signin_end_date <= date.today():
                                    context.update({
                                        program.id: program.name
                                    })
                                    if len(program.pre_test_ids) > 0:
                                        pre_test_context.update({
                                            program.id: {
                                            }
                                        })
                                        for rec in program.pre_test_ids:
                                            pre_test_list.update({
                                                rec.id: rec.name
                                            })
                                        pre_test_context.update({
                                            program.id: pre_test_list
                                        })

                                    # pre_test_context.update({
                                    #     program.id: {
                                    #         program.pre_test.id: program.pre_test.name} if program.pre_test else False
                                    # })
                            if not program.signin_end_date:
                                context.update({
                                    program.id: program.name
                                })
                                if len(program.pre_test_ids) > 0:
                                    pre_test_context.update({
                                        program.id: {
                                        }
                                    })
                                    for rec in program.pre_test_ids:
                                        pre_test_list.update({
                                            rec.id: rec.name
                                        })
                                    pre_test_context.update({
                                        program.id: pre_test_list
                                    })
                                # pre_test_context.update({
                                #     program.id: {
                                #         program.pre_test.id: program.pre_test.name} if program.pre_test else False
                                # })

            return json.dumps({
                'pretest': pre_test_context,
                'program_offered': context,
                'status': 'noerror'
            })
        except Exception as e:
            return json.dumps({
                'status': 'error',
                'error': f'{e}'
            })

    @route('/download/admit/interview', csrf=False, type="http", methods=['GET'], auth="user")
    def download_admit_card_interview(self, **kw):
        report_type = "pdf"

        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)], limit=1)
        admit_card = request.env['applicant.entry.test'].sudo().search(
            [('student_id', "=", application.id), ('active', '=', True), ('paper_status', '=', False),('paper_conducted','=',False),
             ('slot_type', '=', 'interview')])
        # if not admit_card.slot_type:
        #     report_ref=
        if admit_card:
            report_ref = 'odoocms_admission_ucp.action_student_interview_admit_card'

        # if admit_card.slot_type == 'test' or not admit_card.slot_type:
            # report_ref = 'odoocms_admission_ucp.action_student_admit_card'
        # if admit_card.slot_type == 'interview':

        # report_ref = 'odoocms_admission_portal.action_student_admit_card_download'
        return self._show_report_admit(model=admit_card, report_type=report_type, report_ref=report_ref, download="download")

    @route('/download/admit/test', csrf=False, type="http", methods=['GET'], auth="user")
    def download_admit_card_test(self, **kw):
        report_type = "pdf"
        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)], limit=1)

        admit_card = request.env['applicant.entry.test'].sudo().search(
            [('student_id', "=", application.id), ('active', '=', True),('paper_status', 'not in', ('missed','passed','failed')),('paper_conducted','=',False),
             ('slot_type', '=', 'test')])
        if admit_card:
            # if not admit_card.slot_type:
            #     report_ref=
            # if kw.get('test') == 'test':
            report_ref = 'odoocms_admission_ucp.action_student_admit_card'
            # if kw.get('test') == 'interview':
            #     report_ref = 'odoocms_admission_ucp.action_student_interview_admit_card'

            # report_ref = 'odoocms_admission_portal.action_student_admit_card_download'
            return self._show_report_admit(model=admit_card, report_type=report_type, report_ref=report_ref, download="download")
        # return json.dumps({
        #     'status':'ok',
        #     'msg':'No Admit Card'
        # })

    @route('/download/admission/form', csrf=False, type="http", methods=['GET'], auth="user")
    def download_admission_form(self, **kw):
        report_type = "pdf"
        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)], limit=1)

        if application:
            # if not admit_card.slot_type:
            #     report_ref=
            # if kw.get('test') == 'test':
            report_ref = 'odoocms_admission.action_application_final_report'
            # if kw.get('test') == 'interview':
            #     report_ref = 'odoocms_admission_ucp.action_student_interview_admit_card'

            # report_ref = 'odoocms_admission_portal.action_student_admit_card_download'
            return self._show_report_admit(model=application, report_type=report_type, report_ref=report_ref, download="download")
        # return json.dumps({
        #     'status':'ok',
        #     'msg':'No Admit Card'
        # })

    @route('/get/merit/', csrf=False, type="http", methods=['GET'], auth="user")
    def get_merit(self, **kw):
        try:
            application = request.env['odoocms.application'].sudo().search(
                [('application_no', '=', request.env.user.login)], limit=1)
            merit_current_user = request.env['odoocms.merit.register.line'].sudo().search(
                [('applicant_id', '=', application.id)])
            return json.dumps({
                'status': 'noerror',
                'merit_no': merit_current_user.merit_no,
                'score': merit_current_user.score,
                'aggregate': merit_current_user.aggregate,
            })
        except Exception as e:
            return json.dumps({
                'error': f'{e}',
                'status': 'noerror',
            })

    @http.route(['/file/download/<int:id>/<model>'], type='http', auth="user", website=True, csrf=False)
    def download_attachment_file(self, model=None, id=0, **kw):

        env = http.request.env
        record = env[str(model)].sudo().browse(int(id))

        status, content, filename, mimetype, filehash = env['ir.http'].sudo(
        )._binary_record_content(record, field=str('attachment'))
        status, headers, content = env['ir.http'].sudo()._binary_set_headers(status, content, filename, mimetype,
                                                                             unique=False, filehash=filehash,
                                                                             download=True)
        if status != 200:
            return request.env['ir.http'].sudo()._response_by_status(status, headers, content)
        else:
            content_base64 = base64.b64decode(content)
            headers.append(('Content-Length', len(content_base64)))
            response = request.make_response(content_base64, headers)
        return response

    # download invoice ucp
    @route('/download/offer/letter/', csrf=False, type="http", methods=['POST', 'GET'], auth="user", website=True)
    def download_offer_letter(self, **kw):
        report_type = "pdf"
        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', request.env.user.login)], limit=1)
        offer_letter = request.env['ucp.offer.letter'].sudo().search(
            [('applicant_id', '=', application.id)], limit=1)
        report_ref = 'odoocms_admission_ucp.admission_offer_letter'
        return self._show_report_admit(model=offer_letter, report_type=report_type, report_ref=report_ref, download="download")
