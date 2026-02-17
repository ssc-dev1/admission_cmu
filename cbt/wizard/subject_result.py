import odoo
from odoo import fields, models, _, api, http
import xmlrpc.client
import pdb


class CBTGetSubjectResult(models.Model):
    _name = 'cbt.get.subject.result'

    def get_subject_result(self):
        student_result = self.env['cbt.paper.conduct'].search([])
        for result in student_result:
            result.subject_wise_score()
