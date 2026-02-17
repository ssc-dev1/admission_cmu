from odoo.osv import expression
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import pdb


class OdooCMSDiscipline(models.Model):
    _name = 'odoocms.discipline'
    _description = 'CMS Discipline'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Discipline", help="Discipline Name")
    code = fields.Char(string="Code", help="Discipline Code")
    description = fields.Text(string='Description', help="Short Description about the Discipline")
    program_ids = fields.One2many('odoocms.program','discipline_id','Academic Programs')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)

    _sql_constraints = [
        ('code', 'unique(code,company_id)', "Code already exists!"),
    ]


class OdooCMSCampus(models.Model):
    _name = 'odoocms.campus'
    _description = 'CMS Campus'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    name = fields.Char('Name', required=True)
    code = fields.Char('Code', help='Campus City Code')
    effective_date = fields.Date('Effective Date', help='Effective Date of Campus')
    active = fields.Boolean('Active', default=True, help="Current Status of Course")
    description = fields.Text('Description', help="Description about the Campus")
    short_description = fields.Text('Short Description', help="Short Description about the Campus")
    formal_description = fields.Text('Formal Description', help="Formal Description about the Campus")
    street = fields.Char('Address 1')
    street2 = fields.Char('Address 2')
    zip = fields.Char(change_default=True)
    city = fields.Char('City')
    country_id = fields.Many2one('res.country', 'Country', ondelete='cascade')
    website = fields.Char('Website')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    
    institute_ids = fields.One2many('odoocms.institute', 'campus_id', 'Institutes')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    to_be = fields.Boolean(default=False)
    
    def unlink(self):
        for rec in self:
            raise ValidationError(_("Calendar Year can not be deleted, You only can Archive it."))
        
    _sql_constraints = [
        ('code', 'unique(code)', "Campus Code already exists."),
        ('name', 'unique(name)', "Campus Name already exists."),
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


class OdooCMSInstitute(models.Model):
    _name = 'odoocms.institute'
    _description = 'CMS Institute'
    _inherit = ['mail.thread', 'mail.activity.mixin','image.mixin']

    name = fields.Char('Name', required=True)
    code = fields.Char('Code', required=True, help='Institute Code')
    effective_date = fields.Date('Effective Date', help='Effective Date of Institute')
    active = fields.Boolean('Active', default=True, help="Current Status of Institute")
    website = fields.Char('Website')
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    campus_id = fields.Many2one('odoocms.campus', 'Campus', required=True, ondelete='restrict')
    
    department_ids = fields.One2many('odoocms.department', 'institute_id', 'Departments')
    
    parent_id = fields.Many2one('odoocms.institute', 'Parent Institute')
    child_ids = fields.One2many('odoocms.institute', 'parent_id', 'SubInstitutes', domain=[('active', '=', True)])
    company_id = fields.Many2one('res.company', string='Company', related='campus_id.company_id', store=True)
    
    to_be = fields.Boolean(default=False)
    
    _sql_constraints = [
        ('code', 'unique(code,campus_id)', "Institute Code already exists."),
        ('name', 'unique(name,campus_id)', "Institute Name already exists."),
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
    
      
class OdooCMSDepartment(models.Model):
    _name = 'odoocms.department'
    _description = 'CMS Department'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string="Name", help="Department Name", required=True)
    code = fields.Char(string="Code", help="Department Code", required=True)
    effective_date = fields.Date(string="Effective Date", help="Effective Date", required=True)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean('Active', default=True, help="Current Status of Department")
    institute_id = fields.Many2one("odoocms.institute", string="Institute/Faculty", required=True, ondelete='restrict')
    campus_id = fields.Many2one('odoocms.campus', 'Campus', related='institute_id.campus_id', store=True)

    parent_id = fields.Many2one('odoocms.department', 'Parent Department')
    child_ids = fields.One2many('odoocms.department', 'parent_id', 'SubDepartments', domain=[('active', '=', True)])
    
    program_ids = fields.One2many('odoocms.program', 'department_id', string="Programs")
    company_id = fields.Many2one('res.company', string='Company', related='campus_id.company_id', store=True)

    to_be = fields.Boolean(default=False)
    
    _sql_constraints = [
        ('code', 'unique(code,campus_id)', "Department Code already exists."),
        ('name', 'unique(name,campus_id)', "Department Name already exists."),
    ]

    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.institute_id:
                name = name + ' - ' + record.institute_id.code or ''
            res.append((record.id, name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
 

class OdooCMSProgram(models.Model):
    _name = 'odoocms.program'
    _description = "CMS Program"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code', required=True)
    short_code = fields.Char('Short Code',size=4)
    color = fields.Integer(string='Color Index')
    duration = fields.Char('Duration Text')
    duration_basic = fields.Float('Duration')
    duration_basic_unit = fields.Selection([('year','Year(s)'),('month','Month(s)')])
    duration_extended = fields.Float('Duration Extended')
    duration_extended_unit = fields.Selection([('year', 'Year(s)'), ('month', 'Month(s)')])
    
    credits = fields.Integer('Credit Hours')
    effective_date = fields.Date(string="Effective Date", help="Effective Date", required=True)
    description = fields.Text(string='Formal Description')
    active = fields.Boolean('Active', default=True, help="Current Status of Department")

    department_id = fields.Many2one('odoocms.department', string="Department", required=True, ondelete='restrict')
    career_id = fields.Many2one('odoocms.career', string="Career/Degree Level", required=True, ondelete='restrict')
    discipline_id = fields.Many2one('odoocms.discipline', string="Discipline", ondelete='restrict')
    institute_id = fields.Many2one("odoocms.institute", string="Institute",related='department_id.institute_id',store=True)
    campus_id = fields.Many2one('odoocms.campus',string='Campus', related='institute_id.campus_id',store=True)
    
    specialization_ids = fields.One2many('odoocms.specialization', 'program_id', string='Specializations')
    company_id = fields.Many2one('res.company', string='Company', related='campus_id.company_id', store=True)

    to_be = fields.Boolean(default=False)
    
    _sql_constraints = [
        ('code', 'unique(code,campus_id)', "Code already exists!"),
    ]

    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.department_id:
                name = name + ' - ' + (record.department_id.institute_id and record.department_id.institute_id.code or '')
            res.append((record.id, name))
        return res

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class OdooCMSSpecialization(models.Model):
    _name = "odoocms.specialization"
    _description = "CMS Specialization"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    description  = fields.Text(string='Formal Description')
    program_id = fields.Many2one('odoocms.program', string='Program', ondelete='restrict')
    company_id = fields.Many2one('res.company', string='Company', related='program_id.company_id', store=True)
    

class ResCompany(models.Model):
    _inherit = "res.company"
    
    identifier = fields.Char('Import Identifier')
    
    

        
    
