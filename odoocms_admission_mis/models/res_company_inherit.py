from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    challan_check_merit_list = fields.Boolean('Check Merit List', default=True, 
                                            help='Verify if student is on merit list before generating challan')
    challan_check_document_verification = fields.Boolean('Check Document Verification', default=True,
                                                        help='Verify if all documents are verified before generating challan')
    challan_check_scholarship = fields.Boolean('Check Scholarship', default=True,
                                             help='Verify scholarship status before generating challan')
    # allow singups 
    allow_signups = fields.Boolean(
        string='Allow Online Signups',
        default=True,
        help='If unchecked, new applicants will not see the Sign-Up option on the admission portal.'
    )
    challan_check_offer_letter = fields.Boolean('Check Offer Letter', default=False, 
                                            help='Verify if the offer letter is sent to student')