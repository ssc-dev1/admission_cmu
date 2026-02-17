# -*- coding: utf-8 -*-
import pdb
from odoo import models, fields, api, _
from datetime import datetime, date
import json
import logging

_logger = logging.getLogger(__name__)


class OdooCmsRegisterInherit(models.Model):
    _inherit = 'odoocms.admission.register'

    def write(self, vals):
        # ***** Updating Prospectus Challan Due Date ****#
        if 'prospectus_fee_due_date' in vals:
            prospectus_fee_due_date = vals['prospectus_fee_due_date']
            if prospectus_fee_due_date != self.prospectus_fee_due_date:
                domain = [('application_id.register_id', '=', self.id),
                          ('payment_state', '!=', 'paid'),
                          ('invoice_date_due', '<', prospectus_fee_due_date),
                          ('challan_type', '=', 'prospectus_challan'),
                          ('move_type', '=', 'out_invoice'),
                          ('program_id.prospectus_program_fee_date','=',False)
                          ]

                move_ids = self.env['account.move'].sudo().search(domain)
                if move_ids:
                    move_ids.sudo().write({'invoice_date_due': vals['prospectus_fee_due_date']})

        # Update First Challan Due Date
        if 'first_challan_due_date' in vals:
            first_challan_due_date = vals['first_challan_due_date']
            if first_challan_due_date != self.first_challan_due_date:
                domain = [('application_id.register_id', '=', self.id),
                          ('payment_state', '!=', 'paid'),
                          ('invoice_date_due', '<', first_challan_due_date),
                          ('challan_type', '=', 'admission'),
                          ('move_type', '=', 'out_invoice'),
                          ('program_id.prospectus_program_fee_date','=',False)
                          ]

                move_ids = self.env['account.move'].sudo().search(domain)
                if move_ids:
                    move_ids.sudo().write({'invoice_date_due': vals['first_challan_due_date']})

        return super(OdooCmsRegisterInherit, self).write(vals)


class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    # *************
    scholarship_ids_domain = fields.Char(compute="_compute_scholarship_domain", readonly=True, store=False)
    scholarship_ids = fields.Many2many('odoocms.fee.waiver', 'odoocms_application_scholarship_rel2', 'application_id', 'scholarship_id', 'Scholarships')
    scholarship_id = fields.Many2one('odoocms.fee.waiver', 'Availed Scholarship', compute='_compute_scholarship_id', store=True)

    faculty_id = fields.Many2one('odoocms.institute', 'Faculty', compute='_compute_applicant_faculty', store=True)
    faculty_code = fields.Char('Faculty Code')
    to_be = fields.Boolean('To Be')

    @api.depends('register_id', 'register_id.term_id')
    def _compute_scholarship_domain(self):
        for rec in self:
            s_list = []
            if rec.register_id:
                program_id = rec.preference_ids and rec.preference_ids[0].program_id
                if program_id:
                    scholarship_rec = self.env['odoocms.program.term.scholarship'].search([('term_id', '=', rec.register_id.term_id.id),
                                                                                           ('program_id', '=', program_id.id)])
                    if scholarship_rec:
                        s_list = scholarship_rec.scholarship_ids.ids
            rec.scholarship_ids_domain = json.dumps([('id', 'in', s_list)])

    def create_student(self, view=False, student_data={}):
        _logger.warning("Application NO: %s  is being processed for Student Profile Creation" % (self.application_no))
        result = super(OdooCMSAdmissionApplication, self).create_student(view=view, student_data=student_data)
        if self.scholarship_ids:
            student = self.student_id
            if not student:
                student = result
            for scholarship_id in self.scholarship_ids.filtered(lambda s: s.waiver_type.auto_type == 'auto'):
                program_term_scholarship_id = False
                student_program_id = student.program_id
                if not student_program_id:
                    student_program_id = self.preference_ids and self.preference_ids[0].program_id or False

                # if student_program_id:
                #     program_term_scholarship_id = self.env['odoocms.program.term.scholarship'].search([('program_id', '=', student_program_id.id),
                #                                                                                        ('term_id', '=', self.register_id.term_id.id),
                #                                                                                        ('scholarship_ids', 'in', [scholarship_id.id])])
                #     data_values = {
                #         'student_id': student and student.id or False,
                #         'student_code': student.code,
                #         'student_name': student.name,
                #         'program_id': student.program_id and student.program_id.id or False,
                #         'applied_term_id': self.register_id.term_id and self.register_id.term_id.id or False,
                #         'program_term_scholarship_id': program_term_scholarship_id and program_term_scholarship_id.id or False,
                #         'scholarship_id': scholarship_id.id,
                #         'scholarship_value': scholarship_id.line_ids and scholarship_id.line_ids[0].percentage or 0,
                #         'state': 'lock',
                #     }
                #     new_rec = self.env['odoocms.student.scholarship.eligibility'].create(data_values)

            # To Create History Record
            # self.create_availed_scholarship_history()
            self.student_id.scholarship_id = self.scholarship_id and self.scholarship_id.id or False
        return result

    @api.depends('scholarship_ids')
    def _compute_scholarship_id(self):
        for rec in self:
            if rec._origin.scholarship_ids:
                sorted_scholarships = rec._origin.scholarship_ids.line_ids.sorted(key=lambda line: line.percentage, reverse=True)
                rec._origin.scholarship_id = sorted_scholarships and sorted_scholarships[0].waiver_id.id or False
            if not rec._origin.scholarship_ids:
                rec._origin.scholarship_id = False

    def create_availed_scholarship_history(self):
        for rec in self:
            if rec.scholarship_id:
                data_values = {
                    'student_id': rec.student_id and rec.student_id.id or False,
                    'student_code': rec.student_id and rec.student_id.code or '',
                    'student_name': rec.student_id and rec.student_id.name,
                    'program_id': rec.student_id.program_id and rec.student_id.program_id.id or False,
                    'term_id': rec.register_id.term_id and rec.register_id.term_id.id or False,
                    'scholarship_id': rec.scholarship_id and rec.scholarship_id.id or False,
                    'scholarship_percentage': rec.scholarship_id.amount,
                    'current': True,
                    'state': 'lock',
                }
                new_rec = self.env['odoocms.student.applied.scholarships'].sudo().create(data_values)

    def write(self, values):
        if values.get('scholarship_ids', False):
            old_scholarship_list = self.scholarship_ids
            new_scholarship_list = self.env['odoocms.fee.waiver'].browse(values['scholarship_ids'][0][1])
            added_title = "Following Scholarships are Added "
            dropped_title = "Following Scholarships Are Dropped "
            added_body = ''
            dropped_body = ''

            for new_scholarship_list1 in new_scholarship_list:
                if new_scholarship_list1 not in old_scholarship_list:
                    added_body = added_body + ", " + new_scholarship_list1.name

            for old_scholarship_list1 in old_scholarship_list:
                if old_scholarship_list1 not in new_scholarship_list:
                    dropped_body = dropped_body + ", " + old_scholarship_list1.name

            if len(added_body) > 1:
                added_body = added_title + added_body
                self.message_post(body=added_body)

            if len(dropped_body) > 1:
                dropped_body = dropped_title + dropped_body
                self.message_post(body=dropped_body)

        res = super(OdooCMSAdmissionApplication, self).write(values)
        return res

    @api.depends('prefered_program_id')
    def _compute_applicant_faculty(self):
        for rec in self:
            institute = rec.prefered_program_id.institute_id
            rec.faculty_id = institute.id if institute else False
            rec.faculty_code = institute.code if institute else ''
