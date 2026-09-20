/* -------------------------------------------------------------------
   SmartComplaint AI — Architectural / Editorial JavaScript Engine
------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  initTableSearch();
  initAutoDismissAlerts();
});

/**
 * Client-side table search utility
 */
function initTableSearch() {
  const searchInput = document.getElementById('tableSearchInput');
  const table = document.querySelector('.table-editorial');

  if (!searchInput || !table) return;

  const rows = table.querySelectorAll('tbody tr');

  searchInput.addEventListener('input', (e) => {
    const term = (e.target.value || '').toLowerCase().trim();
    rows.forEach(row => {
      const text = row.textContent.toLowerCase();
      row.style.display = text.includes(term) ? '' : 'none';
    });
  });
}

/**
 * Auto-dismiss flash notifications
 */
function initAutoDismissAlerts() {
  const alerts = document.querySelectorAll('.alert-editorial');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.opacity = '0';
      alert.style.transition = 'opacity 0.4s ease';
      setTimeout(() => alert.remove(), 400);
    }, 5000);
  });
}
