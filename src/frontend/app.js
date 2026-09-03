/**
 * Federated Campus Energy Cloud — Operations Dashboard
 * Student 1 · Phase I prototype · app.js
 *
 * Simulates live telemetry updates, chart animation, countdown timer,
 * tab switching, and alert dismissal. No external dependencies.
 */

'use strict';

/* ── Simulated telemetry data ────────────────────────────────────── */
const SIMULATED_DATA = {
  demandBase: 842,   // kW
  peakReduction: 24.2,
  savings: 8460,
  clients: [5, 5],
  privacyEpsilon: 1.05,

  // Bar chart heights (%) for 12h → 23h
  bars: [36, 47, 58, 66, 72, 84, 97, 79, 63, 51, 41, 68],
};

/* ── DOM references ──────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);

const valDemand   = $('val-demand');
const valPeak     = $('val-peak');
const valSavings  = $('val-savings');
const valClients  = $('val-clients');
const valPrivacy  = $('val-privacy');

const refreshAllBtn = $('refresh-all');
const dismissAlert  = $('dismiss-alert');
const alertBanner   = $('alert-banner');
const liveText      = $('live-text');
const liveIndicator = $('live-indicator');

const nextRoundTimer = $('next-round-timer');
const applyBtn       = $('apply-schedule-btn');
const viewPolicyBtn  = $('view-policy-btn');
const exportBtn      = $('export-btn');

const tabs       = document.querySelectorAll('.tab');
const navLinks   = document.querySelectorAll('.nav-link');

/* ── Utility ─────────────────────────────────────────────────────── */
function rand(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function formatINR(n) {
  return '₹ ' + n.toLocaleString('en-IN');
}

/* ── Alert dismiss ───────────────────────────────────────────────── */
if (dismissAlert) {
  dismissAlert.addEventListener('click', () => {
    alertBanner.classList.add('hidden');
  });
}

/* ── Tab switching ───────────────────────────────────────────────── */
tabs.forEach((tab) => {
  tab.addEventListener('click', () => {
    tabs.forEach((t) => {
      t.classList.remove('tab--active');
      t.setAttribute('aria-selected', 'false');
    });
    tab.classList.add('tab--active');
    tab.setAttribute('aria-selected', 'true');
    animateBars(); // re-animate bars on period change
  });
});

/* ── Smooth-scroll navigation ────────────────────────────────────── */
navLinks.forEach((link) => {
  link.addEventListener('click', (e) => {
    const href = link.getAttribute('href');
    if (href && href.startsWith('#')) {
      e.preventDefault();
      const target = document.querySelector(href);
      if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      navLinks.forEach((l) => l.classList.remove('active'));
      link.classList.add('active');
    }
  });
});

/* ── Chart bar animation ─────────────────────────────────────────── */
function animateBars() {
  const barEls = document.querySelectorAll('.bar');
  barEls.forEach((bar, i) => {
    const base  = SIMULATED_DATA.bars[i] ?? 50;
    const jitter = rand(-6, 6);
    const pct   = Math.min(99, Math.max(8, base + jitter));
    setTimeout(() => {
      bar.style.setProperty('--h', pct + '%');
    }, i * 40);
  });
}

/* ── Telemetry refresh ───────────────────────────────────────────── */
function refreshTelemetry(isManual = false) {
  // Flash live indicator
  liveText.textContent = isManual ? 'Refreshing…' : 'Updating…';
  liveIndicator.style.opacity = '.5';

  setTimeout(() => {
    // Demand
    const demand = SIMULATED_DATA.demandBase + rand(-30, 40);
    valDemand.textContent = demand + ' kW';

    // Peak reduction
    const peak = (SIMULATED_DATA.peakReduction + (rand(-5, 5) / 10)).toFixed(1);
    valPeak.textContent = peak + '%';

    // Savings
    const savings = SIMULATED_DATA.savings + rand(-200, 300);
    valSavings.textContent = formatINR(savings);

    // Privacy
    const eps = (1.0 + rand(0, 15) / 100).toFixed(2);
    valPrivacy.textContent = 'ε = ' + eps;

    // Animate bars
    animateBars();

    liveText.textContent = 'Live telemetry';
    liveIndicator.style.opacity = '1';

    if (isManual) {
      refreshAllBtn.disabled = false;
      refreshAllBtn.title = 'Refresh all data';
    }
  }, 700);
}

/* ── Manual refresh button ───────────────────────────────────────── */
if (refreshAllBtn) {
  refreshAllBtn.addEventListener('click', () => {
    refreshAllBtn.disabled = true;
    refreshAllBtn.title = 'Refreshing…';
    refreshTelemetry(true);
  });
}

/* ── Countdown to next federation round ──────────────────────────── */
let secondsLeft = 4 * 60 + 38; // 04:38

function updateCountdown() {
  if (!nextRoundTimer) return;
  if (secondsLeft <= 0) {
    nextRoundTimer.textContent = '00:00';
    nextRoundTimer.style.color = '#22c55e';
    return;
  }
  const mm = String(Math.floor(secondsLeft / 60)).padStart(2, '0');
  const ss = String(secondsLeft % 60).padStart(2, '0');
  nextRoundTimer.textContent = mm + ':' + ss;
  secondsLeft--;
}

setInterval(updateCountdown, 1000);
updateCountdown();

/* ── Auto telemetry refresh every 30 s ──────────────────────────── */
setInterval(() => refreshTelemetry(false), 30_000);

/* ── Apply schedule button ───────────────────────────────────────── */
if (applyBtn) {
  applyBtn.addEventListener('click', () => {
    const orig = applyBtn.textContent;
    applyBtn.textContent = 'Sending to BMS…';
    applyBtn.disabled = true;
    setTimeout(() => {
      applyBtn.textContent = '✓ Schedule applied';
      applyBtn.style.background = 'var(--green)';
      applyBtn.style.color = '#fff';
      setTimeout(() => {
        applyBtn.textContent = orig;
        applyBtn.style.background = '';
        applyBtn.style.color = '';
        applyBtn.disabled = false;
      }, 3000);
    }, 1200);
  });
}

/* ── View policy button ──────────────────────────────────────────── */
if (viewPolicyBtn) {
  viewPolicyBtn.addEventListener('click', () => {
    alert(
      'Control policy (simulated)\n\n' +
      '• HVAC: lower set-point by 1°C between 16:30 and 17:15\n' +
      '• EV charging stations: capped at 40% of rated capacity 18:00-19:00\n' +
      '• Battery: dispatch 120 kW at 18:00 to reduce grid draw\n' +
      '• Constraints: occupancy comfort and battery SoC limits enforced\n\n' +
      'Source: Lambda optimiser · DynamoDB tariff schedule'
    );
  });
}

/* ── CSV export (simulated) ──────────────────────────────────────── */
if (exportBtn) {
  exportBtn.addEventListener('click', () => {
    const rows = [
      ['Facility', 'Quality', 'Epsilon', 'Samples', 'Weight', 'Latency', 'Status'],
      ['Engineering Block', '0.94', '1.0', '12480', '0.32', '1.2s', 'Validated'],
      ['Library',           '0.91', '1.0', '9320',  '0.28', '0.9s', 'Validated'],
      ['Hostel Complex',    '0.88', '1.2', '14760', '0.21', '1.7s', 'Validated'],
      ['Science Labs',      '0.95', '0.9', '8100',  '0.11', '0.8s', 'Validated'],
      ['Admin Block',       '0.89', '1.1', '6940',  '0.08', '1.1s', 'Validated'],
    ];
    const csv  = rows.map((r) => r.join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url;
    a.download = 'federated_round_24.csv';
    a.click();
    URL.revokeObjectURL(url);
  });
}

/* ── Initial animations on load ──────────────────────────────────── */
window.addEventListener('DOMContentLoaded', () => {
  // Stagger KPI card entrance
  document.querySelectorAll('.kpi-card').forEach((card, i) => {
    card.style.opacity = '0';
    card.style.transform = 'translateY(16px)';
    card.style.transition = `opacity .4s ease ${i * 60}ms, transform .4s ease ${i * 60}ms`;
    setTimeout(() => {
      card.style.opacity = '1';
      card.style.transform = 'translateY(0)';
    }, 50);
  });

  // Animate bars on load
  setTimeout(animateBars, 300);
});
