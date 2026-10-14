# -*- coding: utf-8 -*-
{
    'name': 'Time Off Portal Exposure',
    'version': '18.0.1.0.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Expose Time Off balances, requests, and hierarchical manager-to-HR approvals to free Portal Users in Odoo 18 & 19',
    'description': """
Time Off Portal Exposure for Odoo 18 & 19 Enterprise
===================================================
Enables organizations to reduce Odoo user license costs by granting self-service 
Time Off capabilities to employees operating as free Portal Users.

Key Features:
-------------
1. **Self-Service Time Off Portal**:
   - Time Off card and pending request counter on the Portal Home (`/my`).
   - Dedicated Time Off Dashboard showing real-time allocation balances (Allocated, Taken, Remaining Days/Hours per Leave Type).
   - New Leave Request submission form with start/end date, half-day (Morning/Afternoon), custom hours, reasons, and file attachments.
   - Comprehensive Request History with status badges, detailed view, cancellation, and portal message thread (chatter).

2. **2-Tier Approval Workflow for Portal & Internal Managers**:
   - Direct subordinates submit time off requests directly to their Manager (`parent_id` or `leave_manager_id`).
   - If the Manager is a **Portal User**, they gain a dedicated **"Time Off to Approve"** portal section to review subordinates' requests, see their remaining balance, and **Approve** or **Refuse** (with reason).
   - If the Manager is an Internal User, standard backend and portal approval flows are supported.
   - Once approved by the manager, the request seamlessly routes to the designated **Time Off Officer (HR Officer)** for final validation.

3. **Time Off Officer on Employee Profile (Odoo 19 Feature Set)**:
   - Dedicated `time_off_officer_id` field on the Employee profile (Many2one to internal HR Officer users) to specify the exact HR Officer responsible for approving the employee's time off.
   - Automated routing of validation activities and notifications directly to the designated HR Officer.

4. **Security & Data Isolation**:
   - Strict Portal Record Rules (`ir.rule`) ensuring employees only access their own time off & allocations.
   - Portal managers are restricted to viewing and approving only their direct and indirect subordinates' requests.
    """,
    'author': 'Custom Development',
    'website': 'https://www.odoo.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'portal',
        'hr',
        'hr_holidays',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/mail_template_data.xml',
        'views/hr_employee_views.xml',
        'views/hr_leave_views.xml',
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'time_off_portal_exposure/static/src/css/portal_time_off.css',
            'time_off_portal_exposure/static/src/js/ethiopian_calendar.js',
            'time_off_portal_exposure/static/src/js/portal_time_off.js',
        ],
    },
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
}
