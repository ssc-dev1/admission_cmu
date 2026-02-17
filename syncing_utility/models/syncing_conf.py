
from odoo import models, fields, api



class OdooCMSStudentAcademic(models.Model):
    _inherit = "odoocms.student.academic"
    _description = 'adding fields for student academic detail syncing configuration'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()
    applicant_academic_detail_id = fields.Many2one('applicant.academic.detail', 'Applicant Academic Detail')


class OdooCMSDomicile(models.Model):
    _inherit = "odoocms.domicile"
    _description = 'Adding fields for domicile syncing configuration'

    server_id = fields.Integer('Server ID')


class OdooCmsCountry(models.Model):
    _inherit = "res.country"
    _description = 'Adding fields for country syncing configuration'

    server_id = fields.Integer('Server ID')


class OdooCMSReligion(models.Model):
    _inherit = "odoocms.religion"
    _description = 'Adding fields for religion syncing configuration'

    server_id = fields.Integer('Server ID')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)


class OdooCMSStudent(models.Model):
    _inherit = "odoocms.student"
    _description = 'Adding fields for  student syncing configuration'


    dual_national_country_id =fields.Many2one('res.country' , string='Dual National Country')
    server_id = fields.Integer('Server ID')
    fee_paid = fields.Boolean('Fee Paid' , default =False)


class OdooResPartner(models.Model):
    _inherit = "res.partner"
    _description = 'Adding fields for partner syncing configuration'

    server_id = fields.Integer('Server ID') 
    to_be = fields.Boolean()



class OdoocmsApplicantAcademicDetail(models.Model):
    _inherit = "applicant.academic.detail"
    _description = 'Adding fields for academic detail syncing configuration'

    server_id = fields.Integer('Server ID')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)
    to_be = fields.Boolean()


class OdoocmsStudentAppliedScholarship(models.Model):
    _inherit = "odoocms.student.applied.scholarships"
    _description = 'Adding fields for odoocms.student.applied.scholarships syncing configuration'

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()

class AccountMove(models.Model):
    _inherit = "account.move"
    _description = 'Adding fields for account move syncing configuration'

    odoocms_fee_ref = fields.Integer('Odoocms Fee Ref')


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _description = 'Adding fields for account move line syncing configuration'

    odoocms_fee_line_ref = fields.Integer('Odoocms Fee Line Ref')


class OdoocmsStudentScholarshipEligibility(models.Model):
    _inherit = "odoocms.student.scholarship.eligibility"
    _description = 'Adding fields for account move line syncing configuration'

    server_id = fields.Integer('Server ID')

class OdooCmsApplicantFirstSemester(models.Model):
    _inherit = 'odoocms.applicant.first.semester.courses'


    server_id = fields.Integer('Server ID')


class ResCompany(models.Model):
    _inherit ='res.company'

    server_id = fields.Integer('Server ID')

class OdooCmsProgramTermScholarship(models.Model):
    _inherit ='odoocms.program.term.scholarship'

    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company)



class OdooSyncConf(models.Model):
    _name = 'odoo.sn.aarsol.cms.con'
    _description = 'syncing configuration'

    name = fields.Char(string="Name", required=True)
    target_host = fields.Char(string='DB Host')
    target_port = fields.Char(string='WEB Port')
    target_db_port =fields.Char(string='DB Port')
    current = fields.Boolean('Current')
    target_dbname = fields.Char(string='Database Name')
    target_admin_user = fields.Char(string='Admin User')
    target_admin_password = fields.Char(string='Admin Password')
    target_db_user = fields.Char(string='DB User')
    target_db_password = fields.Char(string='DB Password')
    target_host_web = fields.Char(string='Web Host')

   

class SyncingConfiguration(models.Model):
    _name = 'syncing.configuration'
    _description = 'syncing configuration'

    name = fields.Char(string="Name", required=True)
    current = fields.Boolean('Current')
    target_host = fields.Char(string='DB Host')
    target_port = fields.Char(string='WEB Port')
    target_db_port =fields.Char(string='DB Port')
    target_dbname = fields.Char(string='Database Name')
    target_admin_user = fields.Char(string='Admin User')
    target_admin_password = fields.Char(string='Admin Password')
    target_db_user = fields.Char(string='DB User')
    target_db_password = fields.Char(string='DB Password')
    target_host_web = fields.Char(string='Web Host')


class CustomLog(models.Model):
    _inherit = 'custom.log'
    _description = 'Custom Log'

    to_be =fields.Boolean('To Be')
    company_id = fields.Many2one('res.company', string='Company')