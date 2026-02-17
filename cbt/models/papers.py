import re
from odoo import fields, models, _, api
import pdb
import math
from odoo.exceptions import UserError, ValidationError, Warning
import random


class CBTPaper(models.Model):
    _name = 'cbt.paper'
    _description = 'Paper'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    current_user = fields.Many2one('res.users', 'Created By', default=lambda self: self.env.user, readonly="True")
    name = fields.Char(string='Paper Name', tracking=True, required=True)
    generator_id = fields.Many2one('cbt.paper.generator', 'Paper Generation', tracking=True, required=True)
    questions = fields.Many2many('cbt.mcqs', 'paper_questions_rel', 'paper_id', 'questions_id',
                                 string='Entry Test', tracking=True)
    slot_id = fields.Many2one('cbt.slot', 'Session', required=True, tracking=True)
    # program_id = fields.Many2one('cbt.program', 'Test program', tracking=True)
    program_ids = fields.Many2many('cbt.program', string='Programs')
    number_of_questions = fields.Integer('Total Questions', compute='_count_total_questions', store=True)
    student_paper_gen = fields.Boolean('Student Paper Generated', default=False)

    @api.depends('generator_id')
    def _count_total_questions(self):
        count = 0
        for rec in self:
            for count_ques in rec.questions:
                count = count + 1
        self.number_of_questions = count

    def generate_student_paper(self):
        question_list = []


        for ques in self.questions:
            if ques.scenario_relation == 'parent':
                child_questions = self.env['cbt.mcqs'].search([('scenario_id','=',ques.id),('state', '=', 'approved')])
                question_list.append(ques.id)
                for child in child_questions:
                    # if not child.difficulty_level_id.id == ques.difficulty_level_id.id:
                    #     child.difficulty_level_id.id = ques.difficulty_level_id.id
                    question_list.append(child.id)
            else:
                question_list.append(ques.id)
        participants = self.env['cbt.participant'].search(
            [('program','in',self.program_ids.ids),('slot_id','=',self.slot_id.id)])

        if not participants:
            raise ValidationError(_('Participants/Candidates not available'))
        for participant in participants:

            # random.shuffle(question_list)
            papers_data = {
                'main_paper_id': self.id,
                'questions': [(6, 0, question_list)],
                'participant_id': participant.id,
            }
            self.env['cbt.student.paper'].create(papers_data)
            self.env.cr.commit()
            self.student_paper_gen = True
