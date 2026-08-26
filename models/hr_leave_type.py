# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HrLeaveType(models.Model):
    _inherit = 'hr.leave.type'

    is_portal_visible = fields.Boolean(
        string="Visible on Portal",
        default=True,
        help="If checked, portal users can select this time off type when submitting requests."
    )

    def get_portal_info(self, employee=None):
        self.ensure_one()
        remaining = 0.0
        virtual_remaining = 0.0
        allocated = 0.0
        if employee:
            balances = employee.get_portal_leave_balances()
            type_balance = next((b for b in balances if b['id'] == self.id), None)
            if type_balance:
                remaining = type_balance['remaining']
                virtual_remaining = type_balance['virtual_remaining']
                allocated = type_balance['allocated']

        return {
            'id': self.id,
            'name': self.name,
            'request_unit': self.request_unit,
            'support_document': getattr(self, 'support_document', False),
            'requires_allocation': getattr(self, 'requires_allocation', 'yes'),
            'remaining': remaining,
            'virtual_remaining': virtual_remaining,
            'allocated': allocated,
        }
