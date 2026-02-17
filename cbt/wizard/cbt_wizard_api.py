from odoo import fields, models, _,SUPERUSER_ID
from odoo.exceptions import UserError
import requests
import json
from datetime import datetime, date
import random


class CbtApiWizard(models.TransientModel):
    _name = 'cbt.api.wizard'
    _description = 'CBT Api Wizard'

    name = fields.Char('name')
    total_paper = fields.Integer('Total Paper')
    # discipline_id = fields.Many2one('cbt.discipline', string='Discipline')


    def generate_multi_paper_student(self):
        active_id = self.env.context.get('active_id')
        paper_generator = self.env['cbt.paper.generator'].sudo().search(
            [('id', '=', active_id)])
        for rec in self:
            login = rec.login
            db = rec.db
            api_key = rec.api_key
            base_url = rec.url
        if not login and not db and not api_key and not base_url:
            raise UserError('Invalid Data Please Provide All Fields')

        connection = {
            "jsonrpc": "2.0",
            "params": {
                "db": db,
                "login": login,
                "password": api_key,
            }
        }
        auth_url = base_url + '/web/session/authenticate'
        user = requests.post(auth_url,
                             json=connection, headers={"Content-Type": "application/json"})
        entry_test_url = base_url + '/entry/test'

        request_student_data = requests.post(entry_test_url, json={"jsonrpc": "2.0"}, headers={
            "Content-Type": "application/json", "Cookie": f"session_id={user.cookies.get_dict().get('session_id')}",
            "X-Openerp": user.cookies.get_dict().get('session_id')
        })

        try:
            student_data = json.loads(json.loads(
                request_student_data.content).get('result'))
        except Exception as e:
            error = 'No Data Get '
            raise UserError(error)

        for student in student_data:
            if student.get('application_no'):
                test_date = datetime.strptime(student.get('date'), "%Y-%m-%d") if student.get('date') else False
                data = {
                    'name': student.get('name'),
                    'password': student.get('password'),
                    'login': student.get('application_no'),
                    'room': student.get('room'),
                }
                discipline_admission = json.loads(student.get('discipline'))
                if discipline_admission.get('code') and discipline_admission.get('name'):
                    discipline_cbt = self.env['cbt.discipline'].search(
                        [('code', '=', discipline_admission.get('code'))],limit=1)
                    if discipline_cbt:
                        data.update({
                            'discipline': discipline_cbt.id
                        })
                    if not discipline_cbt:
                        cbt_dis = self.env['cbt.discipline'].create({
                            'name': discipline_admission.get('name'),
                            'code': discipline_admission.get('code'),
                        })
                        data.update({
                            'discipline': cbt_dis.id,
                        })

                # slot
                slot_admission = json.loads(student.get('slot'))
                slot_time_from = slot_admission.get('time_from')
                slot_time_to = slot_admission.get('time_to')
                slot_name = slot_admission.get('name')

                slot_cbt = self.env['cbt.slot'].search(
                    [('name', '=', slot_name)],limit=1)
                if slot_cbt:
                    data.update({
                        'slot_id': slot_cbt.id
                    })
                if not slot_cbt:
                    slot_cbt_new = self.env['cbt.slot'].create({
                        'time': float(slot_time_from),
                        'date': test_date,
                        'name': slot_name,
                    })
                    data.update({
                        'slot_id': slot_cbt_new.id
                    })
                candidate = self.env['cbt.participant'].sudo().search(
                    [('login', '=', student.get('application_no'))])
                candidate_user = self.env['res.users'].sudo().search(
                    [('login', '=', student.get('application_no'))])
                
                if not candidate:
                    self.env['cbt.participant'].sudo().create(data)
                if not candidate_user:
                    portal_group = self.env.ref('base.group_portal')
                    
                    self.env['res.users'].sudo().create({
                        'name': student.get('name'),
                        'password': student.get('password'),
                        'login': student.get('application_no'),
                        'active':True,
                        'email':student.get('application_no'),
                        'groups_id': [(6, 0, [portal_group.id])]
                    })
            self.flush()

        participants = self.env['cbt.participant'].search([])
        paper_id = [paper.id for paper in paper_generator.papers]
        for participant in participants:
            random.shuffle(paper_id)
            paper = paper_generator.papers.filtered(
                lambda x: x.id == paper_id[0])
            question_list = [ques.id for ques in paper.questions]
            random.shuffle(question_list)
            papers_data = {
                'main_paper_id': paper.id,
                'questions': [(6, 0, question_list)],
                'participant_id': participant.id,
            }
            participant_paper = self.env['cbt.student.paper'].create(
                papers_data)
            participant_paper.main_paper_id.slot_id.duration = paper_generator.criteria_id.duration
            participant_test_data = {
                'name': participant_paper.participant_id.name,
                'paper_name': participant_paper.main_paper_id.name,
                'discipline': participant_paper.main_paper_id.discipline_id.name,
                'test_time': participant_paper.main_paper_id.slot_id.time,
                'test_duration': participant_paper.main_paper_id.slot_id.duration,
                'test_date': participant_paper.slot_id.date,
                'login': participant.login,
            }

            participant_test = self.env['cbt.paper.export'].create(
                participant_test_data)
            participant_test.server_id = participant_paper.id
            server_id = participant_paper.id
            
            participant_test_question = []
            for rec in participant_paper.questions:
                question = rec.question
                subject = rec.subject_id.name
                
                test_paper_subject = self.env['cbt.subject.export'].search([('name','=ilike',subject)],limit=1)
                if not test_paper_subject:
                    test_paper_subject = self.env['cbt.subject.export'].create({
                        'name':subject,
                    })
                test_question = participant_test.line_ids.create({
                    'paper_id': participant_test.id,
                    'name': rec.question,
                    'server_id':rec.id,
                    'subject_id':test_paper_subject.id,
                    
                })
                options = [rec.ans1, rec.ans2, rec.ans3,
                           rec.ans4, rec.ans5, rec.ans6]
                correct_ansewer = ''

                if rec.ans1_correct:
                    correct_ansewer = 'A'
                if rec.ans2_correct:
                    correct_ansewer = 'B'
                if rec.ans3_correct:
                    correct_ansewer = 'C'
                if rec.ans4_correct:
                    correct_ansewer = 'D'
                if rec.ans5_correct:
                    correct_ansewer = 'E'
                if rec.ans6_correct:
                    correct_ansewer = 'F'

                for opt in options:
                    participant_test.line_ids.option_ids.create({
                        'question_id': test_question.id,
                        'name': opt,
                        'server_id':test_question.id,
                    })
                # test_question.answer = correct_ansewer

            self.env.cr.commit()
            paper.student_paper_gen = True
