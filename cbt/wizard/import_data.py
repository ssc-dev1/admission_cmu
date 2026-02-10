import xmlrpc.client
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)


class ImportDataWizard(models.TransientModel):
    _name = "import.data.wizard"
    _description = "Import Data Wizard"

    user_id = fields.Char('User ID')
    password = fields.Char('Password')
    admin_pass = fields.Char('Admin Password')
    db = fields.Char('Database')
    
    def import_cbt_data(self):
        host = "localhost"
        port = 8069
        url = "http://localhost:8069/xmlrpc"
        username = "admin"
        password = self.admin_pass
        db = self.db
    
        common = xmlrpc.client.ServerProxy(url + '/common')
        models = xmlrpc.client.ServerProxy(url + '/object')
        
        # Remove previous demo data
        papers = self.env['cbt.paper.attempt.demo'].search([])
        papers.unlink()
        
        questions = self.env['cbt.question.attempt.demo'].search([])
        questions.unlink()
    
        uid = common.login(db, username, password)
        
        # Populate Temp Table
        paper_ids = models.execute_kw(db, uid, password, 'cbt.paper.export', 'search_read',
            [[]],
            {'fields': ['server_id', 'test_date']})
        for paper_id in paper_ids:
            data = {
                'paper_id_portal': int(paper_id['id']),
                'date': paper_id['test_date'],
                'paper_server_id': int(paper_id['server_id'])
            }
            self.env['cbt.paper.attempt.demo'].create(data)
    
        paper_line_ids = models.execute_kw(db, uid, password, 'cbt.paper.line.export', 'search_read',
            [[]],
            {'fields': ['server_id', 'answer_alphabet', 'paper_id']})
    
        for ques in paper_line_ids:
            data = {
                'paper_id_portal': int(ques['paper_id'][0]),
                'question_server_id': int(ques['server_id']),
                'answer': ques['answer_alphabet']
            }
            self.env['cbt.question.attempt.demo'].create(data)
    
        # Process Result
        for paper in self.env['cbt.paper.attempt.demo'].search([]):
            ex_paper_id = self.env['cbt.paper.conduct'].search([('paper_id','=',paper.paper_server_id)])
            if not ex_paper_id:
                data = {
                    'paper_id': paper.paper_server_id,
                    'date': paper.date,
                }
                conduct_id=self.env['cbt.paper.conduct'].create(data)
            
                for question in self.env['cbt.question.attempt.demo'].search([('paper_id_portal','=',paper.paper_id_portal)]):
                    data_question = {
                        'question_id':question.question_server_id,
                        'participant_answer':question.answer,
                        'attempt_id':conduct_id.id
                    }
                    self.env['cbt.paper.attempt'].create(data_question)
        student_result = self.env['cbt.paper.conduct'].search([])
        for result in student_result:
            result.subject_wise_score()
        
