# -*- coding: utf-8 -*-
import pdb

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from ...cms_process.models import main as main
import logging

_logger = logging.getLogger(__name__)


class OdoocmsAdvanceToMainRegistrationWiz(models.TransientModel):
    _name = 'odoocms.advance.to.main.registration.wiz'
    _description = 'Advance to Main Registration'

    @api.model
    def _get_current_term(self):
        term_id, term = main.get_current_term(self)
        return term_id and term_id.id or False

    date = fields.Date('Date', default=fields.Date.today())
    current_term_id = fields.Many2one('odoocms.academic.term', string='Current Term', default=_get_current_term)
    registration_term_id = fields.Many2one('odoocms.academic.term', string='Registration Term')
    institute_ids = fields.Many2many('odoocms.institute', 'advance_to_main_reg_institute_rel', 'wiz_id', 'institute_id', 'Institute/Schools')
    department_ids = fields.Many2many('odoocms.department', 'advance_to_main_reg_department_rel', 'wiz_id', 'department_id', 'Departments/Faculties')
    program_ids = fields.Many2many('odoocms.program', 'advance_to_main_reg_program_rel', 'wiz', 'program_id', 'Programs')
    registration_ids = fields.Many2many('odoocms.course.registration', 'advance_to_main_reg_registration_rel', 'wiz_id', 'registration_id', 'Registrations')

    def action_advance_to_main_registration_funct(self):
        # ***** Check required fields *****#
        if not self.current_term_id:
            raise UserError(_('Please Select Current Active Term'))
        if not self.registration_term_id:
            raise UserError(_('Please Select Registration Term'))

        # ***** Search for course registrations *****#
        registration_domain = [('term_id', '=', self.current_term_id.id), ('state', '!=', 'cancel')]
        # exclude_students = self.env['odoocms.course.registration'].sudo().search(registration_domain).mapped('student_id')

        if self.registration_ids:
            # registration_recs = self.registration_ids.filtered(lambda a: a.student_id not in exclude_students)
            registration_recs = self.registration_ids
        else:
            # ***** Build the domain for registration search ***** #
            build_domain = [('term_id', '=', self.registration_term_id.id), ('state', '=', 'draft'), ('generate_fee', '=', True)]

            # *****Add additional conditions if relevant fields are set *****#
            if self.institute_ids:
                build_domain.append(('program_id.institute_id', 'in', self.institute_ids.ids))
            if self.department_ids:
                build_domain.append(('program_id.department_id', 'in', self.department_ids.ids))
            if self.program_ids:
                build_domain.append(('program_id', 'in', self.program_ids.ids))
            # if exclude_students:
            #     build_domain.append(('student_id', 'not in', exclude_students.ids))

            registration_recs = self.env['odoocms.course.registration'].sudo().search(build_domain)

        n = 0
        for registration_rec in registration_recs:
            n += 1
            _logger.info('***Record No %s Out of %s in process', n, len(registration_recs))
            registration_rec.sudo().action_submit()

            registration_rec.write({
                'enrollment_type': 'advance_enrollment',
                'generate_fee': False
            })

        if registration_recs:
            registration_list = registration_recs.mapped('id')
            form_view = self.env.ref('odoocms_registration.view_odoocms_course_registration_form')
            tree_view = self.env.ref('odoocms_registration.view_odoocms_course_registration_tree')
            return {
                'domain': [('id', 'in', registration_list)],
                'name': _('Invoices'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'odoocms.course.registration',
                'view_id': False,
                'views': [
                    (tree_view and tree_view.id or False, 'tree'),
                    (form_view and form_view.id or False, 'form'),
                ],
                'type': 'ir.actions.act_window'
            }
        else:
            return {'type': 'ir.actions.act_window_close'}
