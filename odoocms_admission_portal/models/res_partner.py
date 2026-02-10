from odoo import api, fields, models, _


class ResUsers(models.Model):
	_inherit = "res.users"

	user_type = fields.Selection([('employee', 'Employee'), ('system', 'System'),('student','Student')], 'Default Access', default='student')
	# emp_id = fields.Many2one('hr.employee', 'Employee.')
	home_page = fields.Selection([('back', 'Back Office')], 'Home Page')


# class ResPartner(models.Model):
# 	_inherit = 'res.partner'
#
# 	cnic = fields.Char(string='CNIC')
#
#
# class ResCompany(models.Model):
# 	_inherit = "res.company"
#
# 	short_name = fields.Char('Short Name')
# 	social_twitter = fields.Char('Twitter Account')
# 	social_facebook = fields.Char('Facebook Account')
# 	social_github = fields.Char('GitHub Account')
# 	social_linkedin = fields.Char('LinkedIn Account')
# 	social_youtube = fields.Char('Youtube Account')
# 	social_instagram = fields.Char('Instagram Account')
