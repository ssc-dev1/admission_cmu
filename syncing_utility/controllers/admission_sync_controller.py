from odoo import http
from odoo.http import request

class AdmissionSyncController(http.Controller):

    @http.route('/admission/sync', type='http', auth='user', website=True)
    def admission_sync(self, **kwargs):
        admission_sync = request.env['admission.sync'].sudo().search([], limit=1)
        if not admission_sync:
            admission_sync = request.env['admission.sync'].sudo().create({})
        return request.render('your_module.admission_sync_template', {
            'admission_sync': admission_sync
        })

    @http.route('/admission/fetch_students', type='json', auth='user')
    def fetch_students(self):
        admission_sync = request.env['admission.sync'].sudo().search([], limit=1)
        if admission_sync:
            admission_sync.fetch_students()
            return {'status': 'success', 'student_ids': admission_sync.student_ids}
        return {'status': 'error', 'message': 'No admission sync record found'}

    @http.route('/admission/call_db_procedure', type='json', auth='user')
    def call_db_procedure(self):
        admission_sync = request.env['admission.sync'].sudo().search([], limit=1)
        if admission_sync:
            admission_sync.call_db_procedure()
            return {'status': 'success', 'log': admission_sync.log}
        return {'status': 'error', 'message': 'No admission sync record found'}
