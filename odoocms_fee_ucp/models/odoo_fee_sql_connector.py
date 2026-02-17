# -*- coding: utf-8 -*-
import pdb
from odoo import api, fields, models, tools, _
import pyodbc
import logging

_logger = logging.getLogger(__name__)


class OdooFeeSQLConnector(models.Model):
    _name = 'odoo.fee.sql.connector'
    _description = 'Connect Odoo With SQL For Fee Integration'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    driver = fields.Char('Driver', default="ODBC Driver 17 for SQL Server;", tracking=True)
    server = fields.Char('Server', default="hodpgc.southeastasia.cloudapp.azure.com;", tracking=True)
    database = fields.Char('Database', default="CMS360;", tracking=True)
    conn_uid = fields.Char('UID', default='odoo;', tracking=True)
    conn_pwd = fields.Char('PWD', default='Kalkome@786;', tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('lock', 'Locked')], string='Status', default='draft', tracking=True)
    notes = fields.Text('Notes', tracking=True)

    def action_lock(self):
        self.state = 'lock'

    def action_unlock(self):
        self.state = 'draft'

    def action_establish_connection(self):
        connection_string = ("DRIVER=" + self.driver +
                             "SERVER=" + self.server +
                             'DATABASE=' + self.database +
                             'UID=' + self.conn_uid +
                             'PWD=' + self.conn_pwd +
                             'charset=utf8mb4;'
                             )
        conn = pyodbc.connect(connection_string)
        _logger.info('*** Conn Response %s', conn)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION as version")
        # cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES")
        row = cursor.fetchone()
        if row:
            self.notes = "Connection Established " + str(fields.Datetime.now())
            return conn, cursor
            # cursor.close()
            # conn.close()

    def action_close_connection(self, conn, cursor):
        if cursor:
            cursor.close()
        if conn:
            conn.close()
