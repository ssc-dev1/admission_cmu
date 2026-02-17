import pdb
from odoo.osv import expression
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'
    
    term_lines = fields.One2many('odoocms.academic.term.line', 'term_id', string='Term Schedule',copy=True)
    pubilc_holidays_ids = fields.One2many('odoocms.holidays.public', 'term_id', string='Public Holidays')
    line_cnt = fields.Integer(compute='_get_line_count')
    user_ids = fields.Many2many('res.users', 'term_user_access_rel', 'term_id', 'user_id', 'Users',
                                domain="[('share','=', False)]")

    def _get_line_count(self):
        for rec in self:
            rec.line_cnt = len(rec.term_lines)
            
    
class OdooCMSAcademicTermLine(models.Model):
    _name = 'odoocms.academic.term.line'
    _description = 'Term Schedule'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    # def copy(self):
    #     for rec in self:
    #         raise ValidationError(_("Academic Term detail can not duplicated. Create a new One"))
    #
    # def unlink(self):
    #     for rec in self:
    #         raise ValidationError(_("Academic Term Detail can not be deleted, You only can Archive it."))

    term_id = fields.Many2one('odoocms.academic.term', string='Term', required=True, help='Academic Term',ondelete='restrict')
    name = fields.Char(string='Name', required=True,)
    # description = fields.Text(string='Description', help="Description about the Term")
    # type = fields.Selection([('regular', 'Regular'), ('summer', 'Summer'), ('special', 'Special')], string='Type',
    #                         default='regular')
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    planning_ids = fields.One2many('odoocms.academic.term.planning', 'term_line_id', string='Plannings', copy=True )
    campus_ids = fields.Many2many('odoocms.campus', 'campus_term_rel', 'term_line_id', 'campus_id', string='Campuses',copy=True)
    institute_ids = fields.Many2many('odoocms.institute', 'institute_term__rel', 'term_line_id', 'institut_id', string='Institutes',copy=True)
    career_ids = fields.Many2many('odoocms.career', 'career_term_rel', 'term_line_id', 'career_id', string='Careers/Degree Levels',copy=True)
    program_ids = fields.Many2many('odoocms.program', 'program_term_rel', 'term_line_id', 'program_id', string='Program',copy=True)
    batch_ids = fields.Many2many('odoocms.batch', 'batch_term_rel', 'term_line_id','batch_id',string='Batches',copy=True)

    date_start = fields.Date(string='Date Start', required=True, help='Starting Date of Term')
    date_end = fields.Date(string='Date End', required=True, help='Ending of Term')
    active = fields.Boolean('Active', default=True,
                            help="If Unchecked, it will allow you to hide the Term without removing it.")
    domain = fields.Char('Domain')
    company_id = fields.Many2one('res.company', string='Company', related='term_id.company_id', store=True)

    # _sql_constraints = [
    #     ('code', 'unique(code)', "Code already exists for another Term!"),
    #     ('name', 'unique(name)', "Name already exists for another Term!"),
    #     ('short_code', 'unique(short_code)', "Short Code already exists for another Term!"),
    # ]

    @api.constrains('date_start', 'date_end')
    def validate_date(self):
        for rec in self:
            start_date = fields.Date.from_string(rec.date_start)
            end_date = fields.Date.from_string(rec.date_end)
            if start_date >= end_date:
                raise ValidationError(_('Start Date must be Anterior to End Date'))


class OdooCMSAcademicTermPlanning(models.Model):
    _name = 'odoocms.academic.term.planning'
    _description = 'Term Planning'
    _order = 'sequence desc'
    
    term_line_id = fields.Many2one('odoocms.academic.term.line', string='Term Schedule')

    name = fields.Char(string='Label', required=True, help='Name of Calendar Activity')
    type = fields.Selection([
        ('advance_enrollment', 'Advance Enrollment'),
        ('enrollment', 'Course Enrollment'),
        ('duesdate', 'Dues Date'),
        ('drop_w', 'Course Drop(W)'),
        ('drop_f', 'Delete Course Drop(F)'),
        ('i-grade', 'I Grade'),
        ('cancellation', 'Cancellation'),
        ('rechecking', 'Rechecking'),
        ('midterm', 'Mid Term Exam'),
        ('finalterm', 'Final Exam'),
        ('notification', 'Result Notification'),
        ('full_refund', 'Full (100%) Refund'),
        ('half_refund', 'Half (50%) Refund'),
        ('classes_convene', 'Convene of Classes'),
        ('add_drop','Add/Drop of Courses'),
        ('other', 'Other')
    ], string='Type')
    date_start = fields.Date(string='Date Start', required=True, help='Starting Date of Activity')
    date_end = fields.Date(string='Date End', required=True, help='Ending of Activity')
    date_start_admin = fields.Date('Date Start Administrative',)
    date_end_admin = fields.Date('Date End Administrative',)
    sequence = fields.Integer(string='Sequence', required=True, default=50)
    company_id = fields.Many2one('res.company', string='Company', related='term_line_id.company_id', store=True)
    # campus_ids = fields.Many2many('odoocms.campus', string='Campus')

    @api.constrains('date_start', 'date_end')
    def validate_date(self):
        for rec in self:
            start_date = fields.Date.from_string(rec.date_start)
            end_date = fields.Date.from_string(rec.date_end)
            if start_date >= end_date:
                raise ValidationError(_('Start Date must be Anterior to End Date'))


class OdooCMSHolidaysPublic(models.Model):
    _name = 'odoocms.holidays.public'
    _description = 'Public Holidays'
    _order = "date, name desc"
    
    name = fields.Char('Name', required=True)
    date = fields.Date('Date', required=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term')
    variable = fields.Boolean('Date may Change')


class OdooCMSSemester(models.Model):
    _name = "odoocms.semester"
    _description = "Semester"
    _order = 'sequence'

    name = fields.Char("Semester", required=True)
    code = fields.Char('Code')
    number = fields.Integer('Number', required=True)
    sequence = fields.Integer('Sequence')
    color = fields.Integer('Semester Color')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


