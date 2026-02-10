import pdb
from itertools import count

from odoo import fields, models, _, api
from odoo.exceptions import UserError


class EntryTestSchedule(models.Model):
    _name = 'odoocms.entry.test.schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Entry Test Schedule'
    _rec_name = 'entry_test_room_id'

    entry_test_room_id = fields.Many2one('odoocms.entry.test.room', string='Room')
    entry_test_slots_id = fields.Many2one('odoocms.entry.test.slots', string='Slots')
    sequence = fields.Integer('Sequence')
    programs = fields.Many2many('odoocms.program', 'entry_schedule_program_rel',
                                'slot_id', 'program_id', string='Programs', compute='_get_program')
    date = fields.Date(string='Date')
    room_capacity = fields.Integer(related='entry_test_room_id.capacity', string='Room Capacity')
    entry_test_schedule_ids = fields.One2many('odoocms.entry.schedule.details', 'entry_schedule_id')
    count = fields.Integer('Count', compute='_get_applicant_record', store=True)
    capacity_added = fields.Integer('Capacity Added',compute='_compute_capacity_added')
    register_id = fields.Many2one('odoocms.admission.register', string='Register')
    slot_type = fields.Selection(string='Slot Type',
        selection=[('interview', 'interview'),('test', 'Test'), ], required=False, )

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    @api.onchange('entry_test_room_id', 'entry_test_schedule_ids')
    def _get_program(self):
        for rec in self:
            program_ids = []
            for sch in rec.entry_test_schedule_ids:
                program_ids.append(sch.program_id.id)
            rec.programs = [(6, 0, program_ids)]

    @api.constrains('entry_test_room_id', 'entry_test_schedule_ids')
    # @api.onchange('entry_test_room_id', 'entry_test_schedule_ids')
    def sum_capacity(self):
        total = 0
        # for rec in self:
        # for entry in self.entry_test_schedule_ids:
        total = sum(entry.capacity for entry in self.entry_test_schedule_ids)
        if total >= self.entry_test_room_id.capacity:
            raise UserError(_("Capacity is full."))
    
    def _compute_capacity_added(self):
        for rec in self:
            rec.capacity_added = sum(rec.entry_test_schedule_ids.mapped('capacity'))

    @api.model
    def create(self, values):
        record = super(EntryTestSchedule, self).create(values)
        if not record.sequence:
            record.sequence = self.env['ir.sequence'].next_by_code(
                'entry.test')
        return record

    def action_view_candidate(self):
        candidates = self.env['applicant.entry.test']
        # for rec in self:
        # candidates.search([('')])
        subject_list = candidates
        for entry in self.entry_test_schedule_ids:
            subjects = self.env['applicant.entry.test'].search([
                ('entry_test_schedule_details_id.program_id',
                 '=', entry.program_id.id),
                ('room', '=', self.entry_test_room_id.name), ('slots', '=', self.entry_test_slots_id.id),
                ('date', '=', self.date)])
            subject_list += subjects

        # for rec in self
        if subjects:
            candidate_list = subject_list.mapped('id')
            return {
                'domain': [('id', 'in', candidate_list)],
                'name': _('Classes'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'applicant.entry.test',
                'view_id': False,
                'type': 'ir.actions.act_window'
            }

    @api.depends('entry_test_schedule_ids.capacity','entry_test_schedule_ids.count')
    def _get_applicant_record(self):
        for rec in self:
            rec.count = 0
            count_rec = 0
            for entry in rec.entry_test_schedule_ids:
                subjects = self.env['applicant.entry.test'].search([
                    ('entry_test_schedule_details_id.program_id', '=', entry.program_id.id),
                    ('room', '=', rec.entry_test_room_id.name),
                    ('slots', '=', rec.entry_test_slots_id.id),
                    ('date', '=', rec.date)])

                count_rec = count_rec + entry.count
                rec.count = count_rec
                if entry.status in ('open', 'full','initialize'):
                    entry.count = len(subjects)
                    if entry.capacity <= entry.count:
                        entry.status = 'full'
                        
                    # else:
                    #     entry.status = 'open'


class EntryTestScheduleDetails(models.Model):
    _name = 'odoocms.entry.schedule.details'
    _description = 'Entry Test Schedule Details'
    _rec_name = 'program_id'

    capacity = fields.Integer(string='Capacity')
    sequence = fields.Integer('Sequence')
    program_id = fields.Many2one('odoocms.program', string='Program')
    entry_schedule_id = fields.Many2one('odoocms.entry.test.schedule', ondelete='cascade')
    status = fields.Selection(
        string='Status',
        selection=[('open', 'Open'),
                   ('initialize', 'Initialize'),
                   ('full', 'Full'), ('close', 'Close')
                   ],
        default='initialize')
    count = fields.Integer('Count')

    @api.model
    def create(self, values):
        record = super(EntryTestScheduleDetails, self).create(values)
        if record and record.capacity == record.count:
            record.status ='full'
        if not record.sequence:
            record.sequence = self.env['ir.sequence'].next_by_code(
                'entry.test')
        return record

    # def write(self,values):
    #     record = super(EntryTestScheduleDetails, self).write(values)
    #     if record and record.capacity == record.count:
    #         record.status ='full'
    #     return record

    # @api.constrains('count')
    # def test_schedule_count_constrains(self):
    #     if self.count > self.capacity:
    #         raise UserError(_("Capacity is full."))