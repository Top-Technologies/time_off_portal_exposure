# Time Off Portal Exposure for Odoo 18 & 19 Enterprise

**Technical Name:** `time_off_portal_exposure`  
**License:** LGPL-3  
**Category:** Human Resources/Time Off  
**Compatible Versions:** Odoo 18.0 & Odoo 19.0 Enterprise  

---

## 🌟 Overview & Business Objective

In many organizations, the workforce is large, but purchasing full internal Odoo user licenses for every single employee is cost-prohibitive. Odoo offers free **Portal Users**, but natively, the Time Off (`hr_holidays`) module is restricted to internal users.

**Time Off Portal Exposure** unlocks self-service Time Off capabilities for all Portal Users (Free Users) and introduces a seamless **2-Tier Approval Architecture** where:
1. An employee submits a time off request directly from their customer/employee portal.
2. The employee's direct Manager (who can also be a **Portal User**) reviews, tracks subordinate balances, and **Approves** or **Refuses** the request.
3. Upon manager approval, the request routes to the designated **Time Off Officer (HR Officer)** (a paid internal user) for final validation.
4. Includes the Odoo 19 `time_off_officer_id` field on the Employee profile to specify the exact HR Officer in charge of approving time off for each employee.

---

## 🚀 Key Features

### 1. Self-Service Portal Dashboard (`/my/time_off`)
- **Portal Home Entry (`/my`)**: Live "My Time Off" card displaying active request count and total remaining days.
- **KPI Summary Cards**: Total Remaining Days, Requests Pending Approval, Validated Requests this Year.
- **Allocation Breakdown**: Visual card grid detailing Allocated, Taken, Pending, and Remaining Days/Hours per leave type.
- **Request History Table**: Search, filter by status (All, To Approve, Approved, Refused, Cancelled), and sort by date.

### 2. Intuitive Request Submission (`/my/time_off/new`)
- Dynamic Leave Type selector with live balance indicator.
- Half-Day switch (Morning / Afternoon) and custom hours support.
- File attachment uploader (supporting mandatory medical certificates or justifications).
- Real-time approval routing preview (shows designated Manager and HR Officer).

### 3. Portal Manager Approval Dashboard (`/my/time_off/to_approve`)
- Allows **Portal Managers** (managers who are free portal users) to manage their team without needing paid internal licenses!
- Displays team member names, departments, leave types, dates, durations, and reasons.
- Quick 1-click **Approve** and **Refuse** (with refusal reason prompt modal).

### 4. Time Off Officer Assignment on Employee Profile
- Added `time_off_officer_id` on `hr.employee` (Many2one to internal users with HR Officer privileges).
- Automated creation of `mail.activity` and email dispatch directly to the designated HR Officer when manager approves.

### 5. Two-Way Portal Chatter & Notifications
- Integrated chatter widget on `/my/time_off/<id>` for direct communication between employees, managers, and HR.
- Automated email templates for:
  - Request Submission (sent to Manager)
  - Manager Approval (sent to HR Officer & Employee)
  - HR Final Validation (sent to Employee)
  - Request Refusal (sent to Employee with refusal reason)

---

## 📂 Module Structure

```
time_off_portal_exposure/
├── __init__.py
├── __manifest__.py
├── README.md
├── controllers/
│   ├── __init__.py
│   └── portal.py                      # CustomerPortal controller & routing endpoints
├── models/
│   ├── __init__.py
│   ├── hr_employee.py                 # time_off_officer_id & balance computation methods
│   ├── hr_leave.py                    # Portal workflow states & manager approval logic
│   ├── hr_leave_type.py               # is_portal_visible & portal metadata helpers
│   └── res_users.py                   # Portal user to employee resolver
├── security/
│   ├── ir.model.access.csv            # Portal ACL permissions
│   └── security.xml                   # Record rules for employees & portal managers
├── data/
│   └── mail_template_data.xml         # Email templates for all approval phases
├── views/
│   ├── hr_employee_views.xml          # Employee form view with Time Off Officer
│   ├── hr_leave_views.xml             # Backend leave tracking & portal state badges
│   └── portal_templates.xml           # QWeb portal templates (Dashboard, Form, Details, Approvals)
└── static/
    └── src/
        ├── css/
        │   └── portal_time_off.css    # Responsive styles, stepper widget & badges
        ├── js/
        │   └── portal_time_off.js     # Half-day toggles & dynamic balance calculations
        └── img/
            ├── calendar.svg           # Portal home time off icon
            └── check-circle.svg       # Portal home approvals icon
```

---

## ⚙️ Configuration & Quick Start

1. **Place the module**: Copy `time_off_portal_exposure` into your Odoo custom addons directory.
2. **Update App List**: Go to **Apps -> Update Apps List**.
3. **Install Module**: Search for `Time Off Portal Exposure` and click **Install**.
4. **Link Portal Users to Employees**:
   - In **Employees**, open each employee's profile.
   - Under **HR Settings / Work Information**, link the employee to their **Related User** (Portal User).
   - Assign their **Manager** (`parent_id`) or **Time Off Approver** (`leave_manager_id`).
   - Assign their **Time Off Officer** (`time_off_officer_id`).
5. **Allocate Time Off**:
   - Create standard `hr.leave.allocation` records for your employees in the backend Time Off app.
6. **Log in as Portal User**:
   - Open `/my` to view time off balances and submit leave requests!
