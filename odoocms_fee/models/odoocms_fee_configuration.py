# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

payment_types = [('admissiontime', 'Admission Time'),
                 ('permonth', 'Per Month'),
                 ('peryear', 'Per Year'),
                 ('persemester', 'Per Semester'),
                 ('persubject', 'Per Subject'),
                 ('percredit','Per Credit'),
                 ('onetime', 'One Time')]


class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_fee = fields.Boolean('Is Educational fee?')


class OdooCMSPaymentTerms(models.Model):
    _name = 'odoocms.payment.terms'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Fee Payment Terms'

    name = fields.Char('Name', tracking=True)
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence')
    description = fields.Text('Description', tracking=True)


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    donor_id = fields.Many2one('odoocms.fee.donors', 'Donor', tracking=True)


class OdooCMSFeeCategory(models.Model):
    _name = 'odoocms.fee.category'
    _parent_name = 'parent_id'
    _parent_store = True
    _description = 'Fee Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    name = fields.Char('Name', index=True, required=True, translate=True, help='Create a Fee Category suitable for your Institution. Like Institutional, Hostel, Transportation, Arts and Sports, etc')
    code = fields.Char('Code')
    sequence = fields.Integer()
    parent_id = fields.Many2one('odoocms.fee.category', 'Parent Category', index=True, ondelete='cascade')
    parent_path = fields.Char(index=True)
    head_ids = fields.One2many('odoocms.fee.head', 'category_id', 'Fee Heads')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def name_get(self):
        res = []
        for record in self:
            name = record.name
            if record.parent_id:
                name = record.parent_id.name + ' - ' + name
            res.append((record.id, name))
        return res


class OdooCMSFeeHead(models.Model):
    _name = 'odoocms.fee.head'
    _description = 'Fee Head'
    _inherits = {'product.product': 'product_id'}
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    payment_type = fields.Selection(payment_types, string='Payment Type', default='persemester', help='Payment Type describe when a payment effective.')
    category_id = fields.Many2one('odoocms.fee.category', string='Category', required=True, default=lambda self: self.env['odoocms.fee.category'].search([], limit=1))
    product_id = fields.Many2one('product.product', 'Fee Product', required=True, ondelete="cascade")

    refund = fields.Boolean('Refund-able?', help='Refundable at anytime. i.e. Course Registration fee refund etc.')
    security_refund = fields.Boolean('Is Security Fee?', help='Refundable at the end. i.e. University Security Fee, hostel security Fee etc.')
    late_fine = fields.Boolean('Include in Late Fee?', default=False, help='Include/Exclude in Late Fee Application')
    taxable = fields.Boolean('Taxable', default=False, help='Is Fee Head taxable?')
    waiver = fields.Boolean('Waiver', default=False, help='Waiver applicable Head?')
    hostel_fee = fields.Boolean('Hostel Fee', default=False, help='Is Hostel Fee Head?')

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account')
    account_analytic_id = fields.Many2one('account.analytic.account', string='Analytic Account (OLd)')
    analytic_tag_ids = fields.Many2many('account.analytic.tag', string='Analytic Tags')
    sequence = fields.Integer()
    effective_date = fields.Date('Effective Date')
    exclude_from_report = fields.Boolean('Exclude From Fee Challan')
    no_split = fields.Boolean('No Split', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    mapped_fee_head = fields.Many2one('odoocms.pgc.fee.head.mapping', 'Mapped Fee Head')

    @api.model
    def create(self, values):
        values.update({
            'is_fee': True,
        })
        res = super(OdooCMSFeeHead, self).create(values)
        return res

class OdoocmsPGCFeeHeadMapping(models.Model):
    _name = 'odoocms.pgc.fee.head.mapping'
    _description = "PGC Fee Head Mapping"

    sequence = fields.Integer('Sequence')
    name = fields.Char('Fee Head', required=True)
    code = fields.Char('Code')


class OdooCMSFeeHeadMerge(models.Model):
    _name = 'odoocms.fee.head.merge'
    _description = 'Fee Head Merge'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    name = fields.Char('Name', tracking=True, index=True)
    code = fields.Char('Code', tracking=True)
    sequence = fields.Integer('Sequence', default=10)
    fee_heads = fields.Many2many('odoocms.fee.head', 'fee_heads_merge_rel', 'merge_id', 'fee_head', 'Fee Heads')
    state = fields.Selection([('draft', 'Draft'),('lock', 'Locked')], string='Status', default='draft', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def unlink(self):
        for rec in self:
            if rec.fee_heads:
                raise UserError(_("This Cannot de delete because Fee Heads are linked with it."))
        return super(OdooCMSFeeHeadMerge, self).unlink()

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'


class OdooCMSFeeStructure(models.Model):
    _name = 'odoocms.fee.structure'
    _description = 'Fee Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    READONLY_STATES = {
        'lock': [('readonly', True)],
    }

    name = fields.Char('Name', tracking=True, states=READONLY_STATES, copy=False)
    description = fields.Text('Additional Information')
    session_id = fields.Many2one('odoocms.academic.session', string='Academic Session', copy=False, tracking=True, states=READONLY_STATES)
    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term', tracking=True, copy=False, states=READONLY_STATES)
    career_id = fields.Many2one('odoocms.career', string="Career", tracking=True, states=READONLY_STATES)
    batch_id = fields.Many2one('odoocms.batch', 'Program Batch')

    journal_id = fields.Many2one('account.journal', string='Journal', required=True, states=READONLY_STATES,
        help='Setting up of unique Journal for each Structure help to distinguish Account entries of each Structure ', tracking=True)

    # head_ids = fields.One2many('odoocms.fee.structure.head', 'fee_structure_id', string='Structure Heads', copy=True)
    head_ids = fields.Many2many('odoocms.fee.structure.head', 'fee_structure_fee_structure_head_rel', 'fee_structure_id', 'fee_structure_head_id', string='Structure Heads', copy=True)

    sequence = fields.Integer()
    state = fields.Selection([('draft', 'Draft'),
                              ('lock', 'Locked')
                              ], string='Status', default='draft', tracking=True)
    effective_date = fields.Date('Effective Date', tracking=True)
    date_start = fields.Date('Effective From', tracking=True)
    date_end = fields.Date('Effective To', tracking=True)
    current = fields.Boolean('Active', default=True, tracking=True)
    head = fields.Char('Head', tracking=True)

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)


    _sql_constraints = [
        ('name_unique', 'unique(name,session_id,term_id,career_id,current)',
         "Another Structure already exists with this Session,Term and Career!"),
    ]

    def lock_structure(self):
        self.state = 'lock'

    def unlock_structure(self):
        self.state = 'draft'

    def write(self, vals):
        old_head_ids = self.head_ids
        super(OdooCMSFeeStructure, self).write(vals)
        message = ''
        if self.head_ids - old_head_ids:
            message += "<b>Fee Head Added:</b> %s<br/>" % (
                ', '.join([k.fee_head_id.name for k in (self.head_ids - old_head_ids)]))

        # if old_head_ids - self.head_ids:
        #     message += "<b>Fee Head Removed:</b> %s\n" % (
        #         ', '.join([self.head]))
        if message:
            self.message_post(body=message)
        return True


class OdooCMSFeeStructureHead(models.Model):
    _name = 'odoocms.fee.structure.head'
    _description = 'Fee Structure Head'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'fee_head_id'

    sequence = fields.Integer('Sequence')
    category_id = fields.Many2one('odoocms.fee.category', string='Category', required=True, tracking=True)
    fee_head_id = fields.Many2one('odoocms.fee.head', string='Fee Head', required=True, tracking=True)
    payment_type = fields.Selection(string='Payment Type', related="fee_head_id.payment_type", tracking=True)
    fee_description = fields.Text('Fee Description', related='fee_head_id.description_sale', tracking=True)
    fee_structure_id = fields.Many2one('odoocms.fee.structure', string='Fee Structure', ondelete='cascade', index=True, tracking=True)

    current = fields.Boolean('Active', default=True, tracking=True)
    effective_date = fields.Date('Effective Date', tracking=True)
    reference = fields.Char('Reference', tracking=True)
    description = fields.Text('Description', tracking=True)
    line_ids = fields.One2many('odoocms.fee.structure.head.line', 'structure_head_id', string='Head Lines', copy=True)
    company_id = fields.Many2one('res.company', string='Company', related='fee_structure_id.company_id', store=True)

    def unlink(self):
        for rec in self:
            # rec.fee_structure_id.head = rec.fee_head_id.name

            message = "Fee Structure line with category <b>%s</b><br/> and Fee head <b>%s</b> is Removed." % (str(rec.category_id.name), str(rec.fee_head_id.name))
            if rec.fee_structure_id:
                rec.fee_structure_id.message_post(body=message)
            if rec.line_ids:
                raise UserError(_('Warning! \n'
                                  'You cannot delete this Record as this is linked with the Fee Structure Head Lines,\n '
                                  'First Remove these lines from the Record and then Try it'))
        return super(OdooCMSFeeStructureHead, self).unlink()


class OdooCMSFeeStructureHeadLine(models.Model):
    _name = 'odoocms.fee.structure.head.line'
    _description = 'Fee Structure Head Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)
    structure_head_id = fields.Many2one('odoocms.fee.structure.head', string='Structure Head', required=True, tracking=True)
    fee_structure_id = fields.Many2one('odoocms.fee.structure', string='Fee Structure', related='structure_head_id.fee_structure_id', store=True)
    category_id = fields.Many2one('odoocms.fee.category', string='Category', related='structure_head_id.category_id', store=True)
    fee_head_id = fields.Many2one('odoocms.fee.head', string='Fee Head', related='structure_head_id.fee_head_id', store=True)

    domain = fields.Char('Domain Rule', tracking=True)
    current = fields.Boolean('Active', default=True, tracking=True)
    description = fields.Char('Description', tracking=True)

    fee_type = fields.Selection([('fixed', 'Fixed'),('percentage', 'Percentage')], 'Type', default='fixed')
    per_fee_type = fields.Selection([('per_credit_hour','Per Credit Hour'),('per_contact_hour','Per Contact Hour'),('per_course','Per Course')],
        'Fee Type', default='per_credit_hour')
    amount = fields.Float('Amount', tracking=True)
    percentage = fields.Float('Percentage')
    percentage_of = fields.Many2one('odoocms.fee.structure.head.line', '% of')
    amount_text = fields.Char('Fee', compute='_get_amount_text', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id)
    company_id = fields.Many2one('res.company', string='Company', related='structure_head_id.company_id', store=True)

    @api.depends('fee_type', 'amount', 'percentage', 'percentage_of')
    def _get_amount_text(self):
        for rec in self:
            if rec.fee_type=='fixed':
                rec.amount_text = str(rec.amount)
            else:
                rec.amount_text = str(rec.percentage) + '% of ' + rec.percentage_of.name

    def write(self, values):
        old_amount = self.amount
        super(OdooCMSFeeStructureHeadLine, self).write(values)
        if values.get('amount', False):
            message = "<b>Amount update for:</b> %s<br/>" % (
                ', '.join([self.name, 'From', str(old_amount), 'To', str(self.amount)]))

            # self.structure_head_id.message_post(body=message)
        return True


class OdooCMSReceiptType(models.Model):
    _name = 'odoocms.receipt.type'
    _description = 'Fee Receipt Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, id desc'

    name = fields.Char('Name')
    code = fields.Char('Code')
    sequence = fields.Integer()
    fee_head_ids = fields.Many2many('odoocms.fee.head', 'receipt_type_fee_head_rel', 'receipt_type_id', 'fee_head_id', 'Fee Heads')
    semester_required = fields.Boolean('Semester Required?', default=False)
    override_amount = fields.Boolean('Override Amount?', default=False)
    comment = fields.Html('Comments')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSFeeDescription(models.Model):
    _name = 'odoocms.fee.description'
    _description = 'Fee Descriptions'
    _order = 'sequence,id desc'

    name = fields.Char('Name')
    code = fields.Char('Code')
    sequence = fields.Integer('Sequence')
    description = fields.Html('Description')


class InheritJournal(models.Model):
    _inherit = 'account.journal'

    is_fee = fields.Boolean('Is Educational fee?', default=False)

    def action_create_new_fee(self):
        view = self.env.ref('odoocms_fee.receipt_form')
        ctx = self._context.copy()
        ctx.update({'journal_id': self.id, 'default_journal_id': self.id})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_model': 'account.move',
            'view_id': view.id,
            'context': ctx,
            'type': 'ir.actions.act_window',
        }
