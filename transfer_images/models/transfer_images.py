# -*- coding: utf-8 -*-
from odoo import models, fields, api
import pdb
import base64
import codecs
import logging
from odoo_rpc_client import Client
import logging

_logger = logging.getLogger(__name__)


class OdooCMSStudentAcademic(models.Model):
    _inherit = "odoocms.student.academic"

    server_id = fields.Integer('Server ID')
    to_be = fields.Boolean()
    applicant_academic_detail_id = fields.Many2one('applicant.academic.detail', 'Applicant Academic Detail')


class Transfer_Images(models.Model):
    _name = 'transfer_images.transfer_images'
    _description = 'Transfer_Images'

    name = fields.Char(string="Name", required=True)
    # code = fields.Char(string="Code", required=True)
    # sequence = fields.Integer(string="Sequence")
    # color = fields.Integer("Color")

    source_host = fields.Char(string='Host')
    source_port = fields.Char(string='Port')
    source_dbname = fields.Char(string='Database Name')
    source_user = fields.Char(string='User')
    source_password = fields.Char(string='Password')
    target_host = fields.Char(string='Host')
    target_port = fields.Char(string='Port')
    target_dbname = fields.Char(string='Database Name')
    target_user = fields.Char(string='User')
    target_password = fields.Char(string='Password')

    def copy_images(self):
        print(f'Copy Images Button ')
        # pdb.set_trace()
        try:
            # _logger.info("Connecting to  %s on port %s for database %s ......", self.source_host,self.source_port,self.source_dbname)
            # adm_db1 = Client(host=self.source_host, port=self.source_port, dbname=self.source_dbname, user=self.source_user, pwd=self.source_password)
            # _logger.info("Connection Successful")

            _logger.info("Connecting to  %s on port %s for database %s ......", self.target_host, self.target_port, self.target_dbname)
            cms_db2 = Client(host=self.target_host, port=self.target_port, dbname=self.target_dbname, user=self.target_user, pwd=self.target_password)
            _logger.info("Connection Successful")

            # self.transfer_images(adm_db1, cms_db2)
            self.sync_odoocms_student_academic(cms_db2)
        except Exception as e:
            logging.error(f"Failed to initialize databases or sync images: {e}")

    # def transfer_images(self, cms_db2):
    #     adm_student_ids = self.env['odoocms.student'].search([('to_be', '=', True)])
    #     student_obj2 = cms_db2['odoocms.student']
    #
    #     for student_id in adm_student_ids:
    #         if student_id.image_1920:
    #             students_in_cms = student_obj2.search_records([('code', '=', student_id.code)])
    #
    #             if students_in_cms:
    #                 try:
    #                     students_in_cms = students_in_db2[0]
    #                     students_in_cms.write({'image_1920': student_id.image_1920})
    #                     student_id.write({'to_be': False})
    #                 except Exception as e:
    #                     logging.error(f"Failed to sync image for student {student_id.code}: {e}")

    def sync_odoocms_student_academic(self, cms_db2):
        # admission_ids = self.env["odoocms.student.academic"].search([('to_be', '=', True)])
        admission_ids = self.env["odoocms.student.academic"].search([])

        _logger.info("Admission Records %r", len(admission_ids))
        for admission_id in admission_ids:
            _logger.info("Admission Id is being processed %r", admission_id.id)
            attachment = self.env['applicant.academic.detail'].search(
                [('id', '=', admission_id.applicant_academic_detail_id.id)])

            # attachment = admission_applicant.search_records([('id', '=', 2908)])
            if attachment:
                _logger.info("Attachments Found")
                _logger.info("Admission Id %r*** and Server Id %r***", admission_id, admission_id.server_id)
                # if attachment.degree_attachment:
                students_in_cms = cms_db2['odoocms.student.academic'].search_records([('id', '=', admission_id.server_id)])
                # cms_std_academic_id = cms_db2['odoocms.student.academic'].search_records(
                # 	[('id', '=', admission_id.server_id)])

                # students_in_cms_academic_detail = cms_db2['applicant.academic.detail'].search_records([('id', '=', admission_id[-2])])

                if students_in_cms:
                    _logger.info("Student Found")
                    try:
                        student_in_cms = students_in_cms[0]
                        # student_in_cms.write({'degree_attachment': attachment.degree_attachment})
                        student_in_cms.write({'degree_attachment': attachment.degree_attachment})
                        _logger.info("Write Successful")
                    # student_in_cms.write({'to_be': False})
                    except Exception as e:
                        logging.error(f"Failed to sync image for student {admission_id.server_id}: {e}")
