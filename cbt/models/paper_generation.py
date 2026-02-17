import re

from odoo import fields, models, _, api
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
from odoo.tools.safe_eval import safe_eval
import pdb
import math
from odoo.exceptions import AccessError, UserError, RedirectWarning, ValidationError, Warning

from odoo.http import content_disposition, Controller, request, route
import random

class CBTPaperGenerator(models.Model):
    _name = 'cbt.paper.generator'
    _description = 'Generate Paper'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    current_user = fields.Many2one(
        'res.users', 'Created By', default=lambda self: self.env.user, readonly="True")
    name = fields.Char(string='Paper Name', tracking=True, required=True,
                       readonly=True, states={'draft': [('readonly', False)]})
    criteria_id = fields.Many2one('cbt.paper.criteria', 'Paper Criteria', tracking=True,
                                  required=True, readonly=True, states={'draft': [('readonly', False)]})
    etest_id = fields.Many2one('cbt.test', 'Entry Test', tracking=True, readonly=True, states={
                               'draft': [('readonly', False)]})
    type_id = fields.Many2one('cbt.test.type', 'Test Type', tracking=True,
                              readonly=True, states={'draft': [('readonly', False)]})
    program_ids = fields.Many2many(
        'cbt.program', string='Programs', required=True, readonly=True, compute='_total_paper')
    configure_paper = fields.Boolean('Configure Paper', default=False)
    total_paper = fields.Integer(
        string="No of Papers",  compute='_total_paper', store=True)
    papers = fields.One2many('cbt.paper', 'generator_id',
                             string="Papers", tracking=True)
    # slot_id = fields.Many2one('cbt.slot', 'Session', required=True,
    #                           tracking=True, readonly=True, states={'draft': [('readonly', False)]})
    slot_ids = fields.Many2many('cbt.slot', string='Slots')
    state = fields.Selection(
        [('draft', 'Draft'), ('assign', 'Assign Student'), ('done', 'Done')], 'Status', default='draft')
    enable_repeat_question = fields.Boolean(
        'Enable Repeat Question', default=False)

    @api.depends('program_ids', 'criteria_id', 'slot_ids')
    def _total_paper(self):
        for rec in self:
            rec.etest_id = self.criteria_id.etest_id
            rec.type_id = self.criteria_id.type_id
            rec.write({
                'program_ids': [(4, program.id) for program in self.criteria_id.program_ids]
            })
            if not rec.configure_paper:
                participant_candidates = self.env['cbt.participant'].sudo().search(
                    [('program', 'in', rec.criteria_id.program_ids.ids), ('slot_id', 'in', rec.slot_ids.ids)])
                rec.total_paper = len(participant_candidates)

    def papers_generation(self):
        i = 1
        no_of_papers = self.total_paper
        tracked = self.env['cbt.question.repeat.track'].search(
            []).mapped('question_id')
        
        while (no_of_papers > 0):
            for slot_id in self.slot_ids:

                list = []
                for rules in self.criteria_id.rules_ids:

                    rules_id = []
                    rules_number = []
                    rules_remain_number = []
                    if not self.enable_repeat_question:
                        count_subject_questions = len(self.env['cbt.mcqs'].search(
                            [('subject_id', '=', rules.subjects.id), ('scenario_relation', '!=', 'child'), ('state', '=', 'approved'), ('id', 'not in', tracked.ids)]))
                    if self.enable_repeat_question:
                        count_subject_questions = len(self.env['cbt.mcqs'].search(
                            [('subject_id', '=', rules.subjects.id), ('scenario_relation', '!=', 'child'), ('state', '=', 'approved')]))

                    if count_subject_questions < int(rules.no_questions):
                        raise ValidationError(_(
                            "%s has less then " + rules.no_questions + " questions in question bank defined in paper criteria") % (
                            rules.subjects.name))

                    elif count_subject_questions >= int(rules.no_questions):
                        if self.env['cbt.mcqs'].search([('subject_id', '=', rules.subjects.id),('scenario_relation', '!=', 'child')]):
                            if not self.enable_repeat_question:
                                question_env_list = self.env['cbt.mcqs'].search(
                                    [('subject_id', '=', rules.subjects.id), ('state', '=', 'approved'),('scenario_relation', '!=', 'child'), ('id', 'not in', tracked.ids)])
                            if self.enable_repeat_question:
                                question_env_list = self.env['cbt.mcqs'].search(
                                    [('subject_id', '=', rules.subjects.id),('scenario_relation', '!=', 'child'), ('state', '=', 'approved')])

                            if not rules.difficulty_rules:
                                random_id = []
                                no_of_questions = rules.no_questions
                                while (no_of_questions):
                                    random.choice(question_env_list)  #question types
                                    list.append(random.choice(
                                        question_env_list).id)
                                    no_of_questions = int(no_of_questions) - 1
                            elif rules.difficulty_rules:
                                if not rules.topic_rules and not rules.type_rules:
                                    for rules_diff in rules.difficulty_rules:
                                        if not self.enable_repeat_question:
                                            count_subject_questions = len(self.env['cbt.mcqs'].search([('subject_id', '=', rules.subjects.id), ('state', '=', 'approved'), ('id', 'not in', tracked.ids),('scenario_relation', '!=', 'child'),
                                                                                                    ('difficulty_level_id', '=', rules_diff.difficulty_level_id.id)]))
                                        if self.enable_repeat_question:
                                            count_subject_questions = len(self.env['cbt.mcqs'].search([
                                                ('subject_id', '=', rules.subjects.id), ('state', '=', 'approved'),('scenario_relation', '!=', 'child'),
                                                                                                    ('difficulty_level_id', '=', rules_diff.difficulty_level_id.id)]))

                                        if count_subject_questions < int(rules_diff.no_questions):
                                            raise ValidationError(_(
                                                "%s has less then " + rules_diff.no_questions + " questions in question bank defined in difficulty rule in paper criteria ") % (
                                                rules.subjects.name))

                                        elif count_subject_questions >= int(rules_diff.no_questions):
                                            no_of_questions = rules_diff.no_questions
                                            while (no_of_questions):
                                                random_id = random.choice(question_env_list)
                                                if rules_diff.difficulty_level_id.id == random_id.difficulty_level_id.id:
                                                    value_bool = False
                                                    i_value = int(len(list))
                                                    while (i_value):
                                                        if int(list[i_value - 1]) == random_id.id:
                                                            value_bool = True
                                                            break
                                                        i_value = int(i_value) - 1
                                                    if value_bool == False:
                                                        list.append(random_id.id)
                                                        no_of_questions = int(no_of_questions) - 1

                                elif rules.topic_rules:
                                    for rules_diff in rules.difficulty_rules:
                                        rules_id.append(rules_diff.difficulty_level_id.id)
                                        rules_number.append(rules_diff.no_questions)
                                        rules_remain_number.append(rules_diff.no_questions)
                                    list_rules = [
                                        [0] * 3 for i in range(len(rules_id))]
                                    m = 0
                                    for i, j, k in zip(rules_id, rules_number, rules_remain_number):
                                        list_rules[m][0] = i
                                        list_rules[m][1] = j
                                        list_rules[m][2] = k
                                        m += 1
                                    for rules_topic in rules.topic_rules:
                                        if not self.enable_repeat_question:
                                            count_subject_questions = len(self.env['cbt.mcqs'].search(
                                                [('subject_id', '=', rules.subjects.id), ('state', '=', 'approved'),('scenario_relation', '!=', 'child'), ('id', 'not in', tracked.ids),
                                                    ('topic_id', '=', rules_topic.topic_id.id)]))
                                        if self.enable_repeat_question:
                                            count_subject_questions = len(self.env['cbt.mcqs'].search(
                                                [('subject_id', '=', rules.subjects.id), ('state', '=', 'approved'),('scenario_relation', '!=', 'child'),
                                                    ('topic_id', '=', rules_topic.topic_id.id)]))

                                        if count_subject_questions < int(rules_topic.no_questions):
                                            raise ValidationError(_(
                                                "%s topic " + rules_topic.topic_id.name + " has less then " + rules_topic.no_questions + " questions in question bank defined in topic rule in paper criteria ") % (
                                                rules.subjects.name))

                                        elif count_subject_questions >= int(rules_diff.no_questions):
                                            no_of_questions_topic = rules_topic.no_questions
                                            count_question = 0
                                            while (no_of_questions_topic):
                                                count = len(list_rules)
                                                while (count):
                                                    diff_list = list_rules[count - 1]
                                                    if int(diff_list[2]) != 0:
                                                        random_id = random.choice(
                                                            question_env_list)
                                                        if rules_topic.sub_topic_id:
                                                            if diff_list[0] == random_id.difficulty_level_id.id and rules_topic.topic_id.id == random_id.topic_id.id and rules_topic.sub_topic_id.id == random_id.stopic_id.id:
                                                                value_bool = False
                                                                i_value = int(len(list))
                                                                while (i_value):
                                                                    if int(list[i_value - 1]) == random_id.id:
                                                                        value_bool = True
                                                                        break
                                                                    i_value = int(
                                                                        i_value) - 1
                                                                if value_bool == False:
                                                                    list.append(
                                                                        random_id.id)
                                                                    list_rules[int(count) - 1][2] = str(
                                                                        int(diff_list[2]) - 1)
                                                                    list_rules[int(count) - 1][1] = str(
                                                                        int(diff_list[1]) - 1)
                                                                    count = int(
                                                                        count) - 1
                                                                    count_question = int(
                                                                        count_question) + 1
                                                                    if count_question == int(rules_topic.no_questions):
                                                                        count = 0
                                                        elif not rules_topic.sub_topic_id:
                                                            if not self.enable_repeat_question:
                                                                count_topic_questions = self.env['cbt.mcqs'].search(
                                                                    [('subject_id', '=', rules.subjects.id),
                                                                    ('state', '=',
                                                                    'approved'),('scenario_relation', '!=', 'child'),
                                                                    ('topic_id', '=',
                                                                    rules_topic.topic_id.id),
                                                                    ('id', 'not in',
                                                                    tracked.ids),
                                                                    ('difficulty_level_id', '=', diff_list[
                                                                        0])])
                                                            if self.enable_repeat_question:
                                                                count_topic_questions = self.env['cbt.mcqs'].search(
                                                                    [('subject_id', '=', rules.subjects.id),
                                                                    ('state', '=',
                                                                    'approved'),
                                                                     ('scenario_relation', '!=', 'child'),
                                                                    ('topic_id', '=',
                                                                    rules_topic.topic_id.id),
                                                                    ('difficulty_level_id', '=', diff_list[
                                                                        0])])

                                                            random_id = random.choice(count_topic_questions)
                                                            if count_topic_questions:
                                                                if diff_list[
                                                                        0] == random_id.difficulty_level_id.id and rules_topic.topic_id.id == random_id.topic_id.id:

                                                                    value_bool = False
                                                                    i_value = int(
                                                                        len(list))
                                                                    while (i_value):
                                                                        if int(list[i_value - 1]) == random_id.id:
                                                                            value_bool = True
                                                                            break
                                                                        i_value = int(
                                                                            i_value) - 1
                                                                    if value_bool == False:
                                                                        list.append(
                                                                            random_id.id)
                                                                        list_rules[int(count) - 1][2] = str(
                                                                            int(diff_list[2]) - 1)
                                                                        list_rules[int(count) - 1][1] = str(
                                                                            int(diff_list[1]) - 1)
                                                                        count = int(
                                                                            count) - 1
                                                                        count_question = int(
                                                                            count_question) + 1
                                                                        if count_question == int(rules_topic.no_questions):
                                                                            break
                                                            else:
                                                                raise ValidationError(
                                                                    _("Topic criteria defined not correct. There are less "
                                                                        "questions in question bank then the defined "
                                                                        "criteria."))
                                                    elif int(diff_list[2]) == 0:
                                                        count = int(count) - 1

                                                if count_question == int(rules_topic.no_questions):
                                                    no_of_questions_topic = 0

                                                else:
                                                    no_of_questions_topic = int(
                                                        no_of_questions_topic) - 1

                        else:
                            raise ValidationError(
                                _("%s has no questions as per paper criteria") % (rules.subjects.name))

                #sulman
                papers_data = {
                    # 'name': 'Paper ' + str(no_of_papers),
                    'name': self.name + ' '+  str(no_of_papers),
                    'questions': [(6, 0, list)],
                    'generator_id': self.id,
                    'slot_id': slot_id.id,
                    # 'discipline_id': self.criteria_id.discipline_id.id,
                }
                qes_en = self.env['cbt.paper'].create(papers_data)
                qes_en.write({
                    'program_ids': [(4, program.id) for program in self.criteria_id.program_ids]
                })
                self.env.cr.commit()
                for qes in list:
                    qustion_track = {
                        'question_id': qes,
                        'paper_id': qes_en.id,
                    }
                    self.env['cbt.question.repeat.track'].create(qustion_track)
                    self.env.cr.commit()

                no_of_papers = int(no_of_papers) - 1
            
        self.state = 'assign'



    def export_papers_to_cbt_portal(self):
        '''
        allocate papers to students
        '''
        # active_id = self.env.context.get('active_id')

        paper_generator = self.env['cbt.paper.generator'].sudo().search(
            [('id', '=', self.id)])

        participants = self.env['cbt.participant'].search(
            [('program', 'in', paper_generator.program_ids.ids), ('slot_id', 'in', paper_generator.slot_ids.ids)])
        if not participants:
            raise ValidationError(_(
            'Participants not found.'))
        paper_id = [paper.id for paper in paper_generator.papers]
        for participant in participants:
            
            already_paper_checked = self.env['cbt.paper.export'].sudo().search([('login','=',participant.login)])
            if already_paper_checked:
                for rec in already_paper_checked:
                    rec.paper_draft = True
                
            random.shuffle(paper_id)
            paper = paper_generator.papers.filtered(
                lambda x: x.id == paper_id[0])
            paper_id.pop(0)

            # question_list = [ques.id for ques in paper.questions]
            question_list = []

            for ques in paper.questions:
                if ques.scenario_relation == 'parent':
                    child_questions = self.env['cbt.mcqs'].search(
                        [('scenario_id', '=', ques.id), ('state', '=', 'approved')])
                    question_list.append(ques.id)
                    for child in child_questions:
                        # if not child.difficulty_level_id.id == ques.difficulty_level_id.id:
                        #     child.difficulty_level_id.id = ques.difficulty_level_id.id
                        question_list.append(child.id)
                else:
                    question_list.append(ques.id)
            # random.shuffle(question_list)
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
                'program': participant.program.name,
                'test_time': participant.slot_id.time,
                'test_duration': participant_paper.main_paper_id.slot_id.duration,
                'test_date': participant.slot_id.date,
                'login': participant.login,
                'cid': participant.cid,
            }
            if paper_generator.criteria_id.random_section:
                participant_test_data.update({
                    'shuffle_section': True,
                })
            participant_test = self.env['cbt.paper.export'].create(
                participant_test_data)
            participant_test.server_id = participant_paper.id
            server_id = participant_paper.id
            participant_test_question = []
            for rec in participant_paper.questions:
                question = rec.question
                subject = rec.subject_id.name
                test_paper_subject = self.env['cbt.subject.export'].search(
                    [('name', '=ilike', subject)], limit=1)
                if not test_paper_subject:
                    test_paper_subject = self.env['cbt.subject.export'].create({
                        'name': subject,
                    })
                correct_answer = ''

                if not rec.scenario_relation == 'parent':
                    if not rec.type_id.code == '3':
                        if rec.ans1_correct:
                            correct_answer = 'A'
                        if rec.ans2_correct:
                            correct_answer = 'B'
                        if rec.ans3_correct:
                            correct_answer = 'C'
                        if rec.ans4_correct:
                            correct_answer = 'D'
                        if rec.ans5_correct:
                            correct_answer = 'E'
                        if rec.ans6_correct:
                            correct_answer = 'F'
                        test_question = participant_test.line_ids.create({
                            'paper_id': participant_test.id,
                            'name': rec.question,
                            'server_id': rec.id,
                            'scenario_relation': rec.scenario_relation,
                            'subject_id': test_paper_subject.id,
                            'correct_answer': correct_answer,
                        })
                        options = [rec.ans1, rec.ans2, rec.ans3,
                                   rec.ans4, rec.ans5, rec.ans6]
                        opts = 0
                        for opt in options:
                            opts = opts + 1

                            if opts <= int(rec.option_quantity):
                                participant_test.line_ids.option_ids.create({
                                    'question_id': test_question.id,
                                    'name': opt,
                                    'server_id': test_question.id,
                                })
                if rec.scenario_relation == 'parent' or rec.type_id.code == '3':
                    test_question = participant_test.line_ids.create({
                        'paper_id': participant_test.id,
                        'name': rec.question,
                        'question_type': rec.type_id.code,
                        'scenario_relation': rec.scenario_relation,
                        'server_id': rec.id,
                        'subject_id': test_paper_subject.id,
                        'correct_answer': correct_answer,

                    })
                # test_question.answer = correct_answer

            self.env.cr.commit()
            paper.student_paper_gen = True
        self.state = 'done'

        return {
            'warning': {
                'title': 'Warning!',
                'message': 'The warning text'}

        }
