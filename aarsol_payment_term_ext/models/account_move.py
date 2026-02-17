from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _recompute_payment_terms_lines(self):
        return super(AccountMove, self.with_context(last_account_move=self))._recompute_payment_terms_lines()

    payment_term_locked = fields.Boolean(
        string='Payment Term Locked',
        compute='_compute_payment_term_locked',
        store=False,
        help='True if the selected payment term is locked'  
    )

    @api.depends('invoice_payment_term_id', 'invoice_payment_term_id.locked')
    def _compute_payment_term_locked(self):
        """Compute whether the selected payment term is locked"""
        for move in self:
            move.payment_term_locked = move.invoice_payment_term_id.locked if move.invoice_payment_term_id else False


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    label_id = fields.Many2one('account.payment.term.label', 'Label')