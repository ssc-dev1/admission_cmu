from . import models
from odoo import api, SUPERUSER_ID

def _pre_init_aarsol_signin(cr):
    cr.execute("""ALTER TABLE "res_company" ADD COLUMN "identifier" varchar;""")
    cr.execute("""ALTER TABLE "res_company" ADD COLUMN "short_name" varchar;""")
    cr.execute("""ALTER TABLE "res_company" ADD COLUMN "company_tag" varchar;""")
    cr.execute("""ALTER TABLE "res_company" ADD COLUMN "logo_width" integer;""")
    cr.execute("""ALTER TABLE "res_company" ADD COLUMN "logo_height" integer;""")


    # cr.execute("""UPDATE stock_move
    #                  SET is_done=COALESCE(state in ('done', 'cancel'), FALSE);""")
    # cr.execute("""ALTER TABLE "stock_move" ADD COLUMN "unit_factor" double precision;""")
    # cr.execute("""UPDATE stock_move
    #                  SET unit_factor=1;""")


# def pre_init_hook(cr):
#     env = api.Environment(cr, SUPERUSER_ID, {})
#     env['ir.model.data'].search([
#         ('model', 'like', '%stock%'),
#         ('module', '=', 'stock')
#     ]).unlink()
