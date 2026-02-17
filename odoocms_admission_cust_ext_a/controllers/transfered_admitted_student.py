from odoo.http import route, request, Controller
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import json
import logging


_logger = logging.getLogger(__name__)


class TransferAdmittedStudent(Controller):
    @route('/transfer/admitted_student', type='json', auth='user', csrf=False)
    def transfer_admitted_student(self, **kw):
        try:
            sync_ref=''
            if request.httprequest.method == 'POST':
                std_d=json.loads(kw.get('student_date'))
                transferred_student= json.loads(kw.get('student_date'))
                if transferred_student:
                    t_s_code =transferred_student.get('code')
                    t_s_program =transferred_student.get('transferred_program_id')
                    try:
                        student_adm_profile = request.env['odoocms.student'].sudo().search([('code', '=',t_s_code)])
                        student_adm_program = request.env['odoocms.program'].sudo().search([('server_id', '=',t_s_program)])
                        admission_no =request.env['odoocms.student'].sudo().search([('admission_no', '=','t-'+student_adm_profile.admission_no)])
                        if not admission_no:
                            applicant = request.env['odoocms.application'].sudo().search([('application_no', '=',student_adm_profile.admission_no)])
                            batch_domain = [('program_id', '=', student_adm_program.id), ('session_id', '=', applicant.register_id.academic_session_id.id),
                                            ('career_id', '=', applicant.register_id.career_id.id)]
                            program_batch = request.env['odoocms.batch'].search(batch_domain)
                            if program_batch:
                                study_scheme_id = program_batch.study_scheme_id
                                if not student_adm_profile and student_adm_program:
                                    study_scheme_id =request.env['odoocms.study.scheme'].search([('session_id','=',student_adm_profile.session_id.id),('program_id','=',student_adm_program.id)])
                                semester = request.env['odoocms.semester'].search([('number', '=', 1)], limit=1)
                                user = student_adm_profile.user_id
                                blood_group = student_adm_profile.blood_group
                                if  blood_group == 'N':
                                    blood_group = False

                                values = {
                                    'state': 'enroll',
                                    'name': student_adm_profile.name,
                                    'first_name': student_adm_profile.first_name,
                                    'last_name': student_adm_profile.last_name,
                                    'father_name': student_adm_profile.father_name,

                                    'cnic': student_adm_profile.cnic,
                                    'gender': student_adm_profile.gender,
                                    'date_of_birth': student_adm_profile.date_of_birth,
                                    'religion_id': student_adm_profile.religion_id.id,
                                    'nationality': student_adm_profile.nationality.id,
                                    'email': student_adm_profile.email,
                                    'mobile': student_adm_profile.mobile,
                                    'phone': student_adm_profile.phone,
                                    'image_1920': student_adm_profile.image_1920,
                                    'street': student_adm_profile.street,
                                    'street2': student_adm_profile.street2,
                                    'city': student_adm_profile.city,
                                    'zip': student_adm_profile.zip,
                                    'state_id': student_adm_profile.state_id.id,
                                    'country_id': student_adm_profile.country_id.id,

                                    'is_same_address': student_adm_profile.is_same_address,
                                    'per_street': student_adm_profile.per_street,
                                    'per_street2': student_adm_profile.per_street2,
                                    'per_city': student_adm_profile.per_city,
                                    'per_zip': student_adm_profile.per_zip,
                                    'per_state_id': student_adm_profile.per_state_id.id,
                                    'per_country_id': student_adm_profile.per_country_id.id,

                                    'career_id': student_adm_profile.career_id.id,
                                    'session_id': student_adm_profile.session_id.id,
                                    'company_id': student_adm_profile.company_id.id,
                                    'domicile_id': student_adm_profile.domicile_id and student_adm_profile.domicile_id.id or False,
                                    'blood_group': blood_group,
                                    'user_id': student_adm_profile.user_id and student_adm_profile.user_id.id or False,

                                    'mother_name': student_adm_profile.mother_name,
                                    'father_cell': student_adm_profile.father_cell,
                                    'mother_cell': student_adm_profile.mother_cell,
                                    'guardian_name': student_adm_profile.guardian_name,
                                    'guardian_mobile': student_adm_profile.guardian_mobile,
                                    'notification_email': student_adm_profile.email,
                                    'sms_mobile': student_adm_profile.mobile,
                                
                                    'term_id': student_adm_profile.term_id.id or False,
                                    'semester_id': semester.id,
                                    'batch_id': program_batch.id or False,
                                    'program_id': student_adm_program.id or False,
                                    'study_scheme_id': study_scheme_id.id or False,
                                    'admission_no':'t-'+student_adm_profile.admission_no
                                }
                                if user:
                                    values['partner_id'] = user.partner_id.id
                                if not student_adm_profile.is_same_address:
                                    pass
                                else:
                                    values.update({
                                        'per_street': student_adm_profile.street,
                                        'per_street2': student_adm_profile.street2,
                                        'per_city': student_adm_profile.city,
                                        'per_zip': student_adm_profile.zip,
                                        'per_state_id': student_adm_profile.state_id.id,
                                        'per_country_id': student_adm_profile.country_id.id,
                                    })
                                # Determine which program to use for registration number generation
                                # ONLY manual assignment - NO auto-detection
                                # Use program's parent_program_id if set (manually assigned in Admission Register)
                                reg_program = student_adm_program  # Default: use program's own sequence_number
                                
                                if student_adm_program.parent_program_id:
                                    reg_program = student_adm_program.parent_program_id
                                # No parent_program_id set - use program's own sequence_number
                                
                                program_sequence_number = reg_program.sequence_number
                                student = request.env['odoocms.student'].sudo().create(values)
                                last_student = request.env['odoocms.student'].search([('program_id', '=', student.program_id.id), ('id', '!=', student.id)], order='id desc', limit=1)
                                
                                # Generate registration number using reg_program (parent if child, self if parent/standalone)
                                if student.company_id.code and student.company_id.code.lower() in ('cust', 'ubas'):
                                    reg_no = reg_program.short_code + student_adm_profile.term_id.short_code + str(program_sequence_number).zfill(3)
                                elif student.company_id.code and student.company_id.code.lower() == 'maju':
                                    reg_no = student_adm_profile.term_id.short_code +"-"+ reg_program.short_code +"-"+ str(program_sequence_number).zfill(4)
                                else:
                                    reg_no = 'L1' + student_adm_profile.term_id.short_code + reg_program.short_code + str(program_sequence_number).zfill(4)
                                
                                if student and applicant:
                                    applicant.write({'student_id': student.id})
                                    applicant.admission_inv_id.write({'student_id': student.id})
                                    student.write({'code': reg_no, 'id_number': reg_no})
                                    reg_program.sequence_number = program_sequence_number + 1
                                # duplicate_student = student_adm_profile.copy(values)
                                student_adm_profile.state ='cancel'
                                sync_ref=student.code
                        else:
                            return json.dumps({
                            'status':'yes',
                            'sync_ref':admission_no.code,
                            'error': ''
                            })
                      
                    except Exception as e:
                       request.env.cr.rollback()
                       return json.dumps({
                           'status':'no',
                            'sync_ref':'',
                           'error': f'{e.args[0]}'})

                    return json.dumps({
                        'status':'yes',
                        'sync_ref':sync_ref,
                        'error': ''
                        })
                else:
                        return json.dumps({
                        'status':'no',
                         'sync_ref':'',
                        'error': 'No student found in Admission'})
        except Exception as e:
            request.env.cr.rollback()
            return json.dumps({
                'status':'no',
                 'sync_ref':'',
                'error': f'{e.args[0]}'})
