import pdb

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdooCMSCampus(models.Model):
    _inherit = 'odoocms.campus'

    server_id = fields.Integer('Server ID')


class OdooCMSInstitute(models.Model):
    _inherit = 'odoocms.institute'

    server_id = fields.Integer('Server ID')


class OdooCMSDepartment(models.Model):
    _inherit = 'odoocms.department'

    server_id = fields.Integer('Server ID')


class OdooCMSCareer(models.Model):
    _inherit = 'odoocms.career'

    server_id = fields.Integer('Server ID')


class OdooCMSProgram(models.Model):
    _inherit = 'odoocms.program'

    server_id = fields.Integer('Server ID')


class OdooCMSAcademicSEssion(models.Model):
    _inherit = 'odoocms.academic.session'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSBatch(models.Model):
    _inherit = 'odoocms.batch'

    server_id = fields.Integer('Server ID')


class OdooCMSCourseType(models.Model):
    _inherit = 'odoocms.course.type'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSSemester(models.Model):
    _inherit = 'odoocms.semester'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSCourse(models.Model):
    _inherit = 'odoocms.course'

    server_id = fields.Integer('Server ID')


class OdooCMSCourseComponent(models.Model):
    _inherit = 'odoocms.course.component'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSStudyScheme(models.Model):
    _inherit = 'odoocms.study.scheme'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSStudySchemeLine(models.Model):
    _inherit = 'odoocms.study.scheme.line'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()

    @api.depends('component_lines', 'component_lines.weightage')
    def _compute_credits(self):
        pass


class OdooCMSFeeCategory(models.Model):
    _inherit = 'odoocms.fee.category'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeHead(models.Model):
    _inherit = 'odoocms.fee.head'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeStructureHead(models.Model):
    _inherit = 'odoocms.fee.structure.head'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeStructureHeadLine(models.Model):
    _inherit = 'odoocms.fee.structure.head.line'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeStructure(models.Model):
    _inherit = 'odoocms.fee.structure'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdoocmsFeeScholarshipCategory(models.Model):
    _inherit = 'odoocms.fee.scholarship.category'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeWaiverType(models.Model):
    _inherit = 'odoocms.fee.waiver.type'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeWaiver(models.Model):
    _inherit = 'odoocms.fee.waiver'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdooCMSFeeWaiverLine(models.Model):
    _inherit = 'odoocms.fee.waiver.line'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class OdoocmsProgramTermScholarship(models.Model):
    _inherit = 'odoocms.program.term.scholarship'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class ProductProduct(models.Model):
    _inherit = 'product.product'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()
