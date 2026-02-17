# -*- coding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class OdooCMSProgramInherit(models.Model):
    _inherit = 'odoocms.program'

    # Is Parent Program Flag - Used for admission registration
    is_parent = fields.Boolean(
        string='Is Parent Program',
        default=False,
        help='Check this if this program is a parent program. A parent program cannot have another parent program.'
    )

    # Parent Program Relationship - For child programs to link to their parent
    parent_program_id = fields.Many2one(
        'odoocms.program',
        string='Parent Program',
        domain="[('is_parent', '=', True), ('career_id', '=', career_id), ('id', '!=', id)]",
        ondelete='restrict',
        help='Select the parent program for this child program. Only parent programs from the same career will be shown. '
             'Child programs will use parent\'s short_code and sequence_number for registration number generation. '
             'A child program cannot be marked as parent program.'
    )

    @api.constrains('is_parent', 'parent_program_id')
    def _check_parent_child_relationship(self):
        """Ensure a program cannot be both parent and child"""
        for program in self:
            if program.is_parent and program.parent_program_id:
                raise ValidationError(
                    _('A program cannot be both a parent program and have a parent program. '
                      'If "Is Parent Program" is checked, "Parent Program" must be empty.')
                )

    @api.onchange('is_parent')
    def _onchange_is_parent(self):
        """Clear parent_program_id when is_parent is set to True"""
        if self.is_parent:
            self.parent_program_id = False

    @api.onchange('parent_program_id')
    def _onchange_parent_program_id(self):
        """Set is_parent to False when parent_program_id is set"""
        if self.parent_program_id:
            self.is_parent = False
