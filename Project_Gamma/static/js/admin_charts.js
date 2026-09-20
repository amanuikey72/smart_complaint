/* -------------------------------------------------------------------
   SmartComplaint AI — Restrained Editorial Analytics Engine
   Driven directly by database metrics from /api/stats
------------------------------------------------------------------- */

document.addEventListener('DOMContentLoaded', () => {
  if (document.getElementById('priorityDoughnutChart') || document.getElementById('monthlyTrendChart')) {
    loadAndRenderAdminCharts();
  }
});

async function loadAndRenderAdminCharts() {
  try {
    const response = await fetch('/api/stats');
    if (!response.ok) throw new Error('Failed to load stats');

    const stats = await response.json();
    renderPriorityChart(stats);
    renderStatusChart(stats);
    renderCategoryChart(stats);
    renderMonthlyTrendChart(stats);

  } catch (error) {
    console.error('Error initializing admin analytics charts:', error);
  }
}

Chart.defaults.color = '#C5BCB0';
Chart.defaults.font.family = "'JetBrains Mono', monospace";
Chart.defaults.plugins.legend.labels.usePointStyle = true;

/**
 * 1. Priority Distribution Doughnut Chart
 */
function renderPriorityChart(stats) {
  const canvas = document.getElementById('priorityDoughnutChart');
  if (!canvas) return;

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Critical (81-100)', 'High (61-80)', 'Medium (31-60)', 'Low (0-30)'],
      datasets: [{
        data: [stats.critical, stats.high, stats.medium, stats.low],
        backgroundColor: [
          '#9E3B3B', // Burnt Red
          '#C86446', // Terracotta
          '#C88E3A', // Antique Amber
          '#6E8B74'  // Desaturated Sage
        ],
        borderColor: '#241A24',
        borderWidth: 2,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          backgroundColor: '#302B2D',
          borderColor: 'rgba(232, 224, 210, 0.2)',
          borderWidth: 1,
          titleFont: { family: "'JetBrains Mono', monospace" },
          bodyFont: { family: "'JetBrains Mono', monospace" }
        }
      },
      cutout: '70%'
    }
  });
}

/**
 * 2. Status Distribution Doughnut Chart
 */
function renderStatusChart(stats) {
  const canvas = document.getElementById('statusDoughnutChart');
  if (!canvas) return;

  new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels: ['Pending', 'In Progress', 'Resolved', 'Rejected'],
      datasets: [{
        data: [stats.pending, stats.in_progress, stats.resolved, stats.rejected],
        backgroundColor: [
          '#C88E3A', // Amber
          '#A66A4C', // Copper
          '#6E8B74', // Sage
          '#5A5257'  // Charcoal
        ],
        borderColor: '#241A24',
        borderWidth: 2,
        hoverOffset: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom' },
        tooltip: {
          backgroundColor: '#302B2D',
          borderColor: 'rgba(232, 224, 210, 0.2)',
          borderWidth: 1
        }
      },
      cutout: '70%'
    }
  });
}

/**
 * 3. Category Breakdown Bar Chart
 */
function renderCategoryChart(stats) {
  const canvas = document.getElementById('categoryBarChart');
  if (!canvas) return;

  const categories = stats.categories || {};
  const labels = Object.keys(categories);
  const counts = Object.values(categories);

  new Chart(canvas, {
    type: 'bar',
    data: {
      labels: labels,
      datasets: [{
        label: 'Cases',
        data: counts,
        backgroundColor: 'rgba(166, 106, 76, 0.75)',
        hoverBackgroundColor: '#A66A4C',
        borderColor: '#A66A4C',
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { display: false } },
        y: {
          grid: { color: 'rgba(232, 224, 210, 0.08)' },
          beginAtZero: true,
          ticks: { stepSize: 1 }
        }
      }
    }
  });
}

/**
 * 4. Monthly Complaint Trend Line Chart
 */
function renderMonthlyTrendChart(stats) {
  const canvas = document.getElementById('monthlyTrendChart');
  if (!canvas) return;

  const trend = stats.monthly_trend || { labels: [], data: [] };
  const ctx = canvas.getContext('2d');

  const gradient = ctx.createLinearGradient(0, 0, 0, 300);
  gradient.addColorStop(0, 'rgba(166, 106, 76, 0.35)');
  gradient.addColorStop(1, 'rgba(166, 106, 76, 0.0)');

  new Chart(canvas, {
    type: 'line',
    data: {
      labels: trend.labels,
      datasets: [{
        label: 'Submissions',
        data: trend.data,
        borderColor: '#A66A4C',
        borderWidth: 2,
        backgroundColor: gradient,
        fill: true,
        tension: 0.2,
        pointBackgroundColor: '#E8E0D2',
        pointBorderColor: '#A66A4C',
        pointRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        x: { grid: { color: 'rgba(232, 224, 210, 0.05)' } },
        y: {
          grid: { color: 'rgba(232, 224, 210, 0.08)' },
          beginAtZero: true,
          ticks: { stepSize: 1 }
        }
      }
    }
  });
}
