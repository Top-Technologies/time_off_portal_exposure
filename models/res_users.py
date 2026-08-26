# -*- coding: utf-8 -*-
from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    def get_portal_employee(self):
        """ Resolves the linked hr.employee record for portal and internal users alike """
        self.ensure_one()
        Employee = self.env['hr.employee'].sudo()
        
        # 1. Search by user_id
        employee = Employee.search([
            ('user_id', '=', self.id),
            ('active', '=', True),
            '|',
            ('company_id', '=', False),
            ('company_id', '=', self.company_id.id)
        ], limit=1)
        
        if employee:
            return employee

        # 2. Fallback search by partner_id (work_contact_id or address_home_id)
        if self.partner_id:
            employee = Employee.search([
                ('active', '=', True),
                '|',
                ('work_contact_id', '=', self.partner_id.id),
                ('address_home_id', '=', self.partner_id.id)
            ], limit=1)
            if employee:
                return employee

        return Employee.browse()
