import pdb
from datetime import date
from odoo import api, fields, models, _


class OdoocmsRegistrationCacheClassWiz(models.TransientModel):
    _name = 'odoocms.registration.cache.class.wizard'
    _description = 'Registration Cache Class Wizard'

    @api.model
    def _get_classes(self):
        if self.env.context.get('active_model', False) == 'odoocms.class.primary' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    primary_class_ids = fields.Many2many('odoocms.class.primary', 'primary_class_cache_rel','cache_id','class_id',string='Primary Classes',
        help="""Only selected Classes will be Processed.""", default=_get_classes)

    def generate_registration_cache(self):
        for class_id in self.primary_class_ids:
            self.env['odoocms.registration.cache.class'].sudo().cache_enrollment_cards(class_id)


class OdoocmsRegistrationCacheWiz(models.TransientModel):
    _name = 'odoocms.registration.cache.wizard'
    _description = 'Registration Cache Wizard'

    @api.model
    def _get_students(self):
        if self.env.context.get('active_model', False) == 'odoocms.student' and self.env.context.get('active_ids', False):
            return self.env.context['active_ids']

    term_id = fields.Many2one('odoocms.academic.term', 'Academic Term')
    student_ids = fields.Many2many('odoocms.student', 'registration_cache_rel','cache_id','student_id',string='Students',
        help="""Only selected students will be Processed.""", default=_get_students)

    def generate_cache_cards(self):
        for student in self.student_ids:
            self.env['odoocms.registration.cache'].sudo().cache_enrollment_cards(student)

    def generate_cache_classes(self):
        for student_id in self.student_ids:
            self.env['odoocms.registration.cache'].sudo().cache_classes(student_id,self.term_id)



