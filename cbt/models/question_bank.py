# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import UserError, ValidationError, Warning
from datetime import datetime, date
import pdb


class CBTprogram(models.Model):
    _name = 'cbt.program'
    _description = 'program/Study Programs'

    name = fields.Char(string='Program', required=True)
    code = fields.Char(string='Code', required=True)
    sequence = fields.Integer(default=10)
    description = fields.Char(string='Description')
    # paper_generator_id = fields.Many2one('cbt.paper.generator', string='Paper Generator')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', "program name already exists!"),
        ('code_uniq', 'unique(code)', "program code already exists!"),
    ]


class CBTSubject(models.Model):
    _name = 'cbt.subject'
    _description = 'Subject'

    name = fields.Char(string='Course Name')
    code = fields.Char(string='Course Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    topic_count = fields.Integer(
        compute='_compute_topics', string='Number of Topics')
    sub_topic_count = fields.Integer(
        compute='_compute_sub_topics', string='Number of Sub Topics')

    topic_ids = fields.One2many(
        'cbt.subject.topic', 'subject_id', string="Topics")
    role_ids = fields.One2many(
        'cbt.employee.role', 'subject_id', string='Faculty')

    # @api.onchange('topic_ids')
    def _compute_topics(self):
        for rec in self:
            subjects = self.env['cbt.subject.topic'].search([
                ('subject_id', '=', rec.id)])
            rec.topic_count = len(subjects)

    def _compute_sub_topics(self):
        for rec in self:
            sub_topics = self.env['cbt.subject.subtopic'].search([
                ('subject_id', '=', rec.id)])
            rec.sub_topic_count = len(sub_topics)


class CBTSubjectTopic(models.Model):
    _name = 'cbt.subject.topic'
    _description = 'Topics'

    subject_id = fields.Many2one('cbt.subject', 'Subject', ondelete='cascade')
    name = fields.Char(string='Topic')
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    sub_topic_count = fields.Integer(
        compute='_compute_sub_topics', string='Number of Sub Topics')

    sub_topic_ids = fields.One2many(
        'cbt.subject.subtopic', 'topic_id', string=" Sub Topics")
    role_ids = fields.One2many(
        'cbt.employee.role', 'topic_id', string='Faculty')

    def _compute_sub_topics(self):
        for rec in self:
            sub_topics = self.env['cbt.subject.subtopic'].search([
                ('topic_id', '=', rec.id)])
            rec.sub_topic_count = len(sub_topics)


class CBTSubjectSubTopic(models.Model):
    _name = 'cbt.subject.subtopic'
    _description = 'Sub Topic'

    name = fields.Char(string='Sub Topic', required=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    topic_id = fields.Many2one(
        'cbt.subject.topic', string="Topic", ondelete='cascade')
    subject_id = fields.Many2one(
        'cbt.subject', string="Subject", related='topic_id.subject_id', store=True)
    role_ids = fields.One2many(
        'cbt.employee.role', 'subtopic_id', string='Faculty')


class CBTEmployeeRole(models.Model):
    _name = 'cbt.employee.role'
    _description = 'Employee Role'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    employee_id = fields.Many2one(
        'hr.employee', "Faculty", required="True", tracking=True)
    subject_id = fields.Many2one(
        'cbt.subject', "Subject", required="True", tracking=True)
    topic_id = fields.Many2one('cbt.subject.topic', "Topic", tracking=True)
    subtopic_id = fields.Many2one(
        'cbt.subject.subtopic', "Sub Topic", tracking=True)
    create_access = fields.Boolean(
        'Create Access', default=True, tracking=True)
    review_access = fields.Boolean(
        'Review Access', default=True, tracking=True)

    def name_get(self):
        res = []
        for rec in self:
            name = 'New'
            if rec.employee_id and rec.subject_id:
                name = rec.employee_id.name + ' - ' + rec.subject_id.name
            res.append((rec.id, name))
        return res


class CBTTasks(models.Model):
    _name = 'cbt.jobs'
    _description = 'Jobs/Tasks Setup'

    name = fields.Char('Job Name')
    description = fields.Text('Description')
    date = fields.Datetime(string='Date Created', default=datetime.now())
    from_time = fields.Float(string='Start Time')
    to_time = fields.Float(string='End Time')
    state = fields.Selection([
        ('inprogress', 'Inprogress'),
        ('processed', 'Processed'),
    ], string='Status')
    failure = fields.Text('Exception')
    clear = fields.Char('Clear')
    active = fields.Boolean('Active', default=True)


class CBTQuestionType(models.Model):
    _name = 'cbt.question.type'
    _description = 'Question Type'

    name = fields.Char('Question Type')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    code = fields.Char(string="Code")
    description = fields.Char(string='Description')


class CBTQuestionSkill(models.Model):
    _name = 'cbt.question.skill'
    _description = 'Question Skill'

    name = fields.Char('Skill')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    description = fields.Char(string='Description')


class CBTQuestionDifficultySetup(models.Model):
    _name = 'cbt.question.difficulty.level'
    _description = 'Question Difficulty'

    name = fields.Char(string='Difficulty Level')
    code = fields.Integer(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    description = fields.Char(string='Description')


class CBTQuestionTime(models.Model):
    _name = 'cbt.question.time'
    _description = 'Question Time'

    name = fields.Char(string='Time (Seconds)')
    code = fields.Integer(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Char(string='Description')


class CBTTest(models.Model):
    _name = 'cbt.test'
    _description = 'Entry Test'

    name = fields.Char(string='Entry Test Name')
    code = fields.Integer(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    description = fields.Char(string='Description')


class CBTTestType(models.Model):
    _name = 'cbt.test.type'
    _description = 'Test Type'

    name = fields.Char(string='Test Type')
    code = fields.Integer(string='Code')
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    color = fields.Integer(string='Color Index')
    description = fields.Char(string='Description')


class CBTSession(models.Model):
    _name = 'cbt.session'
    _description = 'Sessions'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    etest_id = fields.Many2one('cbt.test', required=True, tracking=True)
    type_id = fields.Many2one('cbt.test.type', required=True, tracking=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    line_ids = fields.One2many('cbt.session.line', 'session_id', string='Sessions list',
                               required=True, tracking=True)

    def name_get(self):
        res = []
        for record in self:
            name = 'New'
            if record.etest_id:
                name = record.type_id.name
            res.append((record.id, name))
        return res


class CBTSessionLine(models.Model):
    _name = 'cbt.session.line'
    _description = 'Sessions list'

    session_no = fields.Integer(string='Session No.')
    time = fields.Float('Session Time')
    date = fields.Date(string='Session Date', default=date.today())
    session_id = fields.Many2one('cbt.session')

    def name_get(self):
        res = []
        for record in self:
            if record.date:
                time = '%02d:%02d' % (divmod(record.time * 60, 60))
                name = str(record.date) + ' ( ' + str(time) + ' )'
            res.append((record.id, name))
        return res


class CBTprogramCourses(models.Model):
    _name = 'cbt.program.courses'
    _description = 'Allocation of Subject to Study Program'

    etest_id = fields.Many2one('cbt.test', 'Entry Test')
    type_id = fields.Many2one('cbt.test.type', 'Test Type')
    program_id = fields.Many2one('cbt.program', 'program')
    subject_ids = fields.Many2many('cbt.subject', 'program_course_rel',
                                   'program_id', 'subject_id', string="program Courses")


class CBTQuestionRepeatTrack(models.Model):
    _name = 'cbt.question.repeat.track'
    _description = 'Track Quesions repeat'

    paper_id = fields.Many2one('cbt.paper', 'Paper ID', required=True)
    date = fields.Datetime(string='Date', default=datetime.now())
    question_id = fields.Many2one('cbt.mcqs', 'Question', required=True)


class CBTMCQS(models.Model):
    _name = 'cbt.mcqs'
    _description = 'CBT Question Bank'
    _order = "subject_id desc"
    _rec_name = "question_title"

    def _get_default_subjects(self):
        subject_list = []
        employees = self.env['cbt.employee.role'].search([
            ('create_access', '=', True), ('employee_id.user_id', '=', self.env.user.id)])
        if employees:
            for employee in employees:
                for sub_id in employee.subject_id:
                    subject_list.append(sub_id.id)
        return [('id', 'in', subject_list)]



    subject_id = fields.Many2one('cbt.subject', 'Subject/Section', domain=_get_default_subjects)
    subject_code = fields.Char(related='subject_id.code', store=True)
    topic_id = fields.Many2one('cbt.subject.topic', 'Topic/Subsection')
    stopic_id = fields.Many2one(
        'cbt.subject.subtopic', 'Sub Topic')
    type_id = fields.Many2one('cbt.question.type')
    type_code = fields.Char(related='type_id.code', store=True)
    skill_id = fields.Many2one('cbt.question.skill')
    difficulty_level_id = fields.Many2one('cbt.question.difficulty.level')
    time_id = fields.Many2one('cbt.question.time')
    question = fields.Html(string='Question', required=True)
    question_title = fields.Char(string='Question Short Description')
    # question_child_count = fields.Html(string='Question Title', required=True)
    scenario_relation = fields.Selection([
        ('parent', 'Main Scenario/Story'),
        ('child', 'Scenario Question'),
    ], string='Scenario Type')
    scenario_id = fields.Many2one('cbt.mcqs', domain=[('scenario_relation','=','parent')])

    def action_view_child_questions(self):
        candidates = self.env['cbt.mcqs']
        subject_list = candidates
        for rec in self:
            rec.count = 0
            count_rec = 0
            questions = self.env['cbt.mcqs'].search([('scenario_id', '=', rec.id)])

            if rec.scenario_relation == 'parent':
                subject_list += questions

        # for rec in self
        if subject_list:
            candidate_list = subject_list.mapped('id')
            return {
                'domain': [('id', 'in', candidate_list)],
                'name': _('Classes'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'cbt.mcqs',
                'view_id': False,
                'type': 'ir.actions.act_window'
            }

    # @api.onchange('scenario_id')
    # def _set_scenario_dificulty_level(self):
    #     for rec in self:
    #         rec.difficulty_level_id.id =  rec.scenario_id.difficulty_level_id.id


    @api.depends('count', 'subject_id','scenario_relation')
    def _get_scenario_questions(self):
        for rec in self:
            rec.count = 0
            count_rec = 0
            questions = self.env['cbt.mcqs'].search([('scenario_id','=',rec.id)])

            if rec.scenario_relation == 'parent':
                count_rec = count_rec + len(questions)
                rec.count = count_rec


    count = fields.Integer('Count Scenario Questiond', compute='_get_scenario_questions')

    option_quantity = fields.Selection([
        ('2', '2'),
        ('3', '3'),
        ('4', '4'),
        ('5', '5'),
        ('6', '6'),
    ], string='Option Count', default='4')
    ans1 = fields.Html(string='Option 1')
    ans1_correct = fields.Boolean(
        string='Option 1 is Correct Answer?', tracking=True)
    ans2 = fields.Html(string='Option 2')
    ans2_correct = fields.Boolean(
        string='Option 2 is Correct Answer?', tracking=True)
    ans3 = fields.Html(string='Option 3')
    ans3_correct = fields.Boolean(
        string='Option 3 is Correct Answer?', tracking=True)
    ans4 = fields.Html(string='Option 4')
    ans4_correct = fields.Boolean(
        string='Option 4 is Correct Answer?', tracking=True)
    ans5_correct = fields.Boolean(
        string='Option 5 is Correct Answer?', tracking=True)
    ans5 = fields.Html(string='Option 5')
    ans6_correct = fields.Boolean(
        string='Option 6 is Correct Answer?', tracking=True)
    ans6 = fields.Html(string='Option 6')
    current_user = fields.Many2one(
        'res.users', 'Created By', default=lambda self: self.env.user)
    reviewed_user = fields.Many2one('res.users', 'Reviewed By')
    state = fields.Selection([
        ('draft', 'Draft'), ('approved', 'Approved'), ('cancel', 'Cancel')
    ], 'Status', default='draft')
    paper_id = fields.Many2one('cbt.paper.criteria', 'Paper ID')
    question_repeat_ids = fields.One2many(
        'cbt.question.repeat.track', 'question_id', "Questions Track")

    def get_filtered_record(self):
        subject_list = []
        record_ids = []
        employees = self.env['cbt.employee.role'].search([
            ('review_access', '=', True), ('employee_id.user_id', '=', self.env.user.id)])
        if employees:
            for employee in employees:
                for sub_id in employee.subject_id:
                    subject_list.append(sub_id.id)
        review_questions = self.env['cbt.mcqs'].search([
            ('current_user', '!=', self.env.user.id), ('subject_id', 'in', subject_list), ('state', '=', 'draft')])
        for qes in review_questions:
            record_ids.append(qes.id)
        treeview_id = self.env.ref('cbt.cbt_question_review_tree').id
        formview_id = self.env.ref('cbt.cbt_question_review_form').id
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'cbt.mcqs',
            'view_type': 'form',
            'name': 'Review Questions',
            'view_mode': 'tree,form',
            'views': [(treeview_id, 'tree'), (formview_id, 'form')],
            'domain': [('id', 'in', record_ids)],
        }

    @api.onchange('ans1_correct', 'ans2_correct', 'ans3_correct', 'ans4_correct', 'ans5_correct', 'ans6_correct')
    def correct_option(self):
        if self.type_id.code == '1':
            if self.ans1_correct:
                self.ans2_correct = False
                self.ans3_correct = False
                self.ans4_correct = False
                self.ans5_correct = False
                self.ans6_correct = False
            elif self.ans2_correct:
                self.ans1_correct = False
                self.ans3_correct = False
                self.ans4_correct = False
                self.ans5_correct = False
                self.ans6_correct = False
            elif self.ans3_correct:
                self.ans1_correct = False
                self.ans2_correct = False
                self.ans4_correct = False
                self.ans5_correct = False
                self.ans6_correct = False
            elif self.ans4_correct:
                self.ans1_correct = False
                self.ans2_correct = False
                self.ans3_correct = False
                self.ans5_correct = False
                self.ans6_correct = False
            elif self.ans5_correct:
                self.ans1_correct = False
                self.ans2_correct = False
                self.ans3_correct = False
                self.ans4_correct = False
                self.ans6_correct = False
            elif self.ans6_correct:
                self.ans1_correct = False
                self.ans2_correct = False
                self.ans3_correct = False
                self.ans4_correct = False
                self.ans5_correct = False

    def name_get(self):
        res = []
        for record in self:
            name = 'New'
            question_title = record.question_title if record.question_title else 'Question'
            if record.subject_id:
                name = record.subject_id.code + ' -' + question_title
            res.append((record.id, name))
        return res

    @api.onchange('subject_id')
    def _get_topic(self):
        topic_list = []
        if self.subject_id:
            topics = self.env['cbt.subject.topic'].search([
                ('role_ids.employee_id.user_id', '=', self.current_user.id), ('subject_id', '=', self.subject_id.id)])
            if topics:
                for topic in topics:
                    topic_list.append(topic.id)
                return {'domain': {'topic_id': [('id', 'in', topic_list)]}}
            else:
                topics_else = self.env['cbt.subject.topic'].search(
                    [('subject_id', '=', self.subject_id.id)])
                for topic in topics_else:
                    topic_list.append(topic.id)
                return {'domain': {'topic_id': [('id', 'in', topic_list)]}}
        else:
            return {'domain': {'topic_id': [('id', 'in', topic_list)]}}

    @api.onchange('topic_id')
    def _get_subtopic(self):
        subtopic_list = []
        if self.subject_id and self.topic_id:
            subtopics = self.env['cbt.subject.subtopic'].search([
                ('role_ids.employee_id.user_id', '=', self.current_user.id), ('topic_id', '=', self.topic_id.id)])
            if subtopics:
                for subtopic in subtopics:
                    subtopic_list.append(subtopic.id)
                return {'domain': {'stopic_id': [('id', 'in', subtopic_list)]}}
            else:
                subtopics_else = self.env['cbt.subject.subtopic'].search(
                    [('topic_id', '=', self.topic_id.id)])
                for subtopic in subtopics_else:
                    subtopic_list.append(subtopic.id)
                return {'domain': {'stopic_id': [('id', 'in', subtopic_list)]}}
        else:
            return {'domain': {'stopic_id': [('id', 'in', subtopic_list)]}}

    def approve_question(self):
        current_login = self.env.user
        self.state = 'approved'
        self.reviewed_user = current_login

    def reject_question(self):
        current_login = self.env.user
        self.state = 'cancel'
        self.reviewed_user = current_login


class CBTQuestionattempdemo(models.Model):
    _name = 'cbt.question.attempt.demo'
    _description = 'Questions Attempt'

    paper_id_portal = fields.Integer('Paper ID', required=True)
    question_server_id = fields.Integer(string='Question Server ID')
    answer = fields.Char("Answer")


class CBTPaperattempdemo(models.Model):
    _name = 'cbt.paper.attempt.demo'
    _description = 'Paper Attempt'

    paper_id_portal = fields.Integer('Paper ID', required=True)
    paper_server_id = fields.Integer(string='paper Server ID')
    date = fields.Datetime(string='Date Created')





class CBTPaperSession(models.Model):
    _name = 'cbt.paper.session'
    _description = 'Paper Sessions'

    #session = fields.Encrypted()  # ,encrypt='session'
    paper_id = fields.Many2one('cbt.paper.export', string="Paper")
    name = fields.Char(string="Session Name")
    start_time = fields.Char(string="Start Time")
    end_time = fields.Char(string="End Time")
    