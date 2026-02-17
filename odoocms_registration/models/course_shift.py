import pdb
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OdooCourseShift(models.Model):
    _name = 'odoocms.course.shift'
    _description = 'Course Shift'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))

    class_id = fields.Many2one('odoocms.class.primary', string='Class to Shift', readonly=True, states={'draft': [('readonly', False)]})
    new_class_id = fields.Many2one('odoocms.class.primary', string='Class Shift to', readonly=True, states={'draft': [('readonly', False)]})

    batch_id = fields.Many2one('odoocms.batch', 'Batch', readonly=True, states={'draft': [('readonly', False)]})
    term_id = fields.Many2one('odoocms.academic.term', 'Term', readonly=True, states={'draft': [('readonly', False)]})

    student_ids = fields.Many2many('odoocms.student', 'course_shift_student_rel', 'shift_id', 'student_id', 'Students'
                                   , readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('done', 'Done'), ('cancel', 'Cancel')], 'Status', default='draft')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    def action_submit(self):
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('odoocms.course.shift') or _('New')
        self.state = 'submit'

    def action_cancel(self):
        self.state = 'submit'

    def action_draft(self):
        self.state = 'draft'

    def fetch_students(self):
        if self.class_id and self.class_id.registration_ids:
            self.student_ids = [(5, 0, 0), (6, 0, self.class_id.registration_ids.mapped('student_id').ids)]

    def shift_course(self):
        registration_ids = self.env['odoocms.student.course']
        for student in self.student_ids:
            registration = student.enrolled_course_ids.filtered(lambda l: l.term_id.id == self.term_id.id and l.primary_class_id.id == self.class_id.id)
            if registration:
                new_class_primary = self.new_class_id
                for component in registration.component_ids:
                    new_class = new_class_primary.class_ids.filtered(lambda m: m.component == component.class_id.component)
                    if new_class:
                        component.class_id = new_class.id

                registration.primary_class_id = new_class_primary.id
                registration_ids += registration

        self.state = 'done'
        if registration_ids:
            reg_list = registration_ids.mapped('id')
            return {
                'domain': [('id', 'in', reg_list)],
                'name': _('Student Courses'),
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'odoocms.student.course',
                'view_id': False,
                # 'context': {'default_class_id': self.id},
                'type': 'ir.actions.act_window'
            }


class OdooCourseShiftReg(models.Model):
    _name = 'odoocms.course.shift.reg'
    _description = 'Course Shift Registration'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))

    source = fields.Selection([('registered', 'Registered'), ('request', 'Request')], 'Source', default='request')
    term_id = fields.Many2one('odoocms.academic.term', 'Term', readonly=True, states={'draft': [('readonly', False)]})
    course_id = fields.Many2one('odoocms.course', 'Course', readonly=True, states={'draft': [('readonly', False)]})
    class_id = fields.Many2one('odoocms.class.primary', string='Class to Shift', readonly=True, states={'draft': [('readonly', False)]})
    new_class_id = fields.Many2one('odoocms.class.primary', string='Class Shift to', readonly=True, states={'draft': [('readonly', False)]})

    student_ids = fields.Many2many('odoocms.course.registration.line', 'course_shift_reg_student_rel', 'shift_id', 'student_id', 'Students',
                                   readonly=True, states={'draft': [('readonly', False)]})
    registration_ids = fields.Many2many('odoocms.student.course', 'course_shift_reg_registration_rel', 'shift_id', 'registration_id', 'Registrations',
                                        readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('done', 'Done'), ('cancel', 'Cancel')], 'Status', default='draft')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.onchange('term_id')
    def onchange_term(self):
        domain = [(1, '=', 1)]
        if self.term_id:
            course_ids = self.env['odoocms.class.primary'].search([('term_id', '=', self.term_id.id)]).mapped('course_id')
            domain = [('id', 'in', course_ids.ids)]
        return {'domain': {'course_id': domain}}

    def action_submit(self):
        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('odoocms.course.shift.reg') or _('New')
        self.state = 'submit'

    def action_cancel(self):
        self.state = 'submit'

    def action_draft(self):
        self.state = 'draft'

    def fetch_students(self):
        if self.source == 'request':
            if self.class_id and self.class_id.registration_request_ids:
                self.student_ids = [(5, 0, 0), (6, 0, self.class_id.registration_request_ids.ids)]
        elif self.source == 'registered':
            if self.class_id and self.class_id.registration_ids:
                self.registration_ids = [(5, 0, 0), (6, 0, self.class_id.registration_ids.ids)]

    def shift_course(self):
        if self.source == 'request':
            for reg_line in self.student_ids:
                move_line = self.env['account.move.line'].search([
                    ('student_id', '=', reg_line.student_id.id),
                    ('move_id.term_id', '=', self.term_id.id),
                    ('course_id_new', '=', reg_line.primary_class_id.id)])
                if move_line:
                    move_line.write({'course_id_new': self.new_class_id.id})

                reg_line.primary_class_id = self.new_class_id.id

                if reg_line.student_course_id:
                    for course_component in reg_line.student_course_id.component_ids:
                        new_component = self.new_class_id.class_ids.filtered(lambda m: m.component == course_component.class_id.component)
                        if new_component:
                            course_component.class_id = new_component.id

                    reg_line.student_course_id.primary_class_id = self.new_class_id.id

        elif self.source == 'registered':
            for registration in self.registration_ids:
                move_line = self.env['account.move.line'].search([
                    ('student_id', '=', registration.student_id.id),
                    ('move_id.term_id', '=', self.term_id.id),
                    ('course_id_new', '=', registration.primary_class_id.id)])
                if move_line:
                    move_line.write({'course_id_new': self.new_class_id.id})

                for course_component in registration.component_ids:
                    new_component = self.new_class_id.class_ids.filtered(lambda m: m.component == course_component.class_id.component)
                    if new_component:
                        course_component.class_id = new_component.id

                registration.primary_class_id = self.new_class_id.id

        self.state = 'done'


class OdooCourseChangeReg(models.Model):
    _name = 'odoocms.course.change.reg'
    _description = 'Course Change - Registration'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))

    term_id = fields.Many2one('odoocms.academic.term', 'Term', readonly=True, states={'draft': [('readonly', False)]})
    course_id = fields.Many2one('odoocms.course', 'Course', readonly=True, states={'draft': [('readonly', False)]})
    class_id = fields.Many2one('odoocms.class.primary', string='Class to Shift', readonly=True, states={'draft': [('readonly', False)]})
    new_class_ids = fields.Many2many('odoocms.class.primary', 'course_change_rel', 'course_1', 'course_2', string='Class Shift to', readonly=True, states={'draft': [('readonly', False)]})

    registration_ids = fields.Many2many('odoocms.student.course', 'course_change_reg_registration_rel', 'course_id1', 'course_id2', 'Registrations',
                                        readonly=True, states={'draft': [('readonly', False)]})
    state = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('done', 'Done'), ('cancel', 'Cancel')], 'Status', default='draft')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')

    @api.onchange('term_id')
    def onchange_term(self):
        domain = [(1, '=', 1)]
        if self.term_id:
            course_ids = self.env['odoocms.class.primary'].search([('term_id', '=', self.term_id.id)]).mapped('course_id')
            domain = [('id', 'in', course_ids.ids)]
        return {'domain': {'course_id': domain}}

    def fetch_students(self):
        if self.class_id and self.class_id.registration_ids:
            self.registration_ids = [(5, 0, 0), (6, 0, self.class_id.registration_ids.ids)]

    def action_submit(self):
        source_credit = sum(self.class_id.mapped('class_ids').mapped('weightage'))
        dest_credit = sum(self.new_class_ids.mapped('class_ids').mapped('weightage'))
        if source_credit != dest_credit:
            raise UserError('Credits Mismatch')

        already_registered = self.env['odoocms.student.course'].search([
            ('term_id', '=', self.term_id.id), ('primary_class_id', 'in', self.new_class_ids.ids), ('student_id', 'in', self.registration_ids.ids)
        ])
        if already_registered:
            raise UserError('There are %s Registration Conflicts: Ex. %s in %s ' % (len(already_registered), already_registered[0].student_id.code, already_registered[0].primary_class_id.code))

        if self.name == _('New'):
            self.name = self.env['ir.sequence'].next_by_code('odoocms.course.change.reg') or _('New')
        self.state = 'submit'

    def shift_course(self):
        # check of earler registration existence
        already_registered = self.env['odoocms.student.course'].search([
            ('term_id', '=', self.term_id.id), ('primary_class_id', 'in', self.new_class_ids.ids), ('student_id', 'in', self.registration_ids.ids)
        ])
        if already_registered:
            raise UserError('There are %s Registration Conflicts: Ex. %s in %s ' % (len(already_registered), already_registered[0].student_id.code, already_registered[0].primary_class_id.code))

        for registration in self.registration_ids:
            move_line = self.env['account.move.line']
            cnt = 0
            for new_primary_class_id in self.new_class_ids:
                if cnt == 0:
                    for course_component in registration.component_ids:
                        class_ids = new_primary_class_id.class_ids
                        if len(class_ids) > 1:
                            new_component = new_primary_class_id.class_ids.filtered(lambda m: m.component == course_component.class_id.component)
                        else:
                            new_component = class_ids[0]

                        if new_component:
                            course_component.write({
                                'class_id': new_component.id,
                                'weightage': new_component.weightage,
                            })

                        registration.write({
                            'primary_class_id': new_primary_class_id.id,
                            'course_id': new_primary_class_id.course_id.id,
                            'course_code': new_primary_class_id.course_id.code,
                            'course_name': new_primary_class_id.course_id.name,
                        })

                        reg_line = self.env['odoocms.course.registration.line'].search([('student_id', '=', registration.student_id.id), ('term_id', '=', registration.term_id.id), ('student_course_id', '=', registration.id)])
                        reg_line.write({
                            'primary_class_id': registration.primary_class_id.id,
                            'course_id': registration.course_id.id,
                            'course_code': registration.course_id.code,
                        })

                if cnt > 0:
                    registration.student_id.register_course(registration.term_id, new_primary_class_id.course_id, registration.student_term_id, new_primary_class_id, registration.date_effective, strength_test=False)
                    self.prepare_account_move_line(registration, new_primary_class_id, move_line)
                cnt = cnt + 1
        self.state = 'done'

    def repair_shift_course(self):
        for registration in self.registration_ids:
            reg_line = self.env['odoocms.course.registration.line'].search([('student_id','=',registration.student_id.id),('term_id','=',registration.term_id.id),('student_course_id','=',registration.id)])
            reg_line.write({
                'primary_class_id': registration.primary_class_id.id,
                'course_id': registration.course_id.id,
                'course_code': registration.course_id.code,
                # 'course_name': registration.course_id.name,
            })
            # ('move_id.payment_state', 'not in', ('in_payment', 'paid')),
            move_line = self.env['account.move.line'].search([
                ('student_id', '=', registration.student_id.id),
                ('term_id', '=', self.term_id.id),
                ('course_id_new', '=', registration.primary_class_id.id)])

            per_credit_hour_fee = registration.student_id.batch_id.per_credit_hour_fee
            course_fee_amount = per_credit_hour_fee * move_line.quantity

            old_payment_state = move_line.move_id.payment_state
            move_line.with_context(check_move_validity=False).write({
                'course_gross_fee': course_fee_amount,
                'price_unit': per_credit_hour_fee,
            })
            move_line.move_id.payment_state = old_payment_state

            audit_line = self.env['odoocms.student.term.audit'].search([('student_id','=',registration.student_id.id)])
            audit_line._get_amount()
            audit_line._compute_gross()
            audit_line._get_tuition_diff()

    def action_cancel(self):
        self.state = 'submit'

    def action_draft(self):
        self.state = 'draft'

    def prepare_account_move_line(self, registration, new_class_id, move_line):
        per_credit_hour_fee = registration.student_id.batch_id.per_credit_hour_fee
        course_fee_amount = per_credit_hour_fee * new_class_id.class_ids.weightage
        course_gross_fee = course_fee_amount
        name = new_class_id.code + '-' + new_class_id.name

        moves = self.env['account.move'].search([
            ('student_id', '=', registration.student_id.id),
            ('term_id', '=', self.term_id.id),
        ])

        unpaid_moves = self.env['account.move.line'].search([
            ('student_id', '=', registration.student_id.id),
            ('move_id.term_id', '=', self.term_id.id),
            ('move_id.payment_state', 'not in', ('paid', 'in_payment'))
        ]).mapped('move_id')

        for move in unpaid_moves:
            receivable_line = move.line_ids.filtered(lambda a: a.account_id.user_type_id.name == 'Receivable')
            old_payment_state = move.payment_state
            mvl_data = {
                'price_unit': (course_fee_amount / len(moves)),
                'quantity': 1.00,
                'product_id': move_line.product_id.id,
                'name': name,
                'account_id': move_line.fee_head_id.property_account_income_id.id,
                'move_id': move.id,
                'fee_head_id': move_line.fee_head_id and move_line.fee_head_id.id or False,
                'exclude_from_invoice_tab': False,
                'discount': move.waiver_percentage,
                'course_gross_fee': course_gross_fee,
                'course_id_new': new_class_id and new_class_id.id or False,
                'registration_id': move_line.registration_id and move_line.registration_id.id or False,
                'registration_line_id': False,
                'course_credit_hours': new_class_id.class_ids.weightage,
                'registration_type': move_line.registration_type,
            }

            self.env['account.move.line'].with_context(check_move_validity=False).sudo().create(mvl_data)
            receivable_line_amount = receivable_line.debit
            receivable_line.with_context(check_move_validity=False).sudo().write({'debit': receivable_line_amount})
            move.payment_state = old_payment_state