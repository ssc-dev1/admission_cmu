import pdb
from odoo.osv import expression
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError

import logging

_logger = logging.getLogger(__name__)


class OdooCMSAcademicSession(models.Model):
    _name = 'odoocms.academic.session'
    _description = 'Calendar Year'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence desc'

    def unlink(self):
        for rec in self:
            raise ValidationError(_("Calendar Year can not be deleted, You only can Archive it."))

    def copy(self):
        for rec in self:
            raise ValidationError(_("Calendar Year can not duplicated. Create a new One"))

    name = fields.Char(string='Name', required=1, help='Name of Calendar Year')
    code = fields.Char(string='Code', required=1, help='Code of Calendar Year')
    description = fields.Text(string='Description', help="Description about the Calendar Year")
    sequence = fields.Integer(string='Sequence', required=True, default=10)
    date_start = fields.Date('Date Start')
    active = fields.Boolean('Active', default=True,
                            help="If Unchecked, it will allow you to hide the Calendar Year without removing it.")
    current_active = fields.Boolean('Currently Active', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    
    _sql_constraints = [
        ('code', 'unique(code,company_id)', "Code already exists for another Calendar Year!"),
        ('name', 'unique(name,company_id)', "Name already exists for another Calendar Year!"),
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class OdooCMSAcademicTerm(models.Model):
    _name = 'odoocms.academic.term'
    _description = 'Academic Term'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'number desc'
    
    def unlink(self):
        for rec in self:
            raise ValidationError(_("Academic Term can not be deleted, You only can Archive it."))

    name = fields.Char(string='Name', required=True, help='Name of Term',copy=False)
    code = fields.Char(string='Code', required=True, help='Code of Term', tracking=True,copy=False)

    short_code = fields.Char('Short Code',copy=False)
    number = fields.Integer('Number')

    sequence = fields.Integer(string='Sequence', required=True)
    type = fields.Selection([('regular', 'Regular'), ('summer', 'Summer'), ('special', 'Special')], string='Type', default='regular')
    
    enrollment_active = fields.Boolean('Enrollment Active?', default=False)
    enrollment_planning = fields.Boolean('Enrollment Planning?', default=False)
    current = fields.Boolean('Current Term', default=False)

    description = fields.Text(string='Description', help="Description about the Term")
    short_description = fields.Text(string='Short Description', help="Short Description about the Term")
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    _sql_constraints = [
        ('code', 'unique(code,company_id)', "Code already exists for another Term!"),
        ('name', 'unique(name,company_id)', "Name already exists for another Term!"),
    ]

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

    
