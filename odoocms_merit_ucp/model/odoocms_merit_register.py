from odoo import fields, models, _, api
from odoo.exceptions import AccessError, UserError
from odoo.fields import Datetime


class UcpOfferLetter(models.Model):
    _inherit = 'ucp.offer.letter'

    merit_reg_id = fields.Many2one('odoocms.merit.registers', string='Merit Register')
    offer_letter = fields.Html('Offer Letter', compute='_get_offer_letter', store=True)

    @api.depends('applicant_id')
    def _get_offer_letter(self):
        for rec in self:
            rec.offer_letter = rec.applicant_id.register_id.offer_letter


class OdooCmsMeritRegister(models.Model):
    _name = 'odoocms.merit.registers'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Odoo Cms Merit Register'
    _order = 'id desc'

    name = fields.Char(string='Name')
    register_id = fields.Many2one('odoocms.admission.register', string='Register')
    program_id = fields.Many2one('odoocms.program', string='Program')
    merit_lines = fields.One2many('odoocms.merit.register.line', 'merit_reg_id')

    ssc_aggregate_percent = fields.Float(string='SSC Aggregate Percent', default=0)
    hssc_aggregate_percent = fields.Float(string='HSSC Aggregate Percent', default=0)
    bs_aggregate_percent = fields.Float(string='BS Aggregate Percent', default=0)
    ms_aggregate_percent = fields.Float(string='MS Aggregate Percent', default=0)

    entry_test_aggregate_percent = fields.Float(string='Entry Test Aggregate Percent', default=0)
    interview_aggregate_percent = fields.Float(string='Interview Aggregate Percent', default=0)
    pre_test_aggregate_percent = fields.Float(string='Pre Test Aggregate Percent', default=0)
    publish_merit = fields.Boolean(string='Publish Merit', default=False)
    posting_date = fields.Datetime(string="Posting Date", required=False, readonly=True)

    program_ids = fields.One2many('odoocms.merit.program', 'merit_register_id', string='Program')
    merit_agg_ids = fields.One2many('odoocms.merit.test.aggregate', 'merit_reg_id')

    minimum_aggregate = fields.Float('Minimum Aggregate', required=True)
    waiting_below = fields.Float('Waiting Below')
    minimum_test_percentage = fields.Float('Minimum Test %', required=True)

    offer_send = fields.Boolean('Offer Send', default=False)
    offer_letter_line = fields.Html('Offer Letter Line')
    merit_list_line = fields.Html('Merit List Line',related='register_id.merit_list_line')
    merit_list_no = fields.Integer('Merit LIst No',default=1)
    select_all = fields.Boolean('Select All',default=True)
    # pre_test_agg_ids = fields.One2many('odoocms.merit.pre.test.aggregate', 'merit_reg_id')
    total_seats = fields.Integer('Total Seats')
    remaining_seats = fields.Integer('Remainig Seats', compute='_remaining_seats', store=True)
    state = fields.Selection(string='State',
        selection=[('draft', 'Draft'), ('open', 'Open'), ('done', 'Done'), ],
        required=False, default='draft')
    transferred_student = fields.Integer('Transferred Student',compute='_calculate_transferred')
    print_report = fields.Boolean('Print Report',compute='_check_report')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    @api.onchange('program_id')
    def onchange_program_id(self):
        for rec in self:
            rec.merit_agg_ids.unlink()
            admit_cards = self.env['applicant.entry.test'].search([('program_id', '=', rec.program_id.id), ('register_id', '=', rec.register_id.id)])
            if admit_cards:
                admit_card = admit_cards[0]
                for section in admit_card.applicant_line_ids:
                    rec.merit_agg_ids.create({
                        'name':  section.name,
                        'merit_reg_id': rec.id
                    })

    def calculate_merit(self):
        try:
            tot_aggregate_percent = sum([self.bs_aggregate_percent + self.ms_aggregate_percent + self.entry_test_aggregate_percent + self.hssc_aggregate_percent + self.ssc_aggregate_percent + self.interview_aggregate_percent])
            if not tot_aggregate_percent == 100:
                raise UserError('Aggregate Combination Must Be Equal to 100')

            # self.merit_lines.filtered(lambda x: not x.transferred and not x.selected and not x.waiting).unlink()
            self.merit_agg_ids.unlink()

            domain = [('state', 'not in', ('draft', 'reject')), ('fee_voucher_state', '=', 'verify'), ('register_id', '=', self.register_id.id),
                      ('prefered_program_id', '=', self.program_id.id),]
            applicants = self.env['odoocms.application'].search(domain)
            previous_merits = self.env['odoocms.merit.registers'].search([('register_id', '=', self.register_id.id), ('program_id', '=', self.program_id.id), ('id', '!=', self.id)]).merit_lines.filtered(lambda x: x.selected and not x.rejected).applicant_id

            if applicants:
                if previous_merits:
                    applicants = applicants - previous_merits

                # applicant entry test
                entry_test_domain = [('state', '=', True), ('register_id', '=', self.register_id.id), ('slot_type', '=', 'test'), ('paper_status', '!=', 'missed')]
                applicant_test = self.env['applicant.entry.test'].search(entry_test_domain)

                def caluclate_aggregate(self, application, entry_test):
                    aggregate = 0.0
                    academic_data = application.applicant_academic_ids
                    ssc_percentage = academic_data.filtered(lambda x: x.degree_name.year_age == 10).percentage or 0.0
                    hssc_percentage = academic_data.filtered(lambda x: x.degree_name.year_age == 12).percentage or 0.0
                    bs_percentage = academic_data.filtered(lambda x: x.degree_name.year_age == 16).percentage or 0.0
                    ms_percentage = academic_data.filtered(lambda x: x.degree_name.year_age == 18).percentage or 0.0

                    entry_test_percentage = 0.0
                    interview_test_percentage = 0.0
                    # only test
                    if self.program_id.entry_test and not self.program_id.interview and not self.program_id.calculate_merit_with_exemption:
                        entry_test_percentage = self.entry_test_percentage(entry_test, application, 'test') or 0.0
                        interview_test_percentage = 0.0

                    # only interview
                    elif not self.program_id.entry_test and self.program_id.interview and not self.program_id.calculate_merit_with_exemption:
                        interview_test_percentage = self.entry_test_percentage(entry_test, application, 'interview') or 0.0
                        entry_test_percentage = 0.0

                    # both test and intervew
                    elif self.program_id.entry_test and self.program_id.interview and not self.program_id.calculate_merit_with_exemption:
                        entry_test_percentage = self.entry_test_percentage(entry_test, application, 'test') or 0.0
                        interview_test_percentage = self.entry_test_percentage(entry_test, application, 'interview') or 0.0
                    elif self.program_id.calculate_merit_with_exemption and application.pre_test_total_marks:
                        entry_test_percentage = (application.pre_test_marks / application.pre_test_total_marks) * 100 or 0.0
                        interview_test_percentage = 0.0

                    ssc_aggregate = (self.ssc_aggregate_percent / 100) * ssc_percentage
                    hssc_aggregate = (self.hssc_aggregate_percent / 100) * hssc_percentage
                    bs_aggregate = (self.bs_aggregate_percent / 100) * bs_percentage
                    ms_aggregate = (self.ms_aggregate_percent / 100) * ms_percentage

                    test_aggregate = (self.entry_test_aggregate_percent / 100) * entry_test_percentage
                    interview_aggregate = (self.interview_aggregate_percent / 100) * interview_test_percentage

                    aggregate = ssc_aggregate + hssc_aggregate + test_aggregate + \
                                interview_aggregate + bs_aggregate + ms_aggregate
                    return "{:.2f}".format(aggregate)

                already_selected = self.merit_lines.mapped('applicant_id')
                applicants = applicants - already_selected
                for application in applicants:
                    pre_test_percentage = 0
                    pretest_marks = 0
                    entry_test = applicant_test.filtered(lambda x: x.student_id == application and x.paper_conducted)

                    if (entry_test and entry_test.applicant_line_ids) or entry_test.exempt_entry_test or application.prefered_program_id.calculate_merit_with_exemption:
                        if not application.prefered_program_id.calculate_merit_with_exemption:
                            entry_test_percentage = self.entry_test_percentage(entry_test[0], application, 'test')
                        else:
                            entry_test_percentage=0
                        if entry_test_percentage >= self.minimum_test_percentage:
                            if not application.prefered_program_id.calculate_merit_with_exemption:
                                entry_test = entry_test[0]
                            aggregate = caluclate_aggregate(self, application, entry_test)
                            if float(aggregate) >= self.minimum_aggregate:
                                selected = True
                                if self.waiting_below > 0 and float(aggregate) < self.waiting_below:
                                    selected = False
                                if application.pre_test_id and application.pre_test_marks and application.pre_test_id.pre_test_total_marks:
                                    pre_test_percentage = (application.pre_test_marks / application.pre_test_id.pre_test_total_marks) * 100
                                    pretest_marks = application.pre_test_marks if application.pre_test_marks else 0

                                data = {
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
                                    'cbt_percentage': round(((entry_test.cbt_marks or 0) / (entry_test.entry_test_marks or 60)) * 100, 2),
                                }
                                self.env['odoocms.merit.register.line'].sudo().create(data)
                                application.meritlist_id = self.id

                self.calculate_merit_no()

                for transfer in self.merit_lines.filtered(lambda x: x.transferred):
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
                                if application.prefered_program_id != self.program_id:
                                    count = 2
                                    for preference in application.preference_ids:
                                        preference.write({
                                            'preference':count
                                            })
                                        count += 1
                                        
                                    # application.preference_ids.sudo().create({
                                    #     'preference':1,
                                    #     'program_id':self.program_id.id
                                    # })
                                    application.transfer_program_id = application.prefered_program_id
                                    existing_preference = self.env['odoocms.application.preference'].sudo().search([
                                        ('application_id', '=', application.id),
                                        ('program_id', '=', self.program_id.id),
                                        ('preference', '=', 1)
                                    ], limit=1)
                                    
                                    if not existing_preference:
                                        self.env['odoocms.application.preference'].sudo().create({
                                            'preference': 1,
                                            'program_id': self.program_id.id,
                                            'application_id': application.id,
                                        })

                                    if len(application.preference_ids) > 3:
                                        application.preference_ids.filtered(lambda x:x.preference == 4).sudo().unlink()

                                selected = True
                            else:
                                transfer.sudo().unlink()

        except Exception as e:
            raise UserError(e)

    def submit(self):
        for rec in self:
            rec.publish_merit = True
            rec.posting_date = Datetime.now()
            rec.state = 'done'

    def open_merit(self):
        for rec in self:
            rec.state = 'open'
            rec.publish_merit = True

    def entry_test_percentage(self,entry_test, application, type_test):
        if type_test == 'test':
            entry_test = entry_test.filtered(lambda x: x.slot_type != 'interview')
            cbt_percentage = False
            pre_test_percentage = False
            if entry_test:
                entry_test = entry_test[-1]
                if entry_test.entry_test_marks and entry_test.entry_test_marks > 0:
                    cbt_percentage = float("{:.2f}".format((entry_test.cbt_marks/entry_test.entry_test_marks)*100))
                else:
                    raise UserError('CBT Total Marks Not Set ' + ' ' + application.application_no)
            if application.pre_test_id:
                if application.pre_test_total_marks and application.pre_test_id.pre_test_total_marks > 0:
                    pre_test_percentage = float("{:.2f}".format(
                        ((application.pre_test_marks or 0) / application.pre_test_id.pre_test_total_marks) * 100))
                else:
                    raise UserError('Pre Test Total Marks Not Set ' + ' ' + application.application_no)

            cbt_percentage = cbt_percentage or 0.0
            pre_test_percentage = pre_test_percentage or 0.0
            if application.pre_test_verification == 'verify':
                max_test_percentage = max(
                [cbt_percentage, pre_test_percentage])
            else:
                max_test_percentage = cbt_percentage
            return max_test_percentage

        elif type_test == 'interview' and entry_test:
            entry_test = entry_test.filtered(lambda x: x.slot_type != 'test')
            if entry_test:
                entry_test = entry_test[-1]
                if entry_test.interview_total_marks and entry_test.interview_total_marks > 0:
                    interview_percentage = float("{:.2f}".format(
                        (entry_test.interview_marks / entry_test.interview_total_marks) * 100))
                else:
                    raise UserError('Interview Total Marks Not Set ' + ' ' + application.application_no)
                return interview_percentage

    def calculate_merit_no(self):
        no = 1
        for merit_no in self.merit_lines.sorted(lambda x: x.aggregate, reverse=True):
            merit_no.merit_no = no
            no += 1
            
    @api.onchange('select_all')
    def onchange_select_all(self):
        if self.select_all:
            for rec in self.merit_lines:
                rec.selected= True

        if not self.select_all:
            for rec in self.merit_lines:
                rec.selected= False

    def generate_offer_letter(self): #this
        try:
            for rec in self:
                # if rec.publish_merit:
                #     for offer in rec.merit_lines:
                #         offer_letter = self.env['ucp.offer.letter'].search([])
                #         offer_letter.create({
                #             'applicant_id': offer.applicant_id.id,
                #             'program_id': offer.program_id.id,
                #         })
                if rec.publish_merit:
                    for offer in rec.merit_lines.filtered(lambda x: x.selected):
                        mail_value = {
                            'mail_to':offer.applicant_id.email,
                            'admission_mail':self.env.company.admission_mail,
                        }
                        offer_letter = self.env['ucp.offer.letter'].search([('applicant_id', '=', offer.applicant_id.id), ('program_id', '=', rec.program_id.id)])
                        if offer_letter:
                            offer.offer_send_status = True
                        if not offer_letter and not offer.offer_send_status:
                            check_black_list = offer.applicant_id.cnic or offer.applicant_id.passport
                            blacklist_applicant = self.env['admission.blacklist.application'].sudo().search([('cnic', '=', check_black_list)])
                            offer_letter = self.env['ucp.offer.letter'].create({
                                'applicant_id': offer.applicant_id.id,
                                'program_id': rec.program_id.id,
                                'merit_reg_id': rec.id,
                                'is_blacklisted': True if blacklist_applicant else False,
                            })
                            if not blacklist_applicant:
                                try:
                                    mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', offer.applicant_id.company_id.id)])
                                    template = self.env['mail.template'].sudo().search([('name', '=', 'Offer Letter'), ('mail_server_id', '=', mail_server_id.id)])
                                    # template = self.env.ref('odoocms_merit_ucp.mail_template_offer_letter').sudo()
                                    template.send_mail(offer_letter.id, force_send=True)
                                    offer.offer_send_status = True
                                except Exception as e:
                                    print(e)

                                # msg_txt = f'Dear {offer.applicant_id.name},\nYou have been selected for the {rec.program_id.name}. Please download the admission offer letter by logging in to your online admission portal and submit your documents in admission office as mentioned in your offer letter'

                                # updated_mobile_no = offer.applicant_id.mobile.replace('-', '')
                                # updated_mobile_no = updated_mobile_no.replace(' ', '')
                                # updated_mobile_no = updated_mobile_no.lstrip('0')
                                # message = self.env['send_sms'].sudo().render_template(msg_txt, 'odoocms.application', offer.applicant_id.id)
                                # gateway_id = self.env['gateway_setup'].sudo().search([], order='id desc', limit=1)
                                # if gateway_id:
                                #     self.env['send_sms'].sudo().send_sms_link(message, updated_mobile_no, offer.applicant_id.id,'odoocms.application', gateway_id, offer.applicant_id.name, 'other', 'student', False, False, False)
                    for rejected in rec.merit_lines.filtered(lambda x: x.rejected):
                        offer_letter = self.env['ucp.offer.letter'].search([('applicant_id', '=', rejected.applicant_id.id), ('program_id', '=', rejected.program_id.id)])
                        if not offer_letter and not offer.offer_send_status:
                            try:
                                mail_value = {
                                    'mail_to': rejected.applicant_id.email,
                                    'admission_mail': self.env.company.admission_mail,
                                    'company': self.env.company
                                }
                                # template = self.env.ref('odoocms_merit_ucp.mail_template_rejected_email').sudo()
                                mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', rejected.applicant_id.company_id.id)])
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Admission Rejected Email'), ('mail_server_id', '=', mail_server_id.id)])
                                template.with_context(mail_value).send_mail(self.id, force_send=True)
                                rejected.applicant_id.merit_rejected = True
                                offer.offer_send_status = True
                            except Exception as e:
                                print(e)
                    for waiting in rec.merit_lines.filtered(lambda x: x.waiting):
                        offer_letter = self.env['ucp.offer.letter'].search([('applicant_id', '=', waiting.applicant_id.id), ('program_id', '=', waiting.program_id.id)])
                        if not offer_letter and not offer.offer_send_status:
                            try:
                                mail_value = {
                                    'mail_to': waiting.applicant_id.email,
                                    'admission_mail': self.env.company.admission_mail,
                                    'company': self.env.company
                                }
                                # template = self.env.ref('odoocms_merit_ucp.mail_template_waiting_email').sudo()
                                mail_server_id = self.env['ir.mail_server'].sudo().search([('company_id', '=', waiting.applicant_id.company_id.id)])
                                template = self.env['mail.template'].sudo().search([('name', '=', 'Admission Waiting Email'), ('mail_server_id', '=', mail_server_id.id)])
                                template.with_context(mail_value).send_mail(self.id, force_send=True)
                                offer.offer_send_status = True
                            except Exception as e:
                                print(e)
                    self.offer_send = True
        
        except Exception as e:
            print(e)
            pass

    @api.depends('merit_lines', 'total_seats')
    def _remaining_seats(self):
        for rec in self:
            rec.remaining_seats = rec.total_seats - \
                len(rec.merit_lines.filtered(lambda x: x.selected))

    def download_report(self):
        client_action = {
            'type': 'ir.actions.act_url',
            'name': "Merit Register Line",
            'target': 'new',
            'url': f'/final/merit/register/line/report/download/{self.id}',
        }
        return client_action
    
    def _check_report(self):
        for rec in self:
            rec.print_report = False
            if rec.merit_lines:
                rec.print_report = True
            

class OdooCmsMeritRegisterLine(models.Model):
    _name = 'odoocms.merit.register.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'program_id , aggregate desc'
    _rec_name = 'applicant_id'
    _description = 'Odoo Cms Merit Register Line'

    merit_no = fields.Integer(string='Merit No')
    aggregate = fields.Float(string='Aggregate')
    applicant_id = fields.Many2one('odoocms.application', string='Application')
    religion_id = fields.Many2one('odoocms.religion', related='applicant_id.religion_id', string='Religion')
    preference_ids = fields.One2many('odoocms.application.preference', related='applicant_id.preference_ids', string='Preferences')
    applicant = fields.Char(related='applicant_id.name', string='Applicant Name', store=True)
    reference_no = fields.Char(related='applicant_id.application_no', string='Reference No',  store=True)
    merit_reg_id = fields.Many2one('odoocms.merit.registers', ondelete='cascade')
    program_id = fields.Many2one('odoocms.program', string='Program')
    pref1 = fields.Char(string='Preference 1', compute='_get_preferences', store=True)
    pref2 = fields.Char(string='Preference 2')
    pref3 = fields.Char(string='Preference 3')
    public_visible = fields.Boolean(string='Public Visible')
    selected = fields.Boolean(string='Selected')
    waiting = fields.Boolean(string='Waiting', compute='_compute_waiting')
    rejected = fields.Boolean('Rejected')
    reject_reason_id = fields.Many2one('odoocms.application.reject.reason', 'Reject Reason')
    matric_marks = fields.Integer(string='Matric Marks', compute='_get_matric_marks', store=True)
    matric_total_marks = fields.Integer(string='Matric Total Marks', compute='_get_matric_marks', store=True)
    matric_marks_per = fields.Float(string='Matric Percentage')
    inter_marks = fields.Integer(string='Inter Marks', compute='_get_inter_marks', store=True)
    inter_total_marks = fields.Integer(string='Inter Total Marks', compute='_get_inter_marks', store=True)
    bs_cgpa = fields.Float('BS CGPA', compute='_get_cgpa')
    ms_cgpa = fields.Float('MS CGPA', compute='_get_cgpa')
    inter_marks_per = fields.Float(string='Inter Percentage')
    entry_test_marks = fields.Integer(string='Entry Test Marks')
    pre_test_marks = fields.Integer(string='Pre Test Marks', compute='_get_pre_test_marks', store=True)
    cbt_english = fields.Integer(string='English Marks', compute='_get_cbt_eng_marks', store=True)
    cbt_t_english = fields.Integer(string='Total English Marks')
    cbt_per_english = fields.Integer(string='Precentage English')
    cbt_math = fields.Integer(string='Mathematics Marks', compute='_get_cbt_math_marks', store=True)
    cbt_t_math = fields.Integer(string='Total Mathematics Marks')
    cbt_per_math = fields.Integer(string='Percentage Mathematics')
    cbt_physics = fields.Integer(string='Physics Marks', compute='_get_cbt_phy_marks', store=True)
    cbt_t_physics = fields.Integer(string='Total Physics Marks')
    cbt_per_physics = fields.Integer(string='Percentage Physics')
    cbt_chemistry = fields.Integer(string='Chemistry Marks', compute='_get_cbt_chem_marks', store=True)
    cbt_t_chemistry = fields.Integer(string='Total Chemistry Marks')
    cbt_per_chemistry = fields.Integer(string='Percentage Chemistry')
    cbt_analytical = fields.Integer(string='Analytical Marks', compute='_get_cbt_analy_marks', store=True)
    cbt_t_analytical = fields.Integer(string='Total Analytical Marks')
    cbt_per_analytical = fields.Integer(string='Percentage Analytical')
    cbt_bio = fields.Integer(string='Biology Marks', compute='_get_cbt_bio_marks', store=True)
    cbt_t_bio = fields.Integer(string='Total Biology Marks')
    cbt_per_bio = fields.Integer(string='Percentage Biology')
    cbt_rc = fields.Integer(string='Reading Comprehension', compute='_get_cbt_rc_marks', store=True)
    cbt_t_rc = fields.Integer(string='Total Reading Comprehension')
    cbt_per_rc = fields.Integer(string='Precentage Reading Comprehension')
    cbt_ew = fields.Integer(string='Essay Writing', compute='_get_cbt_ew_marks', store=True)
    cbt_t_ew = fields.Integer(string='Total Essay Writing')
    cbt_per_ew = fields.Integer(string='Percentage Essay Writing')

    cbt_obtained = fields.Integer(string='CBT Obtained Marks',)
    cbt_total = fields.Integer(string='CBT Total Marks')
    cbt_percentage = fields.Float(string='CBT Percentage')

    cbt_section_ids = fields.One2many('cbt.section.marks', 'merit_line_id',compute='_get_cbt_sections',store=True)
    cbt_aggregate_ids = fields.One2many('cbt.test.aggregate', 'merit_line_id')
    transferred = fields.Boolean('Transfered', default=False)
    offer_allocated = fields.Boolean('Offer Allocated',compute='_offer_allocated')
	
    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    pre_test_name = fields.Char(string="Pre Test Name")
    pre_test_percentage = fields.Integer(string="Pre Test Percentage", readonly=True)
    pretest_marks = fields.Integer(string="Pre Test Marks", readonly=True)

    def _offer_allocated(self):
        for rec in self:
            rec.offer_allocated = False
            offer_letter = self.env['ucp.offer.letter'].sudo().search([('applicant_id','=',rec.applicant_id.id)],limit=1)
            if offer_letter:
                rec.offer_allocated = True
            
            

    def reject_application(self):
        for rec in self:
            if (not rec.reject_reason_id):
                raise UserError(_('Rejection Reason not provided'))
            rec.selected = False
            rec.applicant_id.write({
                'state': 'reject'
            })

    def _compute_waiting(self):
        for rec in self:
            if not rec.selected and not rec.rejected:
                rec.waiting = True
            if rec.selected and not rec.rejected:
                rec.waiting = False
            if rec.rejected:
                rec.waiting = False
                rec.selected = False

    @api.depends('applicant_id', 'merit_no')
    def _get_preferences(self):
        for rec in self:
            for pref in rec.applicant_id.preference_ids:
                if pref.preference == 1:
                    rec.pref1 = pref.program_id.name
                elif pref.preference == 2:
                    rec.pref2 = pref.program_id.name
                elif pref.preference == 3:
                    rec.pref3 = pref.program_id.name

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_eng_marks(self):
        for rec in self:
            rec.cbt_english = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'English':
                    rec.cbt_english = cbt_sec.obtained_marks
                    rec.cbt_t_english = cbt_sec.total_marks
                    if rec.cbt_total and rec.cbt_total > 0:
                        rec.cbt_per_english = round(
                            (cbt_sec.obtained_marks/cbt_sec.total_marks)*100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_obtained_marks(self):
        for rec in self:
            rec.cbt_obtained = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            # for app in applicant_cbt_id:
            rec.cbt_obtained = applicant_cbt_id.entry_test_marks
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                rec.cbt_total += cbt_sec.total_marks
            if rec.cbt_total and rec.cbt_total > 0:
                rec.cbt_percentage = round(
                    (rec.cbt_obtained/rec.cbt_total)*100, 2)
            else:
                raise UserError('CBT Total Marks Not Set '  + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_math_marks(self):
        for rec in self:
            rec.cbt_math = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Mathematics':
                    rec.cbt_math = cbt_sec.obtained_marks
                    rec.cbt_t_math = cbt_sec.total_marks
                    if cbt_sec.total_marks and cbt_sec.total_marks > 0:
                        rec.cbt_per_math = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + cbt_sec.name + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_phy_marks(self):
        for rec in self:
            rec.cbt_physics = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Physics':
                    rec.cbt_physics = cbt_sec.obtained_marks
                    rec.cbt_t_physics = cbt_sec.total_marks
                    if cbt_sec.total_marks and cbt_sec.total_marks > 0:
                        rec.cbt_per_physics = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + cbt_sec.name + ' ' + rec.applicant_id.application_no)
    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_chem_marks(self):
        for rec in self:
            rec.cbt_chemistry = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Chemistry':
                    rec.cbt_chemistry = cbt_sec.obtained_marks
                    rec.cbt_t_chemistry = cbt_sec.total_marks
                    if cbt_sec.total_marks and cbt_sec.total_marks > 0:
                        rec.cbt_per_chemistry = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + cbt_sec.name + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_analy_marks(self):
        for rec in self:
            rec.cbt_analytical = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Analytical':
                    rec.cbt_analytical = cbt_sec.obtained_marks
                    rec.cbt_t_analytical = cbt_sec.total_marks
                    if cbt_sec.total_marks and cbt_sec.total_marks > 0:
                        rec.cbt_per_analytical = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + cbt_sec.name + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_bio_marks(self):
        for rec in self:
            rec.cbt_bio = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Biology':
                    rec.cbt_bio = cbt_sec.obtained_marks
                    rec.cbt_t_bio = cbt_sec.total_marks
                    if cbt_sec.total_marks and cbt_sec.total_marks > 0:
                        rec.cbt_per_bio = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + cbt_sec.name + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_rc_marks(self):
        for rec in self:
            rec.cbt_rc = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Reading Comprehension':
                    rec.cbt_rc = cbt_sec.obtained_marks
                    rec.cbt_t_rc = cbt_sec.total_marks
                    if cbt_sec.total_marks and cbt_sec.total_marks > 0:
                        rec.cbt_per_rc = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)
                    else:
                        raise UserError('CBT Total Marks Not Set ' + cbt_sec.name + ' ' + rec.applicant_id.application_no)

    @api.depends('applicant_id', 'merit_no')
    def _get_cbt_ew_marks(self):
        for rec in self:
            rec.cbt_ew = 0
            applicant_cbt_id = self.env['applicant.entry.test'].search(
                [('student_id', '=', rec.applicant_id.id), ('paper_conducted', '!=', False), ('state', '=', True)])
            for cbt_sec in applicant_cbt_id.applicant_line_ids:
                if cbt_sec.name == 'Essay Writing':
                    rec.cbt_ew = cbt_sec.obtained_marks
                    rec.cbt_t_ew = cbt_sec.total_marks
                    if cbt_sec.total_marks:
                        rec.cbt_per_ew = round(
                            (cbt_sec.obtained_marks / cbt_sec.total_marks) * 100, 2)

    @api.depends('applicant_id.applicant_academic_ids')
    def _get_inter_marks(self):
        for rec in self:
            applicant_marks = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)])
            for marks in applicant_marks.applicant_academic_ids:
                if marks.degree_name.name in ('Intermediate', 'A-Level') or marks.degree_name.year_age == 12:
                    obtained_marks = marks.obt_marks
                    rec.inter_marks = obtained_marks
                    rec.inter_total_marks = marks.total_marks
                    rec.inter_marks_per = marks.percentage

    # @api.depends('applicant_id.applicant_academic_ids')
    def _get_cgpa(self):
        for rec in self:
            rec.bs_cgpa = 0
            rec.ms_cgpa = 0
            academics = rec.applicant_id.applicant_academic_ids
            bs = academics.filtered(lambda x: x.degree_name.year_age == 16)
            if bs:
                rec.bs_cgpa = bs.obtained_cgpa
            ms = academics.filtered(lambda x: x.degree_name.year_age == 18)
            if ms:
                rec.ms_cgpa = ms.obtained_cgpa

    @api.depends('applicant_id.applicant_academic_ids')
    def _get_matric_marks(self):
        for rec in self:
            applicant_marks = self.env['odoocms.application'].search(
                [('id', '=', rec.applicant_id.id)])
            for marks in applicant_marks.applicant_academic_ids:
                if marks.degree_name.name in ('Matric', 'O-Level'):
                    obtained_marks = marks.obt_marks
                    rec.matric_marks = obtained_marks
                    rec.matric_total_marks = marks.total_marks
                    rec.matric_marks_per = marks.percentage

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

    # @api.depends('applicant_id')
    def _get_cbt_sections(self):
        for rec in self:
            rec.cbt_section_ids = [(5)]
            entry_test = self.env['applicant.entry.test'].sudo().search([('student_id','=',rec.applicant_id.id)],limit=1,order='id desc')
            if entry_test and entry_test.paper_conducted and entry_test.applicant_line_ids:
                for section in entry_test.applicant_line_ids:
                    self.env['cbt.section.marks'].sudo().create({ "merit_line_id":rec.id,'marks':section.obtained_marks,'total_marks':section.total_marks,'name':section.name })
                    # rec.cbt_section_ids = [(0, 0,  )]


class OdooCMSAdmissionApplication(models.Model):
    _inherit = 'odoocms.application'

    meritlist_id = fields.Many2one('odoocms.merit.registers', 'Merit List', required=False)
    meritlist_date = fields.Datetime('MeritList Date', related='meritlist_id.posting_date', store=True, readonly=True)


class OdooCmsMeritAggregate(models.Model):
    _name = 'odoocms.merit.test.aggregate'
    _description = 'Merit Aggregate'

    name = fields.Char(string='Name')
    merit_reg_id = fields.Many2one('odoocms.merit.registers', string='Merit Register')
    program_id = fields.Many2one('odoocms.program', string='Program', )
    aggregate = fields.Float(string='Aggregate')


# class OdooCmsMeritAggregate(models.Model):
#     _name = 'odoocms.merit.pre.test.aggregate'
#     _description = 'Odoo Cms Pre Test Merit Aggregate'
#
#     pre_test_id = fields.Many2one('odoocms.pre.test', string='Name')
#     aggregate = fields.Float(string='Aggregate')
#     merit_reg_id = fields.Many2one(
#         'odoocms.merit.registers', string='Merit Register')

class OdoocmsMeritProgram(models.Model):
    _name = 'odoocms.merit.program'
    _description = 'Odoocms Merit Program'

    merit_register_id = fields.Many2one('odoocms.merit.registers', 'Merit Register')
    program_id = fields.Many2one('odoocms.program', string='Program')


class CBTMarks(models.Model):
    _name = 'cbt.section.marks'
    _description = 'CBT Section Marks'

    name = fields.Char(string='Name')
    marks = fields.Integer(string='Obtained Marks')
    total_marks = fields.Integer('Total Marks')
    merit_line_id = fields.Many2one('odoocms.merit.register.line')


class CBTTestGroupAggregate(models.Model):
    _name = 'cbt.test.aggregate'
    _description = 'CBT Test Group Aggregate'

    name = fields.Char(string='Name')
    marks = fields.Integer(string='Marks')
    total_marks = fields.Integer('Total Marks')
    merit_line_id = fields.Many2one('odoocms.merit.register.line')
