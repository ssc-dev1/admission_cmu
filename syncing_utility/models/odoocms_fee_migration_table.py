
from odoo import models, fields

class OdoocmsFee(models.Model):
    _name = 'odoocms.fee'
    _description = 'Odoocms Fee'



    server_id = fields.Integer(string='Server ID')
    name = fields.Char(string='Name')
    date = fields.Date()
    state = fields.Char(string='State')
    company_id = fields.Many2one('res.company', string='Company') 
    payment_reference = fields.Char(string='Payment Reference')
    amount_total = fields.Float(string='Total Amount')
    amount_residual = fields.Float(string='Residual Amount')
    payment_state = fields.Char(string='Payment State')
    invoice_date = fields.Date(string='Invoice Date')
    invoice_date_due = fields.Date(string='Invoice Date Due')
    student_id = fields.Many2one('odoocms.student', string='Student') 
    program_id = fields.Many2one('odoocms.program', string='Program') 
    term_id = fields.Many2one('odoocms.academic.term', string='Term')
    waiver_amount = fields.Float(string='Waiver Amount')
    waiver_percentage = fields.Float(string='Waiver Percentage')
    challan_type = fields.Char(string='Challan Type')
    account_move_id =fields.Integer(string='Account Move ID')
    odoocms_fee_ref = fields.Integer(string="Odoocms Fee Ref")



class OdoocmsFeeLine(models.Model):
    _name = 'odoocms.fee.line'
    _description = 'Odoocms Fee Line'



    odoocms_fee_id =fields.Many2one ('odoocms.fee',String ='Odoocms Fee Ref')
    move_id = fields.Integer(string='Move')
    move_name = fields.Char(string='Move Name')
    date = fields.Date(string='Date')
    ref = fields.Char(string='Reference')
    parent_state = fields.Char(string='Parent State')
    company_id = fields.Many2one('res.company', string='Company')
    sequence = fields.Integer(string='Sequence')
    name = fields.Char(string='Name')
    quantity = fields.Float(string='Quantity')
    price_unit = fields.Float(string='Unit Price')
    discount = fields.Float(string='Discount')
    debit = fields.Float(string='Debit')
    credit = fields.Float(string='Credit')
    balance = fields.Float(string='Balance')
    amount_currency = fields.Float(string='Amount Currency')
    price_subtotal = fields.Float(string='Price Subtotal')
    price_total = fields.Float(string='Price Total')
    date_maturity = fields.Date(string='Maturity Date')
    payment_id = fields.Integer( string='Payment')
    amount_residual = fields.Float(string='Residual Amount')
    student_id = fields.Many2one('odoocms.student', string='Student')
    term_id = fields.Many2one('odoocms.academic.term', string='Term')
    course_credit_hours = fields.Float(string='Course Credit Hours', digits=(16, 2))
    course_gross_fee = fields.Float(string='Course Gross Fee', digits=(16, 2))
    challan_no = fields.Char(string='Challan Number')
    account_move_line_id =fields.Integer(string='Account Move Line ID')


