from odoo import fields, models, api, _
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning
from datetime import datetime, date
import requests
import json
import random


class CBTSessionExport(models.Model):
    _name = 'cbt.session.export'
    _description = 'Sessions Export'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    server_id = fields.Integer(string='Server ID')
    name = fields.Char('Session')
    time = fields.Float('Session Time')
    date = fields.Date(string='Session Date', default=date.today())


class CBTPaperExport(models.Model):
    _name = 'cbt.paper.export'
    _description = 'Paper Export'
    _rec_name = 'login'

    # data = fields.Encrypted()   # ,encrypt='data'
    # encrypted_password = fields.Encrypted()

    server_id = fields.Integer(string='Server ID')
    user_id = fields.Integer('User')
    login = fields.Char(string="Application Number")
    name = fields.Char(string="Candidate Name")
    paper_name = fields.Char(string="Paper Name")
    # paper_main_id = fields.Many2one('cbt.paper', string='Paper Main')
    program = fields.Char(string="Program")
    test_center = fields.Char(string="Test Center")
    test_date = fields.Date(string="Test Date")
    test_time = fields.Float(string="Start Time")
    test_duration = fields.Integer(string="Duration")
    shuffle_section = fields.Boolean('Shuffle Section', default=False)
    current_q = fields.Integer(default=1)
    paper_draft = fields.Boolean('Paper Draft',default=False)
    time_remaining = fields.Char('Rem. Time')
    line_ids = fields.One2many('cbt.paper.line.export', 'paper_id', string="Questions")
    last_session_id = fields.Char('last Session ID')
    last_session_token = fields.Char('Last Session Token')
    session_ids = fields.One2many('cbt.paper.session', 'paper_id', 'Sessions')
    end_paper = fields.Boolean(string='End Paper', default=False)
    end_paper_time = fields.Datetime(string='Candidate Attempt End Time')
    paper_started = fields.Datetime('Candidate Attempt Time')
    is_login = fields.Boolean(string='Login Status', default=False)
    answered_q = fields.Integer('Q.Att', compute='_get_stats')
    reviewed_q = fields.Integer('Q.Rev', compute='_get_stats')
    cid = fields.Integer('Entery Test Card Id')
    active = fields.Boolean(default=True, help="Set active to false to hide  without removing it.")

    def _get_stats(self):
        for rec in self:
            rec.answered_q = len(rec.line_ids.filtered(lambda l: l.answer > 0))
            rec.reviewed_q = len(rec.line_ids.filtered(
                lambda l: l.mark_review == True))

    def clear(self):
        for rec in self:
            rec.last_session_id = ''
            rec.last_session_token = ''

    def restore(self):
        for rec in self:
            rec.end_paper = False
            rec.end_paper_time = False

    def kill_session(self):
        url = self.env['ir.config_parameter'].sudo(
        ).get_param('cbt.admission_url')
        user = requests.post(f'{url}/web/session/destroy', json={"jsonrpc": "2.0"}, headers={
            "Content-Type": "application/json", "Cookie": f"session_id={self.last_session_id}",
            "X-Openerp": f"{self.last_session_id}"
        })

    def kill_all_user(self):
        url = self.env['ir.config_parameter'].sudo(
        ).get_param('cbt.admission_url')
        login_users = self.env['cbt.paper.export'].sudo().search(
            [('last_session_id', '!=', False)])
        for rec in login_users:
            requests.post(f'{url}/web/session/destroy', json={"jsonrpc": "2.0"}, headers={
                "Content-Type": "application/json", "Cookie": f"session_id={rec.last_session_id}",
                "X-Openerp": f"{self.last_session_id}"
            })


class CBTPaperLineExport(models.Model):
    _name = 'cbt.paper.line.export'
    _description = 'Paper Questions Export'

    # question = fields.Encrypted()  # ,encrypt='question'
    server_id = fields.Integer(string='Server ID')
    paper_id = fields.Many2one('cbt.paper.export', string="Paper")
    subject_id = fields.Many2one(
        'cbt.subject.export', string="Section/Subject")
    name = fields.Text(string="Question")
    question_type = fields.Char(string="Question Type")
    scenario_relation = fields.Char(string="Scenario Relation")
    option_ids = fields.One2many(
        'cbt.paper.line.option.export', 'question_id', string="Options")
    answer = fields.Integer('Selected Option')
    correct_answer = fields.Char('Correct Ansewer', invisible=True)
    # answer = fields.Many2one('cbt.paper.line.option.export','Selected Option')
    answer_alphabet = fields.Char(string="Answer")
    answer_recorded_time = fields.Datetime(
        'Recorded Date', default=datetime.now())
    mark_review = fields.Boolean(string='Review', default=False)


class CBTPaperLineOptionExport(models.Model):
    _name = 'cbt.paper.line.option.export'
    _description = 'Question Options Export'

    # option = fields.Encrypted()  # ,encrypt='option'
    server_id = fields.Integer(string='Server ID')
    question_id = fields.Many2one('cbt.paper.line.export', string='Question')
    name = fields.Char(string="Choice/Answer")


class CBTPaperSession(models.Model):
    _name = 'cbt.paper.session'
    _description = 'Paper Sessions'

    # session = fields.Encrypted()  # ,encrypt='session'
    paper_id = fields.Many2one('cbt.paper.export', string="Paper")
    name = fields.Char(string="Session Name")
    start_time = fields.Char(string="Start Time")
    end_time = fields.Char(string="End Time")


class OdoocmsCBTSubjectExport(models.Model):
    _name = 'cbt.subject.export'
    _description = 'Subjects Export'

    # subject = fields.Encrypted()  # ,encrypt='subject'
    server_id = fields.Integer('Server ID')
    paper_id = fields.Many2one('cbt.paper.export', 'Paper')
    sequence_no = fields.Integer(string='Sequence')
    random_shuffle_no = fields.Integer(
        'Random Shuffle', compute='_compute_random_shuffle')
    name = fields.Char(string="Subject/Topic")
    question_ids = fields.One2many(
        'cbt.paper.line.export', 'subject_id', 'Questions')

    def _compute_random_shuffle(self):
        for rec in self:
            rec.random_shuffle_no = random.randint(1, 9)


class OdoocmsCBTInstructionExport(models.Model):
    _name = 'cbt.instruction.export'
    _description = 'Instructions Export'

    name = fields.Char('Name')
    instruction = fields.Html(string="Paper Guide lines / Instructions")
