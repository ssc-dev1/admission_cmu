import pdb
from odoo.osv import expression
from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)


class OdooCMSReligion(models.Model):
    _name = 'odoocms.religion'
    _description = 'Religion'
    _order = 'sequence'

    name = fields.Char(string="Religion", required=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string='Sequence')
    color = fields.Integer('Color')
    

class OdooCMSCity(models.Model):
    _name = 'odoocms.city'
    _description = 'City'
    _order = 'sequence'

    name = fields.Char(string="City", required=True)
    code = fields.Char(string="City Code", required=True)
    sequence = fields.Integer(string='Sequence')
    district_id = fields.Many2one('odoocms.district','District')
    province_id = fields.Many2one('odoocms.province','Province',related='district_id.province_id',store=True)
    postal_code = fields.Char('Postal Code')
    latitude = fields.Char('Latitude')
    longitude = fields.Char('Longitude')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)
 

class OdooCMSProvince(models.Model):
    _name = 'odoocms.province'
    _description = 'Province'
    _order = 'sequence'

    country_id = fields.Many2one('res.country', string="Country")
    name = fields.Char(string="Province", required=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string='Sequence')
    domicile_ids = fields.One2many('odoocms.domicile', 'province_id', string='Domiciles')
    district_ids = fields.One2many('odoocms.district', 'province_id', string="Districts")

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class OdooCMSDistrict(models.Model):
    _name = 'odoocms.district'
    _description = 'District'
    _order = 'sequence'

    province_id = fields.Many2one('odoocms.province', string="Province")
    name = fields.Char('District Name',size=32, required=True)
    code = fields.Char('Code', size=8, required=True)
    sequence = fields.Integer(string='Sequence')

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)


class OdooCMSDomicile(models.Model):
    _name = 'odoocms.domicile'
    _description = 'Domicile'
    _order = 'sequence'

    name = fields.Char(string="Domicile Region", required=True)
    code = fields.Char(string="Code", required=True)
    province_id = fields.Many2one('odoocms.province', string='Province')
    sequence = fields.Integer(string='Sequence')


class OdooCMSMartialStatus(models.Model):
    _name = 'odoocms.marital.status'
    _description = 'Marital Status'
    _order = 'sequence'

    name = fields.Char(string="Name", required=True)
    code = fields.Char(string="Code", required=True)
    sequence = fields.Integer(string='Sequence')
    color = fields.Integer('Color')
    

class OdooCMSProfession(models.Model):
    _name = 'odoocms.profession'
    _description = 'Profession'
    _order = 'sequence'

    code = fields.Char(string="Code", help="Code")
    name = fields.Char(string="Name", required=False, )
    sequence = fields.Integer(string='Sequence')
    apply_on = fields.Selection([('m','Male'),('f','Female'),('b','Both')], 'Apply on', default='b')
   

class OdooCMSLanguage(models.Model):
    _name = 'odoocms.language'
    _description = "OdooCMS Languages"

    name = fields.Char('Name')
    code = fields.Char('Code')
    sequence = fields.Integer(string='Sequence')


class OdooCMSCareer(models.Model):
    _name = "odoocms.career"
    _description = "CMS Career/Degree Level"
    
    name = fields.Char(string='Name', required=True)
    code = fields.Char(string='Code')
    description = fields.Text(string='Description')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    to_be = fields.Boolean(default=False)

    @api.model
    def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('code', operator, name), ('name', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&', '!'] + domain[1:]
        return self._search(expression.AND([domain, args]), limit=limit, access_rights_uid=name_get_uid)

