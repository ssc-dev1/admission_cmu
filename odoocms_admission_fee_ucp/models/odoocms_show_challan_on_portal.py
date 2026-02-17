# -*- coding: utf-8 -*-
import pdb
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdoocmsShowChallanOnPortal(models.Model):
    _name = 'odoocms.show.challan.on.portal'
    _description = 'Show Challan On Portal'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    date = fields.Date('Date', default=fields.Date.today(), tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term, tracking=True)
    faculty_type = fields.Selection([('Faculty', 'Select Faculty ...'),
                                     ('All', 'All Faculties'),
                                     ], default='Faculty', tracking=True, index=True, string="Faculty Selection")
    program_selection_type = fields.Selection([('Program', 'Select Program ...'),
                                               ('All', 'All Program'),
                                               ], default='Program', string='Program Selection', tracking=True, index=True)

    faculty_ids = fields.Many2many(comodel_name='odoocms.institute',
                                   relation="show_challan_on_portal_institute_rel1",
                                   column1="show_challan_on_portal_id",
                                   column2="institute_id",
                                   string='Faculties')

    program_ids = fields.Many2many(comodel_name='odoocms.program',
                                   relation="show_challan_on_portal_program_rel1",
                                   column1="show_challan_on_portal_id",
                                   column2="program_id",
                                   string='Programs')

    state = fields.Selection([('draft', 'New'),
                              ('confirm', 'Confirmed'),
                              ('cancel', 'Cancel')
                              ], string='Status', default='draft', tracking=True)

    type = fields.Selection([('main_challan', 'Main Challan'),
                             ('2nd_challan', '2nd Challan'),
                             ('admission', 'New Admission'),
                             ('admission_2nd_challan', 'Admission 2nd Challan'),
                             ('add_drop', 'Add Drop'),
                             ('prospectus_challan', 'Prospectus Challan'),
                             ('hostel_fee', 'Hostel Fee'),
                             ('misc_challan', 'Misc Challan'),
                             ('installment', 'Installment'),
                             ], string='Type', tracking=True)

    lines = fields.One2many('odoocms.show.challan.on.portal.line', 'show_line', 'Lines')
    to_be = fields.Boolean('To Be', default=True)
    challan_cnt = fields.Integer('Show Challan Count')
    challan_hide_cnt = fields.Integer('Hide Challan Count')
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    def action_confirm(self):
        self.action_generate_detail()
        program_ids = self.lines.mapped('program_id').ids
        faculty_ids = self.lines.mapped('faculty_id').ids
        students = self.env['odoocms.student'].search([('program_id', 'in', program_ids), ('institute_id', 'in', faculty_ids)])
        challans = self.env['account.move'].search([
            ('student_id', 'in', students.ids),
            ('term_id', '=', self.term_id.id),
            ('challan_type', '=', self.type),
            ('payment_state', 'not in', ('in_payment', 'paid'))])
        challans.write({'show_challan_on_portal': True})
        cnt = len(challans)
        self.write({'state': 'confirm', 'challan_cnt': cnt})
        self.lines.write({'state': 'confirm'})

    def action_cancel(self):
        self.state = 'cancel'
        self.lines.write({'state': 'cancel'})

    @api.model
    def create(self, values):
        result = super(OdoocmsShowChallanOnPortal, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.show.challan.on.portal')
        return result

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('You can delete the Records that are in the Draft State.'))
        return super(OdoocmsShowChallanOnPortal, self).unlink()

    def action_generate_detail(self):
        for rec in self:
            faculties_ids = self.env['odoocms.institute'].search([], order='id asc')
            if rec.faculty_type == "Faculty":
                if not self.faculty_ids:
                    raise UserError(_('Please Select Faculties'))
                faculties_ids = self.faculty_ids

            for faculties_id in faculties_ids:
                program_ids = self.env['odoocms.program'].search([('institute_id', '=', faculties_id.id)])
                if rec.program_selection_type == "Program":
                    if not self.program_ids:
                        raise UserError(_('Please Select Programs'))
                    program_ids = self.program_ids

                for program_id in program_ids:
                    data_values = {
                        'show_line': rec.id,
                        'faculty_id': faculties_id.id,
                        'program_id': program_id.id,
                        'term_id': rec.term_id.id,
                        'type': rec.type,
                        'state': rec.state,
                        'date': rec.date,
                    }
                    self.env['odoocms.show.challan.on.portal.line'].create(data_values)

    def action_hide_from_portal(self):
        cnt = 0
        for line in self.lines:
            students = self.env['odoocms.student'].search([('program_id', '=', line.program_id.id), ('institute_id', '=', line.faculty_id.id)])
            challans = self.env['account.move'].search([('student_id', 'in', students.ids),
                                                        ('term_id', '=', self.term_id.id),
                                                        ('challan_type', '=', self.type),
                                                        ('payment_state', 'not in', ('in_payment', 'paid')),
                                                        ('show_challan_on_portal', '=', True)])
            if challans:
                challans.write({'show_challan_on_portal': False})
                cnt += len(challans)
        self.write({'challan_hide_cnt': cnt, 'state': 'draft'})


class OdoocmsShowChallanOnPortalLine(models.Model):
    _name = 'odoocms.show.challan.on.portal.line'
    _description = 'Show Challan On Portal Detail'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name')
    sequence = fields.Integer('Sequence', default=10)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', tracking=True)
    faculty_id = fields.Many2one('odoocms.institute', 'Faculty', tracking=True)
    faculty_name = fields.Char(related='faculty_id.code', string="Faculty Name", store=True)
    program_id = fields.Many2one('odoocms.program', 'Program')
    program_name = fields.Char(related='program_id.code', string='Program Name', store=True)
    date = fields.Date('Date', tracking=True)
    type = fields.Selection([('main_challan', 'Main Challan'),
                             ('2nd_challan', '2nd Challan'),
                             ('admission', 'New Admission'),
                             ('admission_2nd_challan', 'Admission 2nd Challan'),
                             ('add_drop', 'Add Drop'),
                             ('prospectus_challan', 'Prospectus Challan'),
                             ('hostel_fee', 'Hostel Fee'),
                             ('misc_challan', 'Misc Challan'),
                             ('installment', 'Installment')
                             ], string='Type', tracking=True)

    state = fields.Selection([('draft', 'New'),
                              ('confirm', 'Confirmed'),
                              ('cancel', 'Cancel')
                              ], string='Status', default='draft', tracking=True)
    show_line = fields.Many2one('odoocms.show.challan.on.portal', 'Show On Portal Main Ref', index=True, ondelete='cascade', auto_join=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=False)

    @api.model
    def create(self, values):
        result = super(OdoocmsShowChallanOnPortalLine, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.show.challan.on.portal.line')
        return result
