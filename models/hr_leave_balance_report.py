# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _


class HrLeaveBalanceReport(models.Model):
    _name = "hr.leave.balance.report"
    _description = "Employee Leave Balance Report"
    _auto = False
    _order = "department_id, employee_id, holiday_status_id"

    employee_id = fields.Many2one('hr.employee', string="Employee", readonly=True)
    department_id = fields.Many2one('hr.department', string="Department", readonly=True)
    job_id = fields.Many2one('hr.job', string="Job Position", readonly=True)
    company_id = fields.Many2one('res.company', string="Company", readonly=True)
    active_employee = fields.Boolean(string="Active Employee", readonly=True)
    holiday_status_id = fields.Many2one('hr.leave.type', string="Time Off Type", readonly=True)
    request_unit = fields.Selection([
        ('day', 'Day'),
        ('half_day', 'Half Day'),
        ('hour', 'Hours')
    ], string="Unit", readonly=True)

    allocated_days = fields.Float(string="Allocated (Days)", readonly=True, aggregator="sum")
    allocated_hours = fields.Float(string="Allocated (Hours)", readonly=True, aggregator="sum")
    taken_days = fields.Float(string="Taken (Days)", readonly=True, aggregator="sum")
    taken_hours = fields.Float(string="Taken (Hours)", readonly=True, aggregator="sum")
    pending_days = fields.Float(string="Pending (Days)", readonly=True, aggregator="sum")
    pending_hours = fields.Float(string="Pending (Hours)", readonly=True, aggregator="sum")
    remaining_days = fields.Float(string="Remaining Balance (Days)", readonly=True, aggregator="sum")
    remaining_hours = fields.Float(string="Remaining Balance (Hours)", readonly=True, aggregator="sum")
    virtual_remaining_days = fields.Float(string="Available (After Pending)", readonly=True, aggregator="sum")
    virtual_remaining_hours = fields.Float(string="Available Hours (After Pending)", readonly=True, aggregator="sum")
    closest_allocation_expire = fields.Date(string="Next Allocation Expiry", readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, 'hr_leave_balance_report')

        self._cr.execute("""
            CREATE or REPLACE view hr_leave_balance_report as (
                WITH alloc_summary AS (
                    SELECT
                        employee_id,
                        holiday_status_id,
                        SUM(CASE WHEN state = 'validate' THEN COALESCE(number_of_days, 0) ELSE 0 END) as allocated_days,
                        SUM(CASE WHEN state = 'validate' THEN COALESCE(number_of_hours_display, 0) ELSE 0 END) as allocated_hours,
                        MIN(date_to) FILTER (WHERE state = 'validate' AND (date_to IS NULL OR date_to >= CURRENT_DATE)) as closest_allocation_expire
                    FROM hr_leave_allocation
                    GROUP BY employee_id, holiday_status_id
                ),
                leave_summary AS (
                    SELECT
                        employee_id,
                        holiday_status_id,
                        SUM(CASE WHEN state = 'validate' THEN COALESCE(number_of_days, 0) ELSE 0 END) as taken_days,
                        SUM(CASE WHEN state = 'validate' THEN COALESCE(number_of_hours, 0) ELSE 0 END) as taken_hours,
                        SUM(CASE WHEN state IN ('confirm', 'validate1') THEN COALESCE(number_of_days, 0) ELSE 0 END) as pending_days,
                        SUM(CASE WHEN state IN ('confirm', 'validate1') THEN COALESCE(number_of_hours, 0) ELSE 0 END) as pending_hours
                    FROM hr_leave
                    WHERE state IN ('confirm', 'validate1', 'validate')
                    GROUP BY employee_id, holiday_status_id
                ),
                combined_keys AS (
                    SELECT employee_id, holiday_status_id FROM alloc_summary
                    UNION
                    SELECT employee_id, holiday_status_id FROM leave_summary
                )
                SELECT
                    ROW_NUMBER() OVER (ORDER BY emp.name, lt.id) as id,
                    ck.employee_id,
                    emp.department_id,
                    emp.job_id,
                    emp.company_id,
                    emp.active as active_employee,
                    ck.holiday_status_id,
                    lt.request_unit,
                    COALESCE(als.allocated_days, 0.0) as allocated_days,
                    COALESCE(als.allocated_hours, 0.0) as allocated_hours,
                    COALESCE(ls.taken_days, 0.0) as taken_days,
                    COALESCE(ls.taken_hours, 0.0) as taken_hours,
                    COALESCE(ls.pending_days, 0.0) as pending_days,
                    COALESCE(ls.pending_hours, 0.0) as pending_hours,
                    (COALESCE(als.allocated_days, 0.0) - COALESCE(ls.taken_days, 0.0)) as remaining_days,
                    (COALESCE(als.allocated_hours, 0.0) - COALESCE(ls.taken_hours, 0.0)) as remaining_hours,
                    (COALESCE(als.allocated_days, 0.0) - COALESCE(ls.taken_days, 0.0) - COALESCE(ls.pending_days, 0.0)) as virtual_remaining_days,
                    (COALESCE(als.allocated_hours, 0.0) - COALESCE(ls.taken_hours, 0.0) - COALESCE(ls.pending_hours, 0.0)) as virtual_remaining_hours,
                    als.closest_allocation_expire
                FROM combined_keys ck
                JOIN hr_employee emp ON emp.id = ck.employee_id
                JOIN hr_leave_type lt ON lt.id = ck.holiday_status_id
                LEFT JOIN alloc_summary als ON als.employee_id = ck.employee_id AND als.holiday_status_id = ck.holiday_status_id
                LEFT JOIN leave_summary ls ON ls.employee_id = ck.employee_id AND ls.holiday_status_id = ck.holiday_status_id
            );
        """)

    def action_view_employee_leaves(self):
        """ Smart action to drill down into the employee's time off records """
        self.ensure_one()
        return {
            'name': _("Time Off: %s - %s") % (self.employee_id.name, self.holiday_status_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('holiday_status_id', '=', self.holiday_status_id.id),
            ],
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_holiday_status_id': self.holiday_status_id.id,
            }
        }

    def action_view_employee_allocations(self):
        """ Smart action to drill down into the employee's allocations """
        self.ensure_one()
        return {
            'name': _("Allocations: %s - %s") % (self.employee_id.name, self.holiday_status_id.name),
            'type': 'ir.actions.act_window',
            'res_model': 'hr.leave.allocation',
            'view_mode': 'list,form',
            'domain': [
                ('employee_id', '=', self.employee_id.id),
                ('holiday_status_id', '=', self.holiday_status_id.id),
            ],
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_holiday_status_id': self.holiday_status_id.id,
            }
        }

