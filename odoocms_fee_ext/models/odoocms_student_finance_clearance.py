# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class OdoocmsStudentFinanceClearance(models.Model):
    _name = 'odoocms.student.finance.clearance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _description = "Student Finance Clearance"

    name = fields.Char('Name')
    sequence = fields.Char('Sequence')
    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)
    student_image = fields.Image(related='student_id.image_1920', string="Image")
    cgpa = fields.Float('CGPA', compute='_compute_student_info', store=True)
    earned_credits = fields.Float('Earned Credits', compute='_compute_student_info', store=True)
    accepted_credits = fields.Float('Accepted Credits', compute='_compute_student_info', store=True)

    amount = fields.Float('Amount', required=True, tracking=True)
    date = fields.Date('Applied Date', required=True, default=lambda self: fields.Date.today(), tracking=True)
    clearance_date = fields.Date('Clearance Date', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('done', 'Processed'), ('cancel', 'Cancelled')]
        , string='Status', tracking=True, default='draft')

    notes = fields.Html('Notes', tracking=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    to_be = fields.Boolean('To Be', default=False)

    # Fee Variables
    total_fee = fields.Float('Total Fee')
    paid_fee = fields.Float('Paid Fee')
    unpaid_fee = fields.Float('Unpaid Fee')
    fee_scholarship_amount = fields.Float('Fee Discount')

    # Hostel Fee Variables
    total_hostel_fee = fields.Float('Total Hostel Fee')
    paid_hostel_fee = fields.Float('Paid Hostel Fee')
    unpaid_hostel_fee = fields.Float('Unpaid Hostel Fee')
    hostel_fee_scholarship_amount = fields.Float('Fee Hostel Discount')

    # Attendance Fine Variables
    total_att_fine = fields.Float('Total Attendance Fine')
    invoiced_att_fine = fields.Float('Invoiced Attendance Fine')
    paid_att_fine = fields.Float('Paid Attendance Fine')
    unpaid_att_fine = fields.Float('Unpaid Attendance Fine')
    att_fine_scholarship_amount = fields.Float('Attendance Discount Amount')

    # Late  Fine Variables
    total_late_fee_fine = fields.Float('Total Late Fee Fine')
    paid_late_fee_fine = fields.Float('Paid Late Fee Fine')
    unpaid_late_fee_fine = fields.Float('Unpaid Late Fee Fine')
    late_fee_fine_scholarship_amount = fields.Float('Late Fee Fine Discount')

    # Other Fine Variables
    total_other_fine = fields.Float('Total Other Fine')
    paid_other_fine = fields.Float('Paid Other Fine')
    unpaid_other_fine = fields.Float('Unpaid Other Fine')
    other_fine_scholarship_amount = fields.Float('Other Discount Amount')

    # Library Fine Variables
    total_library_fine = fields.Float('Total Library Fine')
    paid_library_fine = fields.Float('Paid Library Fine')
    unpaid_library_fine = fields.Float('Unpaid Library Fine')
    library_fine_scholarship_amount = fields.Float('Library Discount Amount')

    # Books to Return
    refundable_library_books = fields.Html('Refundable Library Books')
    warning_message = fields.Char()

    challan_id = fields.Many2one('odoocms.fee.barcode', 'Challan', tracking=True)
    move_id = fields.Many2one('account.move', 'Invoice', tracking=True)
    paid_flag = fields.Boolean('Paid Flag', compute='_compute_paid_flag', store=True)

    # For Attendance Issues
    attendance_fine_issue = fields.Boolean('Attendance Fine Issue', tracking=True)

    @api.model
    def create(self, values):
        if not values.get('sequence', False):
            values['name'] = self.env['ir.sequence'].next_by_code('odoocms.student.finance.clearance')
        result = super(OdoocmsStudentFinanceClearance, self).create(values)
        return result

    def unlink(self):
        for rec in self:
            if rec.state == 'done':
                raise UserError('You Cannot Delete Done Records.')
        return super(OdoocmsStudentFinanceClearance, self).unlink()

    @api.depends('student_id')
    def _compute_student_info(self):
        for rec in self:
            student = rec.student_id
            rec.cgpa = student.cgpa
            rec.earned_credits = student.earned_credits
            rec.accepted_credits = student.credits
            rec.refundable_library_books = rec.get_student_refundable_books(student)

    def _compute_fine_detail(self):
        fine = unpaid = paid = invoiced = discount = 0
        att_fine_ids = self.env['odoocms.student.attendance.fine'].sudo().search([('student_id', '=', self.student_id.id)])
        for att_fine_id in att_fine_ids:
            fine += att_fine_id.fine
            discount += att_fine_id.discount
            if att_fine_id.move_id and att_fine_id.move_id.payment_state in ('paid','in_payment','partial'):
                paid += att_fine_id.net_amount
            elif att_fine_id.move_id and att_fine_id.move_id.payment_state not in ('paid', 'in_payment', 'partial'):
                invoiced += att_fine_id.net_amount
            else:
                unpaid += att_fine_id.net_amount
        return fine, paid, unpaid, invoiced, discount

    def action_get_detail(self):
        fee_invoices = self.env['account.move'].search([('student_id', '=', self.student_id.id)])
        paid_invoices = self.env['account.move'].search([('student_id', '=', self.student_id.id), ('payment_state', 'in', ('paid', 'in_payment'))])
        unpaid_invoices = self.env['account.move'].search([('student_id', '=', self.student_id.id), ('payment_state', 'not in', ('paid', 'in_payment'))])

        # ***** Tuition Fee Lines *****#
        tuition_fee_lines = fee_invoices.line_ids.filtered(lambda a: a.fee_category_id.name == 'Tuition Fee')
        paid_tuition_fee_lines = paid_invoices.line_ids.filtered(lambda a: a.fee_category_id.name == 'Tuition Fee')
        unpaid_tuition_fee_lines = unpaid_invoices.line_ids.filtered(lambda a: a.fee_category_id.name == 'Tuition Fee')

        total_fee = sum(line.price_subtotal for line in tuition_fee_lines)
        paid_fee = sum(line.price_subtotal for line in paid_tuition_fee_lines)
        unpaid_fee = sum(line.price_subtotal for line in unpaid_tuition_fee_lines)

        # ***** Hostel Fee Lines *****#
        hostel_fee_lines = paid_invoices.line_ids.filtered(lambda a: a.fee_category_id.name == 'Hostel Fee')
        paid_hostel_fee_lines = paid_invoices.line_ids.filtered(lambda a: a.fee_category_id.name == 'Hostel Fee' and a.move_id.payment_state in ('paid', 'in_payment'))
        unpaid_hostel_fee_lines = unpaid_invoices.line_ids.filtered(lambda a: a.fee_category_id.name == 'Hostel Fee' and a.move_id.payment_state not in ('paid', 'in_payment'))

        total_hostel_fee = sum(line.price_subtotal for line in hostel_fee_lines)
        paid_hostel_fee = sum(line.price_subtotal for line in paid_hostel_fee_lines)
        unpaid_hostel_fee = sum(line.price_subtotal for line in unpaid_hostel_fee_lines)

        # ***** Late Fee Fine Lines *****#
        late_fee_fine_lines = fee_invoices.line_ids.filtered(lambda a: a.fee_head_id.name in ("Late Fee Fine", "Late Fine"))
        paid_late_fee_fine_lines = fee_invoices.line_ids.filtered(lambda a: a.fee_head_id.name in ("Late Fee Fine", "Late Fine") and a.move_id.payment_state in ('paid', 'in_payment'))
        unpaid_late_fee_fine_lines = fee_invoices.line_ids.filtered(lambda a: a.fee_head_id.name in ("Late Fee Fine", "Late Fine") and a.move_id.payment_state not in ('paid', 'in_payment'))

        total_late_fee_fine = sum(line.price_subtotal for line in late_fee_fine_lines)
        paid_late_fee_fine = sum(line.price_subtotal for line in paid_late_fee_fine_lines)
        unpaid_late_fee_fine = sum(line.price_subtotal for line in unpaid_late_fee_fine_lines)

        # ***** Library Fine Lines *****#    ????????????????
        library_fine_lines = self.env['odoocms.library.item.circulation'].search([('member_id.student_id', '=', self.student_id.id), ('fine_amount', '>', 0)])
        total_library_fine = sum(line.fine_amount for line in library_fine_lines)
        paid_library_fine = sum(line.fine_amount if line.fine_challan_payment_state in ('in_payment', 'partial', 'paid') else 0 for line in library_fine_lines)
        unpaid_library_fine = sum(line.fine_amount if line.fine_challan_payment_state not in ('in_payment', 'partial', 'paid') else 0 for line in library_fine_lines)

        # ***** Other Fine Lines *****#
        misc_fine_recs = self.env['odoocms.fee.additional.charges'].search([('student_id', '=', self.student_id.id)])
        total_other_fine = sum(line.amount for line in misc_fine_recs)
        paid_other_fine = sum(line.amount if line.challan_payment_state in ('in_payment', 'partial', 'paid') else 0 for line in misc_fine_recs)
        unpaid_other_fine = sum(line.amount if line.challan_payment_state not in ('in_payment', 'partial', 'paid') else 0 for line in misc_fine_recs)

        other_fine_recs = self.env['odoocms.input.other.fine'].search([('student_id', '=', self.student_id.id)])
        total_other_fine += sum(line.net_amount for line in other_fine_recs)
        paid_other_fine += sum(line.net_amount if line.receipt_id.payment_state in ('in_payment', 'partial', 'paid') else 0 for line in other_fine_recs)
        unpaid_other_fine += sum(line.net_amount if line.receipt_id.payment_state not in ('in_payment', 'partial', 'paid') else 0 for line in other_fine_recs)

        fine_att, paid_att, unpaid_att, invoiced_att, discount_att = self._compute_fine_detail()

        data = {
            'total_fee': total_fee,
            'paid_fee': paid_fee,
            'unpaid_fee': unpaid_fee,

            'total_hostel_fee': total_hostel_fee,
            'paid_hostel_fee': paid_hostel_fee,
            'unpaid_hostel_fee': unpaid_hostel_fee,

            'total_late_fee_fine': total_late_fee_fine,
            'paid_late_fee_fine': paid_late_fee_fine,
            'unpaid_late_fee_fine': unpaid_late_fee_fine,

            'total_library_fine': total_library_fine,
            'paid_library_fine': paid_library_fine,
            'unpaid_library_fine': unpaid_library_fine,

            'total_other_fine': total_other_fine,
            'paid_other_fine': paid_other_fine,
            'unpaid_other_fine': unpaid_other_fine,

            'total_att_fine': fine_att,
            'paid_att_fine': paid_att,
            'unpaid_att_fine': unpaid_att,
            'invoiced_att_fine': invoiced_att,
            'att_fine_scholarship_amount': discount_att,

            'clearance_date': fields.Date.today(),
        }
        self.write(data)

    def action_done(self):
        if self.unpaid_fee > 0:
            raise UserError('Please Clear Fee Dues or Click on the Get Detail to Refresh')
        if self.unpaid_hostel_fee > 0:
            raise UserError('Please Clear Hostel Fee Dues or Click on the Get Detail to Refresh')
        if self.unpaid_att_fine > 0:
            raise UserError('Please Clear Attendance Fine Dues or Click on the Get Detail to Refresh')
        if self.unpaid_other_fine > 0:
            raise UserError('Please Clear Other Fine Dues or Click on the Get Detail to Refresh')
        if self.unpaid_library_fine > 0:
            raise UserError('Please Clear Other Fine Dues or Click on the Get Detail to Refresh')

        member_id = self.env['odoocms.library.member'].search([('student_id', '=', self.student_id.id)])
        refundable_books = self.env['odoocms.library.item.circulation'].search([('member_id', '=', member_id.id), ('state', '=', 'borrowed')])
        if refundable_books:
            raise UserError('Please Return Library Books or Click on the Get Detail to Refresh')
        self.state = 'done'

        # Assign Finance Tag To Student
        finance_tag = self.env['odoocms.student.tag'].search([('name', '=', 'Finance Clearance')], order='id asc', limit=1)
        self.student_id.write({'tag_ids': [(4, finance_tag.id, None)]})

    def action_cancel(self):
        for rec in self:
            if rec.state == 'draft':
                rec.state = 'cancel'

    def action_reset_to_draft(self):
        for rec in self:
            if rec.state == 'cancel':
                rec.state = 'draft'

    # ***** Semester Challan View *****#
    def action_view_student_semester_challan(self):
        form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
        tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')

        domain = [
            ('student_id', '=', self.student_id.id),
            ('challan_type', '!=', 'hostel_fee')
        ]
        ret = {
            'name': 'Student Challan History',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [
                (tree_view and tree_view.id or False, 'tree'),
                (form_view and form_view.id or False, 'form'),
            ],
            'domain': domain,
        }
        return ret

    # ***** Attendance Fine History in View *****#
    def action_view_student_semester_unpaid_challan(self):
        form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
        tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')

        domain = [
            ('student_id', '=', self.student_id.id),
            ('payment_state', 'not in', ('paid', 'in_payment'))
        ]
        ret = {
            'name': 'Student Unpaid Challans',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [
                (tree_view and tree_view.id or False, 'tree'),
                (form_view and form_view.id or False, 'form'),
            ],
            'domain': domain,
        }
        return ret

    def action_view_student_hostel_challan(self):
        form_view = self.env.ref('odoocms_fee.odoocms_receipt_form')
        tree_view = self.env.ref('odoocms_fee.odoocms_receipt_tree')
        domain = [('student_id', '=', self.student_id.id),
                  ('challan_type', '=', 'hostel_fee')
                  ]
        ret = {
            'name': 'Student Hostel Challan History',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move',
            'views': [
                (tree_view and tree_view.id or False, 'tree'),
                (form_view and form_view.id or False, 'form'),
            ],
            'domain': domain,
        }
        return ret

    # ***** Attendance Fine History in View *****#
    def action_view_attendance_fine_history(self):
        domain = [('student_id', '=', self.student_id.id), ('fine', '>', 0)]
        ret = {
            'name': 'Student Attendance Fine History',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'odoocms.class.attendance.line',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
        }
        return ret

    # ***** Late Fee Fine History in View *****#
    def action_view_late_fee_fine_history(self):
        domain = [('student_id', '=', self.student_id.id), ('fee_head_id.name', 'in', ("Late Fee Fine", "Late Fine"))]
        ret = {
            'name': 'Student Late Fee Fine History',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.move.line',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
        }
        return ret

    # ***** Other Fine History in View *****#
    def action_view_other_fine_history(self):
        domain = [('student_id', '=', self.student_id.id)]
        ret = {
            'name': 'Student Other Fine History',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'odoocms.fee.additional.charges',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
        }
        return ret

    # ***** Library Fine History in View *****#
    def action_view_library_fine_history(self):
        domain = [('member_id.student_id', '=', self.student_id.id), ('fine_amount', '>', 0)]
        ret = {
            'name': 'Student Library Fine History',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'odoocms.library.item.circulation',
            'views': [[False, 'list'], [False, 'form']],
            'domain': domain,
        }
        return ret

    def action_create_attendance_challan(self):
        for rec in self:
            lines = []
            term_id = self.env['odoocms.academic.term'].search([('current', '=', True)], order='id desc', limit=1)
            structure_domain = [
                ('session_id', '=', rec.student_id.session_id.id),
                ('batch_id', '=', rec.student_id.batch_id.id),
                ('career_id', '=', rec.student_id.career_id.id)]
            fee_structure = self.env['odoocms.fee.structure'].search(structure_domain, order='id desc', limit=1)
            if not fee_structure:
                raise UserError(_('No Fee Structure Found For Batch-%s') % rec.student_id.batch_id.name)

            receipts = self.env['odoocms.receipt.type'].search([('name', '=', 'Misc Fee')], order='id desc', limit=1)

            lines, attendance_fine_lines = self.student_id.get_attendance_fine_lines(lines)
            lines, input_other_fine_lines = self.student_id.get_input_other_fine_lines(term_id, lines)
            lines, additional_charge_lines = self.student_id.get_additional_charges_lines(term_id, lines)
            if len(lines) > 0:
                data = {
                    'student_id': rec.student_id.id,
                    'partner_id': rec.student_id.partner_id.id,
                    'fee_structure_id': fee_structure.id,
                    'journal_id': fee_structure.journal_id.id,
                    'invoice_date': rec.date,
                    'invoice_date_due': rec.date + relativedelta(days=7),
                    'state': 'draft',
                    'is_fee': True,
                    'is_cms': True,
                    'is_hostel_fee': False,
                    'move_type': 'out_invoice',
                    'invoice_line_ids': lines,
                    'receipt_type_ids': [(4, receipt.id, None) for receipt in receipts],
                    'waiver_amount': 0,
                    'term_id': term_id and term_id.id or False,
                    'validity_date': rec.date + relativedelta(days=7),
                    'first_installment': False,
                    'second_installment': False,
                    'challan_type': 'misc_challan',
                    # 'registration_id': registration_id and registration_id.id or False,
                }

                # Create Fee Receipt
                invoice = self.env['account.move'].sudo().create(data)

                additional_charge_lines.sudo().write({'receipt_id': invoice.id})
                input_other_fine_lines.sudo().write({'receipt_id': invoice.id})
                attendance_fine_lines.sudo().write({'move_id': invoice.id})

                challan_ids = invoice.generate_challan_barcode(rec.student_id, 'Misc')

                rec.write({
                    'challan_id': challan_ids[0].id,
                    'move_id': invoice.id
                })



    def get_student_refundable_books(self, student_id):
        detail = ""
        if student_id:
            member_id = self.env['odoocms.library.member'].search([('student_id', '=', student_id.id)])
            if member_id:
                detail = """
                    <table class="table">
                        <tbody>
                            <tr style="text-left:center;font-size:16;">
                                <th>Accession#</th>
                                <th>Description</th>
                                <th>Status</th>
                                <th>Issue Date</td>
                                <th>Over Days</td>
                            </tr>
                        """

                refundable_books = self.env['odoocms.library.item.circulation'].search([('member_id', '=', member_id.id), ('state', '=', 'borrowed')])
                if refundable_books:
                    for refundable_book in refundable_books:
                        detail += """
                            <tr style="text-left:center;font-size:16;background-color: #EAEDED;">
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                                <td>%s</td>
                            </tr>
                        """ % (refundable_book.accession_no, refundable_book.item_detail_id.item_id.name, refundable_book.state.capitalize(), refundable_book.assigned_date, refundable_book.day_over)
                detail += """ 
                        </tbody>
                    </table"""
        return detail
