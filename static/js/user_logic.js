/* user_logic.js — user edit modal + page transitions. Loaded after ui_helpers.js. */

        
        // Prevent Future Date Selection
        const datePicker = document.getElementById('custom-date-picker');
        const todayStr = new Date().toISOString().split('T')[0];
        datePicker.setAttribute('max', todayStr);

        function toggleCustomDate(val) {
            if (val === 'Custom') {
                datePicker.classList.remove('hidden');
            } else {
                datePicker.classList.add('hidden');
                document.getElementById('filter-form').submit();
            }
        }

        // Modal Handlers
        function openEditModal(button) {
            const id = button.dataset.userId;
            const firstName = button.dataset.firstName || '';
            const mi = button.dataset.middleInitial || '';
            const lastName = button.dataset.lastName || '';
            const username = button.dataset.username || '';
            const role = button.dataset.role || 'Staff';
            const contact = button.dataset.contact || '';

            const _modal = document.getElementById('edit-modal');
            const _qSearch = _modal ? (_modal.dataset.search || '') : '';
            const _qDate = _modal ? (_modal.dataset.dateFilter || '') : '';
            document.getElementById('edit-form').action = "/admin/users/update/" + id + "?search=" + encodeURIComponent(_qSearch) + "&date_filter=" + encodeURIComponent(_qDate);

            document.getElementById('edit-user-id').value = "USR-" + String(id).padStart(3, '0');
            document.getElementById('edit-first-name').value = firstName;
            document.getElementById('edit-mi').value = mi;
            document.getElementById('edit-last-name').value = lastName;
            document.getElementById('edit-username').value = username;
            document.getElementById('edit-role').value = role;
            document.getElementById('edit-contact').value = contact;

            document.getElementById('edit-modal').classList.remove('hidden');
        }

        function closeEditModal() {
            document.getElementById('edit-modal').classList.add('hidden');
        }

        /* Delete-user confirmation modal: populated from the row button. */
        function openDeleteUserModal(btn) {
            const id = btn.dataset.userId;
            const name = btn.dataset.username || '';
            document.getElementById('delete-user-id-text').innerText =
                'USR-' + String(id).padStart(3, '0');
            document.getElementById('delete-user-name-text').innerText = name;
            document.getElementById('delete-user-form').action =
                '/admin/users/delete/' + id + window.location.search;
            document.getElementById('delete-user-modal').classList.remove('hidden');
        }
        function closeDeleteUserModal() {
            document.getElementById('delete-user-modal').classList.add('hidden');
        }
    
        document.addEventListener('DOMContentLoaded', function() {
            const isFromLogin = document.referrer.includes('/login');
            const skeleton = document.getElementById('skeleton-overlay');
            // Only show skeleton when coming from /login, otherwise bypass and do cascade
            if (!isFromLogin) {
                document.getElementById('skeleton-overlay')?.remove();
                const main = document.getElementById('main-dashboard-content');
                if (main) { main.style.opacity = '1'; main.classList.add('loaded'); }
                const fallbackMain = document.querySelector('.main-wrapper') || document.body;
                if (fallbackMain && !main) {
                    fallbackMain.style.opacity = '1';
                }
            }
            // Progressive cascade unveil - top to bottom, sidebar stays static
            const header = document.querySelector('.top-header');
            const cards = document.querySelector('.cards-grid');
            const tables = document.querySelectorAll('.action-bar-card, .table-card, .chart-card, .dashboard-container, .control-card, .content-card, .workspace-grid');
            if (!isFromLogin || !skeleton) {
                if (header) { header.classList.add('cascade-unveil'); header.style.animationDelay = '0s'; }
                if (cards) { cards.classList.add('cascade-unveil'); cards.style.animationDelay = '0.25s'; }
                tables.forEach(el => { 
                    if (el.classList.contains('dashboard-container') && el.querySelector('.cards-grid')) return;
                    el.classList.add('cascade-unveil'); el.style.animationDelay = '0.5s'; 
                });
                const lockTarget = document.getElementById('main-dashboard-content') || document.querySelector('.main-wrapper') || document.querySelector('.dashboard-container') || document.body;
                if (lockTarget) {
                    lockTarget.classList.add('cascade-lock');
                    lockTarget.style.pointerEvents = 'none';
                    lockTarget.style.userSelect = 'none';
                    const lastEl = tables.length ? tables[tables.length - 1] : (cards || header);
                    if (lastEl) {
                        lastEl.addEventListener('animationend', () => {
                            lockTarget.classList.remove('cascade-lock');
                            lockTarget.style.pointerEvents = 'auto';
                            lockTarget.style.userSelect = 'auto';
                        }, { once: true });
                    }
                    setTimeout(() => {
                        lockTarget.classList.remove('cascade-lock');
                        lockTarget.style.pointerEvents = 'auto';
                        lockTarget.style.userSelect = 'auto';
                    }, 1800);
                }
            }

            // Navigation-Only Unveil Trigger: suppress cascade for search/filter/refresh
            const isNavigation = document.referrer && !document.referrer.includes('/admin/users');
            const hasSearchOrFilter = window.location.search.length > 0;
            if (!isNavigation || hasSearchOrFilter) {
                document.querySelectorAll('.top-header, .cards-grid, .action-bar-card, .table-card, .dashboard-container, .control-card')
                    .forEach(el => {
                        el.classList.remove('cascade-unveil');
                        el.style.opacity = '1';
                        el.style.transform = 'none';
                        el.style.clipPath = 'none';
                        el.style.animation = 'none';
                    });
                const lockTarget2 = document.getElementById('main-dashboard-content') || document.querySelector('.main-wrapper') || document.querySelector('.dashboard-container') || document.body;
                if (lockTarget2) {
                    lockTarget2.classList.remove('cascade-lock');
                    lockTarget2.style.pointerEvents = 'auto';
                    lockTarget2.style.userSelect = 'auto';
                }
            }
        });
    