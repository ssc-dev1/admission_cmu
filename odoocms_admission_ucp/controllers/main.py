from odoo.http import route, request, Controller
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import json
import logging


_logger = logging.getLogger(__name__)


class Cbt(Controller):

    @route('/entry/test/', type='json', auth='user', csrf=False)
    def entry_test(self, **kw):
        try:
            company_id = kw.get('company_id')
            schedule_details = request.env['odoocms.entry.schedule.details'].sudo().search([('status','=','full')])
            entry_test = []
            if schedule_details:
                # entry_test = request.env['applicant.entry.test'].sudo().search([('entry_test_schedule_details_id','in',schedule_details.ids),('state', '=', True),('paper_conducted','=',False)])
                entry_test = request.env['applicant.entry.test'].sudo().search([('entry_test_schedule_details_id', 'in', schedule_details.ids), ('state', '=', True), ('paper_conducted', '=', False), ('company_id', '=', company_id),('cbt_sync','=',False)])
            data = []
            for rec in entry_test:
                first_name = rec.student_id.first_name or ''
                last_name = rec.student_id.last_name or ''
                middle_name = rec.student_id.middle_name if rec.student_id.middle_name else ''
                name = f"{first_name} {middle_name} {last_name}"
                if not rec.cbt_password:
                    return json.dumps([{'error': 'Password not set. App: ' + rec.student_id.application_no}])

                program_id = {'code': rec.student_id.preference_ids.filtered(
                    lambda x: x.preference == 1).program_id.code or False,
                              'name': rec.student_id.preference_ids.filtered(
                                  lambda x: x.preference == 1).program_id.name or False} or False,
                if not program_id:
                    return json.dumps({'error': 'Program not set properly. App: ' + rec.student_id.application_no})
                test_date = datetime.strftime(rec.date, '%Y-%m-%d') if rec.date else False
                if not test_date:
                    return json.dumps([{'error': 'Test Date not set properly. App: ' + rec.student_id.application_no}])
                slot = {'time_from': rec.slots.time_from, 'time_to': rec.slots.time_to,
                        'name': rec.slots.name} or False,
                if not slot:
                    return json.dumps([{'error': 'Test Slot not set properly. App: ' + rec.student_id.application_no}])

                record = {
                    'name': name,
                    'application_no': rec.student_id.application_no,
                    'password': rec.cbt_password,
                    'program_id': json.dumps({'code': rec.student_id.preference_ids.filtered(lambda x : x.preference == 1 ).program_id.code or False,'name': rec.student_id.preference_ids.filtered(lambda x : x.preference == 1 ).program_id.name or False  }) or False,
                    'cid':rec.id,
                    'slot': json.dumps(
                        {'time_from': rec.slots.time_from, 'time_to': rec.slots.time_to,'name': rec.slots.name}) or False,
                    'room': rec.room.name if rec.room else False,
                    'date': datetime.strftime(rec.date, '%Y-%m-%d') if rec.date else False,
                    'master_id': rec.master_id if rec.master_id else False,
                }

                data.append(record)
                rec.cbt_sync = True
            return json.dumps(data)
        except Exception as e:
            return json.dumps({'error': f'{e}'})
    

    @route('/result/import/', type='json', auth='user', csrf=False)
    def import_result(self, **kw):
        try:
            error_sync_ref=[]
            if request.httprequest.method == 'POST':
                _logger.info('*********************************TOtal %s', len(json.loads(kw.get('result_all'))))
                for result in json.loads(kw.get('result_all')):
                    try:
                        application_no = list(result.keys())[0]
                        application_cid = list(result.values())[1]
                        test_date =list(result.values())[2]
                        subject_dict = list(result.values())[0]
    
                        application_id = request.env['odoocms.application'].sudo().search(
                            [('application_no', '=', application_no)])
                        if len(application_id) > 0:
                            application_id = application_id[0]
                        else:
                            if application_no not in error_sync_ref:
                                error_sync_ref.append(application_no)
                            continue
                       
                        #student_entry_test = request.env['applicant.entry.test'].sudo().search([('id', '=', application_cid)])
                        student_entry_test = request.env['applicant.entry.test'].sudo().search([('student_id', '=', application_id.id),('date','=',test_date)])
                        if len(student_entry_test) > 0:
                            student_entry_test = student_entry_test[0]
                        else:
                            if application_no not in error_sync_ref:
                                error_sync_ref.append(application_no)
                            continue

                        _logger.info('****************** Student Entry Test %s', student_entry_test)

                        # if student_entry_test.applicant_line_ids:
                        #     student_entry_test.applicant_line_ids.sudo().unlink()
                        if student_entry_test:
                            student_entry_test.paper_conducted = True
                            for k, v in subject_dict.items():
                                subject_name = k
                                subject_score = v['subject_score']
                                subject_total_score = v['subject_total_score']
                                student_entry_test.applicant_line_ids.create({
                                    'applicant_id': student_entry_test.id,
                                    'name': subject_name,
                                    'obtained_marks': subject_score,
                                    'total_marks': subject_total_score,
                                })
                    except Exception as e:
                            _logger.info('*********** Exception %s', e)
                            failed_id =list(result.keys())[0]
                            if failed_id not in error_sync_ref:
                                error_sync_ref.append(list(result.keys())[0])
                            continue
                error_sync_ref_str = ','.join(map(str, error_sync_ref))
                return json.dumps({
                    'status':'yes',
                    'error_sync_ref':error_sync_ref_str
                })
        except Exception as e:
            print(e)
            _logger.info('*********** Exception %s', e)
            return json.dumps({
                'status':'no',
                'error': f'{e}'})

    # @route('/result/import/', type='json', auth='user', csrf=False)
    # def import_result(self, **kw):
    #     try:

    #         if request.httprequest.method == 'POST':
    #             for result in json.loads(kw.get('result_all')):
    #                 application_no = list(result.keys())[0]
    #                 application_cid = list(result.values())[1]
    #                 subject_dict = list(result.values())[0]
 
    #                 # application_id = request.env['odoocms.application'].sudo().search(
    #                 #     [('id', '=', application_cid)])
                    
    #                 student_entry_test = request.env['applicant.entry.test'].sudo().search([('id', '=', application_cid)])
    #                 # if student_entry_test.applicant_line_ids:
    #                 #     student_entry_test.applicant_line_ids.sudo().unlink()
    #                 if student_entry_test:
    #                     student_entry_test.paper_conducted = True
    #                     for k, v in subject_dict.items():
    #                         subject_name = k
    #                         subject_score = v['subject_score']
    #                         subject_total_score = v['subject_total_score']
    #                         student_entry_test.applicant_line_ids.create({
    #                             'applicant_id': student_entry_test.id,
    #                             'name': subject_name,
    #                             'obtained_marks': subject_score,
    #                             'total_marks': subject_total_score,
    #                         })
    #             return json.dumps({
    #                 'status':'yes'
    #             })
    #     except Exception as e:
    #         print(e)
    #         return json.dumps({
    #             'status':'no',
    #             'error': f'{e}'})
