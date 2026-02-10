# -*- coding: utf-8 -*-
from odoo.addons.base_rest.controllers import main


class BaseRestHUApiController(main.RestController):
    _root_path = "/odoo/"
    _collection_name = "odoo.services"
    _default_auth = 'api_key'  # "public"    api_key


class BaseRestPrivateApiController(main.RestController):
    _root_path = "/rest/private/"
    _collection_name = "base.rest.private.services"
    _default_auth = 'api_key'  # "user"


class BaseRestMobileApiController(main.RestController):
    _root_path = "/aarsol/"
    _collection_name = "aarsol.services"
    _default_auth = 'public'  # api_key
