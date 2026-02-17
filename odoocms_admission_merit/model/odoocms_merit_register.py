import pdb

from odoo import fields, models, _, api


class OdooCmsMeritRegister(models.Model):
    _name = 'odoocms.merit.registers'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Odoo Cms Merit Register'

    name = fields.Char(string='Name')
    register_id = fields.Many2one('odoocms.admission.register', string='Register')
    merit_lines = fields.One2many('odoocms.merit.register.line', 'merit_reg_id')

    program_id = fields.Many2one('odoocms.program', string='Program')
    ssc_aggregate_percent = fields.Float('SSC Aggregate Percent', default=0)
    hssc_aggregate_percent = fields.Float('HSSC Aggregate Percent', default=0)
    entry_test_aggregate_percent = fields.Float('Entry Test Aggregate Percent', default=0)
    interview_aggregate_percent = fields.Float('Interview Aggregate Percent', default=0)
    pre_test_aggregate_percent = fields.Float('Pre Test Aggregate Percent', default=0)

    publish_merit = fields.Boolean('Publish Merit', default=False)

    merit_seats = fields.Integer('Open Merit Seats')
    self_seats = fields.Integer('Self Finance Seats')
    sports_seats = fields.Integer('Sports/Extra curricular activities Seats')
    disabled_seats = fields.Integer('Disabled Seats')
    # other_province_seats = fields.Integer(string='Other Province Seats')
    kpk_seats = fields.Integer('KP + FATA Seats')
    ajk_seats = fields.Integer('AJK Seats')
    gilgit_seats = fields.Integer('GB Seats')
    sindh_seats = fields.Integer('Sindh Rural Seats')
    baloch_seats = fields.Integer('Baloch Rural Seats')
    minority_seats = fields.Integer('Minority Seats')
    # army_seats = fields.Integer(string='Army Seats')
    # af_seats = fields.Integer(string='Airforce Seats')
    # pn_seats = fields.Integer(string='Navy Seats')
    international = fields.Integer('Overseas/Foreign Seats')

    # pre_test_agg_ids = fields.One2many('odoocms.merit.pre.test.aggregate', 'merit_reg_id')
    state = fields.Selection(string='State',
        selection=[('draft', 'Draft'),('open', 'Open'),('done', 'Done'),],
        required=False, default='draft')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")


    def calculate_merit(self):
        for rec in self:

            rec.merit_lines.unlink()
            # rec.merit_agg_ids.unlink()

            academics = self.env['odoocms.application'].search(
                [('state', 'not in', ('draft', 'reject')),('fee_voucher_state','=','verify'), ('register_id', '=', rec.register_id.id),
                 ]).applicant_academic_ids
            # applicants_academics = self.env['odoocms.application'].search(
            #     [('state', 'not in', ('draft', 'reject')),('fee_voucher_state','=','verify'), ('register_id', '=', rec.register_id.id),
            #      ]).applicant_academic_ids

            preferences = academics.filtered(lambda x: x.doc_state in ('yes','reg_verified')).application_id.preference_ids
            applicants = preferences.filtered(lambda x: rec.program_id.id == x.program_id.id).application_id
            previous_merits = self.env['odoocms.merit.registers'].search([('register_id','=',rec.register_id.id),
                                                                          ('program_id','=',rec.program_id.id),
                                                                          ('id','!=', rec.id)]).merit_lines.filtered(lambda x:x.selected == True).applicant_id
            previous_merits = False

            if applicants:
                if previous_merits:
                    applicants = applicants - previous_merits
                for app in applicants:
                    # if merit_seats < rec.merit_seats:
                    ssc_per = 0
                    inter_per = 0
                    for student_merit in app.applicant_academic_ids:
                        if student_merit.degree_name.name in ('Matric', 'O-Level'):
                            ssc_percentage = (student_merit.obt_marks / student_merit.total_marks) * 100
                            ssc_per = float("{:.2f}".format(ssc_percentage))

                        elif student_merit.degree_name.name in ('Intermediate', 'A-Level', 'DAE'):
                            # if app.hafize_quran == True:
                            #     inter_percentage = ((
                            #                                     student_merit.obt_marks + app.hafize_quran_marks) / student_merit.total_marks) * 100
                            #     inter_per = float("{:.2f}".format(inter_percentage))
                            # if app.hafize_quran == False:
                            inter_percentage = (student_merit.obt_marks / student_merit.total_marks) * 100
                            inter_per = float("{:.2f}".format(inter_percentage))

                    # partial_agg = 0
                    # for app_agg in app.applicant_line_ids.sorted(key=lambda r: r.name):
                    #     for agg_rec in rec.merit_agg_ids.sorted(key=lambda r: r.name):
                    #         if app_agg.name == agg_rec.name:
                    #             partial_agg = partial_agg + (((app_agg.obtained_marks / app_agg.total_marks) * 100) * (
                    #                     agg_rec.aggregate / 100))

                    total_aggregate = ((rec.ssc_aggregate_percent / 100) * (ssc_per)) + (
                            (rec.hssc_aggregate_percent / 100) * (inter_per))
                    print(total_aggregate)

                    merit_line = self.env['odoocms.merit.register.line'].sudo().create({
                        'merit_reg_id': rec.id,
                        'applicant_id': app.id,
                        'aggregate': total_aggregate,
                        'program_id': rec.program_id.id,
                        'public_visible': True,
                        'selected': False,
                    })

                rec.state = 'open'

                # this loop is based on of model order_by program_id and aggregate
                program_app = []
                merit_seats = 0
                self_seats = 0
                army_quota = 0
                navy_quota = 0
                af_quota = 0
                ajk_seats = 0
                gb_seats = 0
                baloch_seats = 0
                sindh_seats = 0
                international = 0
                kpk_seats = 0
                sports_quota = 0
                disabled_seats = 0
                for merit in rec.merit_lines:
                    categorized_merit = merit.search(
                        [('program_id', '=', merit.program_id.id), ('merit_reg_id', '=', rec.id)])

                    merit_no = 1
                    for cm in categorized_merit.filtered(lambda x: x.applicant_id.admission_type == 'open_merit'):
                        if merit_seats < rec.merit_seats:
                            if merit.program_id.id not in program_app:
                                program_app.append(merit.program_id.id)
                            cm.merit_no = merit_no
                            cm.selected = True
                            cm.open_merit = True

                        else:
                            cm.merit_no = merit_no

                        merit_no += 1
                        merit_seats = merit_seats + 1

                    for cm in categorized_merit.filtered(lambda x: x.applicant_id.admission_type == 'self'):
                        if self_seats < rec.self_seats:
                            if merit.program_id.id not in program_app:
                                program_app.append(merit.program_id.id)
                            cm.merit_no = merit_no
                            cm.selected = True
                            cm.self_merit = True
                        self_seats = self_seats + 1

                    sports_quota_app = categorized_merit.filtered(lambda x:
                        x.applicant_id.sports_quota == 'yes' and x.open_merit == False )

                    for sp in sports_quota_app:
                        if sports_quota < rec.sports_seats:
                            if merit.program_id.id not in program_app:
                                program_app.append(merit.program_id.id)
                            sp.merit_no = merit_no
                            sp.selected = True
                            sp.sports_quota = True

                            sports_quota = sports_quota + 1
                    # disabled_seats_app = categorized_merit.filtered(
                    #     lambda x: x.disabled_person == 'yes' and x.open_merit == False)
                    # if disabled_seats_app:
                    #     for dis in disabled_seats_app:
                    #         if disabled_seats < rec.disabled_seats:
                    #             if merit.program_id.id not in program_app:
                    #                 program_app.append(merit.program_id.id)
                    #             dis.merit_no = merit_no
                    #             dis.selected = True
                    #             dis.disabled_quota = True
                    #             merit_no += 1
                    #             disabled_seats = disabled_seats + 1

                    kpk_province_merit = categorized_merit.filtered(
                        lambda x: x.applicant_id.province_id.code in ('KP','FATA') and x.applicant_id.provincial_quota == 'yes'
                                  and x.open_merit == False)
                    if kpk_province_merit:
                        for kp in kpk_province_merit:
                            if kpk_seats < rec.kpk_seats:
                                if merit.program_id.id not in program_app:
                                    program_app.append(merit.program_id.id)
                                kp.merit_no = merit_no
                                kp.selected = True
                                kp.kpk_seats = True

                                kpk_seats = kpk_seats + 1
                    sindh_province_merit = categorized_merit.filtered(
                        lambda x: x.applicant_id.province_id.code == 'SINDH'
                                  and x.open_merit == False  and x.applicant_id.provincial_quota == 'yes')
                    if sindh_province_merit:
                        for sn in sindh_province_merit:
                            if sindh_seats < rec.sindh_seats:
                                if merit.program_id.id not in program_app:
                                    program_app.append(merit.program_id.id)
                                sn.merit_no = merit_no
                                sn.selected = True
                                sn.sindh_seats = True

                                sindh_seats = sindh_seats + 1

                    ajk_province_merit = categorized_merit.filtered(
                        lambda x: x.applicant_id.province_id.code == 'AJK'  and x.applicant_id.provincial_quota == 'yes'
                                  and x.open_merit == False )
                    if ajk_province_merit:
                        for aj in ajk_province_merit:
                            if ajk_seats < rec.ajk_seats:
                                if merit.program_id.id not in program_app:
                                    program_app.append(merit.program_id.id)
                                aj.merit_no = merit_no
                                aj.selected = True
                                aj.ajk_seats = True

                                ajk_seats = ajk_seats + 1

                    gb_province_merit = categorized_merit.filtered(
                        lambda x: x.applicant_id.province_id.code == 'GB'  and x.applicant_id.provincial_quota == 'yes'
                                  and x.open_merit == False)
                    if gb_province_merit:
                        for gb in gb_province_merit:
                            if gb_seats < rec.gilgit_seats:
                                if merit.program_id.id not in program_app:
                                    program_app.append(merit.program_id.id)
                                gb.merit_no = merit_no
                                gb.selected = True
                                gb.gilgit_seats = True

                                gb_seats = gb_seats + 1

                    international_merit = categorized_merit.filtered(
                        lambda x: x.applicant_id.applicant_type == 'international'
                                  and x.open_merit == False)
                    if international_merit:
                        for int in international_merit:
                            if international < rec.international:
                                if merit.program_id.id not in program_app:
                                    program_app.append(merit.program_id.id)
                                int.merit_no = merit_no
                                int.selected = True
                                int.international = True

                                international = international + 1

                    baloch_province_merit = categorized_merit.filtered(
                        lambda x: x.applicant_id.province_id.code == 'BAL' and x.applicant_id.provincial_quota == 'yes'
                                  and x.open_merit == False)
                    if baloch_province_merit:
                        for blc in baloch_province_merit:
                            if baloch_seats < rec.baloch_seats:
                                if merit.program_id.id not in program_app:
                                    program_app.append(merit.program_id.id)
                                blc.merit_no = merit_no
                                blc.selected = True
                                blc.baloch_seats = True

                                baloch_seats = baloch_seats + 1

                    # army_merit = categorized_merit.filtered(
                    #     lambda x: x.applicant_id.forces_quota == 'yes' and x.applicant_id.force_type == 'army'
                    #               and x.open_merit == False)
                    # if army_merit:
                    #     for arm in army_merit:
                    #         if army_quota < rec.army_seats:
                    #             if merit.program_id.id not in program_app:
                    #                 program_app.append(merit.program_id.id)
                    #             arm.merit_no = merit_no
                    #             arm.selected = True
                    #             arm.army_seats = True
                    #
                    #             army_quota = army_quota + 1
                    # af_merit = categorized_merit.filtered(
                    #     lambda x: x.applicant_id.forces_quota == 'yes' and x.applicant_id.force_type == 'af'
                    #               and x.open_merit == False)
                    # if af_merit:
                    #     for af in af_merit:
                    #         if af_quota < rec.af_seats:
                    #             if merit.program_id.id not in program_app:
                    #                 program_app.append(merit.program_id.id)
                    #             af.merit_no = merit_no
                    #             af.selected = True
                    #             af.af_seats = True
                    #
                    #             af_quota = af_quota + 1

                    # navy_merit = categorized_merit.filtered(
                    #     lambda x: x.applicant_id.forces_quota == 'yes' and x.applicant_id.force_type == 'navy'
                    #               and x.open_merit == False)
                    # if navy_merit:
                    #     for nv in navy_merit:
                    #         if navy_quota < rec.navy_seats:
                    #             if merit.program_id.id not in program_app:
                    #                 program_app.append(merit.program_id.id)
                    #             nv.merit_no = merit_no
                    #             nv.selected = True
                    #             nv.navy_seats = True
                    #             navy_quota = navy_quota + 1

                    # other_province_merit = categorized_merit.filtered(
                    #     lambda x: x.applicant_id.province_id.code in (
                    #         'Sindh', 'PB', 'BLC', 'GB', 'AJK',
                    #         'ICT') and x.open_merit == False and x.disabled_quota == False and x.sports_quota == False)
                    # if other_province_merit:
                    #     for op in other_province_merit:
                    #         if other_province_seats < rec.other_province_seats:
                    #             if merit.program_id.id not in program_app:
                    #                 program_app.append(merit.program_id.id)
                    #             op.merit_no = merit_no
                    #             op.selected = True
                    #             op.other_province = True
                    #
                    #             other_province_seats = other_province_seats + 1

    def submit(self):
        for rec in self:
            rec.publish_merit = True
            rec.state = 'done'

    def generate_offer_letter(self):
        for rec in self:
            if rec.publish_merit == True:
                for offer in rec.merit_lines.filtered(lambda x: x.selected == True):
                    offer_letter = self.env['admission.offer.letter'].search(
                        [('applicant_id', '=', offer.applicant_id.id),
                         ('program_id', '=', rec.program_id.id),
                         ('merit_reg_id', '=', rec.id)])
                    if not offer_letter:
                        self.env['admission.offer.letter'].create({
                            'applicant_id': offer.applicant_id.id,
                            'program_id': rec.program_id.id,
                            'merit_reg_id': rec.id,
                        })


class OdooCmsMeritRegisterLine(models.Model):
    _name = 'odoocms.merit.register.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'program_id , aggregate desc'
    _rec_name = 'applicant_id'
    _description = 'Odoo Cms Merit Register Line'

    merit_no = fields.Integer(string='Merit No')
    aggregate = fields.Float(string='Aggregate')
    applicant_id = fields.Many2one('odoocms.application', string='Application')
    applicant = fields.Char( related='applicant_id.name', string='Applicant Name', store=True)
    reference_no = fields.Char( related='applicant_id.application_no', string='Reference No',  store=True)
    merit_reg_id = fields.Many2one('odoocms.merit.registers', string='Merit Register')
    program_id = fields.Many2one('odoocms.program', string='Program')
    public_visible = fields.Boolean(string='Public Visible')
    selected = fields.Boolean(string='Selected')
    matric_marks = fields.Integer(string='Matric Marks', compute='_get_matric_marks', store=True)
    inter_marks = fields.Integer(string='Inter Marks', compute='_get_inter_marks', store=True)
    open_merit = fields.Boolean(string='Open Merit', default=False)
    self_merit = fields.Boolean(string='Self Finance', default=False)
    international = fields.Boolean(string='Internationl', default=False)
    kpk_seats = fields.Boolean(string='kPK+FATA Seats', default=False)
    ajk_seats = fields.Boolean(string='AJK Seats', default=False)
    gilgit_seats = fields.Boolean(string='GB Seats', default=False)
    sindh_seats = fields.Boolean(string='Sindh Rural', default=False)
    baloch_seats = fields.Boolean(string='Baloch Rural', default=False)
    # army_seats = fields.Boolean(string='Army', default=False)
    # af_seats = fields.Boolean(string='AF', default=False)
    # pn_seats = fields.Boolean(string='PN', default=False)
    disabled_quota = fields.Boolean(string='Disabled Seats', default=False)
    sports_quota = fields.Boolean(string='Sports Seats', default=False)
    # entry_test_marks = fields.Integer(string='Entry Test Marks')
    # pre_test_marks = fields.Integer(string='Pre Test Marks', compute='_get_pre_test_marks', store=True)
    # cbt_obtained = fields.Integer(string='CBT Obtained Marks', compute='_get_cbt_obtained_marks', store=True)
    # cbt_total = fields.Integer(string='CBT Total Marks')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    @api.depends('applicant_id.applicant_academic_ids')
    def _get_inter_marks(self):
        for rec in self:
            applicant_marks = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)])
            for marks in applicant_marks.applicant_academic_ids:
                if marks.degree_name.name in ('Intermediate', 'A-Level'):
                    obtained_marks = marks.obt_marks
                    rec.inter_marks = obtained_marks

    @api.depends('applicant_id.applicant_academic_ids')
    def _get_matric_marks(self):
        for rec in self:
            applicant_marks = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)])
            for marks in applicant_marks.applicant_academic_ids:
                if marks.degree_name.name in ('Matric', 'O-Level'):
                    obtained_marks = marks.obt_marks
                    rec.matric_marks = obtained_marks

    @api.depends('applicant_id.preference_ids')
    def _get_pre_test_marks(self):
        self.pre_test_marks = 0
        for rec in self:
            # application = self.env['odoocms.application'].search([('id', '=', rec.applicant_id.id)])
            # program = application.preference_ids[0].program_id
            # if program and program.pre_test:
            #     marks = application.pre_test_marks
            #     rec.pre_test_marks = marks
            application = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)])
            preference = application.preference_ids.filtered(
                lambda x: x.preference == 1).program_id
            preference_program = preference
            if preference and preference.pre_test:
                rec.pre_test_marks = application.pre_test_marks


# class OdooCmsMeritAggregate(models.Model):
#     _name = 'odoocms.merit.test.aggregate'
#     _description = 'Odoo Cms Merit Aggregate'
#
#     name = fields.Char(string='Name')
#     aggregate = fields.Float(string='Aggregate')
#     merit_reg_id = fields.Many2one(
#         'odoocms.merit.registers', string='Merit Register')
#     program_id = fields.Many2one('odoocms.program', string='Program', )
#
#
# class OdooCmsMeritAggregate(models.Model):
#     _name = 'odoocms.merit.pre.test.aggregate'
#     _description = 'Odoo Cms Pre Test Merit Aggregate'
#
#     pre_test_id = fields.Many2one('odoocms.pre.test', string='Name')
#     aggregate = fields.Float(string='Aggregate')
#     merit_reg_id = fields.Many2one(
#         'odoocms.merit.registers', string='Merit Register')








