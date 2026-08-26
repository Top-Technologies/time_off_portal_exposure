/** @odoo-module **/

document.addEventListener('DOMContentLoaded', () => {
    const holidaySelect = document.getElementById('holiday_status_id');
    const halfDayCheckbox = document.getElementById('request_unit_half');
    const halfDayOptions = document.getElementById('half_day_options');
    const dateFromInput = document.getElementById('date_from');
    const dateToInput = document.getElementById('date_to');
    const dateToWrapper = document.getElementById('date_to_wrapper');
    const docRequiredBadge = document.getElementById('doc_required_badge');
    const balanceIndicator = document.getElementById('leave_type_balance_indicator');

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
        // Initial state
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
            const remaining = selectedOpt.getAttribute('data-remaining');
            const unit = selectedOpt.getAttribute('data-unit') === 'hour' ? 'hours' : 'days';

            if (docRequiredBadge) {
                docRequiredBadge.style.display = isSupportDoc ? 'inline-block' : 'none';
            }

            if (balanceIndicator && remaining !== null) {
                balanceIndicator.innerHTML = `<span class="badge bg-primary bg-opacity-10 text-primary p-2"><i class="fa fa-info-circle me-1"></i> Available Balance: <strong>${remaining} ${unit}</strong></span>`;
            }
        };

        holidaySelect.addEventListener('change', updateTypeConfig);
        // Run on initial load if pre-selected
        updateTypeConfig();
    }
});
