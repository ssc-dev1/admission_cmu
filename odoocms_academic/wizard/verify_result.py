import pdb
from odoo import api, fields, models, _


class OdooCMSVerifyResultWiz(models.TransientModel):
    _name = 'odoocms.verify.result.wiz'
    _description = 'Verify Result Wizard'
    
    term_id = fields.Many2one('odoocms.academic.term','Academic Term',required=True)
    grade_class_ids = fields.Many2many('odoocms.class.grade',string='Grade Classes')

    def verify_result(self):
        self.ensure_one()
        for grade_class in self.grade_class_ids:
            if grade_class.state == 'verify':
                grade_class.result_verified()

        return {'type': 'ir.actions.act_window_close'}
