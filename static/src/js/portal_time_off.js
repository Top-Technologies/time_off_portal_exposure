/** @odoo-module **/

function initTimeOffPortal() {
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

            const isSupportDoc = selectedOpt.getAttribute('data-support-doc') === 'True' || selectedOpt.getAttribute('data-support-doc') === 'true';
            const requiresAlloc = selectedOpt.getAttribute('data-requires-alloc') === 'yes';
            const remaining = parseFloat(selectedOpt.getAttribute('data-remaining')) || 0;
            const unit = selectedOpt.getAttribute('data-unit') === 'hour' ? 'hours' : 'days';
            const submitBtn = timeOffForm ? timeOffForm.querySelector('button[type="submit"]') : null;

            if (docRequiredBadge) {
                docRequiredBadge.style.display = isSupportDoc ? 'inline-block' : 'none';
            }

            if (balanceIndicator) {
                if (requiresAlloc && remaining <= 0) {
                    balanceIndicator.innerHTML = `<span class="badge bg-danger p-2"><i class="fa fa-times-circle me-1"></i> No Allocated Balance (0 ${unit})</span><div class="small text-danger mt-1 fw-bold"><i class="fa fa-ban me-1"></i>You cannot submit this request without an active allocation from HR.</div>`;
                    if (submitBtn) submitBtn.disabled = true;
                } else if (requiresAlloc) {
                    balanceIndicator.innerHTML = `<span class="badge bg-primary bg-opacity-10 text-primary p-2"><i class="fa fa-info-circle me-1"></i> Available Balance: <strong>${remaining} ${unit}</strong></span>`;
                    if (submitBtn) submitBtn.disabled = false;
                } else {
                    balanceIndicator.innerHTML = `<span class="badge bg-success bg-opacity-10 text-success p-2"><i class="fa fa-check-circle me-1"></i> No Allocation Required (${unit})</span>`;
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
