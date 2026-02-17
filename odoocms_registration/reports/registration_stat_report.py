import pdb
from odoo import api, fields, models,tools
from datetime import date, datetime
from ...cms_process.models import main as main
import pytz


class RegistrationStatReport(models.AbstractModel):
    _name = 'report.odoocms_registration.registration_stat_report'
    _description = 'Registration Stat Report'

    @api.model
    def _get_report_values(self, docsid, data=None):
        term_id, term = main.get_current_term(self)

        institute_ids = self.env['odoocms.institute'].search([])
        items = {}
        for institute_id in institute_ids:
            inst = {
                'name': institute_id.code,
                'programs': [],
            }
            i_confirmed = i_registered = i_new = i_total = 0
            for program in institute_id.department_ids.mapped('program_ids'):

                confirmed_students = self.env['odoocms.student.course'].search([
                    ('program_id','=',program.id),('term_id','=',term)]).mapped('student_id').filtered(
                    lambda l: l.cgpa > 0
                )

                registered_students = self.env['odoocms.course.registration'].search([
                    ('program_id','=',program.id),('term_id','=',term),('state','not in',('draft','cancel'))]).mapped('student_id')

                new_students = self.env['odoocms.student.course'].search([
                    ('program_id', '=', program.id), ('term_id', '=', term)]).mapped('student_id').filtered(
                    lambda l: l.cgpa == 0
                )

                total_registered = list(set(registered_students + confirmed_students))
                confirmed = len(confirmed_students)
                new = len(new_students)
                registered = len(total_registered)
                total = registered + new
                i_confirmed += confirmed
                i_registered += registered
                i_new += new
                i_total += total
                program = {
                    'name': program.code,
                    'new': new,
                    'registered': registered,
                    'confirmed': confirmed,
                    'total': total,
                }
                inst['programs'].append(program)

            inst.update({
                'new': i_new,
                'registered': i_registered,
                'confirmed': i_confirmed,
                'total': i_total
            })
            items[institute_id.id] = inst
            # items.append(inst)
        
        institutes = []
        for key,val in items.items():
            institutes.append(val)

        KarachiTz = pytz.timezone("Asia/Karachi")
        timeKarachi = datetime.now(KarachiTz)
        today = timeKarachi.strftime("%B %d, %Y %H:%M")
        
        docargs = {
            'today':today or False,
            'term': term_id,
            'institutes': institutes,
        }
        return docargs
