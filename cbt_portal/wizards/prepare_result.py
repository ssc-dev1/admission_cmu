from odoo import fields, models, api
from odoo.exceptions import UserError
import json
import requests
import pdb


class PrepareResultWizard(models.TransientModel):

    _name = 'prepare.result.wizard'
    _description = 'Result Export'

    paper_id = fields.Many2one('cbt.paper.generator', 'Generated Paper', required=True)

    def prepare_result(self):
        try:
            db = self.env['ir.config_parameter'].get_param('cbt.admission_db')
            url = self.env['ir.config_parameter'].get_param(
                'cbt.admission_url')
            login = self.env['ir.config_parameter'].get_param(
                'cbt.admission_login')
            password = self.env['ir.config_parameter'].get_param(
                'cbt.admission_password')

            if not db or not login or not password or not url:
                raise UserError('Please Fill All Fields In Configuration')
            if not self.paper_id:
                raise UserError('Please Select Test')

            # Remove previous demo data
            papers = self.env['cbt.paper.attempt.demo'].search([])
            papers.unlink()

            questions = self.env['cbt.question.attempt.demo'].search([])
            questions.unlink()

            paper_ids = self.env['cbt.paper.export'].search_read(
                [('is_login','=',True),('paper_draft','=',False)], ['server_id', 'test_date'])

            for paper_id in paper_ids:
                if paper_id['id'] and paper_id['server_id']:
                    data = {
                        'paper_id_portal': int(paper_id['id']),
                        'date': paper_id['test_date'],
                        'paper_server_id': int(paper_id['server_id'])

                    }
                self.env['cbt.paper.attempt.demo'].create(data)

            paper_line_ids = self.env['cbt.paper.line.export'].search_read(
                [], ['server_id', 'answer_alphabet', 'paper_id'])

            for ques in paper_line_ids:
                if ques['paper_id'] and ques['server_id']:
                    # if int(ques['paper_id'][0]) == 46:

                    data = {
                        'paper_id_portal': int(ques['paper_id'][0]),
                        'question_server_id': int(ques['server_id']),
                        'answer': ques['answer_alphabet']
                    }
                    self.env['cbt.question.attempt.demo'].create(data)

            for paper in self.env['cbt.paper.attempt.demo'].search([]):
                ex_paper_id = self.env['cbt.paper.conduct'].search(
                    [('paper_id', '=', paper.paper_server_id)])
                if not ex_paper_id:
                    data = {
                        'paper_id': paper.paper_server_id,
                        'date': paper.date,
                    }
                    conduct_id = self.env['cbt.paper.conduct'].create(data)
                    for question in self.env['cbt.question.attempt.demo'].search([('paper_id_portal', '=', paper.paper_id_portal)]):
                        data_question = {
                            'question_id': question.question_server_id,
                            'participant_answer': question.answer,
                            'attempt_id': conduct_id.id
                        }
                        self.env['cbt.paper.attempt'].create(data_question)
            student_result = self.env['cbt.paper.conduct'].search([('paper_id','!=', False)])
            for result in student_result:
                result.subject_wise_score()

            # raise UserError('Data Exported Successfully!')
            user = requests.post(url + '/web/session/authenticate',
                                 json={
                                     "jsonrpc": "2.0",
                                     "params": {
                                         "db": db,
                                         "login": login,
                                         "password": password,
                                     }
                                 }, headers={"Content-Type": "application/json"})

            result_export = url + '/result/import'

            subjects = self.env['cbt.paper.subject.score'].search([('conduct.paper_id.main_paper_id.generator_id', '=', self.paper_id.id)])

            results_all = []
            for subject in subjects:
                result_stu = {
                    subject.conduct.paper_id.participant_id.login: {
                        subject.subject_id.name: {
                            'subject_score': subject.score,
                            'subject_total_score': subject.total_score,
                        },

                    }, 'cid': subject.conduct.paper_id.participant_id.cid,

                }
                    # 'cbt_id': subject.conduct.paper_id.participant_id.cid,
                results_all.append(result_stu)

            request_student_data = requests.post(result_export, json={"jsonrpc": "2.0", "params": {
                "result_all": json.dumps(results_all),
            }}, headers={
                "Content-Type": "application/json", "Cookie": f"session_id={user.cookies.get_dict().get('session_id')}",
                "X-Openerp": user.cookies.get_dict().get('session_id')
            })

            response = json.loads(request_student_data.content)['result']
            response_status = json.loads(response)
            if response_status['status'] == 'yes':
                return False
                # message_id = self.env['success.message.wizard'].create(
                #     {'message': 'Data Exported Successfully!...'})
                # return {
                #     'name': 'Message',
                #     'type': 'ir.actions.act_window',
                #     'view_mode': 'form',
                #     'res_model': 'success.message.wizard',
                #     'res_id': message_id.id,
                #     'target': 'new'
                # }
            if response_status['status'] == 'no':
                error = response_status['error']
            # message_id = self.env['success.message.wizard'].create(
            #     {'message': 'Data Exported Successfully!...'})
            # return {
            #     'name': 'Message',
            #     'type': 'ir.actions.act_window',
            #     'view_mode': 'form',
            #     'res_model': 'success.message.wizard',
            #     'res_id': message_id.id,
            #     'target': 'new'
            # }
        except Exception as e:
            raise UserError(f"{e}")
