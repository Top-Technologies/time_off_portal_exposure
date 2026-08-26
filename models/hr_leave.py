# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError


class HrLeave(models.Model):
    _inherit = 'hr.leave'

    portal_state = fields.Selection([
        ('draft', 'Draft'),
        ('pending_manager', 'Pending Manager Approval'),
        ('pending_hr', 'Pending HR Officer Approval'),
        ('approved', 'Approved'),
        ('refused', 'Refused'),
        ('cancelled', 'Cancelled'),
    ], string="Portal Status", compute="_compute_portal_state", store=True)

    manager_approved = fields.Boolean(
        string="Manager Approved",
        default=False,
        copy=False,
        help="Flag set to True when the direct manager approves the time off request."
    )
    manager_approval_date = fields.Datetime(
        string="Manager Approval Date",
        copy=False,
        readonly=True
    )
    manager_approved_by_id = fields.Many2one(
        'res.users',
        string="Manager Approved By",
        copy=False,
        readonly=True
    )
    refusal_reason = fields.Text(
        string="Refusal Reason",
        copy=False,
        help="Reason provided by Manager or HR Officer when refusing the time off request."
    )
    is_portal_submitted = fields.Boolean(
        string="Submitted via Portal",
        default=False,
        copy=False
    )

    @api.depends('state', 'manager_approved', 'holiday_status_id.leave_validation_type')
    def _compute_portal_state(self):
        for leave in self:
            if leave.state == 'cancel':
                leave.portal_state = 'cancelled'
            elif leave.state == 'refuse':
                leave.portal_state = 'refused'
            elif leave.state == 'validate':
                leave.portal_state = 'approved'
            elif leave.state == 'draft':
                leave.portal_state = 'draft'
            elif leave.state in ['confirm', 'validate1']:
                val_type = getattr(leave.holiday_status_id, 'leave_validation_type', 'both')
                if val_type in ['both', 'manager']:
                    if not leave.manager_approved:
                        leave.portal_state = 'pending_manager'
                    else:
                        leave.portal_state = 'pending_hr' if val_type == 'both' else 'approved'
                elif val_type == 'hr':
                    leave.portal_state = 'pending_hr'
                else:
                    leave.portal_state = 'pending_manager'
            else:
                leave.portal_state = 'draft'

    def action_approve(self, check_state=True):
        """ Allow HR Officer to approve in a single click if manager already approved or HR is approving """
        leaves_to_validate = self.filtered(lambda l: l.manager_approved or self.env.user.has_group('hr_holidays.group_hr_holidays_user'))
        other_leaves = self - leaves_to_validate

        if leaves_to_validate:
            leaves_to_validate.action_validate(check_state=False)

        if other_leaves:
            super(HrLeave, other_leaves).action_approve(check_state=check_state)

        return True

    def action_validate(self, check_state=True):
        """ Trigger approval email to employee on final validation """
        res = super().action_validate(check_state=check_state)
        for leave in self:
            leave._send_mail_safe('time_off_portal_exposure.email_template_time_off_approved_employee')
        return res

    def action_portal_manager_approve(self):
        """ Executed when manager (Portal or Internal) approves the subordinate's time off request """
        for leave in self:
            if leave.manager_approved:
                continue

            if leave.state not in ['confirm', 'validate1']:
                raise UserError(_("Only requests waiting for approval can be approved."))

            manager_emp = self.env.user.get_portal_employee()
            leave_vals = {
                'manager_approved': True,
                'manager_approval_date': fields.Datetime.now(),
                'manager_approved_by_id': self.env.user.id,
            }
            if manager_emp:
                leave_vals['first_approver_id'] = manager_emp.id

            leave.sudo().write(leave_vals)

            # Clean, concise message in chatter
            leave.sudo().message_post(
                body=_("✅ <b>Approved by Manager:</b> %s.") % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

            val_type = getattr(leave.holiday_status_id, 'leave_validation_type', 'both')
            
            # Check if 2-tier approval is needed (both or hr)
            if val_type in ['both', 'hr']:
                try:
                    leave.sudo().write({'state': 'validate1'})
                except Exception:
                    pass
                
                # Notify designated HR Officer
                leave._notify_time_off_officer()
                # Notify employee of manager approval
                leave._send_mail_safe('time_off_portal_exposure.email_template_time_off_manager_approved_employee')
            else:
                # Fully validate since only manager approval was required
                try:
                    leave.sudo().action_validate()
                except Exception:
                    leave.sudo().write({'state': 'validate'})

        return True

    def action_portal_refuse(self, reason=""):
        """ Executed when manager or HR officer refuses the request with a reason """
        for leave in self:
            if leave.state in ['validate', 'refuse', 'cancel']:
                raise UserError(_("This request cannot be refused in its current state."))

            clean_reason = (reason or "").strip() or _("No specific reason provided.")
            leave.sudo().write({
                'refusal_reason': clean_reason,
            })

            try:
                leave.sudo().action_refuse()
            except Exception:
                leave.sudo().write({'state': 'refuse'})

            # Clean, concise refusal note in chatter
            leave.sudo().message_post(
                body=_("❌ <b>Refused by %s.</b><br/><b>Reason:</b> %s") % (
                    self.env.user.name,
                    clean_reason
                ),
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

            # Send refusal email to employee
            leave._send_mail_safe('time_off_portal_exposure.email_template_time_off_refused_employee')

        return True

    def action_portal_cancel(self):
        """ Executed when employee cancels their own pending request """
        for leave in self:
            if leave.state not in ['draft', 'confirm', 'validate1']:
                raise UserError(_("You can only cancel pending requests."))

            try:
                leave.sudo().action_cancel()
            except Exception:
                leave.sudo().write({'state': 'cancel'})

            # Clean, concise cancellation note in chatter
            leave.sudo().message_post(
                body=_("🚫 <b>Cancelled by Employee:</b> %s.") % self.env.user.name,
                message_type='comment',
                subtype_xmlid='mail.mt_comment',
            )

        return True

    def _notify_time_off_officer(self):
        """ Creates activity and sends email notification to the designated Time Off Officer """
        for leave in self:
            officer = leave.employee_id.time_off_officer_id
            
            # If no specific officer assigned, find users in Time Off Officer group
            if not officer:
                group_officer = self.env.ref('hr_holidays.group_hr_holidays_user', raise_if_not_found=False)
                if group_officer and group_officer.users:
                    officer = group_officer.users.filtered(lambda u: not u.share)[:1]

            if officer:
                # Avoid duplicate activities
                existing_activity = self.env['mail.activity'].sudo().search([
                    ('res_model', '=', 'hr.leave'),
                    ('res_id', '=', leave.id),
                    ('user_id', '=', officer.id),
                ], limit=1)

                if not existing_activity:
                    try:
                        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
                        if activity_type:
                            leave.sudo().activity_schedule(
                                activity_type_id=activity_type.id,
                                summary=_("Time Off Approval: %s") % leave.employee_id.name,
                                note=_("Time off for %s (%s to %s) approved by manager; awaiting HR confirmation.") % (
                                    leave.employee_id.name,
                                    leave.request_date_from or leave.date_from,
                                    leave.request_date_to or leave.date_to
                                ),
                                user_id=officer.id,
                            )
                    except Exception:
                        pass

                # Send email directly to officer inbox without chatter HTML dump
                leave._send_mail_safe('time_off_portal_exposure.email_template_time_off_manager_approved_hr')

    def _notify_manager_on_submission(self):
        """ Notifies the employee's manager when a new request is submitted via portal """
        for leave in self:
            manager = leave.employee_id.parent_id.user_id or leave.employee_id.leave_manager_id
            if manager:
                leave._send_mail_safe('time_off_portal_exposure.email_template_time_off_submitted_manager')

    def _send_mail_safe(self, template_xml_id):
        """ Helper to send notification emails directly without polluting the record's chatter thread """
        template = self.env.ref(template_xml_id, raise_if_not_found=False)
        if template:
            try:
                template.sudo().send_mail(
                    self.id,
                    force_send=True,
                    email_values={'model': False, 'res_id': False, 'auto_delete': True}
                )
            except Exception:
                pass
