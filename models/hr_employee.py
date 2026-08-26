# -*- coding: utf-8 -*-
from datetime import date
from odoo import api, fields, models, _


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    time_off_officer_id = fields.Many2one(
        'res.users',
        string="Time Off Officer",
        domain="[('share', '=', False)]",
        tracking=True,
        help="Designated HR Officer responsible for the final approval of time off requests for this employee."
    )
    is_portal_manager = fields.Boolean(
        string="Is Portal Manager",
        compute="_compute_portal_manager_status",
        help="Technical field indicating if this employee is a manager or time off approver for other employees."
    )
    portal_subordinate_count = fields.Integer(
        string="Portal Subordinates Count",
        compute="_compute_portal_manager_status"
    )

    def _compute_portal_manager_status(self):
        for employee in self:
            subordinates = self.env['hr.employee'].sudo().search([
                '|',
                ('parent_id', '=', employee.id),
                ('leave_manager_id', '=', employee.user_id.id if employee.user_id else False),
                ('id', '!=', employee.id),
                ('active', '=', True)
            ])
            employee.portal_subordinate_count = len(subordinates)
            employee.is_portal_manager = len(subordinates) > 0

    def get_subordinate_employees(self):
        """ Returns all direct and indirect subordinates for this employee """
        self.ensure_one()
        domain = [
            '|',
            ('parent_id', '=', self.id),
            ('leave_manager_id', '=', self.user_id.id if self.user_id else False),
            ('id', '!=', self.id),
            ('active', '=', True)
        ]
        return self.env['hr.employee'].sudo().search(domain)

    def get_portal_leave_balances(self, target_date=None):
        """ Computes a clear structured breakdown of time off balances for portal display """
        self.ensure_one()
        target_date = target_date or fields.Date.today()
        leave_types = self.env['hr.leave.type'].sudo().search([
            ('active', '=', True),
            ('is_portal_visible', '=', True)
        ])

        balances = []
        for ltype in leave_types:
            # Calculate allocations
            allocations = self.env['hr.leave.allocation'].sudo().search([
                ('employee_id', '=', self.id),
                ('holiday_status_id', '=', ltype.id),
                ('state', '=', 'validate'),
                '|',
                ('date_from', '=', False),
                ('date_from', '<=', target_date),
                '|',
                ('date_to', '=', False),
                ('date_to', '>=', target_date),
            ])

            # Calculate total allocated
            if ltype.request_unit == 'hour':
                allocated = sum(allocations.mapped('number_of_hours_display'))
            else:
                allocated = sum(allocations.mapped('number_of_days_display'))

            # Calculate validated leaves taken
            leaves_taken_records = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', self.id),
                ('holiday_status_id', '=', ltype.id),
                ('state', '=', 'validate'),
            ])
            if ltype.request_unit == 'hour':
                taken = sum(leaves_taken_records.mapped('number_of_hours'))
            else:
                taken = sum(leaves_taken_records.mapped('number_of_days'))

            # Calculate pending / submitted leaves
            leaves_pending_records = self.env['hr.leave'].sudo().search([
                ('employee_id', '=', self.id),
                ('holiday_status_id', '=', ltype.id),
                ('state', 'in', ['confirm', 'validate1']),
            ])
            if ltype.request_unit == 'hour':
                pending = sum(leaves_pending_records.mapped('number_of_hours'))
            else:
                pending = sum(leaves_pending_records.mapped('number_of_days'))

            remaining = allocated - taken
            virtual_remaining = remaining - pending

            # If leave type requires no allocation (e.g. Unpaid Leave or Sick Leave without allocation)
            requires_allocation = ltype.requires_allocation == 'yes' if hasattr(ltype, 'requires_allocation') else True

            balances.append({
                'id': ltype.id,
                'name': ltype.name,
                'color': ltype.color_name if hasattr(ltype, 'color_name') and ltype.color_name else 'info',
                'request_unit': ltype.request_unit,
                'requires_allocation': requires_allocation,
                'allocated': round(allocated, 2),
                'taken': round(taken, 2),
                'pending': round(pending, 2),
                'remaining': round(remaining, 2),
                'virtual_remaining': round(virtual_remaining, 2),
                'support_document': getattr(ltype, 'support_document', False),
            })

        return balances


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    time_off_officer_id = fields.Many2one(
        'res.users',
        string="Time Off Officer",
        readonly=True
    )
