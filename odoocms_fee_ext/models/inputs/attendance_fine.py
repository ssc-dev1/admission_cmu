from odoo import models, fields, api, _

import logging
_logger = logging.getLogger(__name__)
# For UCP
# 1
# insert into odoocms_student_attendance_fine(student_id, term_id,fine,discount,state)
# with fines as (select least(sum(x.fine),500) as fine_amount, x.date_class, x.student_id as student
# 	from odoocms_class_attendance_line x, odoocms_student_course c
#         where x.fine > 0 and x.term_id=193 and x.student_course_id = c.id and c.grade != 'W' and policy is not null
# 	group by x.date_class,x.student_id
# 	union
# 	select sum(x.fine) as fine_amount, x.date_class, x.student_id as student
# 	from odoocms_class_attendance_line x, odoocms_student_course c
#         where x.fine > 0 and x.term_id=193 and x.student_course_id = c.id and c.grade != 'W' and policy is null
# 	group by x.date_class,x.student_id)
# select student, 194 as term_id, sum(fine_amount) as fine,0 as discount,'draft' as state from fines group by student;
#
# 2
# update odoocms_student_attendance_fine set discount=0 where term_id = 194;
# update odoocms_student_attendance_fine set net_amount = fine where term_id = 194;
# 3
# update odoocms_class_attendance_line set fine_summary_id = fine.id
# from odoocms_student_attendance_fine fine where odoocms_class_attendance_line.student_id = fine.student_id and odoocms_class_attendance_line.term_id = fine.term_id
# and fine.term_id = 194 and odoocms_class_attendance_line.fine > 0
#
# 4
# insert into odoocms_student_attendance_fine_line(fine_id,date,type,amount)
# with fines as (select 'absent' as type,least(sum(x.fine),500) as amount, x.date_class as date, x.student_id as student
# 	from odoocms_class_attendance_line x, odoocms_student_course c
#         where x.fine > 0 and x.term_id=193 and x.student_course_id = c.id and c.grade != 'W' and policy is not null
# 	group by x.date_class,x.student_id
# 	union
# 	select 'late' as type, sum(x.fine) as amount, x.date_class as date, x.student_id as student
# 	from odoocms_class_attendance_line x, odoocms_student_course c
#         where x.fine > 0 and x.term_id=193 and x.student_course_id = c.id and c.grade != 'W' and policy is null
# 	group by x.date_class,x.student_id)
# select att.id as fine_id, fines.date, fines.type, fines.amount
# from fines, odoocms_student_attendance_fine att
# where fines.student = att.student_id and att.term_id = 193

# update odoocms_student_attendance_fine set net_amount = fine-discount where term_id = 240

# For CUST
# 1
# insert into odoocms_student_attendance_fine(student_id, term_id,fine,discount,state)
# with fines as (
# select sum(x.fine) as fine_amount, x.date_class, x.student_id as student
#  	from odoocms_class_attendance_line x, odoocms_student_course c
#          where x.fine > 0 and x.term_id=234 and x.student_course_id = c.id and c.grade != 'W' and policy is not null
#  	group by x.date_class,x.student_id)
#  select student, 234, sum(fine_amount) as fine,0,'draft' from fines group by student;
#
# 2
# update odoocms_student_attendance_fine set discount=0 where term_id=234;
#
# 3
# update odoocms_class_attendance_line set fine_summary_id = fine.id
# from odoocms_student_attendance_fine fine where odoocms_class_attendance_line.student_id = fine.student_id and odoocms_class_attendance_line.term_id = fine.term_id
# and odoocms_class_attendance_line.fine > 0 and fine_summary_id is null
#
# 4
# insert into
# odoocms_student_attendance_fine_line(fine_id, date, type, amount)
# with fines as (select 'absent' as type, sum(x.fine) as amount, x.date_class as date, x.student_id as student
# from odoocms_class_attendance_line x, odoocms_student_course c
# where x.fine > 0 and x.term_id=234 and x.student_course_id = c.id and c.grade != 'W' and policy is not null
# group by x.date_class, x.student_id)
#
# select att.id as fine_id, fines.date, fines.type, fines.amount
# from fines, odoocms_student_attendance_fine
# att where fines.student = att.student_id and att.term_id = 234

# update odoocms_student_attendance_fine set net_amount = fine-discount where term_id = 240


class OdoocmsStudentAttFine(models.Model):
    _name = 'odoocms.student.attendance.fine'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'odoocms.student': 'student_id'}
    _description = 'Student Attendance Fine'

    name = fields.Char('Name')
    student_id = fields.Many2one('odoocms.student', 'Student', required=True, ondelete="cascade", index=True)
    term_id = fields.Many2one('odoocms.academic.term', 'Term')

    date = fields.Date('Date')
    fine = fields.Float('Fine')
    discount = fields.Float('Discount', tracking=True)
    net_amount = fields.Float('Due Amount', compute='_compute_net_amount', store=True)

    move_id = fields.Many2one('account.move', 'Invoice', tracking=True)
    state = fields.Selection([('draft', 'UnBilled'), ('invoice','Invoiced'), ('paid', 'Paid'), ('cancel', 'Cancel')], string='Status', index=True,
        tracking=True, compute='_get_state', store=True, readonly=False)
    line_ids = fields.One2many('odoocms.student.attendance.fine.line', 'fine_id', 'Lines')

    to_be = fields.Boolean('To Be')

    @api.model_create_multi
    def create(self, vals):
        result = super().create(vals)
        if not result.name:
            result.name = self.env['ir.sequence'].next_by_code('odoocms.student.attendance.fine')
        return result

    @api.depends('move_id','to_be')
    def _get_state(self):
        for rec in self:
            if rec.state != 'cancel':
                if not rec.move_id:
                    rec.state = 'draft'
                elif rec.move_id and rec.move_id.payment_state in ('in_payment', 'paid'):
                    rec.state = 'paid'
                else:
                    rec.state = 'invoice'

    @api.depends('fine', 'discount')
    def _compute_net_amount(self):
        for rec in self:
            rec.net_amount = rec.fine - rec.discount

    def get_attendance_fine_lines(self, student_id, lines):
        domain = [('student_id', '=', student_id), ('move_id','=',False),('state', '!=', 'cancel')]
        rec_ids = self.env['odoocms.student.attendance.fine'].search(domain)
        if rec_ids:
            if rec_ids[0].student_id.company_id:
                domain = [('name', '=', 'Attendance Fine'),'|',('company_id','=',False),('company_id','=',rec_ids[0].student_id.company_id.id)]
            else:
                domain = [('name', '=', 'Attendance Fine')]

            fee_head = self.env['odoocms.fee.head'].search(domain)
            for rec_id in rec_ids:
                data_dict = {
                    'sequence': 200,
                    'price_unit': rec_id.net_amount,
                    'quantity': 1,
                    'product_id': fee_head.product_id.id,
                    'name': fee_head.name,
                    'account_id': fee_head.property_account_income_id.id,
                    'fee_head_id': fee_head.id,
                    'exclude_from_invoice_tab': False,
                    'no_split': fee_head.no_split,
                }
                lines.append((0, 0, data_dict))
        return lines, rec_ids


class OdoocmsStudentAttFineLine(models.Model):
    _name = 'odoocms.student.attendance.fine.line'
    _description = 'Student Attendance Fine Line'

    fine_id = fields.Many2one('odoocms.student.attendance.fine','Fine ID')
    date = fields.Date('Date')
    type = fields.Selection([('absent','Absent'),('late','Late')], 'Type')
    amount = fields.Float('Fine')




