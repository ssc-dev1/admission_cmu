from datetime import date
from odoo import fields, models, api, _
from odoo.osv import expression
import pdb


class OdooCMSSectionPattern(models.Model):
    _name = "odoocms.section.pattern"
    _description = "CMS Section Pattern"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Pattern Name', required=True)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean(default=True)
    line_ids = fields.One2many('odoocms.section.pattern.line','pattern_id')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSSectionPatternLine(models.Model):
    _name = "odoocms.section.pattern.line"
    _description = "CMS Section Pattern Line"
    
    name = fields.Char(string='Section Name', required=True)
    sequence = fields.Integer('Sequence')
    pattern_id = fields.Many2one('odoocms.section.pattern','Section Pattern')
    
    
class OdooCMSBatch(models.Model):
    _name = 'odoocms.batch'
    _description = "Program Batches"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence desc'

    name = fields.Char(string='Name', compute='_get_name_code', store=True)
    code = fields.Char(string="Code", compute='_get_name_code', store=True)
    
    sequence = fields.Integer('Sequence')
    color = fields.Integer(string='Color Index')
    short_code = fields.Char('Short Code')
    department_id = fields.Many2one('odoocms.department', string="Department/Center", required=True, ondelete='restrict')
    institute_id = fields.Many2one("odoocms.institute", string="Faculty/Institute",related='department_id.institute_id',store=True)
    career_id = fields.Many2one('odoocms.career', string="Career/Degree Level", required=True, ondelete='restrict')
    program_id = fields.Many2one('odoocms.program', string="Program", required=True, ondelete='restrict')
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year', required=True, ondelete='restrict')
    
    term_id = fields.Many2one('odoocms.academic.term', 'Current Term')   # needs to remove
    semester_id = fields.Many2one('odoocms.semester', 'Semester')   # needs to remove
    
    term_line = fields.Many2one('odoocms.academic.term.line','Term Schedule',compute='get_term_line',store=True)    # need update in function by passing term_id
    user_ids = fields.Many2many('res.users', 'batch_user_access_rel', 'batch_id', 'user_id', 'Users', domain="[('share','=', False)]")

    building_id = fields.Many2one('odoocms.building', 'Building')
    floor_ids = fields.Many2many('odoocms.building.floor','batch_floor_rel','batch_id','floor_id','Floors')
    room_type = fields.Many2one('odoocms.room.type', 'Room Type')
    room_ids = fields.Many2many('odoocms.room', 'batch_room_rel', 'bath_id', 'room_id', 'Rooms')
    
    study_scheme_id = fields.Many2one('odoocms.study.scheme', 'Study Scheme', required=True, ondelete='restrict')
    batch_number = fields.Integer('Batch Number')
    vis_required = fields.Boolean('VIS Tag Required', default=True)
    to_be = fields.Boolean(default=False)
    active = fields.Boolean(default=True)
    can_sync = fields.Boolean('Can Sync', default=False)
    requirement_ids = fields.One2many('odoocms.batch.requirement', 'batch_id', 'Requirements')
    company_id = fields.Many2one('res.company', string='Company', related='department_id.company_id', store=True)

    _sql_constraints = [
        ('name', 'unique(name)', "Name already exists for some other Batch!"),
        ('code', 'unique(code)', "Code already exists for some other Batch!"),
    ]
    
    @api.depends('program_id', 'session_id','short_code')
    def _get_name_code(self):
        for rec in self:
            if rec.program_id and rec.session_id:
                batch_code = rec.program_id.code + '-' + rec.session_id.code
                batch_name = rec.program_id.code + '-' + rec.session_id.code
                if rec.short_code:
                    batch_code = batch_code + '-' + rec.short_code
                    batch_name = batch_name + '-' + rec.short_code
                rec.code = batch_code
                rec.name = batch_name

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    def copy_requirements(self):
        requirements = self.env['odoocms.program.requirement'].search([('program_id', '=', self.program_id.id)])
        for requirement in requirements:
            # if not self.requirement_ids.filtered(lambda l: l.code == plo.code):
            data = {
                'batch_id': self.id,
                'category_id': requirement.category_id.id,
                'sub_category_id': requirement.sub_category_id.id,
                'credits': requirement.credits,
                'mandatory': requirement.mandatory
            }
            self.env['odoocms.batch.requirement'].create(data)

    @api.depends('term_id.term_lines')
    def get_term_line(self):
        for batch in self:
            term_line = self.env['odoocms.academic.term.line']
            for rec in batch.term_id.term_lines.sorted(key=lambda s: s.sequence,reverse=False):
                term_line = rec
                if rec.campus_ids and batch.program_id.campus_id not in rec.campus_ids:
                    continue
                elif rec.institute_ids and batch.program_id.department_id.institute_id not in rec.institute_ids:
                    continue
                elif rec.career_ids and batch.career_id not in rec.career_ids:
                    continue
                elif rec.program_ids and batch.program_id not in rec.program_ids:
                    continue
                elif rec.batch_ids and batch not in rec.batch_ids:
                    continue
                else:
                    break
            batch.term_line = term_line and term_line.id or False

    def getermline(self, term_id):
        batch = self.sudo()
        term_line = self.env['odoocms.academic.term.line']
        for rec in term_id.term_lines.sorted(key=lambda s: s.sequence, reverse=False).sudo():
            if rec.campus_ids and batch.program_id.campus_id not in rec.campus_ids:
                continue
            elif rec.institute_ids and batch.program_id.department_id.institute_id not in rec.institute_ids:
                continue
            elif rec.career_ids and batch.career_id not in rec.career_ids:
                continue
            elif rec.program_ids and batch.program_id not in rec.program_ids:
                continue
            elif rec.batch_ids and batch not in rec.batch_ids:
                continue
            else:
                term_line = rec
                break
        return term_line
            
    def can_apply(self, event, term_id=None, date_request =None, admin=False):
        today = date.today() if not date_request else date_request
        can_apply = False
        term_line = self.getermline(term_id) if term_id else self.term_line
        planning_id = term_line.planning_ids.filtered(lambda l: l.type == event)
        if planning_id and (planning_id.date_start <= today <= planning_id.date_end):
            can_apply = True
        if admin and planning_id:
            date_start = planning_id.date_start_admin or planning_id.date_start
            date_end = planning_id.date_end_admin or planning_id.date_end
            if date_start <= today <= date_end:
                can_apply = True
        return can_apply


