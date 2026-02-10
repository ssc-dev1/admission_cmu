from odoo import models, fields, api


class ApplicationTransferLine(models.Model):
    _name = 'application.transfer.register.line'
    _description = 'Admission Register Transfer Line'

    applicant_id = fields.Many2one('odoocms.application', string='Applicant', required=True)
    transfer_register_id = fields.Many2one('application.transfer.register', string='Transfer Register', ondelete='cascade')
    preference_first = fields.Many2one('odoocms.program', compute='_get_preference', store=True, string='Preference First')
    preference_second = fields.Many2one('odoocms.program', compute='_get_preference', store=True, string='Preference Second')
    preference_third = fields.Many2one('odoocms.program', compute='_get_preference', store=True, string='Preference Third')
    merit_register_id = fields.Many2one('odoocms.merit.registers', string='Transfer To Merit')
    remaining_seats = fields.Integer('Remaining Seats', related='merit_register_id.remaining_seats')
    transferd = fields.Boolean('Transfered')

    @api.depends('transfer_register_id')
    def _get_preference(self):
        merit_registers = self.env['odoocms.merit.registers'].sudo().search([('remaining_seats','>',0),('state','!=','done')])
        for rec in self:
            rec.preference_first = False
            rec.preference_second = False
            rec.preference_third = False
            preferences = rec.applicant_id.preference_ids
            first_preference = preferences.filtered(
                lambda x: x.preference == 1)
            second_preference = preferences.filtered(
                lambda x: x.preference == 2)
            third_preference = preferences.filtered(
                lambda x: x.preference == 3)
            if preferences:
                if first_preference:
                    rec.preference_first = first_preference[0].program_id
                if second_preference:
                    rec.preference_second = second_preference[0].program_id
                if third_preference:
                    rec.preference_third = third_preference[0].program_id
            second_preference_merit_registers = merit_registers.filtered(lambda x:x.program_id==rec.preference_second)
            third_preference_merit_registers = merit_registers.filtered(lambda x:x.program_id==rec.preference_third)
            if second_preference_merit_registers:
                rec.merit_register_id=second_preference_merit_registers[0]
            elif third_preference_merit_registers:
                rec.merit_register_id = third_preference_merit_registers[0]
            else:
                rec.merit_register_id = False

class ApplicationTransfer(models.Model):
    _name = 'application.transfer.register'
    _description = 'Admission Register'

    name = fields.Char(string='Name', required=True)
    transfer_applicant_ids = fields.One2many('application.transfer.register.line', 'transfer_register_id', string='Applicants')
    admission_register_id = fields.Many2one('odoocms.admission.register', string='Admission Register', required=True)
    prefered_program_id = fields.Many2one('odoocms.program', string='Prefered Program')
    state = fields.Selection([('draft', 'Draft'),('done', 'Done'),], string='State', default='draft')

    company_id = fields.Many2one('res.company', string='Company', required=True, index=True, default=lambda self: self.env.company, ondelete='restrict')
    company_code = fields.Integer(related="company_id.company_code", readonly=True, store="true")

    @api.onchange('admission_register_id', 'prefered_program_id')
    def _get_applicant(self):
        for rec in self:
            if rec.transfer_applicant_ids:
                rec.transfer_applicant_ids = [
                    (2, _id) for _id in rec.transfer_applicant_ids.ids]

            if rec.admission_register_id and rec.create_date:
                # applications = self.env['applicant.entry.test'].sudo().search([('paper_conducted', '=', True)]).filtered(lambda x: x.student_id.register_id == rec.admission_register_id).mapped('student_id')
                merit_register = self.env['odoocms.merit.registers'].sudo().search([('register_id','=',rec.admission_register_id.id)])
                if rec.prefered_program_id:
                    merit_register = merit_register.filtered(lambda x:x.program_id.id == rec.prefered_program_id.id)
                
                applications = merit_register.mapped('merit_lines').filtered(lambda x:not x.selected and x.waiting).mapped('applicant_id')
                selected_app = self.env['odoocms.merit.register.line'].sudo().search([('applicant_id','in',applications.ids),('selected','=',True)])
                if selected_app:
                    applications = applications.filtered(lambda x:x.id not in selected_app.mapped('applicant_id').ids)
                    

                # selected_application = self.env['odoocms.merit.register.line'].sudo().search([('selected', '=', False),('waiting','=',True)]).mapped('applicant_id')
                # applications = self.env['odoocms.application'].sudo().browse(selected_application.ids)
                # if rec.prefered_program_id:
                #     applications = applications.filtered(lambda x: x.prefered_program_id == rec.prefered_program_id)
                for application in applications:
                    rec.transfer_applicant_ids.create({
                        'applicant_id': application.id,
                        'transfer_register_id': rec.id,
                    })

    @api.model
    def create(self, vals):
        # Agregar codigo de validacion aca
        result = super(ApplicationTransfer, self).create(vals)
        result._get_applicant()
        return result

    def transffered_merit(self):
        if self.transfer_applicant_ids:    
            for rec in self.transfer_applicant_ids:
                if rec.merit_register_id and rec.merit_register_id.remaining_seats > 0:
                    previous_merit_register_line  = self.env['odoocms.merit.register.line'].search([('applicant_id', '=', rec.applicant_id.id)], limit=1, order='id desc')
                    application_preference = self.env['odoocms.application'].search([('id', '=', rec.applicant_id.id)], limit=1).preference_ids
                    # previous_preference = application_preference.filtered(lambda x: x.program_id == rec.applicant_id.prefered_program_id)
                    new_preference = application_preference.filtered(lambda x: x.program_id.id == rec.merit_register_id.program_id.id)[:1]
                    if not new_preference:
                        new_preference=new_preference.sudo().create({
                            'application_id': rec.applicant_id.id,
                            'preference': 4,
                            'program_id': rec.merit_register_id.program_id.id,
                        })
                    if not previous_merit_register_line:
                        new_preference.preference = 1 
                        conflicts = rec.applicant_id.preference_ids.filtered(lambda x: x.preference == 1 and x.id != new_preference.id)
                        for conflict_record in conflicts:
                            current_preference = 1
                            check =True
                            while check:
                                current_preference += 1
                                existing_record = rec.applicant_id.preference_ids.filtered(lambda x: x.preference == current_preference)
                                if existing_record:
                                    for er in existing_record:
                                        if er.id == conflict_record.id:
                                            check=False
                                            break
                                else:
                                    conflict_record.preference = current_preference
                                    check=False
                        rec.applicant_id.prefered_program_id = False


                    if previous_merit_register_line:                      
                        new_preference.preference = 1 
                        conflicts = rec.applicant_id.preference_ids.filtered(lambda x: x.preference == 1 and x.id != new_preference.id)
                        for conflict_record in conflicts:
                            current_preference = 1
                            check =True
                            while check:
                                current_preference += 1
                                existing_record = rec.applicant_id.preference_ids.filtered(lambda x: x.preference == current_preference)
                                if existing_record:
                                    for er in existing_record:
                                        if er.id == conflict_record.id:
                                            check=False
                                            break
                                else:
                                    conflict_record.preference = current_preference
                                    check=False
                        rec.applicant_id.prefered_program_id = False
                        previous_merit_register_line.sudo().unlink()

                    
                    self.env['odoocms.merit.register.line'].sudo().create({
                        'merit_reg_id': rec.merit_register_id.id,
                        'applicant_id':rec.applicant_id.id,
                        'program_id': rec.merit_register_id.program_id.id,
                        'public_visible': True,
                        'selected': True,
                        'transferred':True,
                        'merit_no':999,
                        # 'cbt_obtained': entry_test.cbt_marks,
                        # 'cbt_total': entry_test.entry_test_marks,
                        # 'cbt_percentage': round(((entry_test.cbt_marks or 0)/(entry_test.entry_test_marks or 60))*100, 2),
                        })
                    rec.applicant_id.meritlist_id =rec.merit_register_id.id
                    rec.transferd = True
                    

            self.state='done'

    def generate_offer_letter(self):
        merit_registers = self.transfer_applicant_ids.filtered(lambda x:x.transferd).mapped('merit_register_id')
        for rec in merit_registers:
            rec.generate_offer_letter()
