from odoo.fields import Datetime
from odoo import fields, models, _, api
from odoo.exceptions import AccessError, UserError


class OdooCmsMeritRegister(models.Model):
    _inherit = 'odoocms.merit.registers'

    posting_date = fields.Datetime(string="Posting Date", required=False, readonly=True)

    def submit(self):
        for rec in self:
            rec.publish_merit = True
            rec.posting_date = Datetime.now()
            rec.state = 'done'
            merit_ids_tuple = tuple(rec.merit_register_ids.ids)
            application_ids = self.env['odoocms.merit.register.line'].sudo().search([('id', 'in', merit_ids_tuple)])
            application_ids.mapped('applicant_id').sudo().write({'ref_meritlist': rec.id})

    def calculate_merit(self):
        try:
            if not sum([
                self.bs_aggregate_percent + self.ms_aggregate_percent + self.entry_test_aggregate_percent + self.hssc_aggregate_percent + self.ssc_aggregate_percent + self.interview_aggregate_percent]) == 100:
                raise UserError('Aggregate Combination Must Be Equal to 100')
            self.merit_register_ids.filtered(lambda x: not x.transferred and not x.selected and not x.waiting).unlink()
            self.merit_agg_ids.unlink()
            applicants = self.env['odoocms.application'].search([('state', 'not in', ('draft', 'reject')), (
                'fee_voucher_state', '=', 'verify'), ('register_id', '=', self.register_id.id),
                                                                 ('prefered_program_id', '=', self.program_id.id), ])
            previous_merits = self.env['odoocms.merit.registers'].search([('register_id', '=', self.register_id.id), (
                'program_id', '=', self.program_id.id), ('id', '!=', self.id)]).merit_register_ids.filtered(
                lambda x: x.selected and not x.rejected).applicant_id

            if applicants:
                if previous_merits:
                    applicants = applicants - previous_merits

                # applicant entry test
                applicant_test = self.env['applicant.entry.test'].search(
                    [('state', '=', True), ('register_id', '=', self.register_id.id), ('slot_type', '=', 'test'),
                     ('paper_status', '!=', 'missed')])

                def caluclate_aggregate(self, application, entry_test):
                    aggregate = 0.0
                    academic_data = application.applicant_academic_ids
                    ssc_percentage = academic_data.filtered(
                        lambda x: x.degree_name.year_age == 10).percentage or 0.0
                    hssc_percentage = academic_data.filtered(
                        lambda x: x.degree_name.year_age == 12).percentage or 0.0
                    bs_percentage = academic_data.filtered(
                        lambda x: x.degree_name.year_age == 16).percentage or 0.0
                    ms_percentage = academic_data.filtered(
                        lambda x: x.degree_name.year_age == 18).percentage or 0.0

                    # only test
                    if self.program_id.entry_test and not self.program_id.interview:
                        entry_test_percentage = self.entry_test_percentage(
                            entry_test, application, 'test') or 0.0
                        interview_test_percentage = 0.0
                    # only interview
                    elif not self.program_id.entry_test and self.program_id.interview:
                        interview_test_percentage = self.entry_test_percentage(
                            entry_test, application, 'interview') or 0.0
                        entry_test_percentage = 0.0
                    # both test and intervew
                    elif self.program_id.entry_test and self.program_id.interview:
                        entry_test_percentage = self.entry_test_percentage(
                            entry_test, application, 'test') or 0.0
                        interview_test_percentage = self.entry_test_percentage(
                            entry_test, application, 'interview') or 0.0

                    # not both test and intervew
                    elif not self.program_id.entry_test and not self.program_id.interview:
                        entry_test_percentage = 0.0
                        interview_test_percentage = 0.0

                    ssc_aggregate = (
                            (self.ssc_aggregate_percent / 100) * (ssc_percentage))
                    hssc_aggregate = (
                            (self.hssc_aggregate_percent / 100) * (hssc_percentage))
                    bs_aggregate = (
                            (self.bs_aggregate_percent / 100) * (bs_percentage))
                    ms_aggregate = (
                            (self.ms_aggregate_percent / 100) * (ms_percentage))

                    test_aggregate = (
                            (self.entry_test_aggregate_percent / 100) * (entry_test_percentage))
                    interview_aggregate = (
                            (self.interview_aggregate_percent / 100) * (interview_test_percentage))

                    aggregate = ssc_aggregate + hssc_aggregate + test_aggregate + \
                                interview_aggregate + bs_aggregate + ms_aggregate
                    return "{:.2f}".format(aggregate)

                already_selected = self.merit_register_ids.mapped('applicant_id')
                applicants = applicants - already_selected
                for application in applicants:
                    pre_test_percentage = 0
                    pretest_marks = 0
                    entry_test = applicant_test.filtered(lambda x: x.student_id == application and x.paper_conducted)

                    if (entry_test and entry_test.applicant_line_ids) or entry_test.hec:  # added by abubab
                        entry_test_percentage = self.entry_test_percentage(
                            entry_test[0], application, 'test')
                        if entry_test_percentage >= self.minimum_test_percentage:
                            entry_test = entry_test[0]
                            aggregate = caluclate_aggregate(self, application, entry_test)
                            if float(aggregate) >= self.minimum_aggregate:
                                selected = True
                                if self.waiting_below > 0 and float(aggregate) < self.waiting_below:
                                    selected = False
                                if application.pre_test_id and application.pre_test_marks and application.pre_test_id.pre_test_total_marks:
                                    pre_test_percentage = (application.pre_test_marks / application.pre_test_id.pre_test_total_marks) * 100
                                    pretest_marks = application.pre_test_marks if application.pre_test_marks else 0

                                self.env['odoocms.merit.register.line'].sudo().create({
                                    'merit_reg_id': self.id,
                                    'applicant_id': application.id,
                                    'aggregate': aggregate,
                                    'pre_test_name': application.pre_test_id.name if application.pre_test_id else '',
                                    'program_id': self.program_id.id,
                                    'public_visible': True,
                                    'pre_test_percentage': pre_test_percentage,
                                    'pretest_marks': pretest_marks,
                                    'selected': False,
                                    'cbt_obtained': entry_test.cbt_marks,
                                    'cbt_total': entry_test.entry_test_marks,
                                    'cbt_percentage': round(
                                        ((entry_test.cbt_marks or 0) / (entry_test.entry_test_marks or 60)) * 100, 2),
                                })
                self.calculate_merit_no()

                for transfer in self.merit_register_ids.filtered(lambda x: x.transferred):
                    application = transfer.mapped('applicant_id')
                    entry_test = applicant_test.filtered(lambda x: x.student_id == application and x.paper_conducted)
                    if entry_test and entry_test.applicant_line_ids:
                        entry_test_percentage = self.entry_test_percentage(entry_test[0], application, 'test')

                        if entry_test_percentage >= self.minimum_test_percentage:
                            entry_test = entry_test[0]
                            aggregate = caluclate_aggregate(self, application, entry_test)
                            transfer.aggregate = aggregate
                            transfer.cbt_percentage = round(
                                ((entry_test.cbt_marks or 0) / (entry_test.entry_test_marks or 60)) * 100, 2)
                            if float(aggregate) >= self.minimum_aggregate:
                                selected = True
                            else:
                                transfer.sudo().unlink()

        except Exception as e:
            raise UserError(e)

    def entry_test_percentage(self, entry_test, application, type_test):
        if type_test == 'test':
            entry_test = entry_test.filtered(
                lambda x: x.slot_type != 'interview')
            cbt_percentage = False
            pre_test_percentage = False
            if entry_test:
                entry_test = entry_test[-1]
                if entry_test.entry_test_marks and entry_test.entry_test_marks > 0:
                    cbt_percentage = float("{:.2f}".format(
                        (entry_test.cbt_marks / entry_test.entry_test_marks) * 100))
                else:
                    raise UserError('CBT Total Marks Not Set ' + ' ' + application.id.application_no)
            if application.pre_test_id:
                if application.pre_test_id.pre_test_total_marks and application.pre_test_id.pre_test_total_marks > 0:
                    pre_test_percentage = float("{:.2f}".format(
                        ((application.pre_test_marks or 0) / application.pre_test_id.pre_test_total_marks) * 100))
                else:
                    raise UserError('Pre Test Total Marks Not Set ' + ' ' + application.id.application_no)

            cbt_percentage = cbt_percentage or 0.0
            pre_test_percentage = pre_test_percentage or 0.0
            max_test_percentage = max(
                [cbt_percentage, pre_test_percentage])
            return max_test_percentage
        elif type_test == 'interview' and entry_test:
            entry_test = entry_test.filtered(
                lambda x: x.slot_type != 'test')
            if entry_test:
                entry_test = entry_test[-1]
                if entry_test.interview_total_marks and entry_test.interview_total_marks > 0:
                    interview_percentage = float("{:.2f}".format(
                        (entry_test.interview_marks / entry_test.interview_total_marks) * 100))
                else:
                    raise UserError('Interview Total Marks Not Set ' + ' ' + application.id.application_no)
                return interview_percentage


class OdooCmsMeritRegisterLine(models.Model):
    _inherit = 'odoocms.merit.register.line'
    pre_test_name = fields.Char(string="Pre Test Name")
    pre_test_percentage = fields.Integer(string="Pre Test Percentage", readonly=True)
    pretest_marks = fields.Integer(string="Pre Test Marks", readonly=True)
