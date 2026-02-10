from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
import base64
import os

class NeedBasedScholarship(models.Model):
    _name = "need.based.scholarship"
    _description = "CMU Need-Based Scholarship"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _rec_name = "applicant_id"
    _order = "id desc"

    # -----------------------------
    # 1) Student Information
    # -----------------------------
    applicant_id = fields.Many2one(
        "odoocms.application",
        string="Application",
        required=True,
        index=True,
        tracking=True,
        help="Linked CMU admission application",
    )
    full_name = fields.Char(string="Full Name", compute="_compute_student_details", store=True)
    registration_number = fields.Char(string="Student Registration Number", compute="_compute_student_details", store=True)
    degree_program = fields.Char(string="Degree Program", compute="_compute_student_details", store=True)
    program_year = fields.Char(string="Year", compute="_compute_student_details", store=True)
    contact_number = fields.Char(string="Contact Number", compute="_compute_student_details", store=True)
    email = fields.Char(string="Email", compute="_compute_student_details", store=True)

    prev_scholarship = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Previously on Scholarship?",
        default="no",
        tracking=True,
    )
    prev_scholarship_details = fields.Text(
        string="Previous Scholarship Details",
        help="Provide details if previously on any scholarship"
    )

    # -----------------------------
    # 2) Household: Father / Mother
    # -----------------------------
    father_name = fields.Char(string="Father's Name", compute="_compute_student_details", store=True)
    father_occupation = fields.Selection(
        [
            ("employed", "Employed"),
            ("self_employed", "Self-Employed / Business owner"),
            ("unemployed", "Un-employed"),
            ("deceased", "Deceased"),
        ],
        string="Father’s Occupation",
        tracking=True,
    )
    father_employer_name = fields.Char(string="Father Employer / Business Name")
    father_designation = fields.Char(string="Father Designation / Business Type")
    father_salary_slips = fields.Binary(string="Father Salary/Income Proof (PDF)")
    father_unemployed_reason = fields.Text(string="Father Unemployment Reason")
    father_death_certificate = fields.Binary(string="Father Death Certificate (PDF)")

    mother_name = fields.Char(string="Mother's Name", compute="_compute_student_details", store=True)
    mother_occupation = fields.Selection(
        [
            ("employed", "Employed"),
            ("self_employed", "Self-Employed / Business owner"),
            ("unemployed", "Un-employed"),
            ("deceased", "Deceased"),
        ],
        string="Mother’s Occupation",
        tracking=True,
    )
    mother_employer_name = fields.Char(string="Mother Employer / Business Name")
    mother_designation = fields.Char(string="Mother Designation / Business Type")
    mother_salary_slips = fields.Binary(string="Mother Salary/Income Proof (PDF)")
    mother_unemployed_reason = fields.Text(string="Mother Unemployment Reason")
    mother_death_certificate = fields.Binary(string="Mother Death Certificate (PDF)")

    # -----------------------------
    # 2) Household: Other Members (repeatable)
    # -----------------------------
    household_member_ids = fields.One2many(
        "nbs.household.member",
        "nbs_id",
        string="Other Household Members (living/contributing)"
    )

    # -----------------------------
    # 3) Household Income (Monthly)
    # -----------------------------
    father_monthly_income = fields.Float(string="Father Monthly Income (PKR)")
    mother_monthly_income = fields.Float(string="Mother Monthly Income (PKR)")

    other_income_ids = fields.One2many(
        "nbs.other.income", "nbs_id", string="Other Contributing Members"
    )

    income_rental = fields.Boolean(string="Rental income?")
    income_rental_amount = fields.Float(string="Rental Income (Monthly)")

    income_pension = fields.Boolean(string="Pension?")
    income_pension_amount = fields.Float(string="Pension (Monthly)")

    income_zakat = fields.Boolean(string="Zakat received?")
    income_zakat_amount = fields.Float(string="Zakat (Monthly)")

    income_remittance = fields.Boolean(string="Remittances received?")
    income_remittance_amount = fields.Float(string="Remittances (Monthly)")

    income_self = fields.Boolean(string="Self income (applicant)?")
    income_self_amount = fields.Float(string="Self Income (Monthly)")

    total_monthly_income = fields.Float(
        string="Total Monthly Household Income",
        compute="_compute_total_income",
        store=True,
        readonly=True,
    )

    # -----------------------------
    # 4) Household Expenses (Monthly)
    # -----------------------------
    # Education (siblings) – toggle + lines
    has_sibling_education_expense = fields.Boolean(string="Education expenses for siblings?")
    sibling_expense_ids = fields.One2many(
        "nbs.sibling.education.expense",
        "nbs_id",
        string="Sibling Education Expenses"
    )

    # Rent
    is_living_on_rent = fields.Boolean(string="Living on Rent?")
    monthly_rent = fields.Float(string="Monthly Rent (PKR)")
    rent_agreement = fields.Binary(string="Rental Agreement (PDF)")

    # Utilities (Latest Month ONLY, per revised note)
    gas_bill_amount = fields.Float(string="Gas Bill (Latest Month)")
    gas_bill_attachment = fields.Binary(string="Gas Bill (PDF)")
    elec_bill_amount = fields.Float(string="Electricity Bill (Latest Month)")
    elec_bill_attachment = fields.Binary(string="Electricity Bill (PDF)")
    water_bill_amount = fields.Float(string="Water Bill (Latest Month)")
    water_bill_attachment = fields.Binary(string="Water Bill (PDF)")

    # Other expenses
    monthly_grocery = fields.Float(string="Monthly Grocery / Living")

    has_medical_expense = fields.Boolean(string="Recurring Medical Expense?")
    medical_expense_nature = fields.Char(string="Medical Expense Nature")
    medical_expense_amount = fields.Float(string="Medical Expense Amount (Monthly)")
    medical_expense_attachment = fields.Binary(string="Medical Evidence (PDF)")

    has_other_recurring = fields.Boolean(string="Other Major Monthly Recurring Expense?")
    other_recurring_nature = fields.Char(string="Other Expense Nature")
    other_recurring_amount = fields.Float(string="Other Expense Amount (Monthly)")
    other_recurring_attachment = fields.Binary(string="Other Expense Evidence (PDF)")

    total_monthly_expense = fields.Float(
        string="Total Monthly Household Expense",
        compute="_compute_total_expense",
        store=True,
        readonly=True,
    )

    # Hidden from students on portal (do not render in portal views)
    net_monthly_income = fields.Float(
        string="Net Monthly Income (Auto)",
        compute="_compute_net_income",
        store=True,
        readonly=True,
        help="Total Income - Total Expense"
    )

    # -----------------------------
    # 5) Assets (info only; NO attachments)
    # -----------------------------
    asset_house = fields.Boolean(string="House (Self-owned)")
    asset_house_area = fields.Char(string="House Area / Locality")
    asset_house_value = fields.Float(string="House Value (Approx.)")

    asset_land = fields.Boolean(string="Land / Property")
    asset_land_area = fields.Char(string="Land Area / Locality")
    asset_land_value = fields.Float(string="Land Value (Approx.)")

    asset_business = fields.Boolean(string="Business Ownership")
    asset_business_value = fields.Float(string="Business Value (Approx.)")

    vehicle_ids = fields.One2many("nbs.vehicle", "nbs_id", string="Vehicles")

    # -----------------------------
    # 6) Loans / Liabilities (repeatable)
    # -----------------------------
    has_loans = fields.Boolean(string="Any Outstanding Loans / Liabilities?")
    loan_ids = fields.One2many("nbs.loan", "nbs_id", string="Loans / Liabilities")

    net_assets = fields.Float(
        string="Net Assets (Assets - Liabilities)",
        compute="_compute_net_assets",
        store=True,
        readonly=True,
        help="(House + Land + Business + Vehicles) - Outstanding Loans"
    )

    # -----------------------------
    # 7) Statement & 8) Declaration & Mandatory Attachments
    # -----------------------------
    sop = fields.Text(string="Statement of Purpose (≤ 350 words)")
    declaration = fields.Boolean(
        string="I declare that information provided is true.",
        help="Must be checked to submit."
    )

    bank_statements_6m = fields.Binary(string="6-month Bank Statement (Parents/Guardians)")
    cnic_parents = fields.Binary(string="CNIC Copies (Parents/Guardians) - front & back in one file")
    house_pic_outside_1 = fields.Binary(string="House Picture (Outside 1)")
    house_pic_outside_2 = fields.Binary(string="House Picture (Outside 2)")
    house_pic_drawing_1 = fields.Binary(string="Drawing Room Picture 1")
    house_pic_drawing_2 = fields.Binary(string="Drawing Room Picture 2")

    # Extra (per important note)
    continuation_plan = fields.Text(
        string="If scholarship not granted, how will you continue your degree?"
    )

    # -----------------------------
    # Workflow
    # -----------------------------
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("submitted", "Submitted"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        default="draft",
        tracking=True,
        index=True,
    )
    ####################### company id ##########################
    

    company_id = fields.Many2one(
        'res.company', 
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        help='Company to which this scholarship belongs'
    )

    def get_white_logo_uri(self):
        """Returns the data URI for the white logo (CUST/MAJU/UBAS) based on company."""
        # Calculate path relative to this file: .../admission/need_based_scholarship/models/need_based_scholarship.py
        # up 3 levels to .../admission/
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Determine filename based on company name
        company_name = (self.company_id.name or "").upper()
        
        # LOGIC:
        # MAJU: Mohammad Ali Jinnah University
        # UBAS: Lahore University of Biological and Applied Sciences (or Baltistan)
        # CUST: Capital University of Science and Technology
        
        if any(k in company_name for k in ["MOHAMMAD ALI", "MAJU", "JINNAH"]):
            filename = "maju_white_logo.png"
        elif any(k in company_name for k in ["BIOLOGICAL", "UBAS", "BALTISTAN"]):
            filename = "ubas_white_logo.png"
        else:
            # Default to CUST (Capital University)
            filename = "cust_white_logo.png"

        img_path = os.path.join(base_path, 'odoocms_admission_portal', 'static', 'img', filename)
        
        if os.path.exists(img_path):
            with open(img_path, 'rb') as f:
                return 'data:image/png;base64,' + base64.b64encode(f.read()).decode('utf-8')
        return ''

    def action_download_attachments_zip(self):
        """Open the HTTP route that streams a ZIP of all related attachments."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_url',
            'url': f'/nbs/admin/download_zip/{self.id}',
            'target': 'self',
        }
        

    # -----------------------------
    # COMPUTES
    # -----------------------------
    @api.depends('applicant_id')
    def _compute_student_details(self):
        """Auto-sync student details from linked application"""
        for rec in self:
            if rec.applicant_id:
                app = rec.applicant_id
                rec.full_name = app.name or ''
                rec.registration_number = app.application_no or ''
                rec.contact_number = app.mobile or ''
                rec.email = app.email or ''
                rec.father_name = getattr(app, 'father_name', '') or ''
                rec.mother_name = getattr(app, 'mother_name', '') or ''
                
                # Degree program
                if getattr(app, 'prefered_program_id', False):
                    rec.degree_program = app.prefered_program_id.name or ''
                
                # Year/Session
                if getattr(app, 'academic_session_id', False):
                    rec.program_year = app.academic_session_id.name or ''
                elif getattr(app, 'term_id', False):
                    rec.program_year = app.term_id.name or ''

    @api.depends(
        "father_monthly_income",
        "mother_monthly_income",
        "other_income_ids.monthly_income",
        "income_rental", "income_rental_amount",
        "income_pension", "income_pension_amount",
        "income_zakat", "income_zakat_amount",
        "income_remittance", "income_remittance_amount",
        "income_self", "income_self_amount",
    )
    def _compute_total_income(self):
        for rec in self:
            total = (rec.father_monthly_income or 0.0) + (rec.mother_monthly_income or 0.0)
            total += sum(line.monthly_income or 0.0 for line in rec.other_income_ids)
            total += (rec.income_rental_amount or 0.0) if rec.income_rental else 0.0
            total += (rec.income_pension_amount or 0.0) if rec.income_pension else 0.0
            total += (rec.income_zakat_amount or 0.0) if rec.income_zakat else 0.0
            total += (rec.income_remittance_amount or 0.0) if rec.income_remittance else 0.0
            total += (rec.income_self_amount or 0.0) if rec.income_self else 0.0
            rec.total_monthly_income = total

    @api.depends(
        "has_sibling_education_expense",
        "sibling_expense_ids.monthly_expense",
        "is_living_on_rent", "monthly_rent",
        "gas_bill_amount", "elec_bill_amount", "water_bill_amount",
        "monthly_grocery",
        "has_medical_expense", "medical_expense_amount",
        "has_other_recurring", "other_recurring_amount",
    )
    def _compute_total_expense(self):
        for rec in self:
            total = 0.0
            if rec.has_sibling_education_expense:
                total += sum(line.monthly_expense or 0.0 for line in rec.sibling_expense_ids)
            total += (rec.monthly_rent or 0.0) if rec.is_living_on_rent else 0.0
            total += (rec.gas_bill_amount or 0.0)
            total += (rec.elec_bill_amount or 0.0)
            total += (rec.water_bill_amount or 0.0)
            total += (rec.monthly_grocery or 0.0)
            total += (rec.medical_expense_amount or 0.0) if rec.has_medical_expense else 0.0
            total += (rec.other_recurring_amount or 0.0) if rec.has_other_recurring else 0.0
            rec.total_monthly_expense = total

    @api.depends("total_monthly_income", "total_monthly_expense")
    def _compute_net_income(self):
        for rec in self:
            rec.net_monthly_income = (rec.total_monthly_income or 0.0) - (rec.total_monthly_expense or 0.0)

    @api.depends(
        "asset_house", "asset_house_value",
        "asset_land", "asset_land_value",
        "asset_business", "asset_business_value",
        "vehicle_ids.estimated_value",
        "has_loans", "loan_ids.outstanding_amount",
    )
    def _compute_net_assets(self):
        for rec in self:
            assets = 0.0
            if rec.asset_house:
                assets += rec.asset_house_value or 0.0
            if rec.asset_land:
                assets += rec.asset_land_value or 0.0
            if rec.asset_business:
                assets += rec.asset_business_value or 0.0
            assets += sum(v.estimated_value or 0.0 for v in rec.vehicle_ids)
            liabilities = sum(l.outstanding_amount or 0.0 for l in rec.loan_ids) if rec.has_loans else 0.0
            rec.net_assets = assets - liabilities

    # -----------------------------
    # ONCHANGES (clear irrelevant fields)
    # -----------------------------
    @api.onchange("father_occupation")
    def _onchange_father_occupation(self):
        if self.father_occupation in (False, "unemployed", "deceased"):
            self.father_employer_name = False
            self.father_designation = False
            self.father_salary_slips = False
        if self.father_occupation != "unemployed":
            self.father_unemployed_reason = False
        if self.father_occupation != "deceased":
            self.father_death_certificate = False

    @api.onchange("mother_occupation")
    def _onchange_mother_occupation(self):
        if self.mother_occupation in (False, "unemployed", "deceased"):
            self.mother_employer_name = False
            self.mother_designation = False
            self.mother_salary_slips = False
        if self.mother_occupation != "unemployed":
            self.mother_unemployed_reason = False
        if self.mother_occupation != "deceased":
            self.mother_death_certificate = False

    @api.onchange("is_living_on_rent")
    def _onchange_is_living_on_rent(self):
        if not self.is_living_on_rent:
            self.monthly_rent = 0.0
            self.rent_agreement = False

    @api.onchange("has_sibling_education_expense")
    def _onchange_has_sibling_education_expense(self):
        if not self.has_sibling_education_expense:
            self.sibling_expense_ids = [(5, 0, 0)]  # clear lines

    @api.onchange("has_medical_expense")
    def _onchange_has_medical_expense(self):
        if not self.has_medical_expense:
            self.medical_expense_nature = False
            self.medical_expense_amount = 0.0
            self.medical_expense_attachment = False

    @api.onchange("has_other_recurring")
    def _onchange_has_other_recurring(self):
        if not self.has_other_recurring:
            self.other_recurring_nature = False
            self.other_recurring_amount = 0.0
            self.other_recurring_attachment = False

    # -----------------------------
    # CONSTRAINTS
    # -----------------------------
    @api.constrains("sop")
    def _check_sop_length(self):
        for rec in self:
            if rec.sop:
                # limit to approx 350 words
                words = len(rec.sop.split())
                if words > 350:
                    raise ValidationError(_("Statement of Purpose must be 350 words or less (currently %s).") % words)

    @api.constrains("continuation_plan")
    def _check_continuation_plan_length(self):
        for rec in self:
            if rec.continuation_plan:
                # limit to approx 500 words
                words = len(rec.continuation_plan.split())
                if words > 500:
                    raise ValidationError(_("Continuation Plan must be 500 words or less (currently %s).") % words)

    # -----------------------------
    # ACTIONS
    # -----------------------------
    def action_submit(self):
        for rec in self:
            if not rec.declaration:
                raise ValidationError(_("Please accept the declaration before submitting."))
            # Enforce the "offer letter" gate
            # if not rec.has_offer_letter:
            #     raise ValidationError(_("This form is available only to students who have received an admission offer letter."))
            rec.state = "submitted"

    def action_set_under_review(self):
        self.write({"state": "under_review"})

    def action_approve(self):
        self.write({"state": "approved"})

    def action_reject(self):
        self.write({"state": "rejected"})


# =========================================================
# Child: Other Household Member (living/contributing)
# =========================================================
class NbsHouseholdMember(models.Model):
    _name = "nbs.household.member"
    _description = "Other Household Member (living/contributing)"
    _order = "id asc"

    nbs_id = fields.Many2one(
        "need.based.scholarship",
        string="Scholarship",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(required=True)
    relation = fields.Char(string="Relation to Applicant")

    occupation = fields.Selection(
        [
            ("employed", "Employed"),
            ("student", "Student"),
            ("self_employed", "Self-Employed / Business"),
            ("unemployed", "Un-employed"),
        ],
        string="Occupation",
    )

    # Employed
    employer_or_institute = fields.Char(string="Employer / Institute / Business Name")
    designation_or_type = fields.Char(string="Designation / Type of Business")
    salary_slips = fields.Binary(string="Salary Slips (PDF)")

    # Student
    student_institute = fields.Char(string="If Student: Institute/School/University")

    # Unemployed
    reason_unemployed = fields.Text(string="Reason of Unemployment")

    @api.onchange("occupation")
    def _onchange_occupation(self):
        if self.occupation != "employed":
            self.salary_slips = False
        if self.occupation != "student":
            self.student_institute = False
        if self.occupation != "unemployed":
            self.reason_unemployed = False


# =========================================================
# Child: Other Household Income (Add More)
# =========================================================
class NbsOtherIncome(models.Model):
    _name = "nbs.other.income"
    _description = "Other Household Income Contributor"
    _order = "id asc"

    nbs_id = fields.Many2one(
        "need.based.scholarship",
        string="Scholarship",
        required=True,
        ondelete="cascade",
        index=True,
    )
    name = fields.Char(required=True)
    relation = fields.Char()
    monthly_income = fields.Float(string="Monthly Income (PKR)")
    income_proof = fields.Binary(string="Proof of Income (PDF)")


# =========================================================
# Child: Sibling Education Expense (Add More)
# =========================================================
class NbsSiblingEducationExpense(models.Model):
    _name = "nbs.sibling.education.expense"
    _description = "Sibling Education Monthly Expense"
    _order = "id asc"

    nbs_id = fields.Many2one(
        "need.based.scholarship",
        string="Scholarship",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sibling_name = fields.Char(string="Sibling Name", required=True)
    monthly_expense = fields.Float(string="Monthly Education Expense (PKR)")
    fee_challan = fields.Binary(string="Fee Challan (PDF)")


# =========================================================
# Child: Vehicles (Add More) – info only (no attachments)
# =========================================================
class NbsVehicle(models.Model):
    _name = "nbs.vehicle"
    _description = "Vehicle (info only, no attachments)"
    _order = "id asc"

    nbs_id = fields.Many2one(
        "need.based.scholarship",
        string="Scholarship",
        required=True,
        ondelete="cascade",
        index=True,
    )
    make_model = fields.Char(string="Make & Model", required=True)
    estimated_value = fields.Float(string="Estimated Value (PKR)")


# =========================================================
# Child: Loans / Liabilities (Add More)
# =========================================================
class NbsLoan(models.Model):
    _name = "nbs.loan"
    _description = "Loans / Liabilities"
    _order = "id asc"

    nbs_id = fields.Many2one(
        "need.based.scholarship",
        string="Scholarship",
        required=True,
        ondelete="cascade",
        index=True,
    )
    purpose = fields.Char(string="Purpose of Loan")
    outstanding_amount = fields.Float(string="Outstanding Amount (PKR)")
    proof = fields.Binary(string="Supporting Document (PDF)")
