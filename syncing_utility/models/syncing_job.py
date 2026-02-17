from odoo import models, fields, api
from pytz import timezone
import logging
import datetime

_logger = logging.getLogger(__name__)

class AdmissionSync(models.Model):
    _inherit = 'admission.sync'
    _description = 'Admission Sync'



    @api.model
    def admitted_students_syncing(self, company_id=None):
            student_records = self.env['odoocms.student'].search([('fee_paid','=',True),('server_id','=',None),('company_id','=',company_id)], limit=50)
            now = datetime.datetime.now(timezone('Asia/Karachi'))
            formatted_now = now.strftime('%Y-%m-%d %H:%M:%S')
            cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
            if student_records:
                sync_rec_data={
                    'name':str(formatted_now),
                    'cms_action':'all',
                    # 'conf': cms_sync_conf.id,
                    'company' : company_id
                }
                sync_rec =self.env['admission.sync'].sudo().create(sync_rec_data)
                sync_rec.student_ids = [(6, 0, student_records.ids)]
                sync_rec.call_db_procedure()
