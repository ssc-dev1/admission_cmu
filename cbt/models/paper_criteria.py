import re

from odoo import fields, models, _, api
import pdb
import math
from odoo.exceptions import UserError, ValidationError, Warning
import random


class CBTGeneratePaper(models.Model):
    _name = 'cbt.paper.criteria'
    _description = 'Paper Criteria'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    current_user = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user, readonly="True")
    name = fields.Char(string='Paper Criteria Name', tracking=True)
    duration = fields.Char(string='Duration (Minutes)', tracking=True)
    etest_id = fields.Many2one('cbt.test', 'Entry Test', tracking=True)
    type_id = fields.Many2one('cbt.test.type', 'Test Type', tracking=True)
    program_ids = fields.Many2many('cbt.program', string='Test Program')    
    total_questions = fields.Char(string='Total Questions', tracking=True)
    random_section = fields.Boolean('Random Section',default=False)
    total_questions_compute = fields.Char()
    rules_ids = fields.One2many('cbt.paper.criteria.rule', 'paper_id', string='Rules ID', required="True",
                                tracking=True)

    @api.model
    def create(self, vals):
        result = super().create(vals)
        if vals.get('total_questions') != vals.get('total_questions_compute'):
            raise UserError(_("Number of questions in subject should be equal to total number of questions"))
        else:
            return result

    @api.onchange('rules_ids')
    def change_total_question_lines(self):
        count = 0
        for each in self.rules_ids:
            count = count + int(each.no_questions)
        self.total_questions_compute = str(count)


class CBTPaperCriteriaRule(models.Model):
    _name = 'cbt.paper.criteria.rule'
    _description = 'Paper rules'

    subjects = fields.Many2one('cbt.subject', 'Subjects', required=True)
    topic_rules = fields.One2many('cbt.paper.criteria.rule.topic', 'criteria_rule_id', 'Topic Rules')
    difficulty_rules = fields.One2many('cbt.paper.criteria.rule.difficulty', 'criteria_rule_id', 'Paper Difficulty',
                                       required=True)
    type_rules = fields.One2many('cbt.paper.criteria.rule.type', 'criteria_rule_id', 'Type')
    # topics = fields.Many2one('cbt.subject.topic', 'Topics')
    # sub_topics = fields.Many2one('cbt.subject.subtopic', 'Sub Topics')
    # difficulty_level_id = fields.Many2one('cbt.question.difficulty.level', 'Difficulty Level')
    no_questions = fields.Char(string='Number of Questions', required=True)
    total_questions_difficulty_rule = fields.Char()
    total_questions_topic_rule = fields.Char()
    paper_id = fields.Many2one('cbt.paper.criteria', 'Paper ID')
    sequence = fields.Integer('Section Sequence', required=True, default=1)
    subjects = fields.Many2one('cbt.subject', 'Sections', required=True)


    @api.model
    def create(self, vals):
        result = super().create(vals)
        if not vals.get('difficulty_rules'):
            raise UserError(_("Please Define Paper Difficulty Criteria in Paper Rules"))
        elif vals.get('no_questions') != vals.get('total_questions_difficulty_rule'):
            raise ValidationError(_("Number of Questions in Subject and Difficult Level Criteria should be equal"))
        elif vals.get('topic_rules'):
            if vals.get('no_questions') != vals.get('total_questions_topic_rule'):
                raise ValidationError(_("Number of Questions in Subject and Topics/Subtopics Criteria should be equal"))

        return result

    @api.onchange('difficulty_rules')
    def change_total_question_lines(self):
        count = 0
        for difficulty_rule in self.difficulty_rules:
            count = count + int(difficulty_rule.no_questions)
        self.total_questions_difficulty_rule = str(count)

    @api.onchange('topic_rules')
    def change_total_questions_topics_lines(self):
        count = 0
        for topic_rule in self.topic_rules:
            count = count + int(topic_rule.no_questions)
        self.total_questions_topic_rule = str(count)

    def write(self, vals):
        result = super().write(vals)
        if not self.difficulty_rules:
            raise UserError(_("Please Define Paper Difficulty Criteria in Paper Rules"))
        elif self.no_questions != self.total_questions_difficulty_rule:
            raise ValidationError(_("Number of Questions in Subject and Difficult Level Criteria should be equal"))
        elif self.topic_rules:
            if self.no_questions != self.total_questions_topic_rule and int(self.total_questions_topic_rule) > 0:
                raise ValidationError(_("Number of Questions in Subject and Topics/Subtopics Criteria should be equal"))

        return result


class CBTPaperCriteriaRuleTopic(models.Model):
    _name = 'cbt.paper.criteria.rule.topic'
    _description = 'Paper Rule Topic'

    topic_id = fields.Many2one('cbt.subject.topic', 'Topic')
    sub_topic_id = fields.Many2one('cbt.subject.subtopic', 'Sub Topic')
    difficulty_level_id = fields.Many2one('cbt.question.difficulty.level', 'Difficulty Level')
    criteria_rule_id = fields.Many2one('cbt.paper.criteria.rule', 'Criteria Rule')
    no_questions = fields.Char(string='Number of Questions', required=True)
    subjects = fields.Many2one(related='criteria_rule_id.subjects')




class CBTPaperCriteriaRuleDifficulty(models.Model):
    _name = 'cbt.paper.criteria.rule.difficulty'
    _description = 'Paper Rule Difficulty'

    difficulty_level_id = fields.Many2one('cbt.question.difficulty.level', 'Difficulty Level', required=True)
    criteria_rule_id = fields.Many2one('cbt.paper.criteria.rule', 'Criteria Rule')
    no_questions = fields.Char(string='Number of Questions', required=True)


class CBTPaperCriteriaRuleType(models.Model):
    _name = 'cbt.paper.criteria.rule.type'
    _description = 'Paper Rule Type'

    type_id = fields.Many2one('cbt.question.type', 'Type')
    criteria_rule_id = fields.Many2one('cbt.paper.criteria.rule', 'Criteria Rule')
    no_questions = fields.Char(string='Number of Questions', required=True)
