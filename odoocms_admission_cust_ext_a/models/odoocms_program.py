from odoo.fields import Datetime
from odoo import fields, models, _, api


class OdooCMSProgramInherit(models.Model):
    _inherit = 'odoocms.program'
    _description = 'Odoo CMS Program Inherit'



    work_experience_required = fields.Boolean(string="Work Experience Required", readonly=False)
    calculate_merit_with_exemption=fields.Boolean(string="Calculate Merit with Execption", readonly=False,default =False, help='Allow compute merit list without entrytest or interview' )
    publish_merit = fields.Boolean(string="Publish Merit", readonly=False , default =False)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', ondelete='set null')
    def_courses_group= fields.Many2many('applicant.academic.group', string="Def. Courses Group")



class OdoocmsCourseType(models.Model):
    _inherit = 'odoocms.course.type'  

    type = fields.Selection(selection_add=[('deficiency', 'Deficiency')],  ondelete={'deficiency': 'set default'} )