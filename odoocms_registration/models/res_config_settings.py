# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import pdb
from ast import literal_eval

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    allow_repeat_wo_fee = fields.Boolean(string='Allow Course Repeat before Fee Submit', config_parameter='odoocms_registration.allow_repeat_wo_fee')
    re_checking_subject_limit = fields.Integer(string='Re-Checking Subjects Limit', config_parameter='odoocms_registration.re_checking_subject_limit',default='1')
    
    allow_portal_course_del = fields.Boolean(string='Allow Course Deletion From Portal', config_parameter='odoocms_registration.allow_portal_course_del',default = False )

    repeat_allow_in_summer = fields.Boolean(string='Allow Repeat Courses in Summer', config_parameter='odoocms_registration.repeat_allow_in_summer')
    repeat_allow_in_winter = fields.Boolean(string='Allow Repeat Courses in Winter', config_parameter='odoocms_registration.repeat_allow_in_winter')

    show_faculty = fields.Boolean(string="Faculty information for Self Enrollment", config_parameter='odoocms_registration.show_faculty', default=False)
    show_class_strength = fields.Boolean(string="Class Strength for Self Enrollment", config_parameter='odoocms_registration.show_class_strength', default=False)
    absent_before_fee = fields.Boolean(string="Consider Absent before Fee", config_parameter='odoocms_registration.absent_before_fee', default=False)

    extra_credit_over_strength = fields.Integer(string='Extra Credit over Given Strength', config_parameter='odoocms_registration.extra_credit_over_strength',default='50')
    extra_two_credit_over_courses = fields.Integer(string='Extra Two Credits over Given Courses', config_parameter='odoocms_registration.extra_two_credit_over_courses',default='15')
    extra_one_credit_over_courses = fields.Integer(string='Extra Credit over Given Courses', config_parameter='odoocms_registration.extra_one_credit_over_courses',default='10')
    
    # @api.depends('predictive_lead_scoring_fields_str')
    # def _compute_pls_fields(self):
    #     """ As config_parameters does not accept m2m field,
	# 		we get the fields back from the Char config field, to ease the configuration in config panel """
    #     for setting in self:
    #         if setting.predictive_lead_scoring_fields_str:
    #             names = setting.predictive_lead_scoring_fields_str.split(',')
    #             fields = self.env['ir.model.fields'].search([('name', 'in', names), ('model', '=', 'crm.lead')])
    #             setting.predictive_lead_scoring_fields = self.env['crm.lead.scoring.frequency.field'].search([('field_id', 'in', fields.ids)])
    #         else:
    #             setting.predictive_lead_scoring_fields = None
    
    # @api.depends('no_registration_tags')
    # def _compute_no_registration_tags(self):
    #     """ As config_parameters does not accept m2m field,
    #         we get the fields back from the Char config field, to ease the configuration in config panel """
    #     for setting in self:
    #         if setting.no_registration_tags:
    #             codes = setting.no_registration_tags.split(',')
    #             tags = self.env['odoocms.student.tag'].search([('code', 'in', codes)])
    #             setting.no_registration_tag = tags
    #         else:
    #             setting.no_registration_tag = None
    #
    # def _inverse_no_registration_tags(self):
    #     """ As config_parameters does not accept m2m field,
    #     we store the fields with a comma separated string into a Char config field """
    #     for setting in self:
    #         if setting.no_registration_tag:
    #             setting.no_registration_tags = ','.join(setting.no_registration_tag.mapped('code'))
    #         else:
    #             setting.no_registration_tags = ''
