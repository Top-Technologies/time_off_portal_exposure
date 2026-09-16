# -*- coding: utf-8 -*-
import base64
from datetime import datetime, date
from werkzeug.exceptions import Forbidden, NotFound

from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from ..models.ethiopian_date_utils import ethiopian_to_gregorian, format_ethiopian_date


class TimeOffCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        user = request.env.user
        employee = user.get_portal_employee()

        if employee:
            values['time_off_count'] = request.env['hr.leave'].sudo().search_count([
                ('employee_id', '=', employee.id)
            ])

            subordinates = employee.get_subordinate_employees()
            if subordinates:
                values['time_off_to_approve_count'] = request.env['hr.leave'].sudo().search_count([
                    ('employee_id', 'in', subordinates.ids),
                    ('state', 'in', ['confirm', 'validate1']),
                    ('manager_approved', '=', False)
                ])
            else:
                values['time_off_to_approve_count'] = 0
        else:
            values['time_off_count'] = 0
            values['time_off_to_approve_count'] = 0

        return values

    def _get_current_employee(self):
        """ Helper to retrieve current user's linked employee record """
        return request.env.user.get_portal_employee()

    def _check_leave_access(self, leave_id, mode='read'):
        """ Security validation verifying user rights over a leave record """
        user = request.env.user
        employee = self._get_current_employee()
        leave = request.env['hr.leave'].sudo().browse(leave_id)

        if not leave.exists():
            raise NotFound()

        # Internal HR users with Officer access have full permissions
        if user.has_group('hr_holidays.group_hr_holidays_user'):
            return leave

        # Check if user is the employee requesting the leave
        is_owner = employee and leave.employee_id.id == employee.id
        
        # Check if user is the manager or time off approver
        is_manager = employee and (
            leave.employee_id.parent_id.id == employee.id or
            leave.employee_id.leave_manager_id.id == user.id
        )

        # Check if user is the assigned Time Off Officer
        is_officer = leave.employee_id.time_off_officer_id.id == user.id

        if mode == 'read':
            if not (is_owner or is_manager or is_officer):
                raise Forbidden(_("You do not have access to view this time off request."))
        elif mode == 'approve':
            if not (is_manager or is_officer):
                raise Forbidden(_("You do not have permission to approve/refuse this request."))
        elif mode == 'cancel':
            if not is_owner:
                raise Forbidden(_("You can only cancel your own requests."))

        return leave

    # -------------------------------------------------------------------------
    # My Time Off - Dashboard & Requests
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off', '/my/time_off/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_time_off(self, page=1, sortby=None, filterby=None, **kw):
        employee = self._get_current_employee()
        if not employee:
            return request.render('time_off_portal_exposure.portal_no_employee_linked', {
                'page_name': 'time_off_no_employee'
            })

        Leave = request.env['hr.leave'].sudo()

        # Sorting definitions
        sortings = {
            'date_desc': {'label': _('Date (Newest)'), 'order': 'request_date_from desc, id desc'},
            'date_asc': {'label': _('Date (Oldest)'), 'order': 'request_date_from asc, id asc'},
            'type': {'label': _('Leave Type'), 'order': 'holiday_status_id asc'},
            'state': {'label': _('Status'), 'order': 'state asc'},
        }
        if not sortby or sortby not in sortings:
            sortby = 'date_desc'
        order = sortings[sortby]['order']

        # Filter definitions
        filters = {
            'all': {'label': _('All Requests'), 'domain': []},
            'pending': {'label': _('To Approve'), 'domain': [('state', 'in', ['confirm', 'validate1'])]},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'validate')]},
            'refused': {'label': _('Refused'), 'domain': [('state', '=', 'refuse')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancel')]},
        }
        if not filterby or filterby not in filters:
            filterby = 'all'

        base_domain = [('employee_id', '=', employee.id)]
        domain = expression.AND([base_domain, filters[filterby]['domain']])

        # Counts
        total_leaves = Leave.search_count(domain)
        pager = portal_pager(
            url="/my/time_off",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total_leaves,
            page=page,
            step=10
        )

        leaves = Leave.search(domain, order=order, limit=10, offset=pager['offset'])

        # Compute Balances & KPIs
        balances = employee.get_portal_leave_balances()
        total_remaining = sum(b['remaining'] for b in balances if b.get('request_unit') != 'hour')
        pending_count = Leave.search_count([
            ('employee_id', '=', employee.id),
            ('state', 'in', ['confirm', 'validate1'])
        ])
        current_year = date.today().year
        approved_this_year = Leave.search_count([
            ('employee_id', '=', employee.id),
            ('state', '=', 'validate'),
            ('request_date_from', '>=', f'{current_year}-01-01'),
            ('request_date_from', '<=', f'{current_year}-12-31'),
        ])

        values = {
            'page_name': 'time_off_dashboard',
            'employee': employee,
            'leaves': leaves,
            'balances': balances,
            'total_remaining': round(total_remaining, 1),
            'pending_count': pending_count,
            'approved_this_year': approved_this_year,
            'pager': pager,
            'sortby': sortby,
            'sortings': sortings,
            'filterby': filterby,
            'filters': filters,
            'default_url': '/my/time_off',
            'is_manager': employee.is_portal_manager,
        }
        return request.render('time_off_portal_exposure.portal_my_time_off_dashboard', values)

    # -------------------------------------------------------------------------
    # Submit New Time Off Request
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off/new'], type='http', auth='user', methods=['GET', 'POST'], website=True, csrf=True)
    def portal_my_time_off_new(self, **post):
        employee = self._get_current_employee()
        if not employee:
            return request.render('time_off_portal_exposure.portal_no_employee_linked', {
                'page_name': 'time_off_no_employee'
            })

        subordinates = employee.get_subordinate_employees()
        target_id_str = post.get('target_employee_id') or request.params.get('target_id')
        target_employee = employee
        is_subordinate_request = False

        if target_id_str:
            try:
                t_id = int(target_id_str)
                if subordinates and t_id in subordinates.ids:
                    target_employee = request.env['hr.employee'].sudo().browse(t_id)
                    is_subordinate_request = True
            except (ValueError, TypeError):
                target_employee = employee

        LeaveType = request.env['hr.leave.type'].sudo()
        leave_types = LeaveType.search([
            ('active', '=', True),
            ('is_portal_visible', '=', True)
        ])

        errors = []
        if request.httprequest.method == 'POST':
            holiday_status_id = post.get('holiday_status_id')
            date_from_str = post.get('date_from')
            date_to_str = post.get('date_to')
            request_unit_half = post.get('request_unit_half') == 'on'
            request_date_from_period = post.get('request_date_from_period', 'am')
            request_unit_hours = post.get('request_unit_hours') == 'on'
            request_hour_from = post.get('request_hour_from')
            request_hour_to = post.get('request_hour_to')
            name = post.get('name', '').strip()
            attachment = request.httprequest.files.get('attachment')

            # Validation
            if not holiday_status_id:
                errors.append(_("Please select a valid Time Off Type."))

            selected_type = LeaveType.browse(int(holiday_status_id)) if holiday_status_id else False

            # If Gregorian date input wasn't populated but Ethiopian was submitted, convert it
            if not date_from_str and post.get('eth_year_from') and post.get('eth_month_from') and post.get('eth_day_from'):
                try:
                    g_dt = ethiopian_to_gregorian(post['eth_year_from'], post['eth_month_from'], post['eth_day_from'])
                    date_from_str = g_dt.strftime('%Y-%m-%d')
                except Exception:
                    pass

            if not date_to_str and post.get('eth_year_to') and post.get('eth_month_to') and post.get('eth_day_to'):
                try:
                    g_dt = ethiopian_to_gregorian(post['eth_year_to'], post['eth_month_to'], post['eth_day_to'])
                    date_to_str = g_dt.strftime('%Y-%m-%d')
                except Exception:
                    pass

            if not date_from_str:
                errors.append(_("Please select a Start Date."))
            if not date_to_str and not request_unit_half:
                date_to_str = date_from_str

            if request_unit_half:
                date_to_str = date_from_str

            if not errors:
                try:
                    date_from = fields.Date.from_string(date_from_str)
                    date_to = fields.Date.from_string(date_to_str) if date_to_str else date_from

                    if date_to < date_from:
                        errors.append(_("End Date cannot be earlier than Start Date."))
                except Exception as e:
                    errors.append(_("Invalid date format."))

            # Allocation Balance Pre-Check
            if selected_type and not errors:
                requires_alloc = getattr(selected_type, 'requires_allocation', 'no') == 'yes'
                if requires_alloc:
                    balances = target_employee.get_portal_leave_balances()
                    b_match = next((b for b in balances if b['id'] == selected_type.id), None)
                    available_balance = b_match['virtual_remaining'] if b_match else 0.0
                    unit = 'hours' if selected_type.request_unit == 'hour' else 'days'

                    if available_balance <= 0:
                        errors.append(_("You do not have any allocated %(unit)s remaining for '%(type)s' (Available balance: 0 %(unit)s). Please request an allocation first.") % {
                            'unit': unit,
                            'type': selected_type.name
                        })
                    else:
                        if request_unit_half:
                            req_duration = 0.5
                        elif request_unit_hours and request_hour_from and request_hour_to:
                            try:
                                req_duration = float(request_hour_to) - float(request_hour_from)
                            except (ValueError, TypeError):
                                req_duration = 1.0
                        else:
                            try:
                                d_from = fields.Date.from_string(date_from_str)
                                d_to = fields.Date.from_string(date_to_str) if date_to_str else d_from
                                req_duration = max((d_to - d_from).days + 1, 1)
                            except Exception:
                                req_duration = 1.0

                        if req_duration > available_balance:
                            errors.append(_("The requested duration (%(req)s %(unit)s) exceeds the remaining allocated balance (%(avail)s %(unit)s) for '%(type)s'.") % {
                                'req': req_duration,
                                'avail': available_balance,
                                'unit': unit,
                                'type': selected_type.name
                            })

            if not errors:
                try:
                    leave_vals = {
                        'employee_id': target_employee.id,
                        'holiday_status_id': selected_type.id,
                        'request_date_from': date_from_str,
                        'request_date_to': date_to_str,
                        'name': name or _("Time off request submitted via portal"),
                        'is_portal_submitted': True,
                    }

                    if request_unit_half:
                        leave_vals['request_unit_half'] = True
                        leave_vals['request_date_from_period'] = request_date_from_period
                    elif request_unit_hours and request_hour_from and request_hour_to:
                        leave_vals['request_unit_hours'] = True
                        leave_vals['request_hour_from'] = request_hour_from
                        leave_vals['request_hour_to'] = request_hour_to

                    # Check manager status and routing
                    has_direct_manager = bool(target_employee.parent_id or target_employee.leave_manager_id)
                    val_type = getattr(selected_type, 'leave_validation_type', 'both')

                    if is_subordinate_request or not has_direct_manager:
                        # Manager submitted on behalf of subordinate OR requester has no assigned manager
                        leave_vals['manager_approved'] = True
                        leave_vals['manager_approved_by_id'] = request.env.user.id
                        leave_vals['manager_approval_date'] = fields.Datetime.now()
                        if is_subordinate_request:
                            leave_vals['first_approver_id'] = employee.id

                    # Create the leave record as sudo
                    leave = request.env['hr.leave'].sudo().create(leave_vals)

                    # Handle optional attachment
                    if attachment and attachment.filename:
                        file_content = attachment.read()
                        attachment_record = request.env['ir.attachment'].sudo().create({
                            'name': attachment.filename,
                            'datas': base64.b64encode(file_content),
                            'res_model': 'hr.leave',
                            'res_id': leave.id,
                            'type': 'binary',
                        })
                        if hasattr(leave, 'supported_attachment_ids'):
                            leave.sudo().write({'supported_attachment_ids': [(4, attachment_record.id)]})

                    # Handle Post-Creation Workflow & Routing
                    if is_subordinate_request:
                        leave.sudo().message_post(
                            body=_("📋 <b>Submitted &amp; Pre-Approved by Manager:</b> %s on behalf of %s.<br/>Dispatched directly to HR Officer for review.") % (
                                request.env.user.name,
                                target_employee.name
                            ),
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
                        if val_type in ['both', 'hr']:
                            try:
                                leave.sudo().write({'state': 'validate1'})
                            except Exception:
                                pass
                            leave._notify_time_off_officer()
                        else:
                            try:
                                leave.sudo().action_validate()
                            except Exception:
                                leave.sudo().write({'state': 'validate'})

                    elif not has_direct_manager:
                        leave.sudo().message_post(
                            body=_("ℹ️ <b>Direct Routing:</b> %s has no manager assigned.<br/>Request dispatched directly to HR Officer for review.") % (
                                target_employee.name
                            ),
                            message_type='comment',
                            subtype_xmlid='mail.mt_comment',
                        )
                        if val_type in ['both', 'hr']:
                            try:
                                leave.sudo().write({'state': 'validate1'})
                            except Exception:
                                pass
                            leave._notify_time_off_officer()
                        else:
                            try:
                                leave.sudo().action_validate()
                            except Exception:
                                leave.sudo().write({'state': 'validate'})

                    else:
                        # Standard workflow: notify direct manager
                        leave._notify_manager_on_submission()

                    return request.redirect(f'/my/time_off/{leave.id}?submitted=1')

                except (UserError, ValidationError) as e:
                    request.env.cr.rollback()
                    errors.append(str(e))
                except Exception as e:
                    request.env.cr.rollback()
                    errors.append(_("An unexpected error occurred: %s") % str(e))

        balances = target_employee.get_portal_leave_balances()
        balances_by_type = {b['id']: b for b in balances}

        values = {
            'page_name': 'time_off_new',
            'employee': employee,
            'target_employee': target_employee,
            'subordinates': subordinates,
            'selected_target_id': str(target_employee.id),
            'is_subordinate_request': is_subordinate_request,
            'leave_types': leave_types,
            'balances': balances,
            'balances_by_type': balances_by_type,
            'errors': errors,
            'post': post,
            'today': fields.Date.today(),
        }
        return request.render('time_off_portal_exposure.portal_my_time_off_new', values)

    # -------------------------------------------------------------------------
    # Single Time Off Details View & Chatter
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off/<int:leave_id>'], type='http', auth='user', website=True)
    def portal_my_time_off_detail(self, leave_id, submitted=None, **kw):
        leave = self._check_leave_access(leave_id, mode='read')
        employee = self._get_current_employee()

        is_owner = employee and leave.employee_id.id == employee.id
        is_manager = employee and (
            leave.employee_id.parent_id.id == employee.id or
            leave.employee_id.leave_manager_id.id == request.env.user.id
        )
        is_officer = leave.employee_id.time_off_officer_id.id == request.env.user.id

        values = {
            'page_name': 'time_off_detail',
            'leave': leave,
            'employee': employee,
            'is_owner': is_owner,
            'is_manager': is_manager,
            'is_officer': is_officer,
            'submitted': bool(submitted),
            'token': kw.get('token'),
            'object': leave,
        }
        return request.render('time_off_portal_exposure.portal_my_time_off_detail', values)

    # -------------------------------------------------------------------------
    # Cancel Time Off Request (by Employee)
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off/<int:leave_id>/cancel'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_time_off_cancel(self, leave_id, **kw):
        leave = self._check_leave_access(leave_id, mode='cancel')
        try:
            leave.action_portal_cancel()
        except Exception as e:
            return request.redirect(f'/my/time_off/{leave_id}?error={str(e)}')
        return request.redirect(f'/my/time_off/{leave_id}')

    # -------------------------------------------------------------------------
    # Portal Manager Approvals Dashboard
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off/to_approve', '/my/time_off/to_approve/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_time_off_to_approve(self, page=1, filterby=None, sortby=None, **kw):
        employee = self._get_current_employee()
        if not employee:
            return request.render('time_off_portal_exposure.portal_no_employee_linked', {
                'page_name': 'time_off_no_employee'
            })

        subordinates = employee.get_subordinate_employees()
        if not subordinates:
            return request.render('time_off_portal_exposure.portal_not_a_manager', {
                'page_name': 'time_off_not_manager'
            })

        Leave = request.env['hr.leave'].sudo()

        sortings = {
            'date_desc': {'label': _('Date (Newest)'), 'order': 'request_date_from desc, id desc'},
            'date_asc': {'label': _('Date (Oldest)'), 'order': 'request_date_from asc, id asc'},
            'employee': {'label': _('Employee Name'), 'order': 'employee_id asc'},
        }
        if not sortby or sortby not in sortings:
            sortby = 'date_desc'
        order = sortings[sortby]['order']

        filters = {
            'pending': {'label': _('Pending My Approval'), 'domain': [('state', 'in', ['confirm', 'validate1']), ('manager_approved', '=', False)]},
            'all': {'label': _('All Team Requests'), 'domain': []},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'validate')]},
            'refused': {'label': _('Refused'), 'domain': [('state', '=', 'refuse')]},
        }
        if not filterby or filterby not in filters:
            filterby = 'pending'

        base_domain = [('employee_id', 'in', subordinates.ids)]
        domain = expression.AND([base_domain, filters[filterby]['domain']])

        total_requests = Leave.search_count(domain)
        pager = portal_pager(
            url="/my/time_off/to_approve",
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total_requests,
            page=page,
            step=10
        )

        leaves = Leave.search(domain, order=order, limit=10, offset=pager['offset'])

        pending_approval_count = Leave.search_count([
            ('employee_id', 'in', subordinates.ids),
            ('state', 'in', ['confirm', 'validate1']),
            ('manager_approved', '=', False)
        ])

        values = {
            'page_name': 'time_off_to_approve',
            'employee': employee,
            'subordinates': subordinates,
            'leaves': leaves,
            'pending_approval_count': pending_approval_count,
            'pager': pager,
            'sortby': sortby,
            'sortings': sortings,
            'filterby': filterby,
            'filters': filters,
            'default_url': '/my/time_off/to_approve',
        }
        return request.render('time_off_portal_exposure.portal_my_time_off_to_approve', values)

    # -------------------------------------------------------------------------
    # Manager Action: Approve / Refuse
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off/<int:leave_id>/approve'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_time_off_approve(self, leave_id, redirect_to=None, **kw):
        leave = self._check_leave_access(leave_id, mode='approve')
        try:
            leave.action_portal_manager_approve()
        except Exception as e:
            return request.redirect(f'/my/time_off/{leave_id}?error={str(e)}')

        if redirect_to == 'to_approve':
            return request.redirect('/my/time_off/to_approve?approved=1')
        return request.redirect(f'/my/time_off/{leave_id}?approved=1')

    @http.route(['/my/time_off/<int:leave_id>/refuse'], type='http', auth='user', methods=['POST'], website=True, csrf=True)
    def portal_my_time_off_refuse(self, leave_id, refusal_reason=None, redirect_to=None, **kw):
        leave = self._check_leave_access(leave_id, mode='approve')
        try:
            leave.action_portal_refuse(reason=refusal_reason or "")
        except Exception as e:
            return request.redirect(f'/my/time_off/{leave_id}?error={str(e)}')

        if redirect_to == 'to_approve':
            return request.redirect('/my/time_off/to_approve?refused=1')
        return request.redirect(f'/my/time_off/{leave_id}?refused=1')

    # -------------------------------------------------------------------------
    # AJAX Endpoint: Get Leave Type Balances and Config
    # -------------------------------------------------------------------------

    @http.route(['/my/time_off/get_leave_type_info'], type='json', auth='user')
    def portal_get_leave_type_info(self, type_id=None, **kw):
        if not type_id:
            return {'error': 'No leave type specified.'}
        employee = self._get_current_employee()
        ltype = request.env['hr.leave.type'].sudo().browse(int(type_id))
        if not ltype.exists():
            return {'error': 'Leave type not found.'}
        return ltype.get_portal_info(employee=employee)
