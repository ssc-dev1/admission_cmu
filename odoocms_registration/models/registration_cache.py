import json
import pdb
from ...cms_process.models import main as main
from odoo import fields, models, api, _


class OdooCMSRegistrationCacheClass(models.Model):
    _name = 'odoocms.registration.cache.class'
    _description = 'Registration Cache Class'

    primary_class_id = fields.Many2one('odoocms.class.primary')
    # career_id = fields.Many2one('odoocms.career',related='student_id.career_id',store=True)
    # institute_id = fields.Many2one('odoocms.institute',related='student_id.institute_id',store=True)
    # batch_id = fields.Many2one('odoocms.batch',related='student_id.batch_id',store=True)
    course_card = fields.Text()
    section_card = fields.Text()
    valid = fields.Boolean(default=True)

    # course_type of course_card needs update
    # section_status, seats_available,   section_status (for Clash) and clash_course of section_card needs update
    def cache_enrollment_cards(self, class_id):
        course_card, section_card = self.env['odoocms.student'].fill_portal_cards_ucp(class_id, 'compulsory')
        exist = self.search([('primary_class_id','=', class_id.id)])
        if exist:
            exist.write({
                'course_card': json.dumps(course_card),
                'section_card': json.dumps(section_card),
            })
        else:
            self.create({
                'primary_class_id': class_id.id,
                'course_card': json.dumps(course_card),
                'section_card': json.dumps(section_card)
            })

    def cron_cache(self, limit=10):
        class_ids = self.env['odoocms.class.primary'].search([('to_be','=',True)], limit=limit)
        for class_id in class_ids:
            self.cache_enrollment_cards(class_id)
            class_id.to_be = False


class OdooCMSRegistrationCache(models.Model):
    _name = 'odoocms.registration.cache'
    _description = 'Registration Cache'

    student_id = fields.Many2one('odoocms.student')
    career_id = fields.Many2one('odoocms.career',related='student_id.career_id',store=True)
    institute_id = fields.Many2one('odoocms.institute',related='student_id.institute_id',store=True)
    batch_id = fields.Many2one('odoocms.batch',related='student_id.batch_id',store=True)
    cards = fields.Text()
    classes = fields.Text()
    valid = fields.Boolean(default=True)

    def prepare_portal_values(self, student_id):
        user = student_id.user_id
        partner = user.partner_id
        student = student_id

        if not student:
            values = {
                'error_message': 'Unauthorized Access',
            }
            return values, False, False
        else:
            term_id, term = main.get_registration_term(self)
            menus = self.env['odoocms.student.portal.menu'].sudo().search([], order='sequence')

            block_reason = False
            block_tags = self.env['odoocms.student.tag'].sudo().search([('block', '=', True)])
            block = (student.tag_ids and block_tags and any(
                tag in block_tags for tag in student.tag_ids) or False)
            if block:
                block_reason = student.warning_message
            else:
                allow_reg_before_result = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms_student_portal.allow_reg_before_result', 'False'))
                if not allow_reg_before_result and any([course.state in ('submit', 'disposal', 'approval') for course in student.course_ids]):
                    block = True
                    block_reason = 'Dear Student, Your Course(s) result is pending. It will be completed within two working days positively. Please wait!'

            student_query = eval(self.env['ir.config_parameter'].sudo().get_param('aarsol.student.query') or 'False')
            values = {
                'client_ip': False,
                'client_mac': False,
                'block': block,
                'block_reason': block and block_reason or False,
                'menu_ids': menus.ids,
                'company': self.env.company.id,
                'notifications': [],
                'alerts': [],
                'config_term': term,
                'partner': partner.id,
                'portal': 1,
                'student_query': student_query,
            }
        return values, True, student

    def cache_enrollment_cards(self, student_id):
        values, success, student = self.prepare_portal_values(student_id)
        term_id = values['config_term']
        term = self.env['odoocms.academic.term'].browse(term_id)

        try:
            probation_tags = self.env['odoocms.student.tag'].sudo().search([('code', 'like', 'probation_')])
            probation_tag = (student.tag_ids and probation_tags and any(
                tag in probation_tags for tag in student.tag_ids) or False)
            st_terms = self.env['odoocms.student.term'].sudo().search([
                ('student_id', '=', student.id), ('number', '<', term.number)], order='number desc').filtered(lambda l: l.term_id.type == 'regular')
            prev_regular_term = self.env['odoocms.academic.term'].sudo().search([('number', '<', term.number), ('type', '=', 'regular')], order='number desc', limit=1)

            allow_semester_break_register = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms_student_portal.allow_semester_break_register', 'False'))
            allow_probation_register = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms_student_portal.allow_probation_register', 'False'))

            if not allow_semester_break_register and st_terms and prev_regular_term and st_terms[0].term_id.id != prev_regular_term.id and values.get('portal') == 1:
                values['error_message'] = 'You did not enrolled in term %s. Please contact Registration Department for Enrollment!' % (prev_regular_term.name)
            # elif st_terms and st_terms[0].earned_credits == 0 and values.get('portal') == 1:
            #     values['error_message'] = 'You did not earned credits in term %s. Please contact Registration Department for Enrollment!' % (prev_regular_term.name)
            elif probation_tag and values.get('portal') == 1 and not allow_probation_register:
                    values['error_message'] = 'You are on Probation. Please contact Registration Department for Enrollment!'
            elif term.grade_notification_date and student.batch_id.date_over_extended and term.grade_notification_date > student.batch_id.date_over_extended:
                values['error_message'] = 'Time barred for Degree Completion!'
            else:
                tt_check = student.batch_id.tt_check or False
                card_values = student.get_registration_cards(term, registration=False, tt_check=tt_check, advance_enrollment=True)
                values.update(card_values)

                allow_reg_before_result = eval(self.env['ir.config_parameter'].sudo().get_param('odoocms_student_portal.allow_reg_before_result', 'False'))
                if not allow_reg_before_result and any([course.state in ('submit', 'disposal', 'approval') for course in student.course_ids]):
                    values['error_message'] = 'There are some courses pending for Result Publishing!'

            values.update({
                'active_menu': 'enrollment',
                'active_menu_sub_menu': 'enrollment_cards',
                'term_name': term.name,
            })
            exist = self.search([('student_id','=', student.id)])
            if exist:
                exist.write({
                    'cards': json.dumps(values)
                })
            else:
                self.create({
                    'student_id': student.id,
                    'cards': json.dumps(values)
                })
        except Exception as e:
            pass

    def cache_classes(self, student_id, term_id, tt_check=True, enrollment='A', registration=False):
        values = {}
        classes = student_id.get_possible_classes(term_id, portal=True, tt_check=tt_check, enrollment=enrollment, registration=registration)
        if not classes.get('error',False):
            for k, v in classes.items():
                values[k] = v.ids if v else False

            exist = self.search([('student_id', '=', student_id.id)])
            if exist:
                exist.write({
                    'classes': json.dumps(values)
                })
            else:
                self.create({
                    'student_id': student_id.id,
                    'classes': json.dumps(values)
                })

    def cron_enrollment(self, limit=10):
        students = self.env['odoocms.student'].search([('to_be','=',True)], limit=limit)
        for student in students:
            self.cache_enrollment_cards(student)
            student.to_be = False