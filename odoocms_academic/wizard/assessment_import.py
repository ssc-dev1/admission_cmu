# -*- coding: utf-8 -*-
import binascii
from odoo import models, fields
import logging

_logger = logging.getLogger(__name__)

try:
    import xlwt
except ImportError:
    _logger.debug('Cannot `import xlwt`.')
try:
    import cStringIO
except ImportError:
    _logger.debug('Cannot `import cStringIO`.')
try:
    import base64
except ImportError:
    _logger.debug('Cannot `import base64`.')


class AssessmentImportWizard(models.TransientModel):
    _name = "odoocms.assessment.import.wizard"
    _description = 'Assessment Import Wizard'
    
    file = fields.Binary('File')
    # import_option = fields.Selection([('csv', 'CSV File'),('xls', 'XLS File')],string='Select',default='xls')
    session_id = fields.Many2one('odoocms.academic.session', 'Calendar Year')
    batch_id = fields.Many2one('odoocms.batch', 'Intake')
    term_id = fields.Many2one('odoocms.academic.term', 'Term')
    class_id = fields.Many2one('odoocms.class', 'Class')    

    def import_assessment_data(self):
        self.env['odoocms.class'].assessment_import_excel(binascii.a2b_base64(self.file))
        
        return {'type': 'ir.actions.act_window_close'}


        
        

        
        
        



