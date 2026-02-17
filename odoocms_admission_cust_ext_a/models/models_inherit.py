from odoo import models, fields, api, _



class OdooCMSAcademicTerm(models.Model):
    _inherit = 'odoocms.academic.term'

    admission_start_date = fields.Date('Admission Start Date')




# class OdooCMSFeeBarcode(models.Model):
#     _inherit = 'odoocms.fee.barcode'

#     sync_challan = fields.Boolean('Syncable to Dynamics')
#     synced_challan = fields.Boolean('Synced to Dynamics')
#     sql_id = fields.Char('SQL ID')
#     date_sync = fields.Date('Sync Date')



class OdooCMSCourseComponent(models.Model):
    _inherit = 'odoocms.course.component'

    server_id = fields.Integer('Client ID')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
    to_be = fields.Boolean()



class OdooCMSCourseType(models.Model):
    _inherit = 'odoocms.course.type'

    client_id = fields.Integer('Client ID')
    to_be = fields.Boolean()
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)

class OdooCMSEntryTestScheduleDetail(models.Model):
    _inherit = 'odoocms.entry.schedule.details'


    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.user.company_id)
   

class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"


    server_id =fields.Integer('Server ID')
   
