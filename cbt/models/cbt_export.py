from odoo import fields, models, _, api, http
import xmlrpc.client
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pdb
import subprocess
from odoo.exceptions import UserError, ValidationError, Warning
import random
from datetime import datetime, date
import logging

_logger = logging.getLogger(__name__)


class CBTExport(models.Model):
    _name = 'cbt.export'
    _description = 'CBT Export'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    etest_id = fields.Many2one('cbt.test', tracking=True)
    type_id = fields.Many2one('cbt.test.type', tracking=True)
    slot_id = fields.Many2one('cbt.slot', 'Session', tracking=True)
    file_download_link = fields.Text("File Path")
    
    def export_cbt_data(self, user_id, password, admin_pass):
        self._export_data(user_id, password, admin_pass)
        #self.dump_database()
        #self.create_db('localhost', 'cbtportal2', 5432, 'odoo', '')
        #self.restore_database()

    def clear_data1(self, user_id, password):
        cur = self.connect_to_db("localhost", 'cbt_export', user_id, password)
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_paper_export'))
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_paper_line_export'))
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_paper_line_option_export'))
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_subject_export'))
        cur.execute("DELETE FROM res_users where id > 5;")
        cur.close()

    def clear_data2(self, user_id, password):
        cur = self.connect_to_db("localhost", 'cbt', user_id, password)
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_paper_export'))
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_paper_line_export'))
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_paper_line_option_export'))
        cur.execute("TRUNCATE TABLE {} CASCADE;".format('cbt_subject_export'))
        cur.close()
        
    def populate_data(self, password):
        url = "http://localhost:8069/xmlrpc"
        username = "admin"
        db = 'cbt_export'

        print("URLL", url)
        common = xmlrpc.client.ServerProxy(url+'/common')
        models = xmlrpc.client.ServerProxy(url+'/object')

        uid = common.login(db, username, password)
        print("UIDDD", uid)
        
        group_portal = self.env.ref('base.group_portal')
        for paper in self.env['cbt.student.paper'].search([('slot_id', '=', self.slot_id.id)]):

            udata = {
                'login': paper.participant_id.login,
                'password': str(paper.participant_id.password),
                'name': paper.participant_id.name,
                'groups_id': [9],
            }
            user_id = models.execute_kw(db, uid, password, 'res.users', 'create', [udata])
            pdata = {
                'server_id': paper.id,
                'user_id': user_id,
                'login': paper.participant_id.login,
                'name': paper.participant_id.name,
                'paper_name': paper.main_paper_id.name,
                'discipline': paper.main_paper_id.discipline_id.name,
                'test_center': paper.slot_id.center_id.name,
                'test_date': paper.slot_id.date,
                'test_time': paper.slot_id.time,
                'test_duration': paper.main_paper_id.generator_id.criteria_id.duration,
            }
            paper_id = self.env['cbt.paper.export'].create(pdata).id
            shuffle_list = paper.questions.ids
            random.shuffle(shuffle_list)
            for shuffle_elment in shuffle_list:
                question = self.env['cbt.mcqs'].search([('id', '=', shuffle_elment)])
            
                sdata = self.env['cbt.subject.export'].search([
                    ('server_id', '=', question.subject_id.id), ('paper_id', '=', paper_id)])
                if sdata:
                    subject_id = sdata.id
                else:
                    sdata = {
                        'server_id': question.subject_id.id,
                        'paper_id': paper_id,
                        'name': question.subject_id.name
                    }
                    subject_id = self.env['cbt.subject.export'].create(sdata).id
            
                qdata = {
                    'server_id': question.id,
                    'paper_id': paper_id,
                    'subject_id': subject_id,
                    'name': question.question,
                }
                question_id = self.env['cbt.paper.line.export'].create(qdata).id
                odata = []
                odata.append({
                    'server_id': question.id,
                    'question_id': question_id,
                    'name': question.ans1,
                })
                odata.append({
                    'server_id': question.id,
                    'question_id': question_id,
                    'name': question.ans2,
                })
                odata.append({
                    'server_id': question.id,
                    'question_id': question_id,
                    'name': question.ans3,
                })
                odata.append({
                    'server_id': question.id,
                    'question_id': question_id,
                    'name': question.ans4,
                })
                test_id = self.env['cbt.paper.line.option.export'].create(odata)
                
    def _export_data(self, user_id, password, admin_pass):
        self.clear_data1(user_id, password)
        self.clear_data2(user_id, password)
        self.populate_data(admin_pass)
        self.env.cr.commit()
        self.dump_table(user_id, password)
        
        # # paper_ids = models.execute_kw(db, uid, password, 'cbt.paper', 'search', [[]])
        # # models.execute_kw(db, uid, password, 'cbt.paper', 'unlink', [paper_ids])
        
    def connect_to_db(self,host, dbname,user,password):
        # create db connection and return db cursor
        db = psycopg2.connect(dbname=dbname, user=user, password=password, host=host,)
        db.set_session(autocommit=True)
        # Open a cursor to perform database operations
        cur = db.cursor()
        print('Connected to db')
        return cur
    
    def create_db(self, db_host, database, db_port, user_name, user_password):
        try:
            con = psycopg2.connect(dbname='postgres', port=db_port,
                                   user=user_name, host=db_host,
                                   password=user_password)
    
        except Exception as e:
            print(e)
            exit(1)
    
        con.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = con.cursor()
        try:
            cur.execute("DROP DATABASE {} ;".format(database))
        except Exception as e:
            print('DB does not exist, nothing to drop')
        cur.execute("CREATE DATABASE {} ;".format(database))
        cur.execute("GRANT ALL PRIVILEGES ON DATABASE {} TO {} ;".format(database, user_name))
        return database

    def restore_database(self):
        backup_file = '/opt/odoo14/backup.dmp'
        try:
            process = subprocess.Popen(
                ['pg_restore',
                 '--no-owner',
                 '--dbname=postgresql://{}:{}@{}:{}/{}'.format('nutech',  # db user
                                                               'nutech_aarsol',  # db password
                                                               'localhost',  # db host
                                                               '5432', 'cbtportal2'),  # db port ,#db name
                 '-v',
                 '--host=localhost',
                 backup_file],
                stdout=subprocess.PIPE
            )
            output = process.communicate()[0]
    
        except Exception as e:
            print('Exception during restore %e' % (e))
            
    # pg_dump -a -t res_users cbt_export | psql cbt_export_old
    def dump_table(self, user_id, password):
        # command = 'pg_dump -d {0} -U {1} -p 5432 -t public.{2} | psql cbt_export' \
        #     .format(database_name, user_name, table_name)
        
        user_id = 'odoo14'
        #command = 'pg_dump -a -d cbt -U ' + user_id + ' -p 5432 -t cbt_paper_export -t cbt_paper_line_export -t cbt_paper_line_option_export -t cbt_subject_export -t cbt_instruction_export | psql -U ' + user_id + ' cbt_export'
        command = 'pg_dump -a -d cbt -U ' + user_id + ' -p 5432 -t cbt_paper_export -t cbt_paper_line_export -t cbt_paper_line_option_export -t cbt_subject_export  | psql -U ' + user_id + ' cbt_export'

        try:
            proc = subprocess.Popen(command, shell=True, env={
                'PGPASSWORD': password
            }, stdout=subprocess.PIPE, stderr=subprocess.PIPE)    #  , stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            out, err = proc.communicate()


        except Exception as e:
            dump_success = 0
            raise ValidationError(_("Exception happened during dump %s") % (e))
        b = 5
        

class CBTPaperExport(models.Model):
    _name = 'cbt.paper.export'
    _description = 'Paper Export'
    _rec_name = 'login'

    # data = fields.Encrypted()   # ,encrypt='data'
    # encrypted_password = fields.Encrypted()
    
    server_id = fields.Integer(string='Server ID')
    user_id = fields.Integer('User')
    login = fields.Char(string="Roll Number")
    name = fields.Char(string="Candidate Name")
    paper_name = fields.Char(string="Paper Name")
    shuffle_section = fields.Boolean('Shuffle Section',default=False)
    program = fields.Char(string="Discipline")
    test_center = fields.Char(string="Test Center")
    test_date = fields.Date(string="Test Date")
    test_time = fields.Float(string="Start Time")
    test_duration = fields.Integer(string="Duration")
    current_q = fields.Integer(default=1)
    time_remaining = fields.Char()
    line_ids = fields.One2many('cbt.paper.line.export', 'paper_id', string="Questions")
    last_session_id = fields.Char('last Session ID')
    last_session_token = fields.Char('Last Session Token')
    session_ids = fields.One2many('cbt.paper.session', 'paper_id', 'Sessions')
    end_paper = fields.Boolean(string='End Paper', default=False)
    end_paper_time = fields.Datetime(string='Candidate Attempt End Time')
    paper_started = fields.Datetime('Candidate Attempt Time')
    is_login = fields.Boolean(string='Login Status', default=False)
    active = fields.Boolean(default=True, help="Set active to false to hide  without removing it.")

    

class CBTPaperLineExport(models.Model):
    _name = 'cbt.paper.line.export'
    _description = 'Paper Questions Export'

    #question = fields.Encrypted()  # ,encrypt='question'
    server_id = fields.Integer(string='Server ID')
    paper_id = fields.Many2one('cbt.paper.export', string="Paper")
    subject_id = fields.Many2one('cbt.subject.export', string="Section/Subject")
    name = fields.Text(string="Question")
    option_ids = fields.One2many('cbt.paper.line.option.export', 'question_id', string="Options")
    answer = fields.Integer('Selected Option')
    #answer = fields.Many2one('cbt.paper.line.option.export', 'Selected Option')
    answer_alphabet = fields.Char(string="Answer")
    answer_recorded_time = fields.Datetime('Recorded Date', default=datetime.now())
    mark_review = fields.Boolean(string='Review', default=False)


class CBTPaperLineOptionExport(models.Model):
    _name = 'cbt.paper.line.option.export'
    _description = 'Question Options Export'

    #option = fields.Encrypted()  # ,encrypt='option'
    server_id = fields.Integer(string='Server ID')
    question_id = fields.Many2one('cbt.paper.line.export', string='Question')
    name = fields.Char(string="Choice")

    
class OdoocmsCBTSubjectExport(models.Model):
    _name = 'cbt.subject.export'
    _description = 'Subjects Export'

    #subject = fields.Encrypted()  # ,encrypt='subject'
    server_id = fields.Integer('Server ID')
    paper_id = fields.Many2one('cbt.paper.export','Paper')
    sequence_no = fields.Integer(string='Sequence')
    name = fields.Char(string="Subject/Topic")
    question_ids = fields.One2many('cbt.paper.line.export', 'subject_id', 'Questions')
    

class OdoocmsCBTInstructionExport(models.Model):
    _name = 'cbt.instruction.export'
    _description = 'Instructions Export'

    name = fields.Char('Name')
    instruction = fields.Html(string="Paper Guide lines / Instructions")