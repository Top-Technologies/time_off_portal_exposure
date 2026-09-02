/** @odoo-module **/

function initTimeOffPortal() {
    // 0. Remove persistent doc spinner on portal home if present
    const docSpinners = document.querySelectorAll('.o_portal_doc_spinner');
    docSpinners.forEach(s => s.remove());

    const targetEmployeeSelect = document.getElementById('target_employee_id');
    const holidaySelect = document.getElementById('holiday_status_id');
    const halfDayCheckbox = document.getElementById('request_unit_half');
    const halfDayOptions = document.getElementById('half_day_options');
    const dateFromInput = document.getElementById('date_from');
    const dateToInput = document.getElementById('date_to');
    const dateToWrapper = document.getElementById('date_to_wrapper');
    const docRequiredBadge = document.getElementById('doc_required_badge');
    const balanceIndicator = document.getElementById('leave_type_balance_indicator');
    const timeOffForm = document.getElementById('time_off_application_form');
    const processingOverlay = document.getElementById('time_off_processing_overlay');

    // 0. Manager Target Subordinate Switcher
    if (targetEmployeeSelect) {
        targetEmployeeSelect.addEventListener('change', () => {
            const targetId = targetEmployeeSelect.value;
            const currentUrl = new URL(window.location.href);
            currentUrl.searchParams.set('target_id', targetId);
            window.location.href = currentUrl.toString();
        });
    }

    // 1. Half Day Toggle Logic
    if (halfDayCheckbox) {
        const toggleHalfDay = () => {
            if (halfDayCheckbox.checked) {
                if (halfDayOptions) halfDayOptions.style.display = 'block';
                if (dateToWrapper) dateToWrapper.style.display = 'none';
                if (dateToInput && dateFromInput) dateToInput.value = dateFromInput.value;
            } else {
                if (halfDayOptions) halfDayOptions.style.display = 'none';
                if (dateToWrapper) dateToWrapper.style.display = 'block';
            }
        };

        halfDayCheckbox.addEventListener('change', toggleHalfDay);
        toggleHalfDay();
    }

    // Keep date_to synchronized when date_from changes in half-day mode
    if (dateFromInput && dateToInput) {
        dateFromInput.addEventListener('change', () => {
            if (halfDayCheckbox && halfDayCheckbox.checked) {
                dateToInput.value = dateFromInput.value;
            }
            if (dateToInput.value && dateToInput.value < dateFromInput.value) {
                dateToInput.value = dateFromInput.value;
            }
        });
    }

    // 2. Leave Type Change Logic
    if (holidaySelect) {
        const updateTypeConfig = () => {
            const selectedOpt = holidaySelect.options[holidaySelect.selectedIndex];
            if (!selectedOpt || !selectedOpt.value) {
                if (docRequiredBadge) docRequiredBadge.style.display = 'none';
                if (balanceIndicator) balanceIndicator.innerHTML = '';
                return;
            }

            const requiresAlloc = selectedOpt.getAttribute('data-requires-alloc') === 'yes';
            const remaining = parseFloat(selectedOpt.getAttribute('data-remaining')) || 0;
            const unit = selectedOpt.getAttribute('data-unit') === 'hour' ? 'hours' : 'days';
            const submitBtn = timeOffForm ? timeOffForm.querySelector('button[type="submit"]') : null;

            if (balanceIndicator) {
                if (requiresAlloc && remaining <= 0) {
                    balanceIndicator.innerHTML = `
                        <div class="alert alert-danger d-inline-flex align-items-center py-1 px-3 mb-0 rounded-2 fw-semibold text-danger border border-danger border-opacity-25" style="background-color: #f8d7da; color: #842029 !important;">
                            <i class="fa fa-times-circle me-2 text-danger"></i> No Allocated Balance (0 ${unit})
                        </div>
                        <div class="small text-danger mt-1 fw-bold"><i class="fa fa-ban me-1"></i>You cannot submit this request without an active allocation from HR.</div>
                    `;
                    if (submitBtn) submitBtn.disabled = true;
                } else if (requiresAlloc) {
                    balanceIndicator.innerHTML = `
                        <div class="alert alert-primary d-inline-flex align-items-center py-1 px-3 mb-0 rounded-2 fw-semibold text-primary border border-primary border-opacity-25" style="background-color: #cfe2ff; color: #084298 !important;">
                            <i class="fa fa-info-circle me-2 text-primary"></i> Available Balance: <strong class="ms-1">${remaining} ${unit}</strong>
                        </div>
                    `;
                    if (submitBtn) submitBtn.disabled = false;
                } else {
                    balanceIndicator.innerHTML = `
                        <div class="alert alert-success d-inline-flex align-items-center py-1 px-3 mb-0 rounded-2 fw-semibold text-success border border-success border-opacity-25" style="background-color: #d1e7dd; color: #0f5132 !important;">
                            <i class="fa fa-check-circle me-2 text-success"></i> No Allocation Required (${unit})
                        </div>
                    `;
                    if (submitBtn) submitBtn.disabled = false;
                }
            }
        };

        holidaySelect.addEventListener('change', updateTypeConfig);
        updateTypeConfig();
    }

    // 3. Form Submission Indicator & Processing Loader
    if (timeOffForm) {
        timeOffForm.addEventListener('submit', (e) => {
            if (!timeOffForm.checkValidity()) {
                return;
            }

            const submitBtn = timeOffForm.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.innerHTML = '<i class="fa fa-circle-o-notch fa-spin me-2"></i> Submitting Request...';
            }

            if (processingOverlay) {
                processingOverlay.style.display = 'flex';
            }
        });
    }

    // 4. Approval / Rejection Action Loaders
    document.querySelectorAll('form[action*="/my/time_off/"]').forEach((form) => {
        if (form.id === 'time_off_application_form') return;
        form.addEventListener('submit', () => {
            const btn = form.querySelector('button[type="submit"]');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '<i class="fa fa-circle-o-notch fa-spin me-1"></i> Processing...';
            }
            if (processingOverlay) {
                const title = document.getElementById('processing_loader_title');
                const text = document.getElementById('processing_loader_text');
                if (title) title.innerText = 'Processing Approval Decision...';
                if (text) text.innerText = 'Updating record and sending notifications. Please wait...';
                processingOverlay.style.display = 'flex';
            }
        });
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initTimeOffPortal);
} else {
    initTimeOffPortal();
}
