from odoo import models, fields, api
from odoo_rpc_client import Client
from odoo.tools import html_sanitize
import base64
import codecs
import logging

_logger = logging.getLogger(__name__)


class AdmissionSync(models.Model):
    _name = 'admission.sync'
    _description = 'Admission Sync'

    name = fields.Char(string="Name")
    # conf = fields.Many2one(comodel_name="odoo.sn.aarsol.cms.con", string="Configuration", required=False)
    student_ids = fields.Many2many('odoocms.student', string="Student IDs")
    log = fields.Html('Logs:', readonly=True) 
    company =  fields.Many2one(comodel_name="res.company", string="Company", required=True)
    cms_action = fields.Selection([
        ('all','All'),
        ('partner', 'Partner'),
        ('student_profile', 'Student Profile'),
        ('student_p_files','Student Profile Files'),
        ('academic_detail', 'Academic Detail'),
        ('academic_doc', 'Academic Documnets'),
        ('applied_scholarship','Applied Scholarship'),
        ('scholarship_eligibity','Scholarship Eligibity'),
        ('fee','Fee'),
        ('fee_lines','Fee Lines'),
        ('courses','Courses')

    ], string='Select Action',default='all', required=True)

    
    def perform_selected_action(self):
        if self.cms_action == 'all':
            self.call_db_procedure()
        elif self.cms_action == 'partner':
            self.call_db_procedure_sync_partner()
        elif self.cms_action == 'student_profile':
            self.call_db_procedure_sync_student()
        elif self.cms_action == 'student_p_files':
            self.sync_odoocms_student_profile_doc()
        elif self.cms_action == 'academic_detail':
            self.call_db_procedure_sync_academic_detail()
        elif self.cms_action == 'academic_doc':
            self.sync_odoocms_student_academic_doc()
        elif self.cms_action == 'applied_scholarship':
            self.call_db_procedure_applied_scholarship()
        elif self.cms_action == 'scholarship_eligibity':
            self.call_db_procedure_scholarship_eligibility()
        elif self.cms_action == 'fee':
            self.call_db_procedure_odoocms_fee()
        elif self.cms_action == 'fee_lines':
            self.call_db_procedure_odoocms_fee_line()
        elif self.cms_action == 'courses':
             self.call_db_procedure_first_semester_courses()


    def add_log_message(self, message, color='black'):
        log_message = f'<span style="color: {color};">{message}</span><br/>'
        if not self.log:
            self.log = ""
        self.log += html_sanitize(log_message)

    def fetch_students(self):
        student_records = self.env['odoocms.student'].sudo().search([('fee_paid','=',True),('server_id','=',False),('company_id','=',self.company.id)],limit =50)
        # student_records = self.env['odoocms.student'].search([('server_id','=',None)],limit =5)
        if student_records:
            self.student_ids = [(6, 0, student_records.ids)]
            self.add_log_message("Fetching Admitted Students Successfull.", 'green')
            # for std in student_records:
            #     std.to_be =False

        else:
            self.add_log_message("No Admitted Student Found.", 'red')


    def call_db_procedure(self):
        self.add_log_message(f"Students Syncing Process has been started ", '#FFA500')
        # self.fetch_schema_cms_db()
        # self.update_server_id_for_conf_tables()
        # self.update_store_procedures()
        self.call_db_procedure_sync_partner()
        self.call_db_procedure_sync_student()
        self.call_db_procedure_sync_academic_detail()
        self.call_db_procedure_scholarship_eligibility()
        self.call_db_procedure_applied_scholarship()
        self.call_db_procedure_odoocms_fee()
        self.call_db_procedure_odoocms_fee_line()       
        self.sync_odoocms_student_academic_doc()
        self.sync_odoocms_student_profile_doc()
        self.call_db_procedure_first_semester_courses()
        self.add_log_message(f"Students Syncing Process Ended ", '#FFA500')



    def sync_fee_data_to_cms(self):
        fee_data_array = self.create_fee_data()
        insert_query = """
            INSERT INTO odoocms_fee (
                student_id, student_semester_id, total_receivable, total_paid_adjustment, 
                balance_amount, scholarship_adjusted_amount, session_id, term, 
                term_name, term_id, semester, semester_name, semester_id, 
                due_date, paid_date, late_days, late_fee_amount, state, 
                invoice_id, scholarship_payment_id, payment_id, error, to_be
            )
            VALUES %s
        """
        try:
            self.env.cr.savepoint('sync_fee_data_to_cms')
            self.env.cr.execute(insert_query, [fee_data_array])
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f": an error occurred - {str(e)}", 'red')


    def create_fee_data(self):
        students_not_cms =[]
        fee_data = []
        student_ids_list = self.student_ids.ids
        for record in student_ids_list:
            if record.server_id:
                fee_data = (
                    record.server_id,
                    record.student_semester_id,
                    record.total_receivable,
                    record.total_paid_adjustment,
                    record.balance_amount,
                    record.scholarship_adjusted_amount,
                    record.session_id,
                    record.term,
                    record.term_name,
                    record.term_id.id if record.term_id else None, 
                    record.semester,
                    record.semester_name,
                    record.semester_id.id if record.semester_id else None, 
                    record.due_date,
                    record.paid_date,
                    record.late_days,
                    record.late_fee_amount,
                    record.state,
                    record.invoice_id.id if record.invoice_id else None, 
                    record.scholarship_payment_id.id if record.scholarship_payment_id else None,
                    record.payment_id.id if record.payment_id else None,
                    record.error,
                    record.to_be
                )
                fee_data.append(fee_data)
            else:
                students_not_cms.append(record.id)
            if len(students_not_cms) > 0:
                self.add_log_message(f"Students not found at CMS: {students_not_cms}", 'red')
        return fee_data



    def update_server_id_for_conf_tables(self):
        self.add_log_message(f"Updating server ids for configuration level tables for Admission from CMS", 'black')

        queries = {
            """
            UPDATE odoocms_domicile adm 
            SET server_id = cms.id 
            FROM cms.odoocms_domicile AS cms 
            WHERE adm.name = cms.name        
            AND adm.server_id is null;
            """: "Update server_id in odoocms_domicile",

            """
            UPDATE odoocms_religion adm 
            SET server_id = cms.id 
            FROM cms.odoocms_religion AS cms 
            WHERE adm.name = cms.name
            AND adm.server_id is null;
            """: "Update server_id in odoocms_religion",

            """
            UPDATE odoocms_academic_session adm 
            SET server_id = cms.id 
            FROM cms.odoocms_academic_session AS cms 
            WHERE adm.code = cms.code
            AND adm.server_id is null;
            """: "Update server_id in odoocms_academic_session",

            """
            UPDATE res_company adm 
            SET server_id = cms.id 
            FROM cms.res_company AS cms 
            WHERE adm.code = cms.code
            AND adm.server_id is null;
            """: "Update server_id in res_company",

            """
            UPDATE odoocms_study_scheme adm
            SET server_id = subquery.latest_id
            FROM (
                SELECT cms.code, cms.id AS latest_id, company_id
                FROM cms.odoocms_study_scheme AS cms
                JOIN (
                    SELECT code, MAX(create_date) AS max_create_date
                    FROM cms.odoocms_study_scheme
                    GROUP BY code
                ) AS max_date
                ON cms.code = max_date.code
                AND cms.create_date = max_date.max_create_date
            ) AS subquery
            WHERE adm.code = subquery.code
            AND adm.server_id is null;
            """: "Update server_id in odoocms_study_scheme",

            """
            UPDATE res_partner adm 
            SET server_id = cms.id 
            FROM cms.res_partner AS cms 
            WHERE adm.code = cms.code
            AND adm.server_id is null;
            """: "Update server_id in res_partner",

            """
                UPDATE odoocms_fee_waiver adm
            SET server_id = subquery.latest_id
            FROM (
                SELECT cms.name, cms.company_id, cms.id AS latest_id
                FROM cms.odoocms_fee_waiver AS cms
                JOIN (
                    SELECT name, company_id, MAX(create_date) AS max_create_date
                    FROM cms.odoocms_fee_waiver
                    GROUP BY name, company_id
                ) AS max_date
                ON cms.name = max_date.name
                AND cms.company_id = max_date.company_id
                AND cms.create_date = max_date.max_create_date
            ) AS subquery
            WHERE adm.name = subquery.name
            AND adm.server_id IS NULL;

            """: "Update server_id in odoocms_fee_waiver",

            """
            UPDATE odoocms_program_term_scholarship adm
            SET server_id = subquery.latest_id
            FROM (
                SELECT cms.name, cms.term_id, cms.program_id, cms.company_id, cms.id AS latest_id
                FROM cms.odoocms_program_term_scholarship AS cms
                JOIN (
                    SELECT name, term_id, program_id, company_id, MAX(create_date) AS max_create_date
                    FROM cms.odoocms_program_term_scholarship
                    GROUP BY name, term_id, program_id, company_id
                ) AS max_date
                ON cms.name = max_date.name
                AND cms.term_id = max_date.term_id
                AND cms.program_id = max_date.program_id
                AND cms.company_id = max_date.company_id
                AND cms.create_date = max_date.max_create_date
            ) AS subquery
            WHERE adm.name = subquery.name
            AND adm.term_id = subquery.term_id
            AND adm.program_id = subquery.program_id
            AND adm.server_id IS NULL;
            """: "Update server_id in odoocms_program_term_scholarship"
        }

        for query, description in queries.items():
            try:
                self.env.cr.savepoint('update_server_id_for_conf_tables')
                self.env.cr.execute(query)
                self.add_log_message(f"{description}: successful.", 'green')
                self.env.cr.commit()
            except Exception as e:
                self.env.cr.rollback()
                self.add_log_message(f"{description}: an error occurred - {str(e)}", 'red')

                # self.log += f"{description}: an error occurred - {e}\n"


    def fetch_schema_cms_db(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Fetching CMS Schema from Host: {cms_sync_conf.target_host}", 'black')
        queries = [
            "DROP SCHEMA IF EXISTS cms CASCADE;",
            "DROP SERVER IF EXISTS cms_server CASCADE;",
            """
            CREATE SERVER cms_server FOREIGN DATA WRAPPER postgres_fdw OPTIONS (
                host %(host)s, dbname %(dbname)s, port %(port)s
            );
            """,
            """
            CREATE USER MAPPING FOR odoo15 SERVER cms_server OPTIONS (
                user %(user)s, password %(password)s
            );
            """,
            "CREATE SCHEMA cms;",
            "IMPORT FOREIGN SCHEMA public FROM SERVER cms_server INTO cms;"
        ]

        try:
            for query in queries:
                self.env.cr.savepoint('fetch_schema_cms_db')
                if '%' in query:
                    self.env.cr.execute(query, {
                        'host': cms_sync_conf.target_host,
                        'dbname': cms_sync_conf.target_dbname,
                        'port': cms_sync_conf.target_db_port,
                        'user': cms_sync_conf.target_db_user,
                        'password': cms_sync_conf.target_db_password
                    })
                else:
                    self.env.cr.execute(query)
            self.add_log_message("CMS Schema Updated successfully.", 'green')
            self.env.cr.commit()
            # self.log += "CMS Schema Updated successfully.\n"

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message( f"An error occurred: {e}", 'red')
            # self.log += f"An error occurred: {e}\n"

    def create_functions_on_remote_db(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message("Sequence configuration for the involved tables has started.", 'black')
        target_dbname = cms_sync_conf.target_dbname
        target_host = cms_sync_conf.target_host
        target_user = cms_sync_conf.target_db_user
        target_password = cms_sync_conf.target_db_password
        db_con = Client(host=cms_sync_conf.target_host, port=cms_sync_conf.target_port, dbname=cms_sync_conf.target_dbname, user=cms_sync_conf.target_admin_user, pwd=cms_sync_conf.target_admin_password)

        sql_command = f"""CREATE OR REPLACE FUNCTION public.get_nextval_odoocms_fee_line_id()
            RETURNS bigint AS $$
            BEGIN
                RETURN  nextval('odoocms_fee_line_id_seq'::regclass);
            END;
            $$ LANGUAGE plpgsql;"""
        try:
            db_con.env.cr.execute(sql_command)

            # Optionally, you might want to commit the transaction if needed
            db_con.commit()

            # Close the connection if necessary
            db_con.close()
            # try:
            #     self.env.cr.savepoint('create_functions_on_remote_db')
            #     self.env.cr.execute(sql_command)
            #     self.env.cr.commit()
            #     self.add_log_message("Sequence configuration process for the involved tables executed successfully without any failures.", 'green')
            #     self.add_log_message("Sequence configuration for the involved tables has Ended.", 'black')
            # except Exception as e :
            #     self.env.cr.rollback()
            #     self.add_log_message(f"Sequence Configuration Process execution failed: {str(e)}", 'red')
            #     self.add_log_message("Sequence configuration for the involved tables has Ended.", 'black')
        except Exception as e:
                db_con.rollback()
                self.add_log_message(f"Sequence Configuration Process execution failed: {str(e)}", 'red')
                self.add_log_message("Sequence configuration for the involved tables has Ended.", 'black')



    def call_db_procedure_odoocms_fee(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Student Fee data from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_odoocms_fee')
            self.env.cr.execute("""
                CALL public.odoocms_fee_adm_to_cms(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM odoocms_fee_adm_to_cms_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Syncing Student' Fee data Process executed with failures for student IDs: {failed_ids_list}", 'red')
            # else:
            #     self.add_log_message("Syncing Student' Fee data Process executed successfully without any failures.", 'green')
            
            self.env.cr.execute("""
               UPDATE account_move AS adm
                SET odoocms_fee_ref = cms.id
                FROM cms.odoocms_fee AS cms
                WHERE cms.account_move_id = adm.id
                -- AND adm.challan_type='admission'
                AND adm.odoocms_fee_ref is null
                AND EXISTS (
                    SELECT 1 
                    FROM odoocms_student AS st 
                    WHERE st.id = adm.student_id
                    AND st.id = ANY(%s));
                """, (student_ids_list,))

            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Student's Fee data server_id field Updated From CMS to ADM : {row_cnt}", 'green')

            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Syncing Student' Fee data Process execution failed: {str(e)}", 'red')



    def call_db_procedure_odoocms_fee_line(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Student Fee Line data from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_odoocms_fee_line')
            self.env.cr.execute("""
                CALL public.odoocms_fee_line_adm_to_cms(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM odoocms_fee_line_adm_to_cms_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Syncing Student' Fee Line data Process executed with failures for student IDs: {failed_ids_list}", 'red')
         
            # else:
            self.add_log_message("Syncing Student' Fee Line data Process executed successfully without any failures.", 'green')
            self.env.cr.execute("""
             UPDATE account_move_line
                SET odoocms_fee_line_ref = subquery.cms_id
                FROM (
                    SELECT adm.id AS adm_id, cms.id AS cms_id
                    FROM account_move_line AS adm
                    JOIN account_move AS fee ON fee.id = adm.move_id
                    JOIN cms.odoocms_fee_line AS cms ON cms.account_move_line_id = adm.id
                    WHERE 
                    fee.student_id = ANY(%s)
                    -- AND fee.challan_type = 'admission'
                ) AS subquery
                WHERE account_move_line.id = subquery.adm_id;
                """, (student_ids_list,))

            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Student's Fee Line data server_id field Updated From CMS to ADM : {row_cnt}", 'green')

            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Syncing Student' Line Fee data Process execution failed: {str(e)}", 'red')



    def call_db_procedure_scholarship_eligibility(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Student Scholarship Eligibility from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_scholarship_eligibility')
            self.env.cr.execute("""
                CALL public.student_scholarship_eligibility_transfer(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM scholarship_eligibility_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Syncing Student' Scholarship Eligibility Process executed with failures for student IDs: {failed_ids_list}", 'red')
         
            # else:
            self.add_log_message("Syncing Student' Scholarship Eligibility Process executed successfully without any failures.", 'green')
            
            self.env.cr.execute("""
               UPDATE odoocms_student_scholarship_eligibility AS adm
                SET server_id = cms.id
                FROM cms.odoocms_student_scholarship_eligibility AS cms
                WHERE cms.client_id = adm.id
                AND adm.server_id is null
                AND EXISTS (
                    SELECT 1 
                    FROM odoocms_student AS st 
                    WHERE st.id = adm.student_id
                    AND st.id = ANY(%s));
                """, (student_ids_list,))

            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Student's Scholarship Eligibility server_id field Updated From CMS to ADM : {row_cnt}", 'green')

            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Syncing Student' Scholarship Eligibility Process execution failed: {str(e)}", 'red')


    def call_db_procedure_applied_scholarship(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Student Applied Scholarship from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_applied_scholarship')
            self.env.cr.execute("""
                CALL public.student_applied_scholarship_transfer(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM scholarship_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Syncing Student' Applied Scholarship Process executed with failures for student IDs: {failed_ids_list}", 'red')
         
            # else:
            self.add_log_message("Syncing Student' Applied Scholarship Process executed successfully without any failures.", 'green')
            
            self.env.cr.execute("""
               UPDATE odoocms_student_applied_scholarships AS adm
                SET server_id = cms.id
                FROM cms.odoocms_student_applied_scholarships AS cms
                WHERE cms.client_id = adm.id
                AND adm.server_id is null
                AND EXISTS (
                    SELECT 1 
                    FROM odoocms_student AS st 
                    WHERE st.id = adm.student_id
                    AND st.id = ANY(%s));
                """, (student_ids_list,))

            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Student's Applied Scholarship server_id field Updated From CMS to ADM : {row_cnt}", 'green')

            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Syncing Student' Applied Scholarship Process execution failed: {str(e)}", 'red')


    def call_db_procedure_sync_partner(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Student Partner from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_sync_partner')
            self.env.cr.execute("""
                CALL public.res_partner_admission_to_cms(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM temp_partner_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Syncing Student' Partner Process executed with failures for student IDs: {failed_ids_list}", 'red')
            #     # self.log += f"Procedure executed with failures for student IDs: {failed_ids_list}\n"
            # else:
            self.add_log_message("Syncing Student' Partner Process executed successfully without any failures.", 'green')
            
            # self.env.cr.execute("""
            #    UPDATE res_partner AS adm
            #     SET server_id = cms.id
            #     FROM cms.res_partner AS cms
            #     WHERE cms.client_id = adm.id;
            #     and student_id in %s 
            #     """)
            self.env.cr.execute("""
               UPDATE res_partner AS adm
                SET server_id = cms.id
                FROM cms.res_partner AS cms
                WHERE cms.client_id = adm.id
                AND EXISTS (
                    SELECT 1 
                    FROM odoocms_student AS st 
                    WHERE st.partner_id = adm.id 
                    AND st.id = ANY(%s));
                """, (student_ids_list,))

            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Student's partner server_id field Updated From CMS to ADM : {row_cnt}", 'green')
            # self.log += f"CMS res_partner Update From CMS to ADM: {v_cnt}\n"
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Syncing Student' Partner Process execution failed: {str(e)}", 'red')
            # self.log += f"Procedure execution failed: {str(e)}\n"



    def call_db_procedure_sync_student(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Students from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password

        for std in self.student_ids:
            if not std.batch_id:
                session =std.session_id.id
                program = std.program_id.id
                company =std.company_id.id
                batch_id =self.env['odoocms.batch'].search([('program_id','=',program),('session_id','=',session),('company_id','=',company)])
                std.write({'batch_id': batch_id.id})

        # if len(not_batch_id) >0:
        #     self.add_log_message(f"Following Students does not have batch ID : {not_batch_id}", 'red')



        try:
            self.env.cr.savepoint('call_db_procedure_sync_student')
            # self.env.cr.execute("CREATE TEMP TABLE tmp_failed_ids (id INT) ON COMMIT DROP;")
            self.env.cr.execute("""
                CALL public.sync_student_admission_to_cms(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM temp_student_failed_ids")
            # failed_ids = self.env.cr.fetchall()

            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Student Syncing Process executed with failures for student IDs: {failed_ids_list}", 'red')
            #     # self.log += f"Procedure executed with failures for student IDs: {failed_ids_list}\n"
            # else:
            self.add_log_message("Student Syncing Process executed successfully without any failures.", 'green')
                # self.log += "Procedure executed successfully without any failures.\n"
            self.env.cr.execute("""
                UPDATE odoocms_student AS source
                SET server_id = destination.id
                FROM cms.odoocms_student AS destination
                WHERE source.id = destination.client_id
                    AND source.id = ANY(%s);
                """, (student_ids_list,))
            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Student server_id field Updated From CMS to ADM: {row_cnt}", 'green')
            # self.log += f"Student Update From CMS to ADM: {v_cnt}\n"
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Student Syncing Process execution failed: {str(e)}", 'red')
            # self.log += f"Procedure execution failed: {str(e)}\n"


    def call_db_procedure_sync_academic_detail(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"Syncing for Student's Academic Details from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_sync_academic_detail')
            self.env.cr.execute("""
                CALL public.admission_to_cms_academic_detail(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM temp_academic_doc_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"Academic Details Syncing Process executed with failures for student IDs: {failed_ids_list}", 'red')
            #     # self.log += f"Procedure executed with failures for student IDs: {failed_ids_list}\n"
            # else:
            self.add_log_message("Academic Details Syncing Process executed successfully without any failures.", 'green')
                # self.log += "Academic Details Sync Procedure executed successfully without any failures.\n"
            # self.env.cr.execute("""
            #     UPDATE odoocms_student_academic AS cms
            #     SET applicant_academic_detail_id = adm.id, to_be = TRUE
            #     FROM adm.applicant_academic_detail AS adm
            #     WHERE cms.applicant_academic_detail_id = adm.id
            # """)
            # row_cnt = self.env.cr.rowcount
            # self.add_log_message(f"CMS odoocms_student_academic Update From ADM to CMS: {row_cnt}", 'green')
            # self.log += f"CMS odoocms_student_academic Update From ADM to CMS: {v_cnt}\n"
            self.env.cr.commit()
            self.env.cr.savepoint('call_db_procedure_sync_academic_detail_update')
            self.env.cr.execute("""
                UPDATE applicant_academic_detail AS adm
                SET server_id = cms.id, to_be = TRUE
                FROM cms.odoocms_student_academic AS cms
                WHERE cms.applicant_academic_detail_id = adm.id
                AND adm.server_id is null
                AND EXISTS (
                    SELECT 1 
                    FROM odoocms_student AS st 
                    WHERE st.admission_no = adm.reference_no
                    AND st.id = ANY(%s));
                """, (student_ids_list,))
            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"Academic Detail's odoocms_student_academic field Updated From CMS to ADM: {row_cnt}", 'green')
            # self.log += f"CMS odoocms_student_academic Update From CMS to ADM: {v_cnt}\n"
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Academic Details Syncing Process execution failed: {str(e)}", 'red')
            # self.log += f"Procedure execution failed: {str(e)}\n"


    def call_db_procedure_first_semester_courses(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        self.add_log_message(f"First Semester Courses from Admission to CMS is Started", 'black')
        student_ids_list = self.student_ids.ids
        db_host = cms_sync_conf.target_host
        db_name = cms_sync_conf.target_dbname
        db_user = cms_sync_conf.target_db_user
        db_password = cms_sync_conf.target_db_password
        try:
            self.env.cr.savepoint('call_db_procedure_first_semester_courses')
            self.env.cr.execute("""
                CALL public.courses_adm_to_cms(%s, %s, %s, %s, %s)
            """, (student_ids_list, db_host, db_name, db_user, db_password))
            # self.env.cr.execute("SELECT id FROM temp_courses_failed_ids")
            # failed_ids = self.env.cr.fetchall()
            # self.env.cr.commit()
            # self.env.cr.savepoint('call_db_procedure_first_semester_courses_update_server_id')
            # if failed_ids:
            #     failed_ids_list = [row[0] for row in failed_ids]
            #     self.add_log_message(f"First Semester Courses Syncing Process executed with failures for student IDs: {failed_ids_list}", 'red')
            # else:
            self.add_log_message("First Semester Courses Syncing Process executed successfully without any failures.", 'green')
            
            self.env.cr.execute("""
                               UPDATE odoocms_applicant_first_semester_courses AS adm
                SET server_id = cms.id
                FROM cms.odoocms_applicant_first_semester_courses AS cms
                WHERE cms.client_id = adm.id
                AND adm.server_id is null;""")
            row_cnt = self.env.cr.rowcount
            self.add_log_message(f"First Semester Courses's server_id field Updated From CMS to ADM: {row_cnt}", 'green')
            self.env.cr.commit()
        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"First Semester Courses Syncing Process execution failed: {str(e)}", 'red')


    def db_connection_for_doc_transfer(self):
        cms_sync_conf = self.env['odoo.sn.aarsol.cms.con'].sudo().search([('current', '=', True)],limit=1,order='id desc')
        try:
            self.add_log_message(f"Connecting to {cms_sync_conf.target_host} on port {cms_sync_conf.target_port} for database {cms_sync_conf.target_dbname}", '#FFA500')
            db_con = Client(host=cms_sync_conf.target_host_web, port=cms_sync_conf.target_port, dbname=cms_sync_conf.target_dbname, user=cms_sync_conf.target_admin_user, pwd=cms_sync_conf.target_admin_password)
            return db_con
        except Exception as e:
            self.add_log_message(f"Failed to establish connection for sync images: {e}", 'red')

    def sync_odoocms_student_academic_doc(self):
        failed_std_id= []
        self.add_log_message("Academic Files Transfer Process is Started", 'black')
        db_connection=self.db_connection_for_doc_transfer()
        student_ids_list = self.student_ids
        for std in student_ids_list:
            if std and std.admission_no:
                application_no =std.admission_no
            application = self.env["odoocms.application"].sudo().search([('application_no','=',application_no)])
            if application:
                attachment = self.env['applicant.academic.detail'].search([('application_id', '=', application.id)])
                if attachment:
                    for att in attachment:
                            try:
                                students_in_cms = db_connection['odoocms.student.academic'].search_records([('id', '=', att.server_id)])
                                if students_in_cms:
                                    try:
                                        student_in_cms = students_in_cms[0]
                                        student_in_cms.write({'attachment': att.degree_attachment})
                                    except Exception as e:
                                        self.add_log_message(f"Failed to sync image for student {std.server_id}: {e}", 'red')
                                else:
                                    failed_std_id.append(std.code)
                                    
                            except Exception as e :
                                self.add_log_message(f"Failed to establish connection for sync images: {e}", 'green')

                else:
                    self.add_log_message(f"No Academic Record Found for: {student_ids_list}", 'red')
        if len(failed_std_id) >0:
            self.add_log_message(f"No Student Academic Record Found in CMS : {std.code}", 'red')
        self.add_log_message("Academic Files Transfer Process is Ended", 'black')

    def sync_odoocms_student_profile_doc(self):
        failed_std_ids= []
        self.add_log_message("Student Profile Image Transfer Process is Started", 'black')
        db_connection=self.db_connection_for_doc_transfer()
        student_ids_list = self.student_ids
        for std in student_ids_list:
            try:
                student_in_cms = db_connection['odoocms.student'].search_records([('id', '=', std.server_id),('company_id','=',std.company_id.server_id)])
                if student_in_cms:
                    try:
                        student_in_cms = student_in_cms[0]
                        student_in_cms.write({'image_1920': std.image_1920})
                    except Exception as e:
                        self.add_log_message(f"Failed to sync profile image for student {std.server_id}: {e}", 'red')
                else:
                    failed_std_ids.append(std.code)

            except Exception as e :
                self.add_log_message(f"Failed to establish connection for sync profile images: {e}", 'red')
        if len(failed_std_ids) > 0:
            self.add_log_message(f"No Student Record Found in CMS : {failed_std_ids}", 'red')
        self.add_log_message("Student Profile Files Transfer Process is Ended", 'black')




    def update_store_procedures(self):
        self.add_log_message(f"Creating Store Procedures", 'black')
        self.create_dblink_extension()
        self.res_partner_store_procedures_admission_to_cms()
        self.student_store_procedure_admission_to_cms()
        self.academic_information_store_procedures_admission_to_cms()
        self.applied_scholarship_store_procedures_admission_to_cms()
        self.scholarship_eligibility_store_procedures_admission_to_cms()
        self.fee_procedures_admission_to_cms()
        self.fee_line_procedures_admission_to_cms()
        self.first_semester_courses_admission_to_cms()

    def create_dblink_extension(self):
            create_dblink_extension_sql = """DO $$
                                        BEGIN
                                            IF NOT EXISTS (
                                                SELECT 1
                                                FROM pg_extension
                                                WHERE extname = 'dblink'
                                            ) THEN
                                                CREATE EXTENSION dblink;
                                            END IF;
                                        END $$;"""
            try:
                self.env.cr.savepoint('create_dblink_extension')
                self.env.cr.execute(create_dblink_extension_sql)
                self.add_log_message("DB Link Extension created successfully.", 'green')
                self.env.cr.commit()
                _logger.info("DB Link Extension created successfully.")

            except Exception as e:
                self.env.cr.rollback()
                self.add_log_message(f"DB Link Extension creation failed: {e}", 'red')
                _logger.error("DB Link Extension creation failed : %s", e)

    def res_partner_store_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
                            CREATE OR REPLACE PROCEDURE public.res_partner_admission_to_cms(
                            student_ids INT[],
                            db_host TEXT,
                            db_name TEXT,
                            db_user TEXT,
                            db_password TEXT
                        )
                        LANGUAGE 'plpgsql'
                        AS $BODY$
                        DECLARE
                            v_failed_ids INT[] := '{}';
                            v_nextval bigint;
                        BEGIN
                            CREATE TEMP TABLE temp_partner_failed_ids (id INT) ON COMMIT DROP;

                            FOR i IN 1 .. array_length(student_ids, 1) LOOP
                                BEGIN
                                    SELECT nextval
                                    INTO v_nextval
                                    FROM dblink(format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                                'SELECT get_nextval_res_partner_id()')
                                    AS t(nextval bigint);
                                    INSERT INTO cms.res_partner (
                                        id, name, display_name, date, title, ref, lang, tz, vat, website, comment, credit_limit, active, employee,
                                        function, type, street, street2, zip, city, country_id, partner_latitude, partner_longitude, email, phone, mobile, 
                                        is_company, color, partner_share, commercial_company_name, company_name, email_normalized, message_bounce, contact_address_complete, 
                                        signup_token, signup_type, signup_expiration, calendar_last_notif_ack, debit_limit, last_time_entries_checked, invoice_warn, 
                                        invoice_warn_msg, supplier_rank, customer_rank, is_published, ocn_token, partner_gid, additional_info, online_partner_information, 
                                        phone_sanitized, client_id,company_id
                                    ) 
                                    SELECT 
                                        v_nextval, adm.name, adm.display_name, adm.date, adm.title, adm.ref, adm.lang, adm.tz, adm.vat, adm.website, adm.comment, adm.credit_limit, adm.active, adm.employee,
                                        adm.function, adm.type, adm.street, adm.street2, adm.zip, adm.city, adm.country_id, adm.partner_latitude, adm.partner_longitude, adm.email, adm.phone, adm.mobile, 
                                        adm.is_company, adm.color, adm.partner_share, adm.commercial_company_name, adm.company_name, adm.email_normalized, adm.message_bounce, adm.contact_address_complete, 
                                        adm.signup_token, adm.signup_type, adm.signup_expiration, adm.calendar_last_notif_ack, adm.debit_limit, adm.last_time_entries_checked, adm.invoice_warn, 
                                        adm.invoice_warn_msg, adm.supplier_rank, adm.customer_rank, adm.is_published, adm.ocn_token, adm.partner_gid, adm.additional_info, adm.online_partner_information, 
                                        adm.phone_sanitized, adm.id ,com.server_id
                                    FROM 
                                        res_partner AS adm  
                                    LEFT OUTER JOIN res_company AS com ON adm.company_id = com.id
                                    INNER JOIN 
                                        odoocms_student AS st 
                                    ON 
                                        st.partner_id = adm.id 
                                    WHERE 
                                        NOT EXISTS (SELECT 1 FROM cms.res_partner AS cms WHERE cms.client_id = adm.id)
                                    AND 
                                        st.id = student_ids[i]
                                    LIMIT 1;
                                EXCEPTION WHEN OTHERS THEN
                                    INSERT INTO temp_partner_failed_ids (id) VALUES (student_ids[i]);
                                    RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                                END;
                            END LOOP;
                        END;
                        $BODY$;
                    ALTER PROCEDURE public.res_partner_admission_to_cms(
                            student_ids INT[],
                            db_host TEXT,
                            db_name TEXT,
                            db_user TEXT,
                            db_password TEXT)
                    OWNER TO odoo15;

            """
            self.env.cr.savepoint('res_partner_store_procedures_admission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Partner Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Partner Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Partner: {e}", 'red')
            _logger.error("Failed to create stored procedure Partner : %s", e)




    def student_store_procedure_admission_to_cms(self):
        
        try:
            create_procedure_sql = """
                    CREATE OR REPLACE PROCEDURE public.sync_student_admission_to_cms(
                                student_ids INT[],
                                db_host TEXT,
                                db_name TEXT,
                                db_user TEXT,
                                db_password TEXT)
                LANGUAGE 'plpgsql'
                AS $BODY$
                DECLARE
                    v_failed_ids INT[] := '{}';
                    v_cnt INT := 0;
                    s_nextval bigint;
                    v_student_code TEXT;
                    v_company_id INT;
                BEGIN
                    CREATE TEMP TABLE temp_student_failed_ids (id INT) ON COMMIT DROP;
                    FOR i IN 1 .. array_length(student_ids, 1) LOOP
                        BEGIN
                        SELECT nextval
                                        INTO s_nextval
                                        FROM dblink(format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                                    'SELECT get_nextval_student_id()')
                                        AS t(nextval bigint);
                            INSERT INTO cms.odoocms_student(
                                id, admission_no, allow_re_reg_wo_fee, batch_id, blood_group, campus_code, 
                                campus_id, career_code, career_id, cnic, cnic_expiry_date, code, company_id, date_of_birth, department_code, department_id, 
                                disability, disability_detail, discipline_id, domicile_id, emergency_address, emergency_city, emergency_contact, emergency_email, 
                                emergency_mobile, entry_date, exclude_library_fee, father_cell, father_guardian_cnic, father_income, father_name, father_profession, father_status, 
                                fee_enable, fee_generated, feemerit, first_generation_studying, first_name, gender, guardian_cnic, guardian_mobile, guardian_name, 
                                hostel_cubical, hostel_facility, id_number, institute_code, institute_id, 
                                inter_stream, is_same_address, kinship_flag, last_name, last_term, marital_status, merit_no, mother_cell, mother_income, 
                                mother_name, mother_profession, mother_status, nationality, nationality_name, net_stream, new_id_number, notification_email, official_email, old_state, passport_expiry_date, passport_issue_date, 
                                passport_no, pbnet_cbnet, pc_cadet, per_city, per_country_id, per_state_id, per_street, per_street2, per_zip, program_code, program_id, 
                                registration_allowed, religion_id, semester_id, session_id, sms_mobile, son_waiver_flag, specialization_id, state, state2, stream_id, 
                                student_tags_row, study_scheme_id, term_id, to_be, u_id_no, urban_rural, visa_expiry_date, visa_info, visa_issue_date, waiver_association_kinship, waiver_association_son, 
                                warning_message, partner_id, client_id, dual_national_country_id
                            ) 
                            SELECT 
                                s_nextval, rpt.admission_no, rpt.allow_re_reg_wo_fee, bat.server_id, 
                                rpt.blood_group, rpt.campus_code, campus.server_id, rpt.career_code, career.server_id, rpt.cnic, rpt.cnic_expiry_date, rpt.code, com.server_id, rpt.date_of_birth, rpt.department_code, dept.server_id, rpt.disability, rpt.disability_detail, rpt.discipline_id, domicile.server_id,
                                rpt.emergency_address, rpt.emergency_city, rpt.emergency_contact, rpt.emergency_email, rpt.emergency_mobile, rpt.entry_date, rpt.exclude_library_fee, rpt.father_cell, rpt.father_guardian_cnic, rpt.father_income, 
                                rpt.father_name, rpt.father_profession, rpt.father_status, rpt.fee_enable, rpt.fee_generated, rpt.feemerit, rpt.first_generation_studying, rpt.first_name, rpt.gender, rpt.guardian_cnic, rpt.guardian_mobile, 
                                rpt.guardian_name, rpt.hostel_cubical, rpt.hostel_facility, rpt.id_number, rpt.institute_code, ins.server_id, rpt.inter_stream, rpt.is_same_address, rpt.kinship_flag, rpt.last_name, rpt.last_term, rpt.marital_status, 
                                rpt.merit_no, rpt.mother_cell, rpt.mother_income, rpt.mother_name, rpt.mother_profession, rpt.mother_status, 
                                rpt.nationality, rpt.nationality_name, rpt.net_stream, rpt.new_id_number, rpt.notification_email, rpt.official_email, rpt.old_state, rpt.passport_expiry_date, rpt.passport_issue_date, 
                                rpt.passport_no, rpt.pbnet_cbnet, rpt.pc_cadet, rpt.per_city, rpt.per_country_id, rpt.per_state_id, rpt.per_street, rpt.per_street2, rpt.per_zip, rpt.program_code, program.server_id, 
                                rpt.registration_allowed, religion.server_id, rpt.semester_id, ses.server_id, rpt.sms_mobile, rpt.son_waiver_flag, rpt.specialization_id, rpt.state, rpt.state2, rpt.stream_id, 
                                rpt.student_tags_row, ssh.server_id, ter.server_id, TRUE, rpt.u_id_no, rpt.urban_rural, rpt.visa_expiry_date, rpt.visa_info, rpt.visa_issue_date, rpt.waiver_association_kinship, rpt.waiver_association_son, 
                                rpt.warning_message, partner.server_id, rpt.id, country.server_id
                            FROM odoocms_student AS rpt
                            LEFT OUTER JOIN odoocms_campus AS campus ON rpt.campus_id = campus.id
                            LEFT OUTER JOIN odoocms_career AS career ON rpt.career_id = career.id
                            LEFT OUTER JOIN odoocms_department AS dept ON rpt.department_id = dept.id
                            LEFT OUTER JOIN odoocms_program AS program ON rpt.program_id = program.id
                            LEFT OUTER JOIN odoocms_domicile AS domicile ON rpt.domicile_id = domicile.id
                            LEFT OUTER JOIN odoocms_institute AS ins ON rpt.institute_id = ins.id
                            LEFT OUTER JOIN odoocms_religion AS religion ON rpt.religion_id = religion.id
                            LEFT OUTER JOIN odoocms_academic_session AS ses ON rpt.session_id = ses.id
                            LEFT OUTER JOIN res_company AS com ON rpt.company_id = com.id
                            LEFT OUTER JOIN odoocms_study_scheme AS ssh ON rpt.study_scheme_id = ssh.id
                            LEFT OUTER JOIN odoocms_academic_term AS ter ON rpt.term_id = ter.id
                            LEFT OUTER JOIN res_country AS country ON rpt.dual_national_country_id = country.id
                            INNER JOIN res_partner AS partner ON rpt.partner_id = partner.id
                            INNER JOIN odoocms_batch AS bat ON rpt.batch_id = bat.id
                            WHERE NOT EXISTS (
                                SELECT 1 
                                FROM cms.odoocms_student AS cms 
                                WHERE cms.client_id = rpt.id
                            ) 
                            AND rpt.fee_paid = TRUE
                            AND rpt.id = student_ids[i]
                            LIMIT 1;
                        EXCEPTION WHEN OTHERS THEN
                            INSERT INTO temp_student_failed_ids (id) VALUES (student_ids[i]);
                            RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                            SELECT code
                            INTO v_student_code
                            FROM odoocms_student
                            WHERE id = student_ids[i];
                            SELECT code
                            INTO v_student_code
                            FROM odoocms_student
                            WHERE id = student_ids[i];
                            INSERT INTO custom_log (
                            name,
                            model,
                            method,
                            log_level,
                            message,
                            to_be,
                            company_id,
                            create_date,
                            write_date
                        ) VALUES (
                            COALESCE(v_student_code, 'Student Admission Sync Failed'),
                            'odoocms.student',
                            'sync_student_admission_to_cms',
                            'error',
                            format(
                                'Failed to sync student ID %s (Code: %s). Error: %s',
                                student_ids[i],
                                v_student_code,
                                SQLERRM
                            ),
                            TRUE,
                            v_company_id,
                            NOW(),
                            NOW()
                        );
                        END;
                    END LOOP;

                    RAISE NOTICE 'Student Insert From ADM to CMS: %', v_cnt;
                END;
                $BODY$;

                ALTER PROCEDURE public.sync_student_admission_to_cms(
                                student_ids INT[],
                                db_host TEXT,
                                db_name TEXT,
                                db_user TEXT,
                                db_password TEXT)
                OWNER TO odoo15;

            """
            self.env.cr.savepoint('student_store_procedure_admission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Student Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Student Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Student: {e}", 'red')
            _logger.error("Failed to create stored procedure Student : %s", e)


    def academic_information_store_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
                CREATE OR REPLACE PROCEDURE public.admission_to_cms_academic_detail(
                    p_ids INT[],
                    db_host TEXT,
                    db_name TEXT,
                    db_user TEXT,
                    db_password TEXT
                )
                LANGUAGE 'plpgsql'
                AS $BODY$
                DECLARE
                    v_failed_ids INT[] := '{}'; 
                    v_cnt INT;
                    ad_nextval bigint;
                    record RECORD; 
                BEGIN
                  
                    CREATE TEMP TABLE IF NOT EXISTS temp_academic_doc_failed_ids (id INT) ON COMMIT DROP;

                    FOR i IN 1 .. array_length(p_ids, 1) LOOP
                        BEGIN
                            FOR record IN 
                                    SELECT
                                    CASE
                                        WHEN de.name = 'A-Level' THEN 'a-level'
                                        WHEN de.name = 'O-Level' THEN 'o-level'
                                        WHEN de.name = ANY (ARRAY[
                                            'ADP Accounting & Finance (14 years of education)', 
                                            'BA (14 years of education)', 
                                            'B.Com. (14 Years of Education)', 
                                            'B.Sc./Equivalent (Zoology, Botany & Chemistry)', 
                                            'B.Sc./Equivalent (Double Maths & Physics)', 
                                            'B.Sc./Equivalent (Zoology, Botany & Chemistry) (14 years of education)', 
                                            'ADP Computer Science (14 years of education)'
                                        ]) THEN 'grad_14'
                                        WHEN de.name = 'Matric' THEN 'matric'
                                        WHEN de.name = 'Intermediate' THEN 'inter'
                                        WHEN de.name = 'BS Economic' THEN 'grad_16'
                                        WHEN de.name = 'MS BUSINESS ADMINISTRATION/ MANAGEMENT/ ACCOUNTING & FINANCE (18 YEARS OF EDUCATION)' THEN 'ms'
                                        WHEN de.name = 'DAE' THEN 'dae'
                                        WHEN de.name = 'BS Economics' THEN 'grad_16'
                                        ELSE 'other'
                                    END AS degree_level,
                                    de.name AS degree,
                                    ad.year,
                                    COALESCE(ad.board, ad.institute) AS board_or_institute,
                                    ac.name AS subjects,
                                    COALESCE(ad.total_marks, 0) AS total_marks,
                                    COALESCE(ad.obt_marks, 0) AS obtained_marks,
                                    st.server_id AS student_id,
                                    ad.to_be,
                                    ad.id AS applicant_academic_detail_id,
                                    COALESCE(ad.obtained_cgpa, 0) AS cgpa,
                                    com.server_id AS company_id
                                FROM applicant_academic_detail ad
                                JOIN odoocms_application app ON ad.application_id = app.id
                                LEFT JOIN odoocms_admission_degree de ON ad.degree_name = de.id
                                LEFT JOIN odoocms_admission_education ed ON ed.id = ad.degree_level_id
                                LEFT JOIN applicant_academic_group ac ON ad.group_specialization = ac.id
                                LEFT JOIN res_company AS com ON ad.company_id = com.id
                                LEFT JOIN odoocms_student st ON app.application_no::text = st.admission_no::text
                                WHERE ad.server_id IS NULL
                                AND st.fee_paid = TRUE
                                AND st.id = p_ids[i]
                                AND st.server_id IS NOT NULL
                                AND NOT EXISTS (
                                    SELECT 1 FROM cms.odoocms_student_academic cms WHERE cms.applicant_academic_detail_id = ad.id
                                )
                            LOOP
                                BEGIN
                                  
                                    SELECT nextval
                                    INTO ad_nextval
                                    FROM dblink(
                                        format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                        'SELECT get_nextval_student_academic_id()'
                                    ) AS t(nextval bigint);

                                    
                                    INSERT INTO cms.odoocms_student_academic (
                                        id, degree_level, degree, year, board, subjects, total_marks, obtained_marks, student_id, to_be, applicant_academic_detail_id, cgpa, company_id
                                    )
                                    VALUES (
                                        ad_nextval,
                                        record.degree_level,
                                        record.degree,
                                        record.year,
                                        record.board_or_institute,
                                        record.subjects,
                                        record.total_marks,
                                        record.obtained_marks,
                                        record.student_id,
                                        record.to_be,
                                        record.applicant_academic_detail_id,
                                        record.cgpa,
                                        record.company_id
                                    );

                                EXCEPTION WHEN OTHERS THEN
                                    INSERT INTO temp_academic_doc_failed_ids (id) VALUES (record.applicant_academic_detail_id);
                                    RAISE NOTICE 'Error inserting academic detail for applicant ID %: %',  p_ids[i], SQLERRM;
                                END;
                            END LOOP;

                        EXCEPTION WHEN OTHERS THEN
                            INSERT INTO temp_academic_doc_failed_ids (id) VALUES (p_ids[i]);
                            RAISE NOTICE 'Error processing student ID %: %', p_ids[i], SQLERRM;
                        END;
                    END LOOP;
                END;
                $BODY$;

                ALTER PROCEDURE public.admission_to_cms_academic_detail(
                    p_ids INT[],
                    db_host TEXT,
                    db_name TEXT,
                    db_user TEXT,
                    db_password TEXT)
                OWNER TO odoo15;"""
            self.env.cr.savepoint('academic_information_store_procedures_admission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Academic Document Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Academic Document Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Academic Document: {e}", 'red')
            _logger.error("Failed to create stored procedure Academic Document : %s", e) 



    def fee_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
               CREATE OR REPLACE PROCEDURE public.odoocms_fee_adm_to_cms(
                    student_ids INT[],
                    db_host TEXT,
                    db_name TEXT,
                    db_user TEXT,
                    db_password TEXT
                )
                LANGUAGE 'plpgsql'
                AS $BODY$
                DECLARE
                    fee_nextval bigint;
                    record RECORD;
                BEGIN
                    CREATE TEMP TABLE IF NOT EXISTS odoocms_fee_adm_to_cms_failed_ids (id INT) ON COMMIT DROP;

                    FOR i IN 1 .. array_length(student_ids, 1) LOOP
                        BEGIN
                            FOR record IN 
                                SELECT 
                                    adm.name,
                                    fp.date,
                                    adm.state,
                                    adm.payment_reference,
                                    adm.amount_total,
                                    adm.amount_residual,
                                    adm.payment_state,
                                    adm.invoice_date,
                                    adm.invoice_date_due,
                                    st.server_id AS student_id,
                                    program.server_id AS program_id,
                                    ter.server_id AS term_id,
                                    adm.waiver_amount,
                                    adm.waiver_percentage,
                                    adm.challan_type,
                                    com.server_id AS company_id,
                                    adm.id AS account_move_id,
                                
                                    CASE 
                                        WHEN adm.challan_type = 'admission' THEN 
                                            COALESCE(
                                                wv.server_id, 
                                                (
                                                    SELECT fwv.server_id 
                                                    FROM odoocms_fee_barcode_odoocms_fee_waiver_rel AS fbl
                                                    INNER JOIN odoocms_fee_barcode AS fb ON fb.id = fbl.odoocms_fee_barcode_id
                                                    INNER JOIN odoocms_fee_waiver AS fwv ON fbl.odoocms_fee_waiver_id = fwv.id
                                                    WHERE fb.student_id = st.id AND fb.label_id = 1
                                                    LIMIT 1 
                                                )
                                            )
                                        ELSE NULL
                                    END AS waiver_id,
                                    
                                    aj.server_id AS payment_journal_id,
                                    fp.transaction_date AS payment_date,
                                    fp.amount AS paid_amount,
                                    apt.server_id AS payment_term_id,
                                    adm.old_challan_no as challan_no
                                FROM account_move AS adm
                                LEFT OUTER JOIN odoocms_program AS program ON adm.program_id = program.id
                                LEFT OUTER JOIN odoocms_academic_term AS ter ON adm.term_id = ter.id
                                LEFT OUTER JOIN res_company AS com ON adm.company_id = com.id
                                Left JOIN account_payment_term apt ON apt.id = adm.invoice_payment_term_id
                                LEFT JOIN odoocms_fee_payment AS fp ON fp.invoice_id = adm.id
                                LEFT JOIN account_journal AS aj ON aj.id = fp.journal_id
                                LEFT JOIN account_move_odoocms_fee_waiver_rel AS r ON adm.id = r.account_move_id
                                LEFT JOIN odoocms_fee_waiver AS wv ON r.odoocms_fee_waiver_id = wv.id
                                INNER JOIN odoocms_student AS st ON st.id = adm.student_id
                                WHERE 
                                
                                NOT EXISTS (SELECT 1 FROM cms.odoocms_fee AS cms WHERE cms.account_move_id = adm.id)
                                AND st.id = student_ids[i]
                                AND st.server_id IS NOT NULL
                            LOOP
                                BEGIN
                                    SELECT nextval
                                    INTO fee_nextval
                                    FROM dblink(
                                        format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                        'SELECT get_nextval_odoocms_fee_id()'
                                    ) AS t(nextval bigint);

                                    INSERT INTO cms.odoocms_fee (
                                        id, name, date, state, payment_reference, amount_total, amount_residual, payment_state, invoice_date,
                                        invoice_date_due, student_id, program_id, term_id, waiver_amount, waiver_percentage, challan_type, company_id, account_move_id,scholarship_id,journal_id,paid_date,tuition_fee,payment_term_id,challan_no
                                    ) 
                                    VALUES (
                                        fee_nextval,
                                        record.name,
                                        record.date,
                                        record.state,
                                        record.payment_reference,
                                        record.amount_total,
                                        record.amount_residual,
                                        record.payment_state,
                                        record.invoice_date,
                                        record.invoice_date_due,
                                        record.student_id,
                                        record.program_id,
                                        record.term_id,
                                        record.waiver_amount,
                                        record.waiver_percentage,
                                        record.challan_type,
                                        record.company_id,
                                        record.account_move_id,
                                        record.waiver_id,
                                        record.payment_journal_id,
                                        record.payment_date,
                                        record.paid_amount,
                                        record.payment_term_id,
                                        record.challan_no

                                    );

                                EXCEPTION WHEN OTHERS THEN
                                    INSERT INTO odoocms_fee_adm_to_cms_failed_ids (id) VALUES (student_ids[i]);
                                    RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                                END;
                            END LOOP;

                        EXCEPTION WHEN OTHERS THEN
                            INSERT INTO odoocms_fee_adm_to_cms_failed_ids (id) VALUES (student_ids[i]);
                            RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                        END;
                    END LOOP;
                END;
                $BODY$;

                ALTER PROCEDURE public.odoocms_fee_adm_to_cms(
                    student_ids INT[],
                    db_host TEXT,
                    db_name TEXT,
                    db_user TEXT,
                    db_password TEXT)
                OWNER TO odoo15;
            """
            self.env.cr.savepoint('fee_procedures_admission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Odoocms Fee Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Odoocms Fee Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Odoocms Fee: {e}", 'red')
            _logger.error("Failed to create stored procedure Odoocms Fee : %s", e)  

    def fee_line_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
                        CREATE OR REPLACE PROCEDURE public.odoocms_fee_line_adm_to_cms(
                            student_ids INT[],
                            db_host TEXT,
                            db_name TEXT,
                            db_user TEXT,
                            db_password TEXT
                        )
                        LANGUAGE 'plpgsql'
                        AS $BODY$
                        DECLARE
                            fee_line_nextval bigint;
                            record RECORD;
                        BEGIN
                           CREATE TEMP TABLE odoocms_fee_line_adm_to_cms_failed_ids (id INT) ON COMMIT DROP;
                            FOR i IN 1 .. array_length(student_ids, 1) LOOP
                                BEGIN
                                    FOR record IN 
                                        SELECT 
                                            adm.id, 
                                            fee.odoocms_fee_ref,
                                            adm.move_id, 
                                            adm.move_name, 
                                            adm.date, 
                                            adm.ref, 
                                            adm.parent_state, 
                                            com.server_id AS company_id, 
                                            adm.sequence, 
                                            adm.name, 
                                            adm.quantity, 
                                            adm.price_unit, 
                                            adm.discount, 
                                            adm.debit, 
                                            adm.credit,
                                            adm.balance, 
                                            adm.amount_currency, 
                                            adm.price_subtotal, 
                                            adm.price_total, 
                                            adm.payment_id, 
                                            adm.amount_residual,
                                            st.server_id AS student_id, 
                                            ter.server_id AS term_id, 
                                            adm.course_credit_hours,
                                            adm.course_gross_fee, 
                                            adm.date_maturity, 
                                            adm.challan_no,
                                            lb.code as label
                                        FROM 
                                            account_move_line AS adm
                                        INNER JOIN 
                                            account_move AS fee ON adm.move_id = fee.id
                                        INNER JOIN 
                                            odoocms_student AS st ON fee.student_id = st.id
                                        LEFT OUTER JOIN odoocms_fee_barcode br on br.id=adm.challan_id
										LEFT OUTER JOIN account_payment_term_label lb on lb.id=br.label_id
                                        LEFT OUTER JOIN 
                                            odoocms_academic_term AS ter ON adm.term_id = ter.id
                                        LEFT OUTER JOIN 
                                            res_company AS com ON adm.company_id = com.id
                                        WHERE 
                                            NOT EXISTS (SELECT 1 FROM cms.odoocms_fee_line AS cms WHERE cms.account_move_line_id = adm.id)
                                        AND st.id = student_ids[i]
                                        AND st.server_id IS NOT NULL
                                    LOOP
                                        BEGIN
                                         
                                            SELECT nextval
                                            INTO fee_line_nextval
                                            FROM dblink(
                                                format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                                'SELECT get_nextval_odoocms_fee_line_id()'
                                            ) AS t(nextval bigint);

                                        
                                            INSERT INTO cms.odoocms_fee_line (
                                                id, account_move_line_id, odoocms_fee_id, move_id, move_name, date, ref, parent_state, company_id, sequence, name, quantity, price_unit, discount, debit, credit,
                                                balance, amount_currency, price_subtotal, price_total, payment_id, amount_residual, student_id, term_id, course_credit_hours,
                                                course_gross_fee, date_maturity, challan_no,label
                                            )
                                            VALUES (
                                                fee_line_nextval,
                                                record.id, 
                                                record.odoocms_fee_ref,
                                                record.move_id, 
                                                record.move_name, 
                                                record.date, 
                                                record.ref, 
                                                record.parent_state, 
                                                record.company_id, 
                                                record.sequence, 
                                                record.name, 
                                                record.quantity, 
                                                record.price_unit, 
                                                record.discount, 
                                                record.debit, 
                                                record.credit,
                                                record.balance, 
                                                record.amount_currency, 
                                                record.price_subtotal, 
                                                record.price_total, 
                                                record.payment_id, 
                                                record.amount_residual,
                                                record.student_id, 
                                                record.term_id, 
                                                record.course_credit_hours,
                                                record.course_gross_fee, 
                                                record.date_maturity, 
                                                record.challan_no,
                                                record.label
                                            );
                                        EXCEPTION WHEN OTHERS THEN
                                            INSERT INTO odoocms_fee_line_adm_to_cms_failed_ids (id) VALUES (student_ids[i]);
                                            RAISE NOTICE 'Error processing account_move_line ID % for student ID %: %', record.id, student_ids[i], SQLERRM;
                                        END;
                                    END LOOP;
                                EXCEPTION WHEN OTHERS THEN
                                    INSERT INTO odoocms_fee_line_adm_to_cms_failed_ids (id) VALUES (student_ids[i]);
                                    RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                                END;
                            END LOOP;

                        END;
                        $BODY$;

                        ALTER PROCEDURE public.odoocms_fee_line_adm_to_cms(
                            student_ids INT[],
                            db_host TEXT,
                            db_name TEXT,
                            db_user TEXT,
                            db_password TEXT)
                        OWNER TO odoo15;
            """
            self.env.cr.savepoint('fee_line_procedures_admission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Odoocms Fee Line Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Odoocms Fee Line Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Odoocms Fee Line: {e}", 'red')
            _logger.error("Failed to create stored procedure Odoocms Fee Line : %s", e)  


    def applied_scholarship_store_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
                    CREATE OR REPLACE PROCEDURE public.student_applied_scholarship_transfer(
                        student_ids INT[],
                        db_host TEXT,
                        db_name TEXT,
                        db_user TEXT,
                        db_password TEXT
                    )
                    LANGUAGE 'plpgsql'
                    AS $BODY$
                    DECLARE
                        as_nextval bigint;
                        record RECORD;
                    BEGIN
                        CREATE TEMP TABLE IF NOT EXISTS scholarship_failed_ids (id INT);

                        FOR i IN 1 .. array_length(student_ids, 1) LOOP
                            BEGIN
                                FOR record IN 
                                    SELECT 
                                        st.server_id AS student_id,
                                        adm.student_code,
                                        adm.student_name,
                                        program.server_id AS program_id,
                                        ter.server_id AS term_id,
                                        fw.server_id AS scholarship_id,
                                        adm.scholarship_percentage,
                                        adm.current,
                                        adm.state,
                                        com.server_id AS company_id,
                                        adm.id AS client_id
                                    FROM 
                                        odoocms_student_applied_scholarships AS adm  
                                    LEFT OUTER JOIN odoocms_program AS program ON adm.program_id = program.id
                                    LEFT OUTER JOIN odoocms_academic_term AS ter ON adm.term_id = ter.id
                                    LEFT OUTER JOIN res_company AS com ON adm.company_id = com.id
                                    LEFT OUTER JOIN odoocms_fee_waiver fw ON adm.scholarship_id = fw.id
                                    INNER JOIN odoocms_student AS st ON st.id = adm.student_id
                                    WHERE 
                                        NOT EXISTS (SELECT 1 FROM cms.odoocms_student_applied_scholarships AS cms WHERE cms.client_id = adm.id)
                                    AND st.id = student_ids[i]
                                    AND st.server_id IS NOT NULL
                                LOOP
                                    BEGIN
                                        SELECT nextval
                                        INTO as_nextval
                                        FROM dblink(
                                            format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                            'SELECT get_nextval_applied_scholarship_id()'
                                        ) AS t(nextval bigint);
                                        INSERT INTO cms.odoocms_student_applied_scholarships (
                                            id, student_id, student_code, student_name, program_id, term_id, scholarship_id,
                                            scholarship_percentage, current, state, company_id, client_id
                                        ) 
                                        VALUES (
                                            as_nextval,
                                            record.student_id,
                                            record.student_code,
                                            record.student_name,
                                            record.program_id,
                                            record.term_id,
                                            record.scholarship_id,
                                            record.scholarship_percentage,
                                            record.current,
                                            record.state,
                                            record.company_id,
                                            record.client_id
                                        );

                                    EXCEPTION WHEN OTHERS THEN
                                        INSERT INTO scholarship_failed_ids (id) VALUES (student_ids[i]);
                                        RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                                    END;
                                END LOOP;

                            EXCEPTION WHEN OTHERS THEN
                                INSERT INTO scholarship_failed_ids (id) VALUES (student_ids[i]);
                                RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                            END;
                        END LOOP;
                    END;
                    $BODY$;

                    ALTER PROCEDURE public.student_applied_scholarship_transfer(
                        student_ids INT[],
                        db_host TEXT,
                        db_name TEXT,
                        db_user TEXT,
                        db_password TEXT)
                    OWNER TO odoo15;

            """
            self.env.cr.savepoint('applied_scholarship_store_procedures_radmission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Applied Scholarship Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Applied Scholarship Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Applied Scholarship : {e}", 'red')
            _logger.error("Failed to create stored procedure Applied Scholarship  : %s", e)

    def scholarship_eligibility_store_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
                                CREATE OR REPLACE PROCEDURE public.student_scholarship_eligibility_transfer(
                                student_ids INT[],
                                db_host TEXT,
                                db_name TEXT,
                                db_user TEXT,
                                db_password TEXT
                            )
                            LANGUAGE 'plpgsql'
                            AS $BODY$
                            DECLARE
                                se_nextval bigint;
                                record RECORD;
                            BEGIN
                                CREATE TEMP TABLE IF NOT EXISTS scholarship_eligibility_failed_ids (id INT) ON COMMIT DROP;

                                FOR i IN 1 .. array_length(student_ids, 1) LOOP
                                    BEGIN
                                        FOR record IN 
                                            SELECT 
                                                st.server_id as student_id,
                                                adm.student_code, 
                                                adm.student_name, 
                                                program.server_id AS program_id, 
                                                fw.server_id AS scholarship_id, 
                                                adm.state, 
                                                com.server_id AS company_id, 
                                                adm.id AS client_id,
                                                ptsi.server_id AS program_term_scholarship,
                                                ter.server_id AS applied_term_id
                                            FROM 
                                                odoocms_student_scholarship_eligibility AS adm  
                                            LEFT OUTER JOIN 
                                                odoocms_program AS program ON adm.program_id = program.id
                                            LEFT OUTER JOIN 
                                                res_company AS com ON adm.company_id = com.id
                                            LEFT OUTER JOIN 
                                                odoocms_fee_waiver fw ON adm.scholarship_id = fw.id
                                            LEFT OUTER JOIN 
                                                odoocms_program_term_scholarship ptsi ON adm.program_term_scholarship_id = ptsi.id
                                            LEFT OUTER JOIN 
                                                odoocms_academic_term AS ter ON adm.applied_term_id = ter.id
                                            INNER JOIN 
                                                odoocms_student AS st ON st.id = adm.student_id
                                            WHERE 
                                                NOT EXISTS (SELECT 1 FROM cms.odoocms_student_scholarship_eligibility AS cms WHERE cms.client_id = adm.id)
                                            AND st.id = student_ids[i]
                                            AND st.server_id IS NOT NULL
                                        LOOP
                                            BEGIN
                                                SELECT nextval
                                                INTO se_nextval
                                                FROM dblink(
                                                    format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                                    'SELECT get_nextval_scholarship_eligibility_id()'
                                                ) AS t(nextval bigint);

                                                -- Insert the record with the unique nextval
                                                INSERT INTO cms.odoocms_student_scholarship_eligibility (
                                                    id, student_id, student_code, student_name, program_id, scholarship_id, state, company_id, client_id, program_term_scholarship_id, applied_term_id
                                                ) 
                                                VALUES (
                                                    se_nextval,
                                                    record.student_id,
                                                    record.student_code,
                                                    record.student_name,
                                                    record.program_id,
                                                    record.scholarship_id,
                                                    record.state,
                                                    record.company_id,
                                                    record.client_id,
                                                    record.program_term_scholarship,
                                                    record.applied_term_id
                                                );

                                            EXCEPTION WHEN OTHERS THEN
                                                INSERT INTO scholarship_eligibility_failed_ids (id) VALUES (student_ids[i]);
                                                RAISE NOTICE 'Error processing scholarship eligibility for student ID %: %', student_ids[i], SQLERRM;
                                            END;
                                        END LOOP;

                                    EXCEPTION WHEN OTHERS THEN
                                        INSERT INTO scholarship_eligibility_failed_ids (id) VALUES (student_ids[i]);
                                        RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                                    END;
                                END LOOP;

                            END;
                            $BODY$;
                            ALTER PROCEDURE public.student_scholarship_eligibility_transfer(
                                student_ids INT[],
                                db_host TEXT,
                                db_name TEXT,
                                db_user TEXT,
                                db_password TEXT)
                            OWNER TO odoo15;
                                        """
            self.env.cr.savepoint('scholarship_eligibility_store_procedures_radmission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Scholarship Eligibility Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Scholarship Eligibility Stored procedure created successfully.")
            self.env.cr.commit()

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Scholarship Eligibility: {e}", 'red')
            _logger.error("Failed to create stored procedure Scholarship Eligibility : %s", e)   





    def applied_scholarship_store_procedures_admission_to_cms(self):
        try:
            create_procedure_sql = """
 CREATE OR REPLACE PROCEDURE public.student_applied_scholarship_transfer(
                    student_ids INT[],
                    db_host TEXT,
                    db_name TEXT,
                    db_user TEXT,
                    db_password TEXT
                )
                LANGUAGE 'plpgsql'
                AS $BODY$
                DECLARE
                    as_nextval bigint;
                    record RECORD;
                BEGIN
                    CREATE TEMP TABLE IF NOT EXISTS scholarship_failed_ids (id INT) ON COMMIT DROP;

                    FOR i IN 1 .. array_length(student_ids, 1) LOOP
                        BEGIN
                            FOR record IN 
                                SELECT 
                                    st.server_id AS student_id,
                                    adm.student_code,
                                    adm.student_name,
                                    program.server_id AS program_id,
                                    ter.server_id AS term_id,
                                    fw.server_id AS scholarship_id,
                                    adm.scholarship_percentage,
                                    adm.current,
                                    adm.state,
                                    com.server_id AS company_id,
                                    adm.id AS client_id
                                FROM 
                                    odoocms_student_applied_scholarships AS adm  
                                LEFT OUTER JOIN odoocms_program AS program ON adm.program_id = program.id
                                LEFT OUTER JOIN odoocms_academic_term AS ter ON adm.term_id = ter.id
                                LEFT OUTER JOIN res_company AS com ON adm.company_id = com.id
                                LEFT OUTER JOIN odoocms_fee_waiver fw ON adm.scholarship_id = fw.id
                                INNER JOIN odoocms_student AS st ON st.id = adm.student_id
                                WHERE 
                                    NOT EXISTS (SELECT 1 FROM cms.odoocms_student_applied_scholarships AS cms WHERE cms.client_id = adm.id)
                                AND st.id = student_ids[i]
                                AND st.server_id IS NOT NULL
                            LOOP
                                BEGIN
                                    SELECT nextval
                                    INTO as_nextval
                                    FROM dblink(
                                        format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                        'SELECT get_nextval_applied_scholarship_id()'
                                    ) AS t(nextval bigint);
                                    INSERT INTO cms.odoocms_student_applied_scholarships (
                                        id, student_id, student_code, student_name, program_id, term_id, scholarship_id,
                                        scholarship_percentage, current, state, company_id, client_id
                                    ) 
                                    VALUES (
                                        as_nextval,
                                        record.student_id,
                                        record.student_code,
                                        record.student_name,
                                        record.program_id,
                                        record.term_id,
                                        record.scholarship_id,
                                        record.scholarship_percentage,
                                        record.current,
                                        record.state,
                                        record.company_id,
                                        record.client_id
                                    );

                                EXCEPTION WHEN OTHERS THEN
                                    INSERT INTO scholarship_failed_ids (id) VALUES (student_ids[i]);
                                    RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                                END;
                            END LOOP;

                        EXCEPTION WHEN OTHERS THEN
                            INSERT INTO scholarship_failed_ids (id) VALUES (student_ids[i]);
                            RAISE NOTICE 'Error processing student ID %: %', student_ids[i], SQLERRM;
                        END;
                    END LOOP;
                END;
                $BODY$;

                ALTER PROCEDURE public.student_applied_scholarship_transfer(
                    student_ids INT[],
                    db_host TEXT,
                    db_name TEXT,
                    db_user TEXT,
                    db_password TEXT)
                OWNER TO odoo15;
            """
            self.env.cr.savepoint('applied_scholarship_store_procedures_radmission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("Applied Scholarship Stored procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("Applied Scholarship Stored procedure created successfully.")

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure Applied Scholarship : {e}", 'red')
            _logger.error("Failed to create stored procedure Applied Scholarship  : %s", e)

    def first_semester_courses_admission_to_cms(self):
        try:
            create_procedure_sql = """
                                CREATE OR REPLACE PROCEDURE public.courses_adm_to_cms(
                                    p_ids INT[],
                                    db_host TEXT,
                                    db_name TEXT,
                                    db_user TEXT,
                                    db_password TEXT
                                )
                                LANGUAGE 'plpgsql'
                                AS $BODY$
                                DECLARE       
                                    cc_nextval bigint;
                                    record RECORD; 
                                BEGIN
                                    CREATE TEMP TABLE IF NOT EXISTS temp_courses_failed_ids (id INT);
                                
                                    FOR i IN 1 .. array_length(p_ids, 1) LOOP
                                        BEGIN
                                            FOR record IN 
                                                SELECT DISTINCT ON (fsc.id)
                                                    fsc.id AS fsc_ref,
                                                    cc.server_id AS course_id,
                                                    ssh.server_id AS study_scheme_id,
                                                    ssh.career_id AS career_id,
                                                    ssl.server_id AS study_scheme_line_id,
                                                    fsc.credit_hours,
                                                    program.server_id AS program_id,
                                                    st.server_id AS student_id,
                                                    ses.server_id as session_id,
                                                    ob.server_id as batch_id,
                                                    ter.server_id as term_id
                                                    -- com.server_id AS company_id
                                                FROM  odoocms_applicant_first_semester_courses AS fsc
                                                INNER JOIN  odoocms_application app ON app.id = fsc.application_id
                                                INNER JOIN odoocms_student st ON app.application_no::text = st.admission_no::text
                                                LEFT JOIN odoocms_study_scheme AS ssh ON fsc.study_scheme_id = ssh.id
                                                LEFT JOIN odoocms_study_scheme_line ssl ON ssl.study_scheme_id = ssh.id
                                                LEFT JOIN odoocms_program AS program ON ssh.program_id = program.id
                                                LEFT JOIN odoocms_course cc ON cc.id = fsc.course_id
                                                LEFT JOIN odoocms_batch ob ON ob.id = ssh.batch_id
                                                LEFT JOIN odoocms_academic_session AS ses ON ssh.session_id = ses.id
                                                LEFT JOIN odoocms_academic_term AS ter ON app.term_id = ter.id
                                                -- LEFT JOIN res_company AS com ON fsc.company_id = com.id
                                                WHERE 
                                                    fsc.server_id IS NULL
                                                    AND st.id = p_ids[i]
                                                    AND st.server_id IS NOT NULL
                                                ORDER BY 
                                                    fsc.id, cc.server_id
                                            LOOP
                                                BEGIN
                                                    SELECT nextval
                                                    INTO cc_nextval
                                                    FROM dblink(
                                                        format('host=%s dbname=%s user=%s password=%s', db_host, db_name, db_user, db_password),
                                                        'SELECT get_first_semester_courses_id()'
                                                    ) AS t(nextval bigint);
                                                    INSERT INTO cms.odoocms_applicant_first_semester_courses (
                                                        id, client_id , course_id, study_scheme_id, credit_hours , student_id , program_id , session_id, batch_id, term_id
                                                    )
                                                    VALUES (
                                                        cc_nextval,
                                                        record.fsc_ref,
                                                        record.course_id,
                                                        record.study_scheme_id,
                                                  
                                                        record.credit_hours,
                                                        record.student_id,
                                                        record.program_id,
                                                     
                                                        record.session_id,
                                                        record.batch_id,
                                                        record.term_id
                                                        
                                                    );
                                
                                                EXCEPTION WHEN OTHERS THEN
                                                    INSERT INTO temp_courses_failed_ids (id) VALUES (p_ids[i]);
                                                    RAISE NOTICE 'Error processing student ID %: %', p_ids[i], SQLERRM;
                                                END;
                                            END LOOP;
                                
                                        EXCEPTION WHEN OTHERS THEN
                                            INSERT INTO temp_courses_failed_ids (id) VALUES (p_ids[i]);
                                            RAISE NOTICE 'Error processing student ID %: %', p_ids[i], SQLERRM;
                                        END;
                                    END LOOP;
                                END;
                                $BODY$;
                                
                                ALTER PROCEDURE public.courses_adm_to_cms(
                                    p_ids INT[],
                                    db_host TEXT,
                                    db_name TEXT,
                                    db_user TEXT,
                                    db_password TEXT)
                                OWNER TO odoo15;

            """
            self.env.cr.savepoint('first_semester_courses_admission_to_cms')
            self.env.cr.execute(create_procedure_sql)
            self.add_log_message("First Semester Courses procedure created successfully.", 'green')
            self.env.cr.commit()
            _logger.info("First Semester Courses Stored procedure created successfully.")
            self.env.cr.commit()

        except Exception as e:
            self.env.cr.rollback()
            self.add_log_message(f"Failed to create stored procedure First Semester Courses: {e}", 'red')
            _logger.error("Failed to create stored procedure First Semester Courses : %s", e)  
