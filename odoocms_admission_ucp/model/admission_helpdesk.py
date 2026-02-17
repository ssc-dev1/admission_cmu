import pdb
from odoo import fields, models, _, api
from datetime import date
import random
import string
from odoo.exceptions import ValidationError


class AdmissionHelpDesk(models.Model):
    _name = 'admission.helpdesk'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Admission Help Desk'

    name = fields.Char(string='Caller Name')
    phone = fields.Char(string='Contact Number')
    admission_id = fields.Many2one('odoocms.application', string='Reference ID (If any)')
    nature = fields.Selection(
        [('information', 'Information'), ('complaint', 'Complaint'), ('dropcall', 'Drop Call / Transfer Call')
         ], string='Call Nature')
    program = fields.Many2many('admission.helpdesk.program.setup', 'admission_helpdesk_program_rel', 'program_id', 'caller_id', string='Interested in Program/Faculty')

    category = fields.Selection(
        [('undergraduate', 'Undergraduate'), ('graduate', 'Graduate'), ('postgraduate', 'Post Graduate'), ('other', 'Other Department / Drop Call - Transfer Call')
         ], string='Category')
    call_tag = fields.Many2many('adm.helpdesk.calltag.setup', 'adm_helpdesk_calltag_rel', 'tag_id', 'caller_id',
                                string='Call Tags/ Workcode')
    pre_admission_info = fields.Many2many('adm.helpdesk.preinfo.setup', 'adm_helpdesk_preinfo_rel', 'info_id', 'caller_id',
                                string='If selected - Pre-Admission Information')
    remarks = fields.Text(string='Remarks (If any)')


class AdmissionHelpDeskProgSetup(models.Model):
    _name = 'admission.helpdesk.program.setup'
    _description = 'Admission Helpdesk Faculty Program'

    name = fields.Char(string='Faculty/Program Name')
    code = fields.Char(string='code')

class AdmissionHelpDesktagSetup(models.Model):
    _name = 'adm.helpdesk.calltag.setup'
    _description = 'Admission Helpdesk Call Tag'

    name = fields.Char(string='Call Tag/ Workcode')
    code = fields.Char(string='code')

class AdmissionHelpDeskPreOnfo(models.Model):
    _name = 'adm.helpdesk.preinfo.setup'
    _description = 'Admission Helpdesk Pre Info'

    name = fields.Char(string='Pre-Admission Information')
    code = fields.Char(string='code')