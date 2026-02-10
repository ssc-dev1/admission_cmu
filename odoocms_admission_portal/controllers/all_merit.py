from odoo.http import route, request, Controller


class MeritPublic(Controller):
    @route(['/merit/all/'], method='GET', type='http', auth="public")
    def merit_all(self, **kw):
        merit_register = request.env['odoocms.merit.registers'].sudo().search(
            [('state', '=', 'done'), ('publish_merit', '=', True)])
        context = {'merit_register': merit_register,
                   'company': request.env.company.name}
        return request.render('odoocms_admission_portal.all_merit', context)
