from odoo import api, fields, models, _


class ChallanMergeWiz(models.TransientModel):
    _name = 'challan.merge.wiz'
    _description = 'Challan Merge Wizard'

    @api.model
    def _get_challans(self):
        if self.env.context.get('active_model', False)=='odoocms.fee.barcode' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    challan_ids = fields.Many2many('odoocms.fee.barcode', string='Challans', default=_get_challans)
    auto_delete = fields.Boolean('Auto Delete', default=True)

    def action_challan_merge(self):
        for challan_id in self.challan_ids:
            if challan_id.label_id.type != 'main':
                student = challan_id.student_id
                term = challan_id.term_id
                registration = self.env['odoocms.course.registration'].search([('invoice_id', '=', challan_id.line_ids[0].move_id.id)])
                if registration.enrollment_type == 'add_drop':
                    domain = [('student_id', '=', student.id), ('term_id', '=', term.id), ('state', '=', 'draft'), ('label_id.type', '=', 'main')]
                    unpaid_main_challan = self.env['odoocms.fee.barcode'].sudo().search(domain)
                    if unpaid_main_challan:
                        data = {
                            'student_id': student.id,
                            'challan_id2': unpaid_main_challan.id,
                            'challan_id': challan_id.id,
                            'company_id': student.company_id.id,
                            # 'registration_id': registration and registration.id or False,
                        }
                        merged = self.env['odoocms.fee.barcode.merge'].sudo().create(data)
                        merged.post_merge()

        return {'type': 'ir.actions.act_window_close'}
