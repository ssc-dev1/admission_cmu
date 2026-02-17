from odoo import models, fields, api
from odoo.tools.misc import xlsxwriter
from odoo.exceptions import UserError
from datetime import datetime, date,timedelta
import asyncio
import base64
import io
import logging



_logger = logging.getLogger(__name__)


class sms_track(models.Model):
    _inherit = "odoocms.application"

    @api.model
    def get_admission_comparison_report(self, report_type=None, group_by=None, term_id =None, compare_term =None,days =None):
        description=''
        if term_id and days and compare_term:
            if term_id:
                term_id =self.env['odoocms.academic.term'].sudo().search([('id','=',int(term_id)),('company_id','=',self.env.company.id)], limit =1)
                admission_register = self.env['odoocms.admission.register'].search([
                ('term_id', '=', int(term_id)),
                ('company_id','=', self.env.company.id)], order='id desc')
                if len(admission_register) <=0:
                    raise ('(No Admission Register Found for term %s.'%(term_id.name))
                else:
                    register_ids = admission_register.ids
                    register_ids_tuple = tuple(register_ids) if len(register_ids) > 1 else (register_ids[0],)
                    print(register_ids_tuple)
            if compare_term:
                compare_term =self.env['odoocms.academic.term'].sudo().search([('id','=',int(compare_term)),('company_id','=',self.env.company.id)], limit =1)

            # from_date_dt = datetime.strptime(from_date, '%Y-%m-%d')
            # to_date_dt = datetime.strptime(to_date, '%Y-%m-%d')
            if term_id and term_id.admission_start_date:
                from_date_dt =term_id.admission_start_date
                to_date_dt =term_id.admission_start_date+ timedelta(days=int(days))
                to_date =to_date_dt.strftime('%Y-%m-%d')
                from_date =from_date_dt.strftime('%Y-%m-%d')
            else:
                raise UserError('Admission start date is not set for term ID')
            if compare_term  and compare_term.admission_start_date:
                prev_from_date_dt = compare_term.admission_start_date 
                prev_to_date_dt = compare_term.admission_start_date + timedelta(days=int(days))
                prev_from_date = prev_from_date_dt.strftime('%Y-%m-%d')
                prev_to_date = prev_to_date_dt.strftime('%Y-%m-%d')
            else:
                raise UserError('Admission start date is not set for Compare Term')
            
            query = self._build_query(register_ids_tuple,term_id.code,compare_term.code,from_date, to_date,prev_from_date,prev_to_date,report_type, group_by,self.env.company.id)
            description = term_id.name + '  date from  (' +from_date_dt.strftime('%d %b %Y') +')   to  (' + to_date_dt.strftime('%d %b %Y') +')     <---------------------------------------------------------->      '+ compare_term.name + '  date from   ('+prev_from_date_dt.strftime('%d %b %Y')+')  to  ('+prev_to_date_dt.strftime('%d %b %Y')+')'
            print(query)
            _logger.warning(query)
            self.env.cr.execute(query)
            data =  self.env.cr.dictfetchall()
            columns = self._get_columns(data)
            keys = self._get_keys(data)
            # variance_columns =['forms_submitted_var', 'verified_and_complete_var', 'appeared_in_test_var', 'selected_var', 'admitted_var']
            # for vc in variance_columns:
            #     columns.append(vc.replace("_", " ").title())
            #     keys.append(vc)
            #     for d in data:
            #         if vc =='forms_submitted_var':
            #             pass
            #         if vc =='verified_and_complete_var':
            #             pass
            #         if vc =='appeared_in_test_var':
            #             pass
            #         if vc =='selected_var':
            #             pass
            #         if vc =='admitted_var':
            #             pass
            #         d.update()

            return data, columns, keys, description
        else:
            if not term_id: 
                pass
                # raise UserError('Term must be given')
            if not compare_term: 
                pass
                # raise UserError('Dompare term must be given')
            if not days: 
                pass
                # raise UserError('No of days must be given')

    @api.model
    def get_terms(self):
        terms = self.env['odoocms.academic.term'].search([('company_id','=',self.env.company.id)], order='number desc')
        return [{'id': term.id, 'name': term.name} for term in terms]

    @api.model
    def get_companies(self):
        companyies = self.env['res.company'].search([('id','=',self.env.company.id)], order='name')
        return [{'id': company.id, 'name': company.name} for company in companyies]
    def _build_query(self,register_ids_tuple,term, compare_term,from_date, to_date,prev_from_date,prev_to_date,report_type, group_by,company_id):
            if report_type:
                query = f"""
                 """
                query = f"""
                            WITH 
                            relevant_programs AS (
                                SELECT 
                                    prm_rel.program_id,
									ins.name as faculty,
                                    prgm.name AS program_name
                                FROM 
                                    odoocms_admission_register reg
                                LEFT JOIN 
                                    register_program_rel prm_rel ON prm_rel.register_id = reg.id
                                JOIN 
                                    odoocms_program prgm ON prgm.id = prm_rel.program_id
								JOIN 
									odoocms_institute ins on ins.id =prgm.institute_id
                                WHERE reg.id in {register_ids_tuple}
                            ),
                            entry_tests AS (
    SELECT DISTINCT student_id,
        CASE
            WHEN DATE(date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
            WHEN DATE(date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
        END AS test_term
    FROM applicant_entry_test
    WHERE paper_conducted = TRUE
),
                            application_data AS (
                         SELECT 
        ap.id AS application_id,
        ap.prefered_program_id,
        ap.state,
        DATE(ap.create_date),
        ap.term_id,
        ap.create_date,
        ap.application_submit_date,
        COALESCE(
            CASE
                WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                WHEN et.test_term IS NOT NULL THEN et.test_term
            END, NULL
        ) AS year_label
    FROM odoocms_application ap
    LEFT JOIN entry_tests et ON et.student_id = ap.id
    WHERE 
        ap.prefered_program_id IS NOT NULL
        AND ap.company_id = '{company_id}'
        AND ap.prefered_program_id IN (SELECT program_id FROM relevant_programs)
        AND (
            DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' 
            OR DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
            OR DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' 
            OR DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
            OR DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' 
            OR DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
            OR EXISTS (
                SELECT 1 FROM applicant_entry_test 
                WHERE DATE(date) BETWEEN '{from_date}' AND '{to_date}' 
                  AND paper_conducted = TRUE 
                  AND student_id = ap.id
            )
            OR EXISTS (
                SELECT 1 FROM applicant_entry_test 
                WHERE DATE(date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' 
                  AND paper_conducted = TRUE 
                  AND student_id = ap.id
            )
        )
                            ),
                            submit_application_data AS (
                                SELECT 
								   ap.id as application_id,
                                   COUNT(DISTINCT ap.id) AS sumitted_application,
                                    CASE
                                                                               WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    odoocms_application ap
                                WHERE 
                                     ap.prefered_program_id IS NOT NULL
                                    AND ap.company_id = '{company_id}'
									AND ap.state ='submit'
                                    AND ap.prefered_program_id IN (SELECT program_id FROM relevant_programs)
                                    AND (
                                        DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' 
                                        OR DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                                    )
								 GROUP BY
								 ap.id,
								 CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                            prospectus_data AS (
                                                   SELECT 
								   ap.id as application_id,
                                   COUNT(DISTINCT ap.id) AS prospectus_paid,
                                    CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    odoocms_application ap
                                WHERE 
                                     ap.prefered_program_id IS NOT NULL
                                    AND ap.company_id = '{company_id}'
                                    AND ap.prefered_program_id IN (SELECT program_id FROM relevant_programs)
                                    AND (
                                        DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' 
                                        OR DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                                    )
								 GROUP BY
								 ap.id,
								 CASE
                                       WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                      
                            entry_test_data AS (
                                SELECT 
                                    et.student_id,
                                    COUNT(DISTINCT et.student_id) AS entry_test_appearance,
                                             CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    applicant_entry_test et
                                JOIN odoocms_application ap on et.student_id = ap.id
                                WHERE 
                                ap.id IN (SELECT application_id FROM application_data)
                                AND   et.paper_conducted = true
								AND (
                                        DATE(et.date) BETWEEN '{from_date}' AND '{to_date}' 
                                        OR DATE(et.date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                                    )
                                GROUP BY 
                                    et.student_id, 
                              								 CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

        
                            merit_list_data AS (
                                SELECT 
                                    ml.applicant_id,
                                    COUNT(DISTINCT ml.applicant_id) AS merit_list_appearance,
                                                          CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    odoocms_merit_register_line ml
                                JOIN odoocms_application ap on ml.applicant_id = ap.id
                                WHERE 
                                ap.id IN (SELECT application_id FROM application_data)
                                AND  ml.selected = true
								AND (
                                        DATE(ml.create_date) BETWEEN '{from_date}' AND '{to_date}' 
                                        OR DATE(ml.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                                    )
                                GROUP BY 
                                    ml.applicant_id, 
                            								 CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                    
                            admission_data AS (
                                SELECT 
                                    ap.id as application_id,
                                    COUNT(DISTINCT ap.id) AS admitted,
                                    CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    odoocms_fee_barcode am
                                JOIN odoocms_application ap on am.admission_no = ap.application_no
                                WHERE 
                                    ap.id IN (SELECT application_id FROM application_data)
                                     AND am.label_id =1
                                    AND am.state IN ('paid', 'partial')
                                                                        AND (
                                        DATE(am.date_payment) BETWEEN '{from_date}' AND '{to_date}'
                                        OR DATE(am.date_payment) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                                    )
                                GROUP BY 
                                    ap.id, 
                              								 CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.application_submit_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.application_submit_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
										WHEN DATE(ap.voucher_verified_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.voucher_verified_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                combined_data AS (
                                      SELECT 
                                        DISTINCT ap.application_id,
                                        rp.program_name,
                                        rp.faculty,
                                        ap.year_label,
                                        CASE WHEN sd.application_id IS NOT NULL THEN 1 ELSE 0 END AS submitted,
                                        CASE WHEN pd.application_id IS NOT NULL THEN 1 ELSE 0 END AS prospectus_paid,
                                        CASE WHEN etd.student_id IS NOT NULL THEN 1 ELSE 0 END AS entry_test_appearance,
                                        CASE WHEN mld.applicant_id IS NOT NULL THEN 1 ELSE 0 END AS merit_list,
                                        CASE WHEN ad.application_id IS NOT NULL THEN 1 ELSE 0 END AS admitted

                                    FROM relevant_programs rp
                                    LEFT JOIN application_data ap 
                                        ON ap.prefered_program_id = rp.program_id

                                    LEFT JOIN submit_application_data sd 
                                        ON sd.application_id = ap.application_id AND sd.year_label = ap.year_label

                                    LEFT JOIN prospectus_data pd 
                                        ON pd.application_id = ap.application_id AND pd.year_label = ap.year_label

                                    LEFT JOIN entry_test_data etd 
                                        ON etd.student_id = ap.application_id AND etd.year_label = ap.year_label

                                    LEFT JOIN merit_list_data mld 
                                        ON mld.applicant_id = ap.application_id AND mld.year_label = ap.year_label

                                    LEFT JOIN admission_data ad 
                                        ON ad.application_id = ap.application_id AND ad.year_label = ap.year_label
                                    ),

                            final_comparison AS (
                                SELECT 
                                    program_name,
                                    faculty,
                            
                                    SUM(CASE WHEN year_label = '{term}' THEN submitted ELSE 0 END) AS Forms_Submitted_{term},
                                    SUM(CASE WHEN year_label = '{term}' THEN prospectus_paid ELSE 0 END) AS Verified_and_Complete_{term},
                                    SUM(CASE WHEN year_label = '{term}' THEN entry_test_appearance ELSE 0 END) AS Appeared_in_Test_{term},
                                    SUM(CASE WHEN year_label = '{term}' THEN merit_list ELSE 0 END) AS Selected_{term},
                                    SUM(CASE WHEN year_label = '{term}' THEN admitted ELSE 0 END) AS Admitted_{term},
                            
                                    SUM(CASE WHEN year_label = '{compare_term}' THEN submitted ELSE 0 END) AS Forms_Submitted_{compare_term},
                                    SUM(CASE WHEN year_label = '{compare_term}' THEN prospectus_paid ELSE 0 END) AS Verified_and_Complete_{compare_term},
                                    SUM(CASE WHEN year_label = '{compare_term}' THEN entry_test_appearance ELSE 0 END) AS Appeared_in_Test_{compare_term},
                                    SUM(CASE WHEN year_label = '{compare_term}' THEN merit_list ELSE 0 END) AS Selected_{compare_term},
                                    SUM(CASE WHEN year_label = '{compare_term}' THEN admitted ELSE 0 END) AS Admitted_{compare_term},
                            		  ROUND(
                                        100.0 * (
                                            SUM(CASE WHEN year_label = '{term}' THEN submitted ELSE 0 END) -
                                            SUM(CASE WHEN year_label = '{compare_term}' THEN submitted ELSE 0 END)
                                        ) / NULLIF(SUM(CASE WHEN year_label = '{compare_term}' THEN submitted ELSE 0 END), 0), 2
                                    ) AS "Forms_Submitted_var_%",
                            		ROUND(
                                        100.0 * (
                                            SUM(CASE WHEN year_label = '{term}' THEN prospectus_paid ELSE 0 END) -
                                            SUM(CASE WHEN year_label = '{compare_term}' THEN prospectus_paid ELSE 0 END)
                                        ) / NULLIF(SUM(CASE WHEN year_label = '{compare_term}' THEN prospectus_paid ELSE 0 END), 0), 2
                                    ) AS "Verified_and_Complete_var_%",
                            
                                    ROUND(
                                        100.0 * (
                                            SUM(CASE WHEN year_label = '{term}' THEN entry_test_appearance ELSE 0 END) -
                                            SUM(CASE WHEN year_label = '{compare_term}' THEN entry_test_appearance ELSE 0 END)
                                        ) / NULLIF(SUM(CASE WHEN year_label = '{compare_term}' THEN entry_test_appearance ELSE 0 END), 0), 2
                                    ) AS "Appeared_in_Test_var_%",
                            
                                    ROUND(
                                        100.0 * (
                                            SUM(CASE WHEN year_label = '{term}' THEN merit_list ELSE 0 END) -
                                            SUM(CASE WHEN year_label = '{compare_term}' THEN merit_list ELSE 0 END)
                                        ) / NULLIF(SUM(CASE WHEN year_label = '{compare_term}' THEN merit_list ELSE 0 END), 0), 2
                                    ) AS "Selected_var_%",
                            
                                    ROUND(
                                        100.0 * (
                                            SUM(CASE WHEN year_label = '{term}' THEN admitted ELSE 0 END) -
                                            SUM(CASE WHEN year_label = '{compare_term}' THEN admitted ELSE 0 END)
                                        ) / NULLIF(SUM(CASE WHEN year_label = '{compare_term}' THEN admitted ELSE 0 END), 0), 2
                                    ) AS "Admitted_var_%"
                                FROM combined_data
                                GROUP BY program_name, faculty
                            )
                            
                            SELECT * FROM final_comparison
                            ORDER BY program_name;

                                    """
                _logger.warning(query)
                return query

            else:
                if group_by == 'program' or group_by == None:
                        query = f"""
                        WITH 
                            -- Relevant Programs CTE
                            relevant_programs AS (
                                SELECT 
                                    prm_rel.program_id, 
                                    prgm.name AS program_name
                                FROM 
                                    odoocms_admission_register reg
                                LEFT JOIN 
                                    register_program_rel prm_rel ON prm_rel.register_id = reg.id
                                JOIN 
                                    odoocms_program prgm ON prgm.id = prm_rel.program_id
                                WHERE 
                                    reg.state = 'application' 
                                    AND reg.career_id = 3
                            ),

                            -- Application Data CTE
                            application_data AS (
                                SELECT 
                                    ap.id AS application_id,
                                    ap.prefered_program_id,
                                    ap.state,
                                    DATE(ap.create_date),
                                    ap.term_id,
                                    CASE
                                        WHEN DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    odoocms_application ap
                                WHERE 

                                    ap.prefered_program_id IS NOT NULL
                                    AND ap.prefered_program_id IN (SELECT program_id FROM relevant_programs)
                                    AND (
                                        DATE(ap.create_date) BETWEEN '{from_date}' AND '{to_date}' 
                                        OR DATE(ap.create_date) BETWEEN '{prev_from_date}' AND '{prev_to_date}'
                                    )
                            ),

                            -- Prospectus Data CTE
                            prospectus_data AS (
                                SELECT 
                                    am.application_id,
                                    COUNT(DISTINCT am.application_id) AS prospectus_paid,
                                    CASE
                                        WHEN am.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN am.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    account_move am
                                WHERE 
                                    am.challan_type = 'prospectus_challan'
                                    AND am.payment_state IN ('paid', 'partial')
                                GROUP BY 
                                    am.application_id, 
                                    CASE
                                        WHEN am.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN am.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                            -- Entry Test Data CTE
                            entry_test_data AS (
                                SELECT 
                                    et.student_id,
                                    COUNT(DISTINCT et.student_id) AS entry_test_appearance,
                                    CASE
                                        WHEN et.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN et.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    applicant_entry_test et
                                WHERE 
                                    et.paper_conducted = true
                                GROUP BY 
                                    et.student_id, 
                                    CASE
                                        WHEN et.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN et.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                            -- Merit List Data CTE
                            merit_list_data AS (
                                SELECT 
                                    ml.applicant_id,
                                    COUNT(DISTINCT ml.applicant_id) AS merit_list_appearance,
                                    CASE
                                        WHEN ml.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN ml.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    odoocms_merit_register_line ml
                                WHERE 
                                    ml.selected = true
                                GROUP BY 
                                    ml.applicant_id, 
                                    CASE
                                        WHEN ml.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN ml.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),

                            -- Admission Data CTE
                            admission_data AS (
                                SELECT 
                                    am.application_id,
                                    COUNT(DISTINCT am.application_id) AS admitted,
                                    CASE
                                        WHEN am.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN am.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END AS year_label
                                FROM 
                                    account_move am
                                WHERE 
                                    am.challan_type = 'admission'
                                    AND am.payment_state IN ('paid', 'partial')
                                GROUP BY 
                                    am.application_id, 
                                    CASE
                                        WHEN am.create_date BETWEEN '{from_date}' AND '{to_date}' THEN '{term}'
                                        WHEN am.create_date BETWEEN '{prev_from_date}' AND '{prev_to_date}' THEN '{compare_term}'
                                    END
                            ),


                            combined_data AS (
                                SELECT 
                                    rp.program_name,
                                    ap.year_label,
                                    COALESCE(SUM(CASE WHEN ap.state = 'submit' THEN 1 ELSE 0 END), 0) AS submitted_forms,
                                    COALESCE(SUM(pd.prospectus_paid), 0) AS complete_forms,
                                    COALESCE(SUM(etd.entry_test_appearance), 0) AS test_appearance,
                                    COALESCE(SUM(mld.merit_list_appearance), 0) AS merit_list,
                                    COALESCE(SUM(ad.admitted), 0) AS admitted
                                FROM 
                                    relevant_programs rp
                                LEFT JOIN 
                                    application_data ap ON rp.program_id = ap.prefered_program_id
                                LEFT JOIN 
                                    prospectus_data pd ON pd.application_id = ap.application_id AND pd.year_label = ap.year_label
                                LEFT JOIN 
                                    entry_test_data etd ON etd.student_id = ap.application_id AND etd.year_label = ap.year_label
                                LEFT JOIN 
                                    merit_list_data mld ON mld.applicant_id = ap.application_id AND mld.year_label = ap.year_label
                                LEFT JOIN 
                                    admission_data ad ON ad.application_id = ap.application_id AND ad.year_label = ap.year_label
                                GROUP BY 
                                    rp.program_name, ap.year_label
                            ),

                            final_comparison AS (
                                SELECT 
                                    program_name,
                                    MAX(CASE WHEN year_label = '{term}' THEN submitted_forms ELSE 0 END) AS submitted_forms_{term},
                                    MAX(CASE WHEN year_label = '{term}' THEN complete_forms ELSE 0 END) AS complete_forms_{term},
                                    MAX(CASE WHEN year_label = '{term}' THEN test_appearance ELSE 0 END) AS test_appearance_{term},
                                    MAX(CASE WHEN year_label = '{term}' THEN merit_list ELSE 0 END) AS merit_list_{term},
                                    MAX(CASE WHEN year_label = '{term}' THEN admitted ELSE 0 END) AS admitted_+{term},
                                    MAX(CASE WHEN year_label = '{compare_term}' THEN submitted_forms ELSE 0 END) AS submitted_forms_{compare_term},
                                    MAX(CASE WHEN year_label = '{compare_term}' THEN complete_forms ELSE 0 END) AS complete_forms_{compare_term},
                                    MAX(CASE WHEN year_label = '{compare_term}' THEN test_appearance ELSE 0 END) AS test_appearance_{compare_term},
                                    MAX(CASE WHEN year_label = '{compare_term}' THEN merit_list ELSE 0 END) AS merit_list_{compare_term},
                                    MAX(CASE WHEN year_label = '{compare_term}' THEN admitted ELSE 0 END) AS admitted_{compare_term}
                                FROM 
                                    combined_data
                                GROUP BY 
                                    program_name
                            )

                            -- Final Output
                            SELECT 
                                *
                            FROM 
                                final_comparison
                            ORDER BY 
                                program_name;
                                        """
                        _logger.warning(query)
                        return query
    def _get_columns(self, data):
        def format_key(key):
            return ' '.join(word.capitalize() for word in key.split('_'))
        if not data:
            return []
        keys = data[0].keys()
        columns = [format_key(key) for key in keys]
        return columns

    def _get_keys(self, data):
        if data and data[0]:
            keys = data[0].keys()
            keys = list(keys)
            return keys
        return []

    
    @api.model
    def generate_excel_report_admission_comparison(self, report_type, group_by, term_id, compare_term, days):
        data, columns, keys, description = self.get_admission_comparison_report(report_type, group_by, term_id, compare_term, days)
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('Admission Comparison Report')

        # Styles
        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        bold_center = workbook.add_format({'bold': True, 'align': 'center'})
        total_format = workbook.add_format({'bold': True, 'bg_color': '#e0e0e0'})

        # === Row 0: Merged header for description ===
        sheet.merge_range(0, 0, 0, len(columns) - 1, description, bold_center)

        # === Row 1: Column Headers ===
        for col_num, column_title in enumerate(columns):
            sheet.write(1, col_num, column_title, bold_center)
            sheet.set_column(col_num, col_num, 15)

        # === Rows 2 to N: Data Rows ===
        for row_num, row_data in enumerate(data, start=2):  # Start from row 2 (index 2)
            for col_num, key in enumerate(keys):
                cell_value = row_data.get(key)
                if isinstance(cell_value, str):
                    try:
                        cell_value = datetime.strptime(cell_value, '%Y-%m-%d').date()
                    except ValueError:
                        pass
                if isinstance(cell_value, date):
                    sheet.write_datetime(row_num, col_num, cell_value, date_format)
                else:
                    sheet.write(row_num, col_num, cell_value)

        total_row = len(data) + 2
        sheet.write(total_row, 0, 'Total', total_format)

        for col_num, key in enumerate(keys[1:], start=1): 
            is_numeric_column = all(
                isinstance(row.get(key), (int, float)) or (isinstance(row.get(key), str) and row.get(key).replace('.', '', 1).isdigit())
                for row in data if row.get(key) not in [None, '']
            )

            if is_numeric_column:
                col_letter = xlsxwriter.utility.xl_col_to_name(col_num)
                start_row = 3
                end_row = len(data) + 2
                formula = f'=sum({col_letter}{start_row}:{col_letter}{end_row})'
                sheet.write_formula(total_row, col_num, formula, total_format)
            else:
                sheet.write(total_row, col_num, '', total_format)
        # workbook = xlsxwriter.Workbook(output, {
        # 'in_memory': True,
        # 'default_date_format': 'yyyy-mm-dd'
        # })
        workbook.set_calc_mode('auto') 

        workbook.close()
        output.seek(0)
        file_content = output.read()
        output.close()
        file_base64 = base64.b64encode(file_content)
        filename = f'admission_comparison_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        return filename, file_base64

