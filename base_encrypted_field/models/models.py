
from collections import defaultdict
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import pdb 


# class Base(models.AbstractModel):
#     _inherit = 'base'
#
#     def _valid_field_parameter(self, field, name):
#         return name == 'sparse' or super()._valid_field_parameter(field, name)


class IrModelFields(models.Model):
    _inherit = 'ir.model.fields'

    ttype = fields.Selection(selection_add=[
        ('encrypted', 'encrypted')
    ], ondelete={'encrypted': 'cascade'})
    encryption_field_id = fields.Many2one('ir.model.fields','Encryption Field',ondelete='cascade',
        help="If set, this field will be stored encrypted in encryption field, instead of having its own database column. This cannot be changed after creation.",
    )
    # domain = "[('ttype','=','encrypted')]",

    def write(self, vals):
        # Limitation: renaming a encrypt field or changing the storing system
        # is currently not allowed
        if 'encryption_field_id' in vals or 'name' in vals:
            for field in self:
                if 'encryption_field_id' in vals and field.encryption_field_id.id != vals['encryption_field_id']:
                    raise UserError(_('Changing the storing system for field "%s" is not allowed.', field.name))
                
                if field.encryption_field_id and (field.name != vals['name']):
                    raise UserError(_('Renaming encrypt field "%s" is not allowed', field.name))

        return super(IrModelFields, self).write(vals)

    def _reflect_fields(self, model_names):
        super()._reflect_fields(model_names)

        # set 'serialization_field_id' on sparse fields; it is done here to
        # ensure that the serialized field is reflected already
        cr = self._cr

        # retrieve existing values
        query = """
            SELECT model, name, id, encryption_field_id
            FROM ir_model_fields
            WHERE model IN %s
        """
        cr.execute(query, [tuple(model_names)])
        existing = {row[:2]: row[2:] for row in cr.fetchall()}

        # determine updates, grouped by value
        updates = defaultdict(list)
        for model_name in model_names:
            for field_name, field in self.env[model_name]._fields.items():
                field_id, current_value = existing[(model_name, field_name)]
                try:
                    value = existing[(model_name, field.encrypt)][0] if field.encrypt else None
                except KeyError:
                    msg = _("Encryption field %r not found for encrypt field %s!")
                    raise UserError(msg % (field.encrypt, field))
                if current_value != value:
                    updates[value].append(field_id)

        if not updates:
            return

        # update fields
        query = "UPDATE ir_model_fields SET encryption_field_id=%s WHERE id IN %s"
        for value, ids in updates.items():
            cr.execute(query, [value, tuple(ids)])

        records = self.browse(id_ for ids in updates.values() for id_ in ids)
        self.pool.post_init(records.modified, ['encryption_field_id'])
    
    # def _reflect_model(self, model):
    #     super(IrModelFields, self)._reflect_model(model)
    #     # set 'encryption_field_id' on encrypted fields; it is done here to
    #     # ensure that the encrypted field is reflected already
    #     cr = self._cr
    #     query = """ UPDATE ir_model_fields
    #                 SET encryption_field_id=%s
    #                 WHERE model=%s AND name=%s
    #                 RETURNING id
    #             """
    #     fields_data = self._existing_field_data(model._name)
    #
    #     for field in model._fields.values():
    #         enc_field_id = None
    #         enc_field_name = getattr(field, 'encrypt', None)
    #         if enc_field_name:
    #             if enc_field_name not in fields_data:
    #                 msg = _("Encryption field `%s` not found for encrypt field `%s`!")
    #                 raise UserError(msg % (enc_field_name, field.name))
    #             ser_field_id = fields_data[enc_field_name]['id']
    #
    #         if fields_data[field.name]['encryption_field_id'] != enc_field_id:
    #             cr.execute(query, (enc_field_id, model._name, field.name))
    #             record = self.browse(cr.fetchone())
    #             self.pool.post_init(record.modified, ['encryption_field_id'])
    #             self.clear_caches()
    
    def _instanciate_attrs(self, field_data):        
        attrs = super(IrModelFields, self)._instanciate_attrs(field_data)
        if attrs and field_data.get('encryption_field_id'):
            encryption_record = self.browse(field_data['encryption_field_id'])
            attrs['encrypt'] = encryption_record.name
        return attrs


class TestEncrypted(models.TransientModel):
    _name = 'encrypted_fields.test'
    _description = 'Encrypted Fields Test'

    encrypted = fields.Encrypted()
    encrypted_password = fields.Encrypted()
    boolean = fields.Boolean(encrypt='encrypted')
    integer = fields.Integer(encrypt='encrypted')
    float = fields.Float(encrypt='encrypted')
    char = fields.Char(encrypt='encrypted')
    password = fields.Char(encrypt='encrypted_password')
    selection = fields.Selection(
        selection=[('one', 'One'), ('two', 'Two')],
        encrypt='encrypted'
    )
    html = fields.Html(encrypt='encrypted')
    partner = fields.Many2one('res.partner', encrypt='encrypted')
