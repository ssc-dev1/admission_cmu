import pdb
from datetime import datetime
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
import logging

_logger = logging.getLogger(__name__)


# def get_selection_label(self, object, field_name, field_value):
#   return _(dict(self.env[object].fields_get(allfields=[field_name])[field_name]['selection'])[field_value])

# KarachiTz = pytz.timezone("Asia/Karachi")
# timeKarachi = datetime.now(KarachiTz)
# weekday = timeKarachi.isoweekday()

# weekday = KarachiTz.localize(classdate).isoweekday()


# class OdooCMSProfs(models.Model):
#     _name = 'odoocms.profs'
#     _description = 'Professions'
#     _order = 'sequence'
#
#     code = fields.Char(string="Code", help="Code")
#     name = fields.Text(string="Description", required=False, )
#     sequence = fields.Integer(string='Sequence')


class OdooCMSBuilding(models.Model):
    _name = 'odoocms.building'
    _description = "Building"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    name = fields.Char('Name')
    code = fields.Char('Code')  # abbreviation
    sequence = fields.Integer('Sequence')
    institute_ids = fields.Many2many('odoocms.institute', 'institute_building_rel', 'building_id', 'institute_id', 'Institutes/Faculties')
    institute_id = fields.Many2one('odoocms.institute', string='Institute/Faculty')

    location_x = fields.Float('Location X', help='X Coordinates')
    location_y = fields.Float('Location Y', help='Y Coordinates')

    floor_ids = fields.One2many('odoocms.building.floor', 'building_id', 'Floors')
    room_ids = fields.One2many('odoocms.room', 'building_id', 'Rooms')
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)


class OdooCMSBuildingFloor(models.Model):
    _name = 'odoocms.building.floor'
    _description = "Building Floor"
    _order = 'sequence'

    name = fields.Char('Name')
    code = fields.Char('Code')  # abbreviation
    sequence = fields.Integer('Sequence')
    building_id = fields.Many2one('odoocms.building', string='Building', ondelete='restrict')
    room_ids = fields.One2many('odoocms.room', 'floor_id', 'Rooms')
    company_id = fields.Many2one('res.company', string='Company', related='building_id.company_id', store=True)


class OdooCMSRoomType(models.Model):
    _name = 'odoocms.room.type'
    _description = "Room Type"

    name = fields.Char('Name')
    code = fields.Char('Code')
    type = fields.Selection([('Room', 'Room'), ('Other', 'Other')], 'Room Type', default='Room')


class OdooCMSRoom(models.Model):
    _name = 'odoocms.room'
    _description = "Class Room"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Room Name')
    code = fields.Char('Room Number')  # roomNumber
    ip_address = fields.Char('IP Address')
    mac_address = fields.Char('MAC Address')
    building_id = fields.Many2one('odoocms.building', 'Building', required=True, ondelete='restrict')
    floor_id = fields.Many2one('odoocms.building.floor', 'Floor', ondelete='restrict')
    department_id = fields.Many2one('odoocms.department', 'Control Department/Center')
    active = fields.Boolean('Active', default=True)

    room_type = fields.Many2one('odoocms.room.type', 'Room Type')  # domain Room
    area = fields.Float('Area', help='Square Feet')

    capacity = fields.Integer('Capacity')

    exam_capacity = fields.Integer('Exam Capacity')
    rows = fields.Integer('Rows')
    cols = fields.Integer('Cols')
    unused_seats = fields.Char('Unused Seats')
    distribution = fields.Char('Distribution')

    feature_ids = fields.One2many('odoocms.room.feature', 'class_room_id', string='Class Amenities')
    company_id = fields.Many2one('res.company', string='Company', related='building_id.company_id', store=True)


class OdooCMSRoomFeature(models.Model):
    _name = 'odoocms.room.feature'
    _description = "Amenities in Class"

    name = fields.Many2one('odoocms.amenities', string="Amenities", help="Select the amenities in Class Room")
    qty = fields.Float(string='Quantity', help="The quantity of the amenities", default=1.0)
    class_room_id = fields.Many2one('odoocms.room', string="Class Room")

    @api.constrains('qty')
    def check_qty(self):
        for rec in self:
            if rec.qty <= 0:
                raise ValidationError(_('Quantity must be Positive'))


class OdooCMSAmenities(models.Model):
    _name = 'odoocms.amenities'
    _description = 'Amenities in Institution'
    _order = 'name asc'
    _rec_name = 'name'

    name = fields.Char(string='Name', required=True, help='Name of Amenity')
    code = fields.Char(string='Code', help='Code of Amenity')

    _sql_constraints = [
        ('code', 'unique(code)', "Another Amenity already exists with this code!"),
    ]


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    def name_get(self):
        # model_id_name = defaultdict(dict)  # {res_model: {res_id: name}}
        # for xid in self:
        #    model_id_name[xid.model][xid.res_id] = None
        #
        # fill in model_id_name with name_get() of corresponding records
        # for model, id_name in model_id_name.items():
        #    try:
        #        ng = self.env[model].browse(id_name).name_get()
        #        id_name.update(ng)
        #    except Exception:
        #        pass

        # return results, falling back on complete_name
        # return [(xid.id, model_id_name[xid.model][xid.res_id] or xid.complete_name)
        #        for xid in self]

        return [(xid.id, xid.complete_name) for xid in self]


class OdooCMSTranscript(models.Model):  # Move to exam
    _name = 'odoocms.transcript.history'
    _description = "Transcript History"

    date = fields.Date('Date', readonly=True)
    student_id = fields.Many2one('odoocms.student', string='Student')
    term_id = fields.Many2one('odoocms.academic.term', 'Term', readonly=True)
    transcript = fields.Binary('Transcript', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')


class OdooCMSPublications(models.Model):
    _name = 'odoocms.publication'
    _description = "OdooCMS Publications"

    date = fields.Date('Publication Date')
    name = fields.Char('Name')
    topic = fields.Char('Topic')
    paper_attachment = fields.Binary('Attachment', attachment=True)
    student_id = fields.Many2one('odoocms.student', string='Student')
    faculty_staff_id = fields.Many2one('odoocms.faculty.staff', string='Faculty')


class OdooCMSExtraActivities(models.Model):
    _name = 'odoocms.extra.activity'
    _description = "OdooCMS Extra Curricular Activities"

    name = fields.Char('Name')
    remarks = fields.Html('Remarks')
    date = fields.Date('Date')
    student_id = fields.Many2one('odoocms.student', string='Student')
    faculty_staff_id = fields.Many2one('odoocms.faculty.staff', string='Faculty')


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    role_domain = fields.Char('Role Domain')

    def _get_role_users(self, program):
        role_domain = eval(self.role_domain)[0]
        check_part = role_domain[0][-21:]  # '.employee_tag_id.name'
        domain_part = role_domain[0][:-21]  # 'institute_id.faculty_ids'
        domain = 'program.' + domain_part  # 'self.program_id.institute_id.faculty_ids'
        operator = role_domain[1]  # =, in
        tags = role_domain[2]  # HOD

        faculties = eval(domain)  # odoocms.department.line(1, 2, 3)
        if operator == '=':
            faculties = faculties.filtered(lambda l: l.employee_tag_id.name == tags)  # odoocms.department.line(1, )
        elif operator == 'in':
            for faculty in faculties:
                for tag in faculty.employee_tag_id:
                    if tag.name == tags:
                        faculties = faculty

        if faculties:
            employee = faculties[0].employee_id
            if employee.user_id:
                return employee.user_id.id
            else:
                raise ValidationError('User Account not created for employee: %s' % (employee.name,))
        # else:
        #     raise ValidationError('No User Found for Approval Role: %s' % (tags,))
        

class Selections(models.Model):
    _name = 'odoocms.selections'
    _description = 'Selections'

    name = fields.Char(string='Name', required=True)
    usage = fields.Char(string='Description')
    in_use = fields.Boolean(string='Active', default=True)
    fields_ids = fields.One2many('odoocms.selections.fields', 'selection_id')

    @api.model
    def get_selection_field(self, selection_name):
        selection = self.search([('name', '=', selection_name), ('in_use', '=', True)])
        selection_list = list()
        for data in selection.fields_ids:
            if data.in_use:
                selection_list.append((data.value, data.name))
        return selection_list


class SelectionsFields(models.Model):
    _name = 'odoocms.selections.fields'
    _description = 'Selection Fields'
    _order = 'sequence,name'

    name = fields.Char(string='Option', required=True)
    value = fields.Char(string='Value', required=True)
    sequence = fields.Integer('Sequence', default=10)
    in_use = fields.Boolean(string='Active', default=True)
    selection_id = fields.Many2one('odoocms.selections', ondelete='cascade', index=True)


class OdooCMSWeekDays(models.Model):  # Time table
    _name = 'odoocms.week.day'
    _description = 'Week Day'
    _order = 'sequence'

    name = fields.Char(string='Name')
    code = fields.Char(string='Code')
    sequence = fields.Integer('Sequence')
    number = fields.Integer('Number')
    color = fields.Integer('Day Color')


class OdooCMSErrorReporting(models.Model):
    _name = 'odoocms.error.reporting'
    _description = 'Errors Reporting'

    def get_default_user(self):
        return self.env.user.id

    name = fields.Char('Title')
    description = fields.Text('Description')
    reported_on = fields.Datetime('Date', default=datetime.now())
    reported_by_id = fields.Many2one('res.users', 'Reported By', default=get_default_user)
    state = fields.Selection([('draft', 'Draft'), ('submit', 'Submit'), ('done', 'Done'), ('cancel', 'Cancel')], 'Status', default='draft')
    allow_preview = fields.Boolean('Allow Preview', default=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company)