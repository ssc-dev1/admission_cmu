# -*- coding: utf-8 -*-
from odoo import http, _
from odoo.http import request
from werkzeug.datastructures import FileStorage
import base64
import json
import logging

_logger = logging.getLogger(__name__)


class NeedBasedScholarship(http.Controller):

    # ------------------------------------------------------------
    # Render the portal page
    # ------------------------------------------------------------
    @http.route('/nbs/application/', type='http', auth='user', csrf=False, website=True, methods=['GET'])
    def nbs_application(self, **kw):
        

        user = request.env.user

        application = request.env['odoocms.application'].sudo().search(
            [('application_no', '=', user.login)], limit=1
        )
        # if not application:
        #     return request.redirect('/web/')


        degree_name = ''
        if getattr(application, 'prefered_program_id', False):
            degree_name = application.prefered_program_id.name or ''
        

        # 4) Year / Session
        year_name = ''
        if getattr(application, 'academic_session_id', False):
            year_name = application.academic_session_id.name or ''
        elif getattr(application, 'term_id', False):
            year_name = application.term_id.name or ''



        nbs = request.env['need.based.scholarship'].sudo().search(
            [('applicant_id', '=', application.id)], limit=1
        )
        if not nbs:
            # No need to seed name/email now since they're related; but harmless if you keep them.
            nbs = request.env['need.based.scholarship'].sudo().create({
                'applicant_id': application.id,
            })

        # Always sync student details from application (in case application was updated)
        sync_vals = {
            'full_name': application.name or '',
            'registration_number': application.application_no or '',
            'degree_program': degree_name,
            'program_year': year_name,
            'contact_number': application.mobile or '',
            'email': application.email or '',
            'father_name': getattr(application, 'father_name', '') or '',
            'mother_name': getattr(application, 'mother_name', '') or '',
        }
        # Only update if values are different to avoid unnecessary writes
        current_vals = nbs.read(['full_name', 'registration_number', 'degree_program', 'program_year', 
                               'contact_number', 'email', 'father_name', 'mother_name'])[0]
        needs_update = False
        for field, new_val in sync_vals.items():
            if current_vals.get(field) != new_val:
                needs_update = True
                break
        if needs_update:
            nbs.sudo().write(sync_vals)

        # Prefill father/mother occupation from application status if empty
        try:
            def _map_status(v):
                if not v:
                    return False
                v = str(v).strip().lower()
                allowed = {'employed','self_employed','unemployed','deceased'}
                if v in allowed:
                    return v
                if v in {'self-employed','self employed', 'business', 'business_owner', 'business owner'}:
                    return 'self_employed'
                if v in {'un-employed','un employed'}:
                    return 'unemployed'
                return False

            write_vals = {}
            if not nbs.father_occupation:
                write_vals['father_occupation'] = _map_status(getattr(application, 'father_status', False))
            if not nbs.mother_occupation:
                write_vals['mother_occupation'] = _map_status(getattr(application, 'mother_status', False))
            if write_vals:
                nbs.sudo().write(write_vals)
        except Exception:
            _logger.exception('Failed to prefill father/mother occupation from application status')

        ctx = {
        'heading': 'Need Based Scholarship',
        'application': application,
        'nbs': nbs,
        'degree_name': degree_name,
        'year_name': year_name,
        'household_members': nbs.household_member_ids.sudo(),
        'other_incomes': nbs.other_income_ids.sudo(),
        'sibling_expenses': nbs.sibling_expense_ids.sudo(),
        'vehicles': nbs.vehicle_ids.sudo(),
        'loans': nbs.loan_ids.sudo(),
    }
        return request.render('need_based_scholarship.nbs_application', ctx)

    # ------------------------------------------------------------
    # Step 1: Personal
    # ------------------------------------------------------------
    @http.route('/nbs/save/personal', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_personal(self, **post):
        """
        We REMOVED fields that are read-only/related:
        - full_name, registration_number, degree_program, program_year, contact_number, email
        Only keep fields students actually input here (prev_scholarship + details).
        """
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            vals = {
                'prev_scholarship': post.get('prev_scholarship') or False,
                'prev_scholarship_details': post.get('prev_scholarship_details') or False,
            }
            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS personal save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save personal info'})

    # ------------------------------------------------------------
    # Step 2: Father
    # ------------------------------------------------------------
    @http.route('/nbs/save/father', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_father(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            files = request.httprequest.files
            app = nbs.applicant_id
            is_deceased_in_app = (getattr(app, 'father_status', '') or '').lower() == 'deceased'
            vals = {'father_name': post.get('father_name') or False}
            if is_deceased_in_app:
                vals.update({
                    'father_occupation': 'deceased',
                    'father_employer_name': False,
                    'father_designation': False,
                    'father_salary_slips': False,
                    'father_unemployed_reason': False,
                })
                # Enforce death certificate presence either newly uploaded or existing on record
                if not (files and 'father_death_certificate' in files) and not nbs.father_death_certificate:
                    return json.dumps({'status': 'error', 'msg': 'Please upload Father Death Certificate (PDF).'})
            else:
                vals.update({
                    'father_occupation': post.get('father_occupation') or False,
                    'father_employer_name': post.get('father_employer_name') or False,
                    'father_designation': post.get('father_designation') or False,
                    'father_unemployed_reason': post.get('father_unemployed_reason') or False,
                })
                occ = (vals['father_occupation'] or '').lower()
                if occ in ('employed', 'self_employed'):
                    if not vals['father_employer_name'] or not vals['father_designation']:
                        return json.dumps({'status': 'error', 'msg': 'Please provide employer/business and designation/type for Father.'})
                if occ == 'unemployed':
                    if not vals['father_unemployed_reason']:
                        return json.dumps({'status': 'error', 'msg': 'Please provide reason of unemployment for Father.'})
            if files and 'father_salary_slips' in files and isinstance(files['father_salary_slips'], FileStorage):
                if not is_deceased_in_app:
                    vals['father_salary_slips'] = base64.b64encode(files['father_salary_slips'].read())
            if files and 'father_death_certificate' in files and isinstance(files['father_death_certificate'], FileStorage):
                vals['father_death_certificate'] = base64.b64encode(files['father_death_certificate'].read())
            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS father save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save father info'})

    # ------------------------------------------------------------
    # Step 3: Mother
    # ------------------------------------------------------------
    @http.route('/nbs/save/mother', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_mother(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            files = request.httprequest.files
            app = nbs.applicant_id
            is_deceased_in_app = (getattr(app, 'mother_status', '') or '').lower() == 'deceased'
            vals = {'mother_name': post.get('mother_name') or False}
            if is_deceased_in_app:
                vals.update({
                    'mother_occupation': 'deceased',
                    'mother_employer_name': False,
                    'mother_designation': False,
                    'mother_salary_slips': False,
                    'mother_unemployed_reason': False,
                })
                if not (files and 'mother_death_certificate' in files) and not nbs.mother_death_certificate:
                    return json.dumps({'status': 'error', 'msg': 'Please upload Mother Death Certificate (PDF).'})
            else:
                vals.update({
                    'mother_occupation': post.get('mother_occupation') or False,
                    'mother_employer_name': post.get('mother_employer_name') or False,
                    'mother_designation': post.get('mother_designation') or False,
                    'mother_unemployed_reason': post.get('mother_unemployed_reason') or False,
                })
                occ = (vals['mother_occupation'] or '').lower()
                if occ in ('employed', 'self_employed'):
                    if not vals['mother_employer_name'] or not vals['mother_designation']:
                        return json.dumps({'status': 'error', 'msg': 'Please provide employer/business and designation/type for Mother.'})
                if occ == 'unemployed':
                    if not vals['mother_unemployed_reason']:
                        return json.dumps({'status': 'error', 'msg': 'Please provide reason of unemployment for Mother.'})
            if files and 'mother_salary_slips' in files and isinstance(files['mother_salary_slips'], FileStorage):
                if not is_deceased_in_app:
                    vals['mother_salary_slips'] = base64.b64encode(files['mother_salary_slips'].read())
            if files and 'mother_death_certificate' in files and isinstance(files['mother_death_certificate'], FileStorage):
                vals['mother_death_certificate'] = base64.b64encode(files['mother_death_certificate'].read())
            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS mother save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save mother info'})

    # ------------------------------------------------------------
    # Step 4a: Household Members (Add / Edit / Delete)
    # ------------------------------------------------------------
    @http.route('/nbs/household_member/add', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_add_household_member(self, **post):
        try:
            vals = {
                'nbs_id': int(post.get('nbs_id')),
                'name': post.get('name'),
                'relation': post.get('relation') or False,
                'occupation': post.get('occupation') or False,
                'employer_or_institute': post.get('employer_or_institute') or False,
                'designation_or_type': post.get('designation_or_type') or False,
                'student_institute': post.get('student_institute') or False,
                'reason_unemployed': post.get('reason_unemployed') or False,
            }
            files = request.httprequest.files
            if files and 'salary_slips' in files and isinstance(files['salary_slips'], FileStorage):
                vals['salary_slips'] = base64.b64encode(files['salary_slips'].read())

            rec = request.env['nbs.household.member'].sudo().create(vals)
            data = rec.read(['id','name','relation','occupation','employer_or_institute','designation_or_type'])[0]
            return json.dumps({'status': 'success', 'record': data})
        except Exception:
            _logger.exception("NBS add household member failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to add member'})

    @http.route('/nbs/household_member/edit', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_edit_household_member(self, **post):
        try:
            rec = request.env['nbs.household.member'].sudo().browse(int(post.get('id')))
            if not rec.exists():
                return json.dumps({'status':'error','msg':'Invalid record'})
            vals = {
                'name': post.get('name') or False,
                'relation': post.get('relation') or False,
                'occupation': post.get('occupation') or False,
                'employer_or_institute': post.get('employer_or_institute') or False,
                'designation_or_type': post.get('designation_or_type') or False,
            }
            rec.write(vals)
            data = rec.read(['id','name','relation','occupation','employer_or_institute','designation_or_type'])[0]
            return json.dumps({'status':'success','record': data})
        except Exception:
            _logger.exception("NBS edit household member failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to update member'})

    @http.route('/nbs/household_member/delete', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_delete_household_member(self, **post):
        try:
            rec = request.env['nbs.household.member'].sudo().browse(int(post.get('id')))
            if rec.exists():
                rec.unlink()
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS delete household member failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to delete member'})

    # ------------------------------------------------------------
    # Step 4b: Other Income Contributors (Add / Edit / Delete)
    # ------------------------------------------------------------
    @http.route('/nbs/other_income/add', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_add_other_income(self, **post):
        try:
            vals = {
                'nbs_id': int(post.get('nbs_id')),
                'name': post.get('name'),
                'relation': post.get('relation') or False,
                'monthly_income': float(post.get('monthly_income') or 0.0),
            }
            if not vals['name']:
                return json.dumps({'status': 'error', 'msg': 'Please provide a name.'})
            if vals['monthly_income'] <= 0.0:
                return json.dumps({'status': 'error', 'msg': 'Monthly income must be greater than zero.'})
            files = request.httprequest.files
            if files and 'income_proof' in files and isinstance(files['income_proof'], FileStorage):
                vals['income_proof'] = base64.b64encode(files['income_proof'].read())

            rec = request.env['nbs.other.income'].sudo().create(vals)
            data = rec.read(['id','name','relation','monthly_income'])[0]
            return json.dumps({'status': 'success', 'record': data})
        except Exception:
            _logger.exception("NBS add other income failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to add income'})

    @http.route('/nbs/other_income/edit', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_edit_other_income(self, **post):
        try:
            rec = request.env['nbs.other.income'].sudo().browse(int(post.get('id')))
            if not rec.exists():
                return json.dumps({'status':'error','msg':'Invalid record'})
            vals = {
                'name': post.get('name') or False,
                'relation': post.get('relation') or False,
                'monthly_income': float(post.get('monthly_income') or 0.0),
            }
            if not vals['name']:
                return json.dumps({'status': 'error', 'msg': 'Please provide a name.'})
            if vals['monthly_income'] <= 0.0:
                return json.dumps({'status': 'error', 'msg': 'Monthly income must be greater than zero.'})
            rec.write(vals)
            data = rec.read(['id','name','relation','monthly_income'])[0]
            return json.dumps({'status':'success','record': data})
        except Exception:
            _logger.exception("NBS edit other income failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to update income'})

    @http.route('/nbs/other_income/delete', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_delete_other_income(self, **post):
        try:
            rec = request.env['nbs.other.income'].sudo().browse(int(post.get('id')))
            if rec.exists():
                rec.unlink()
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS delete other income failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to delete income'})

    # ------------------------------------------------------------
    # Step 5: Household Income toggles/amounts
    # ------------------------------------------------------------
    @http.route('/nbs/save/income', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_income(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            vals = {
                'father_monthly_income': float(post.get('father_monthly_income') or 0.0),
                'mother_monthly_income': float(post.get('mother_monthly_income') or 0.0),
                'income_rental': post.get('income_rental') == 'on',
                'income_rental_amount': float(post.get('income_rental_amount') or 0.0),
                'income_pension': post.get('income_pension') == 'on',
                'income_pension_amount': float(post.get('income_pension_amount') or 0.0),
                'income_zakat': post.get('income_zakat') == 'on',
                'income_zakat_amount': float(post.get('income_zakat_amount') or 0.0),
                'income_remittance': post.get('income_remittance') == 'on',
                'income_remittance_amount': float(post.get('income_remittance_amount') or 0.0),
                'income_self': post.get('income_self') == 'on',
                'income_self_amount': float(post.get('income_self_amount') or 0.0),
            }
            # Require positive amounts when toggled on
            checks = [
                ('income_rental','income_rental_amount','Rental income'),
                ('income_pension','income_pension_amount','Pension'),
                ('income_zakat','income_zakat_amount','Zakat'),
                ('income_remittance','income_remittance_amount','Remittances'),
                ('income_self','income_self_amount','Self income'),
            ]
            for chk, amt, label in checks:
                if vals[chk] and vals[amt] <= 0.0:
                    return json.dumps({'status':'error','msg': f'Please provide a valid amount for {label}.'})
            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS income save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save income'})

    # ------------------------------------------------------------
    # Step 6: Expenses (+ sibling education add/edit/delete)
    # ------------------------------------------------------------
    @http.route('/nbs/save/expenses', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_expenses(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})

            files = request.httprequest.files
            vals = {
                'has_sibling_education_expense': post.get('has_sibling_education_expense') == 'on',
                'is_living_on_rent': post.get('is_living_on_rent') == 'on',
                'monthly_rent': float(post.get('monthly_rent') or 0.0),
                'gas_bill_amount': float(post.get('gas_bill_amount') or 0.0),
                'elec_bill_amount': float(post.get('elec_bill_amount') or 0.0),
                'water_bill_amount': float(post.get('water_bill_amount') or 0.0),
                'monthly_grocery': float(post.get('monthly_grocery') or 0.0),
                'has_medical_expense': post.get('has_medical_expense') == 'on',
                'medical_expense_nature': post.get('medical_expense_nature') or False,
                'medical_expense_amount': float(post.get('medical_expense_amount') or 0.0),
                'has_other_recurring': post.get('has_other_recurring') == 'on',
                'other_recurring_nature': post.get('other_recurring_nature') or False,
                'other_recurring_amount': float(post.get('other_recurring_amount') or 0.0),
            }
            # Validations for toggled groups
            if vals['is_living_on_rent']:
                if vals['monthly_rent'] <= 0.0:
                    return json.dumps({'status':'error','msg':'Please provide a valid Monthly Rent.'})
                if not (files and 'rent_agreement' in files) and not nbs.rent_agreement:
                    return json.dumps({'status':'error','msg':'Please upload Rental Agreement (PDF).'})
            if vals['has_medical_expense']:
                if not vals['medical_expense_nature'] or vals['medical_expense_amount'] <= 0.0:
                    return json.dumps({'status':'error','msg':'Please provide Medical Nature and a valid Monthly Amount.'})
                if not (files and 'medical_expense_attachment' in files) and not nbs.medical_expense_attachment:
                    return json.dumps({'status':'error','msg':'Please upload Medical Evidence (PDF).'})
            if vals['has_other_recurring']:
                if not vals['other_recurring_nature'] or vals['other_recurring_amount'] <= 0.0:
                    return json.dumps({'status':'error','msg':'Please provide Other Recurring Nature and a valid Monthly Amount.'})
                if not (files and 'other_recurring_attachment' in files) and not nbs.other_recurring_attachment:
                    return json.dumps({'status':'error','msg':'Please upload Other Recurring Evidence (PDF).'})
            if files and 'rent_agreement' in files and isinstance(files['rent_agreement'], FileStorage):
                vals['rent_agreement'] = base64.b64encode(files['rent_agreement'].read())
            if files and 'gas_bill_attachment' in files and isinstance(files['gas_bill_attachment'], FileStorage):
                vals['gas_bill_attachment'] = base64.b64encode(files['gas_bill_attachment'].read())
            if files and 'elec_bill_attachment' in files and isinstance(files['elec_bill_attachment'], FileStorage):
                vals['elec_bill_attachment'] = base64.b64encode(files['elec_bill_attachment'].read())
            if files and 'water_bill_attachment' in files and isinstance(files['water_bill_attachment'], FileStorage):
                vals['water_bill_attachment'] = base64.b64encode(files['water_bill_attachment'].read())
            if files and 'medical_expense_attachment' in files and isinstance(files['medical_expense_attachment'], FileStorage):
                vals['medical_expense_attachment'] = base64.b64encode(files['medical_expense_attachment'].read())
            if files and 'other_recurring_attachment' in files and isinstance(files['other_recurring_attachment'], FileStorage):
                vals['other_recurring_attachment'] = base64.b64encode(files['other_recurring_attachment'].read())

            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS expenses save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save expenses'})

    @http.route('/nbs/sibling_expense/add', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_add_sibling_expense(self, **post):
        try:
            amount = float(post.get('monthly_expense') or 0.0)
            if amount <= 0.0:
                return json.dumps({'status':'error','msg':'Monthly Education Expense must be greater than zero.'})
            files = request.httprequest.files
            vals = {
                'nbs_id': int(post.get('nbs_id')),
                'sibling_name': post.get('sibling_name'),
                'monthly_expense': amount,
            }
            if files and 'fee_challan' in files and isinstance(files['fee_challan'], FileStorage):
                vals['fee_challan'] = base64.b64encode(files['fee_challan'].read())
            rec = request.env['nbs.sibling.education.expense'].sudo().create(vals)
            data = rec.read(['id','sibling_name','monthly_expense'])[0]
            return json.dumps({'status': 'success', 'record': data})
        except Exception:
            _logger.exception("NBS add sibling expense failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to add sibling expense'})

    @http.route('/nbs/sibling_expense/edit', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_edit_sibling_expense(self, **post):
        try:
            rec = request.env['nbs.sibling.education.expense'].sudo().browse(int(post.get('id')))
            if not rec.exists():
                return json.dumps({'status':'error','msg':'Invalid record'})
            vals = {
                'sibling_name': post.get('sibling_name') or False,
                'monthly_expense': float(post.get('monthly_expense') or 0.0),
            }
            if vals['monthly_expense'] <= 0.0:
                return json.dumps({'status':'error','msg':'Monthly Education Expense must be greater than zero.'})
            rec.write(vals)
            data = rec.read(['id','sibling_name','monthly_expense'])[0]
            return json.dumps({'status':'success','record': data})
        except Exception:
            _logger.exception("NBS edit sibling expense failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to update sibling expense'})

    @http.route('/nbs/sibling_expense/delete', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_delete_sibling_expense(self, **post):
        try:
            rec = request.env['nbs.sibling.education.expense'].sudo().browse(int(post.get('id')))
            if rec.exists():
                rec.unlink()
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS delete sibling expense failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to delete sibling expense'})

    # ------------------------------------------------------------
    # Step 7: Assets (info only) + Vehicles add/edit/delete
    # ------------------------------------------------------------
    @http.route('/nbs/save/assets', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_assets(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            vals = {
                'asset_house': post.get('asset_house') == 'on',
                'asset_house_area': post.get('asset_house_area') or False,
                'asset_house_value': float(post.get('asset_house_value') or 0.0),
                'asset_land': post.get('asset_land') == 'on',
                'asset_land_area': post.get('asset_land_area') or False,
                'asset_land_value': float(post.get('asset_land_value') or 0.0),
                'asset_business': post.get('asset_business') == 'on',
                'asset_business_value': float(post.get('asset_business_value') or 0.0),
            }
            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS assets save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save assets'})

    @http.route('/nbs/vehicle/add', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_add_vehicle(self, **post):
        try:
            rec = request.env['nbs.vehicle'].sudo().create({
                'nbs_id': int(post.get('nbs_id')),
                'make_model': post.get('make_model'),
                'estimated_value': float(post.get('estimated_value') or 0.0),
            })
            data = rec.read(['id','make_model','estimated_value'])[0]
            return json.dumps({'status': 'success', 'record': data})
        except Exception:
            _logger.exception("NBS add vehicle failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to add vehicle'})

    @http.route('/nbs/vehicle/edit', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_edit_vehicle(self, **post):
        try:
            rec = request.env['nbs.vehicle'].sudo().browse(int(post.get('id')))
            if not rec.exists():
                return json.dumps({'status':'error','msg':'Invalid record'})
            vals = {
                'make_model': post.get('make_model') or False,
                'estimated_value': float(post.get('estimated_value') or 0.0),
            }
            rec.write(vals)
            data = rec.read(['id','make_model','estimated_value'])[0]
            return json.dumps({'status':'success','record': data})
        except Exception:
            _logger.exception("NBS edit vehicle failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to update vehicle'})

    @http.route('/nbs/vehicle/delete', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_delete_vehicle(self, **post):
        try:
            rec = request.env['nbs.vehicle'].sudo().browse(int(post.get('id')))
            if rec.exists():
                rec.unlink()
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS delete vehicle failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to delete vehicle'})

    # ------------------------------------------------------------
    # Step 8: Loans / Liabilities toggle + add/edit/delete
    # ------------------------------------------------------------
    @http.route('/nbs/save/loans', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_loans_toggle(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            nbs.write({'has_loans': post.get('has_loans') == 'on'})
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS loans toggle save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save loans toggle'})

    @http.route('/nbs/loan/add', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_add_loan(self, **post):
        try:
            files = request.httprequest.files
            amount = float(post.get('outstanding_amount') or 0.0)
            if amount <= 0.0:
                return json.dumps({'status':'error','msg':'Outstanding amount must be greater than zero.'})
            rec = request.env['nbs.loan'].sudo().create({
                'nbs_id': int(post.get('nbs_id')),
                'purpose': post.get('purpose'),
                'outstanding_amount': amount,
                'proof': base64.b64encode(files['proof'].read()) if files and 'proof' in files else False,
            })
            data = rec.read(['id','purpose','outstanding_amount'])[0]
            return json.dumps({'status': 'success', 'record': data})
        except Exception:
            _logger.exception("NBS add loan failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to add loan'})

    @http.route('/nbs/loan/edit', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_edit_loan(self, **post):
        try:
            rec = request.env['nbs.loan'].sudo().browse(int(post.get('id')))
            if not rec.exists():
                return json.dumps({'status':'error','msg':'Invalid record'})
            vals = {
                'purpose': post.get('purpose') or False,
                'outstanding_amount': float(post.get('outstanding_amount') or 0.0),
            }
            if vals['outstanding_amount'] <= 0.0:
                return json.dumps({'status':'error','msg':'Outstanding amount must be greater than zero.'})
            rec.write(vals)
            data = rec.read(['id','purpose','outstanding_amount'])[0]
            return json.dumps({'status':'success','record': data})
        except Exception:
            _logger.exception("NBS edit loan failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to update loan'})

    @http.route('/nbs/loan/delete', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_delete_loan(self, **post):
        try:
            rec = request.env['nbs.loan'].sudo().browse(int(post.get('id')))
            if rec.exists():
                rec.unlink()
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS delete loan failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to delete loan'})

    # ------------------------------------------------------------
    # Step 9: Statement, Declaration, Attachments
    # ------------------------------------------------------------
    @http.route('/nbs/save/statement', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_save_statement(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})

            files = request.httprequest.files
            vals = {
                'sop': post.get('sop') or False,
                'declaration': post.get('declaration') == 'on',
                'continuation_plan': post.get('continuation_plan') or False,
            }
            if files and 'bank_statements_6m' in files and isinstance(files['bank_statements_6m'], FileStorage):
                vals['bank_statements_6m'] = base64.b64encode(files['bank_statements_6m'].read())
            if files and 'cnic_parents' in files and isinstance(files['cnic_parents'], FileStorage):
                vals['cnic_parents'] = base64.b64encode(files['cnic_parents'].read())
            for fkey in ['house_pic_outside_1', 'house_pic_outside_2', 'house_pic_drawing_1', 'house_pic_drawing_2']:
                if files and fkey in files and isinstance(files[fkey], FileStorage):
                    vals[fkey] = base64.b64encode(files[fkey].read())

            nbs.write(vals)
            return json.dumps({'status': 'success'})
        except Exception:
            _logger.exception("NBS statement save failed")
            return json.dumps({'status': 'error', 'msg': 'Failed to save statement'})

    # ------------------------------------------------------------
    # Final Submit (state change)
    # ------------------------------------------------------------
    @http.route('/nbs/submit', type='http', auth='user', website=True, methods=['POST'], csrf=False)
    def nbs_submit(self, **post):
        try:
            nbs = request.env['need.based.scholarship'].sudo().browse(int(post.get('nbs_id')))
            if not nbs.exists():
                return json.dumps({'status': 'error', 'msg': 'Invalid NBS reference'})
            nbs.action_submit()
            return json.dumps({'status': 'success', 'message': 'Submitted'})
        except Exception as e:
            _logger.exception("NBS submit failed")
            return json.dumps({'status': 'error', 'msg': str(e)})
