# Copyright 2018 ACSONE SA/NV
# Copyright 2017 Akretion (http://www.akretion.com).
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging

from odoo import models
from odoo.exceptions import AccessDenied
from werkzeug.exceptions import BadRequest
from odoo.http import request

_logger = logging.getLogger(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_api_key(cls):
        user_key = request.httprequest.headers.get("username")
        if not user_key:
            raise BadRequest("Authorization header with username key missing")
        pass_key = request.httprequest.headers.get("password")
        if not pass_key:
            raise BadRequest("Authorization header with password key missing")

        # request.uid = 1
        # uid = request.env["auth.api.key"]._retrieve_uid_from_api_key(api_key)
        user_id = request.env['res.users'].sudo().search([('login', '=', user_key), ('secret', '=', pass_key)])
        if not user_id:
            raise BadRequest("API key invalid")

        request.uid = user_id.id
        return True

        # headers = request.httprequest.environ
        # api_key = headers.get("HTTP_API_KEY")
        # if api_key:
        #     request.uid = 1
        #     auth_api_key = request.env["auth.api.key"]._retrieve_api_key(api_key)
        #     if auth_api_key:
        #         # reset _env on the request since we change the uid...
        #         # the next call to env will instantiate an new
        #         # odoo.api.Environment with the user defined on the
        #         # auth.api_key
        #         request._env = None
        #         request.uid = auth_api_key.user_id.id
        #         request.auth_api_key = api_key
        #         request.auth_api_key_id = auth_api_key.id
        #         return True
        # _logger.error("Wrong HTTP_API_KEY, access denied")
        # raise AccessDenied()
