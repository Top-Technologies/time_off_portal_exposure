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

        # 2. Fallback search by partner_id (work_contact_id)
        if self.partner_id:
            employee = Employee.search([
                ('active', '=', True),
                ('work_contact_id', '=', self.partner_id.id),
                '|',
                ('company_id', '=', False),
                ('company_id', '=', self.company_id.id)
            ], limit=1)
            if employee:
                return employee

        return Employee.browse()

    def write(self, vals):
        """
        Prevent hr_holidays from assigning 'hr_holidays.group_hr_holidays_responsible'
        to portal users. In standard Odoo, hr_holidays automatically promotes any user
        assigned as 'leave_manager_id' to the Time Off Responsible group.
        Since that group implies 'base.group_user' (Internal User), assigning it to a
        portal user violates the single user type constraint (_check_one_user_type).
        """
        if 'groups_id' in vals:
            approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
            if approver_group:
                approver_id = approver_group.id
                portal_users = self.filtered(lambda u: u.share)
                if portal_users:
                    from odoo import Command
                    cleaned_ops = []
                    for op in vals.get('groups_id', []):
                        if isinstance(op, (list, tuple)) and len(op) >= 2:
                            if op[0] in (4, Command.LINK) and op[1] == approver_id:
                                continue
                            elif op[0] in (6, Command.SET) and len(op) > 2 and approver_id in op[2]:
                                cleaned_ids = [gid for gid in op[2] if gid != approver_id]
                                cleaned_ops.append((Command.SET, 0, cleaned_ids))
                                continue
                        cleaned_ops.append(op)

                    if len(portal_users) == len(self):
                        vals = dict(vals)
                        if cleaned_ops:
                            vals['groups_id'] = cleaned_ops
                        else:
                            vals.pop('groups_id')
                        if not vals:
                            return True
                        return super().write(vals)
                    else:
                        non_portal_users = self - portal_users
                        res1 = super(ResUsers, non_portal_users).write(vals)
                        portal_vals = dict(vals)
                        if cleaned_ops:
                            portal_vals['groups_id'] = cleaned_ops
                        else:
                            portal_vals.pop('groups_id')
                        res2 = super(ResUsers, portal_users).write(portal_vals) if portal_vals else True
                        return res1 and res2

        return super().write(vals)


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def write(self, vals):
        """
        Prevent adding portal users to 'hr_holidays.group_hr_holidays_responsible'.
        During hr.employee.create(), hr_holidays executes:
        approver_group.sudo().write({'users': [(4, portal_user_id)]})
        Filtering out portal users here prevents the single user type ValidationError.
        """
        approver_group = self.env.ref('hr_holidays.group_hr_holidays_responsible', raise_if_not_found=False)
        if approver_group and 'users' in vals and approver_group in self:
            from odoo import Command
            cleaned_ops = []
            for op in vals.get('users', []):
                if isinstance(op, (list, tuple)) and len(op) >= 2:
                    if op[0] in (4, Command.LINK):
                        user = self.env['res.users'].sudo().browse(op[1])
                        if user.share:
                            continue
                    elif op[0] in (6, Command.SET) and len(op) > 2:
                        users = self.env['res.users'].sudo().browse(op[2])
                        cleaned_ids = [u.id for u in users if not u.share]
                        cleaned_ops.append((Command.SET, 0, cleaned_ids))
                        continue
                cleaned_ops.append(op)

            if self == approver_group:
                vals = dict(vals)
                if cleaned_ops:
                    vals['users'] = cleaned_ops
                else:
                    vals.pop('users')
                if not vals:
                    return True
            else:
                other_groups = self - approver_group
                res1 = super(ResGroups, other_groups).write(vals)
                app_vals = dict(vals)
                if cleaned_ops:
                    app_vals['users'] = cleaned_ops
                else:
                    app_vals.pop('users')
                res2 = super(ResGroups, approver_group).write(app_vals) if app_vals else True
                return res1 and res2

        return super().write(vals)
