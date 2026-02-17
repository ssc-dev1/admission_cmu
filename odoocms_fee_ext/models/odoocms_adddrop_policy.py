from odoo import models, fields, api, _
from odoo.exceptions import UserError


class OdoocmsAddDropPolicy(models.Model):
    _name = 'odoocms.adddrop.policy'
    _description = 'Add Drop Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def _get_current_term(self):
        term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
        return term_id and term_id.id or False

    name = fields.Char('Name', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    start_date = fields.Date('Start Date', default=fields.Date.today(), tracking=True)
    end_date = fields.Date('End Date', default=fields.Date.today(), tracking=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term', default=_get_current_term)
    term_line_id = fields.Many2one('odoocms.academic.term.line', 'Term Line')
    state = fields.Selection([('draft', 'New'), ('confirm', 'Confirmed'), ('cancel', 'Cancel')], string='Status', default='draft', tracking=True)

    type = fields.Selection([('transaction', 'Per Transaction'),
                             ('add', 'Per Course (Add)'),
                             ('drop', 'Per Course (Drop)'),
                             ('both', 'Per Course'),
                             ], string='Type', tracking=True)

    amount = fields.Float('Amount', tracking=True)
    drop_percentage = fields.Float('Tuition Fee Adjustment', help='Percentage of Tuition Fee adjustment for drop courses')

    to_be = fields.Boolean('To Be', default=False)
    remarks = fields.Text('Remarks')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_confirm(self):
        self.state = 'confirm'

    def action_cancel(self):
        self.state = 'cancel'

    @api.model
    def create(self, values):
        result = super(OdoocmsAddDropPolicy, self).create(values)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.adddrop.policy')
        return result

    def unlink(self):
        for rec in self:
            if not rec.state == 'draft':
                raise UserError(_('You can delete the Records that are in the Draft State.'))
        return super(OdoocmsAddDropPolicy, self).unlink()

    def get_policy(self, term_id):
        today = fields.Date.today()
        dom = [('start_date', '<=', today),
               ('end_date', '>=', today),
               ('state', '=', 'confirm'),
               ('term_id', '=', term_id.id),
        ]
        adddrop_policy = self.env['odoocms.adddrop.policy'].sudo().search(dom, order='id desc', limit=1)
        return adddrop_policy

    def get_adddrop_charge_lines(self, registration, lines):
        adddrop_policy = self.get_policy(registration.term_id)
        if adddrop_policy:
            amount = 0
            if adddrop_policy.type == 'transaction':
                amount = adddrop_policy.amount
            else:
                for course in registration.line_ids:
                    if course.action == 'add':
                        if adddrop_policy.type in ('add','both'):
                            amount += adddrop_policy.amount
                    elif course.action == 'drop':
                        if adddrop_policy.type in ('drop','both'):
                            amount += adddrop_policy.amount

            adddrop_charges_head = self.env['ir.config_parameter'].sudo().get_param('aarsol.adddrop_charges_head', 'Adddrop Charges')
            domain = [('name', '=', adddrop_charges_head),'|',('company_id','=',False),('company_id','=',registration.student_id.company_id.id)]
            fee_head = self.env['odoocms.fee.head'].sudo().search(domain)
            company = registration.student_id.company_id
            account_id = fee_head.product_id.with_company(company).property_account_income_id

            data_dict = {
                'sequence': 500,
                'price_unit': amount,
                'quantity': 1,
                'product_id': fee_head.product_id.id,
                'name': fee_head.name,
                'account_id': account_id.id,
                'fee_head_id': fee_head.id,
                'exclude_from_invoice_tab': False,
                'no_split': fee_head.no_split,
            }
            lines.append((0, 0, data_dict))
        return lines

