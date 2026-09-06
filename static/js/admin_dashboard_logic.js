/* admin_dashboard_logic.js — advanced toolbelt filter: custom dropdown,
   custom-range / specify-year / future-date droplet modals.
   Month > current month forces a year pick; year >= current year is
   rejected as future data. Applies via GET submit on #chart-filter-form. */
(function () {
    'use strict';

    var MONTHS = ['January', 'February', 'March', 'April', 'May', 'June',
                  'July', 'August', 'September', 'October', 'November', 'December'];

    var now = new Date();
    var CUR_MONTH = now.getMonth() + 1; // 1-12
    var CUR_YEAR = now.getFullYear();
    var TODAY_ISO = now.toISOString().slice(0, 10);

    var pendingMonth = null;

    function $(id) { return document.getElementById(id); }

    function openModal(id) {
        var m = $(id);
        if (m) m.classList.remove('hidden');
    }

    function closeModal(id) {
        var m = $(id);
        if (m) m.classList.add('hidden');
    }

    function showError(id, msg) {
        var e = $(id);
        if (!e) return;
        e.textContent = msg;
        e.classList.remove('hidden');
    }

    function hideError(id) {
        var e = $(id);
        if (e) e.classList.add('hidden');
    }

    function applyFilter(filter, year, from, to) {
        $('chart_filter_input').value = filter;
        $('filter_year_input').value = year || '';
        $('date_from_input').value = from || '';
        $('date_to_input').value = to || '';
        $('chart-filter-form').submit();
    }

    function markSelected(value) {
        var items = document.querySelectorAll('#filter-dropdown-list .filter-dropdown-item');
        items.forEach(function (it) {
            it.classList.toggle('selected', it.getAttribute('data-value') === value);
        });
    }

    function setButtonLabel(text) {
        var label = $('filter-selected');
        if (label) label.textContent = text;
    }

    function closeDropdown() {
        var list = $('filter-dropdown-list');
        var btn = $('filter-dropdown-btn');
        if (list) list.classList.add('hidden');
        if (btn) btn.setAttribute('aria-expanded', 'false');
    }

    function handleSelect(value, kind) {
        markSelected(value);
        if (kind === 'month') {
            var monthNum = MONTHS.indexOf(value) + 1;
            if (monthNum > CUR_MONTH) {
                // Future this year — ask which past year was meant.
                pendingMonth = value;
                var monthSpan = $('specify-year-month');
                if (monthSpan) monthSpan.textContent = value;
                var yearInput = $('specify-year-input');
                if (yearInput) yearInput.value = '';
                hideError('specify-year-error');
                closeDropdown();
                openModal('specify-year-modal');
                return;
            }
            setButtonLabel(value + ' ' + CUR_YEAR);
            closeDropdown();
            applyFilter(value, String(CUR_YEAR), '', '');
            return;
        }
        // Presets & quarters apply immediately.
        setButtonLabel(value);
        closeDropdown();
        applyFilter(value, '', '', '');
    }

    function init() {
        var btn = $('filter-dropdown-btn');
        var list = $('filter-dropdown-list');
        var form = $('chart-filter-form');
        if (!btn || !list || !form) return;

        // Reflect the server-side active filter on load.
        var current = $('chart_filter_input') ? $('chart_filter_input').value : 'All Time';
        if (MONTHS.indexOf(current) !== -1) markSelected(current);
        else if (current !== 'Custom') markSelected(current);

        btn.addEventListener('click', function (e) {
            e.stopPropagation();
            var isHidden = list.classList.contains('hidden');
            if (isHidden) {
                list.classList.remove('hidden');
                btn.setAttribute('aria-expanded', 'true');
            } else {
                closeDropdown();
            }
        });

        list.addEventListener('click', function (e) {
            var item = e.target.closest('.filter-dropdown-item');
            if (!item) return;
            handleSelect(item.getAttribute('data-value'), item.getAttribute('data-kind'));
        });

        document.addEventListener('click', function (e) {
            var wrap = $('filter-dropdown');
            if (wrap && !wrap.contains(e.target)) closeDropdown();
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') closeDropdown();
        });

        // ---- Gear → Custom Date Range modal ----
        var gear = $('btn-custom-range');
        if (gear) gear.addEventListener('click', function () {
            var fromInput = $('custom-from');
            var toInput = $('custom-to');
            if (fromInput) {
                fromInput.max = TODAY_ISO;
                if ($('date_from_input') && $('date_from_input').value) {
                    fromInput.value = $('date_from_input').value;
                }
            }
            if (toInput) {
                toInput.max = TODAY_ISO;
                if ($('date_to_input') && $('date_to_input').value) {
                    toInput.value = $('date_to_input').value;
                }
            }
            hideError('custom-date-error');
            closeDropdown();
            openModal('custom-date-modal');
        });

        var customCancel = $('custom-date-cancel');
        if (customCancel) customCancel.addEventListener('click', function () {
            closeModal('custom-date-modal');
        });

        var customApply = $('custom-date-apply');
        if (customApply) customApply.addEventListener('click', function () {
            var from = $('custom-from') ? $('custom-from').value : '';
            var to = $('custom-to') ? $('custom-to').value : '';
            if (!from || !to) {
                showError('custom-date-error', 'Please pick both a From and a To date.');
                return;
            }
            if (from > to) {
                showError('custom-date-error', 'From date cannot be after To date.');
                return;
            }
            if (to > TODAY_ISO || from > TODAY_ISO) {
                showError('custom-date-error', 'Future dates are not allowed — there is no data yet.');
                return;
            }
            hideError('custom-date-error');
            closeModal('custom-date-modal');
            setButtonLabel('Custom: ' + from + ' → ' + to);
            applyFilter('Custom', '', from, to);
        });

        // ---- Specify Year modal ----
        var yearCancel = $('specify-year-cancel');
        if (yearCancel) yearCancel.addEventListener('click', function () {
            pendingMonth = null;
            closeModal('specify-year-modal');
        });

        var yearConfirm = $('specify-year-confirm');
        if (yearConfirm) yearConfirm.addEventListener('click', function () {
            var raw = $('specify-year-input') ? $('specify-year-input').value.trim() : '';
            var year = parseInt(raw, 10);
            if (!raw || isNaN(year) || year < 2000) {
                showError('specify-year-error', 'Please enter a valid year (YYYY).');
                return;
            }
            if (year >= CUR_YEAR) {
                // Still the future — bounce to the error modal.
                hideError('specify-year-error');
                closeModal('specify-year-modal');
                openModal('future-date-modal');
                return;
            }
            hideError('specify-year-error');
            closeModal('specify-year-modal');
            var month = pendingMonth;
            pendingMonth = null;
            setButtonLabel(month + ' ' + year);
            applyFilter(month, String(year), '', '');
        });

        // ---- Future Date Error modal: Confirm closes it, re-opens year ----
        var futureConfirm = $('future-date-confirm');
        if (futureConfirm) futureConfirm.addEventListener('click', function () {
            closeModal('future-date-modal');
            hideError('specify-year-error');
            openModal('specify-year-modal');
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
