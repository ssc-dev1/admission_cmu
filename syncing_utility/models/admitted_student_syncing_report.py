from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class OdoocmsApplicantFirstSemesterCourses(models.Model):
    _name = 'admitted.student.syncing.report'


    
    adm_student_code= fields.Char('adm_student_code')
    adm_student_name=fields.Char('adm_student_name')
    adm_partner_id =  fields.Integer('adm_partner_id')
    admission_no = fields.Char('admission_no')
    adm_student_state = fields.Char('adm_student_state')
    adm_prospectus_challan = fields.Char('adm_prospectus_challan')
    adm_account_move_id= fields.Integer('adm_account_move_id')
    adm_account_move_lines_count= fields.Integer('adm_account_movke_lines_count')
    adm_courses_count = fields.Integer('courses_count')
    adm_academic_term = fields.Char('adm_academic_term')
    adm_program =fields.Char('adm_program')
    adm_academic_document_count = fields.Integer('adm_academic_document_count')
    adm_scholarship_eligibility_count =fields.Integer('adm_scholarship_eligibility_count')
    applied_scholarship =fields.Char('applied_scholarship')
    cms_sync = fields.Boolean('cms_sync', default =True)
    to_be =fields.Boolean('to_be', default=True)
    adm_company_id=fields.Integer('adm_company_id')
    server_id =fields.Integer('server_id')
    adm_credit_hours =fields.Integer('adm_credit_hours')
    adm_eligibility_scholarships=fields.Char('adm_eligibility_scholarships')

    @api.model
    def call_db_procedure_admitted_student_syncing_report_store_procedure(self):

        conf=self.env['syncing.configuration'].sudo().search([('syncing_report_conf','=',True)], limit=1)
        db_host = conf.target_host
        db_name = conf.target_dbname
        db_user = conf.target_db_user
        db_password = conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_admitted_student_syncing_report_store_procedure')
            self.env.cr.execute("""
                CALL public.admitted_student_syncing_report_procedure(%s, %s, %s, %s)
            """, (db_host, db_name, db_user, db_password))
            self.env.cr.execute("SELECT id FROM admitted_student_syncing_report_failed_ids")
            failed_ids = self.env.cr.fetchall()
            if failed_ids:
                failed_ids_list = [row[0] for row in failed_ids]
                pass
         
            else:
                pass
            
            self.env.cr.execute("""
               UPDATE admitted_student_syncing_report AS adm
                SET server_id = cms.id
                FROM cms.admitted_student_syncing_report AS cms
                WHERE cms.client_id = adm.id
                AND server_id is null;
                """)
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()     

    @api.model
    def fill_data_sycning_report_table(self):
        

        students= self.env['odoocms.student'].sudo().search([('fee_paid','=',True),('to_be','=',False)])
        for st in students:
                move_line_count=0
                credit_hours=0
                adm_eligibility_scholarships=''
                prospectus_fee_receipt = self.env['account.move'].sudo().search([('student_id','=',st.id),('challan_type','=','prospectus_challan')],limit=1)
                admission_fee_receipt = self.env['account.move'].sudo().search([('student_id','=',st.id),('challan_type','=','admission')],limit=1)
                challan = self.env['odoocms.fee.barcode'].sudo().search([('label_id','=',1)],limit=1)
                applicant =self.env['odoocms.application'].sudo().search([('application_no','=',st.admission_no)])

                for aml in admission_fee_receipt.line_ids:
                    if not aml.name.startswith('INV/') and aml.name != 'Admission Fee':
                        credit_hours += aml.course_credit_hours
                        move_line_count += 1
                se_count=0
                for aps in st.applied_scholarship_ids: 
                    if  aps[0].scholarship_id and aps[0].scholarship_id.name:
                        applied_scholarship =aps[0].scholarship_id.name
                for se in st.scholarship_eligibility_ids:
                    if se.scholarship_id:
                        se_count +=1
                        adm_eligibility_scholarships +=','+se.scholarship_id.name if se_count >1 else se.scholarship_id.name
                data_values = {
                    'adm_student_code':st.code,
                    'adm_student_name':st.name,
                    'adm_partner_id':st.partner_id.id or applicant.partner_id.id,
                    'admission_no':st.admission_no or applicant.application_no,
                    'adm_student_state':st.state,
                    'adm_credit_hours':credit_hours,
                    'adm_prospectus_challan':prospectus_fee_receipt.old_challan_no or '',
                    'adm_account_move_id':admission_fee_receipt.id or None,
                    'adm_company_id':st.company_id.id or applicant.company_id.id,
                    'adm_account_move_lines_count':move_line_count or None,
                    'adm_courses_count':len(applicant.first_semester_courses) or 0,
                    'adm_academic_term':applicant.term_id.name or st.term_id.name,
                    'adm_program':st.program_id.name,
                    'adm_academic_document_count':len(applicant.applicant_academic_ids) or 0,
                    'adm_scholarship_eligibility_count': st.scholarship_eligibility_ids and len(st.scholarship_eligibility_ids),
                    'adm_eligibility_scholarships':adm_eligibility_scholarships or '',
                    'applied_scholarship':applied_scholarship
                    }
                try:
                    self.env['admitted.student.syncing.report'].create(data_values)
                    st.to_be=True
                except Exception as e :
                    print(e)
                    continue