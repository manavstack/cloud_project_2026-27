/**
 * Federated Campus Energy Cloud — Operations Dashboard
 * Student 1 · Phase I prototype · app.js
 *
 * Integrated with AWS via aws-config.js.
 * Automatically falls back to Demo Mode if AWS is not configured.
 */

'use strict';

/* ── DOM References ──────────────────────────────────────────────────────── */
const $ = (id) => document.getElementById(id);

const valDemand      = $('val-demand');
const valPeak        = $('val-peak');
const valSavings     = $('val-savings');
const valClients     = $('val-clients');
const valPrivacy     = $('val-privacy');

const liveIndicator  = $('live-indicator');
const liveText       = $('live-text');
const pulseDot       = $('pulse-dot');
const modePill       = $('mode-pill');
const refreshAllBtn  = $('refresh-all');

const alertBanner    = $('alert-banner');
const alertText      = $('alert-text');
const dismissAlert   = $('dismiss-alert');

const loginOverlay   = $('login-overlay');
const loginForm      = $('login-form');
const loginError     = $('login-error');
const loginBtn       = $('login-btn');
const signoutBtn     = $('signout-btn');

const fedRoundLabel  = $('fed-round-label');
const fedTbody       = $('federation-tbody');
const fedBadge       = $('fed-badge');
const exportBtn      = $('export-btn');
const nextRoundTimer = $('next-round-timer');

const applyBtn       = $('apply-schedule-btn');
const viewPolicyBtn  = $('view-policy-btn');
const scheduleBadge  = $('schedule-badge');
const actHvacTime    = $('act-hvac-time');
const actEvTime      = $('act-ev-time');
const actBatTime     = $('act-bat-time');

const statMae        = $('stat-mae');
const statRmse       = $('stat-rmse');
const statCvrmse     = $('stat-cvrmse');
const statMape       = $('stat-mape');

const tariffCurrent  = $('tariff-current');
const tariffPeak     = $('tariff-peak');
const tariffOffpeak  = $('tariff-offpeak');
const tariffSource   = $('tariff-source');

const privacyMeters  = $('privacy-meters');
const dataNotice     = $('data-notice');
const dataModeText   = $('data-mode-text');

const tabs           = document.querySelectorAll('.tab');
const navLinks       = document.querySelectorAll('.nav-link');

/* ── Global State ────────────────────────────────────────────────────────── */
let currentSession = null;
let wsConnection = null;
const isLiveMode = !window.AWS_DEMO_MODE;
const cfg = window.AWS_CONFIG;

/* ── Initialization ──────────────────────────────────────────────────────── */
async function init() {
  setupUI();

  if (isLiveMode) {
    modePill.textContent = 'Live';
    modePill.classList.add('mode-pill--live');
    liveText.textContent = 'Connecting…';
    dataModeText.textContent = 'pulled directly from AWS';

    await loadAmplifySDK();
    configureAmplify();
    await checkAuthSession();
  } else {
    // Demo mode: run simulated logic
    modePill.textContent = 'Demo';
    liveText.textContent = 'Demo Mode';
    dataModeText.textContent = 'simulated';
    runDemoMode();
  }
}

function setupUI() {
  // Tab switching
  tabs.forEach((tab) => {
    tab.addEventListener('click', () => {
      tabs.forEach((t) => { t.classList.remove('tab--active'); t.setAttribute('aria-selected', 'false'); });
      tab.classList.add('tab--active'); tab.setAttribute('aria-selected', 'true');
      animateBars();
    });
  });

  // Smooth scroll
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

  // Alert dismiss
  if (dismissAlert) {
    dismissAlert.addEventListener('click', () => alertBanner.classList.add('hidden'));
  }

  // View Policy
  if (viewPolicyBtn) {
    viewPolicyBtn.addEventListener('click', () => {
      alert(
        'Control policy (Active)\n\n' +
        '• HVAC: lower set-point by 1°C before peak\n' +
        '• EV charging: capped at 40% during peak\n' +
        '• Battery: discharge to reduce grid draw\n\n' +
        'Constraints: comfort limits and SoC limits strictly enforced.'
      );
    });
  }
}

/* ── AWS Amplify / Auth (Live Mode Only) ─────────────────────────────────── */
function loadAmplifySDK() {
  return new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/aws-amplify@5.3.11/dist/aws-amplify.min.js';
    script.onload = resolve;
    script.onerror = reject;
    document.head.appendChild(script);
  });
}

function configureAmplify() {
  const { Auth, API } = window.aws_amplify;
  Auth.configure({
    region: cfg.region,
    userPoolId: cfg.cognito.userPoolId,
    userPoolWebClientId: cfg.cognito.userPoolWebClientId,
  });
  API.configure({
    endpoints: [{ name: 'CampusAPI', endpoint: cfg.apiGateway.restUrl }]
  });
}

async function checkAuthSession() {
  const { Auth } = window.aws_amplify;
  try {
    currentSession = await Auth.currentSession();
    startLiveDashboard();
  } catch (err) {
    // Not logged in -> show login modal
    loginOverlay.hidden = false;
  }

  // Handle Login form
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginBtn.disabled = true;
    loginBtn.textContent = 'Signing in...';
    loginError.textContent = '';
    
    const email = $('login-email').value;
    const pwd = $('login-password').value;
    
    try {
      const user = await Auth.signIn(email, pwd);
      
      if (user.challengeName === 'NEW_PASSWORD_REQUIRED') {
        const newPwd = prompt('Please set a permanent password:');
        if (newPwd) {
          await Auth.completeNewPassword(user, newPwd);
          currentSession = await Auth.currentSession();
        } else {
          throw new Error('Password change cancelled.');
        }
      } else {
        currentSession = await Auth.currentSession();
      }
      
      loginOverlay.hidden = true;
      startLiveDashboard();
    } catch (err) {
      loginError.textContent = err.message || 'Sign in failed';
    } finally {
      loginBtn.disabled = false;
      loginBtn.textContent = 'Sign in';
    }
  });

  // Handle Sign out
  signoutBtn.hidden = false;
  signoutBtn.addEventListener('click', async () => {
    await Auth.signOut();
    window.location.reload();
  });
}

/* ── Live Mode ───────────────────────────────────────────────────────────── */
function startLiveDashboard() {
  liveText.textContent = 'Live telemetry';
  pulseDot.style.background = '#34c77b';
  
  // Initial load
  fetchForecast();
  fetchFederation();
  fetchSchedule();
  fetchTariffs();
  
  // Establish WebSocket for alerts/real-time push
  connectWebSocket();

  // Setup refresh button
  refreshAllBtn.addEventListener('click', async () => {
    refreshAllBtn.disabled = true;
    liveText.textContent = 'Refreshing...';
    pulseDot.style.opacity = '0.5';
    
    await Promise.all([
      fetchForecast(),
      fetchFederation(),
      fetchSchedule(),
      fetchTariffs()
    ]);
    
    refreshAllBtn.disabled = false;
    liveText.textContent = 'Live telemetry';
    pulseDot.style.opacity = '1';
  });

  // Setup apply schedule
  applyBtn.addEventListener('click', async () => {
    const origText = applyBtn.textContent;
    applyBtn.textContent = 'Sending to IoT Core...';
    applyBtn.disabled = true;
    
    try {
      const { API } = window.aws_amplify;
      const token = currentSession.getIdToken().getJwtToken();
      
      // We will just read the DOM for the actions to send
      const actions = [
        { name: 'HVAC pre-cooling', time: actHvacTime.textContent },
        { name: 'EV charging cap', time: actEvTime.textContent },
        { name: 'Battery dispatch', time: actBatTime.textContent }
      ];
      
      await API.post('CampusAPI', '/schedule', {
        headers: { Authorization: token },
        body: { actions: actions, round: 24 }
      });
      
      applyBtn.textContent = '✓ Sent to BMS';
      applyBtn.style.background = 'var(--green)';
      applyBtn.style.color = '#fff';
      scheduleBadge.textContent = 'Active via BMS';
    } catch (err) {
      alert('Failed to apply schedule: ' + err.message);
      applyBtn.textContent = origText;
    } finally {
      setTimeout(() => {
        applyBtn.textContent = origText;
        applyBtn.style.background = '';
        applyBtn.style.color = '';
        applyBtn.disabled = false;
      }, 3000);
    }
  });

  // Setup export CSV
  exportBtn.addEventListener('click', async () => {
    exportBtn.disabled = true;
    exportBtn.textContent = 'Generating link...';
    try {
      const { API } = window.aws_amplify;
      const token = currentSession.getIdToken().getJwtToken();
      const res = await API.get('CampusAPI', '/export', {
        headers: { Authorization: token }
      });
      if (res.downloadUrl) {
        window.location.href = res.downloadUrl;
      }
    } catch (err) {
      alert('Export failed: ' + err.message);
    } finally {
      exportBtn.disabled = false;
      exportBtn.textContent = 'Export CSV';
    }
  });

  startTimer();
}

// ── API Fetchers ──
async function fetchForecast() {
  try {
    const { API } = window.aws_amplify;
    const token = currentSession.getIdToken().getJwtToken();
    const data = await API.get('CampusAPI', '/forecast', {
      headers: { Authorization: token }
    });
    
    valDemand.textContent = `${data.predictedDemandKw} kW`;
    valPeak.textContent = `${data.peakReductionPct}%`;
    valSavings.textContent = formatINR(data.savingsINR);
    valClients.textContent = data.activeClients;
    valPrivacy.textContent = `ε = ${data.privacyEpsilonAvg}`;
    
    window.SIMULATED_BARS = data.hourlyBars || window.SIMULATED_BARS;
    animateBars();
  } catch (err) {
    console.error('Fetch forecast error:', err);
  }
}

async function fetchFederation() {
  try {
    const { API } = window.aws_amplify;
    const token = currentSession.getIdToken().getJwtToken();
    const data = await API.get('CampusAPI', '/federation?round=latest', {
      headers: { Authorization: token }
    });
    
    fedRoundLabel.textContent = `FEDERATED ROUND ${data.roundNumber}`;
    fedBadge.textContent = data.allValidated ? 'All validated' : 'Validation pending';
    
    fedTbody.innerHTML = '';
    privacyMeters.innerHTML = '';
    
    data.clients.forEach(c => {
      // Table row
      const tr = document.createElement('tr');
      const isOk = c.status === 'Validated';
      const statusClass = isOk ? 'status-pill--ok' : 'status-pill--warn';
      const dotClass = isOk ? 'facility-dot--green' : 'facility-dot--warn';
      
      tr.innerHTML = `
        <td><span class="facility-dot ${dotClass}"></span>${c.facility}</td>
        <td><div class="quality-bar-wrap"><div class="quality-bar" style="width:${c.quality*100}%"></div><span>${c.quality.toFixed(2)}</span></div></td>
        <td>${c.epsilon.toFixed(1)}</td>
        <td>${c.samples.toLocaleString()}</td>
        <td>${c.weight.toFixed(2)}</td>
        <td>${c.latencyS} s</td>
        <td><span class="status-pill ${statusClass}">${c.status}</span></td>
      `;
      fedTbody.appendChild(tr);

      // Privacy meter
      const pRow = document.createElement('div');
      pRow.className = 'privacy-row';
      const pct = (c.epsilon / 2.0) * 100;
      const barClass = pct > 55 ? 'privacy-bar privacy-bar--warn' : 'privacy-bar';
      pRow.innerHTML = `
        <span class="privacy-label">${c.facility}</span>
        <div class="privacy-bar-wrap" role="meter" aria-valuenow="${pct}" aria-valuemin="0" aria-valuemax="100">
          <div class="${barClass}" style="--w:${pct}%"></div>
        </div>
        <span class="privacy-val">ε ${c.epsilon.toFixed(1)}</span>
      `;
      privacyMeters.appendChild(pRow);
    });

  } catch (err) {
    console.error('Fetch federation error:', err);
  }
}

async function fetchSchedule() {
  try {
    const { API } = window.aws_amplify;
    const token = currentSession.getIdToken().getJwtToken();
    const data = await API.get('CampusAPI', '/schedule', {
      headers: { Authorization: token }
    });
    
    if (data.status === 'approved') {
      scheduleBadge.textContent = 'Approved by ' + data.approvedBy;
      
      data.actions.forEach(a => {
        if (a.name.includes('HVAC')) actHvacTime.textContent = a.time;
        if (a.name.includes('EV')) actEvTime.textContent = a.time;
        if (a.name.includes('Battery')) actBatTime.textContent = a.time;
      });
    }
  } catch (err) {
    console.error('Fetch schedule error:', err);
  }
}

async function fetchTariffs() {
  try {
    const { API } = window.aws_amplify;
    const token = currentSession.getIdToken().getJwtToken();
    const data = await API.get('CampusAPI', '/tariffs', {
      headers: { Authorization: token }
    });
    
    tariffCurrent.textContent = `₹ ${data.currentRateKwh.toFixed(2)}/kWh`;
    tariffPeak.textContent = `₹ ${data.peakRateKwh.toFixed(2)}/kWh`;
    tariffOffpeak.textContent = `₹ ${data.offPeakRateKwh.toFixed(2)}/kWh`;
    tariffSource.textContent = data.source || 'DynamoDB tariffs';
  } catch (err) {
    console.error('Fetch tariffs error:', err);
  }
}

function connectWebSocket() {
  if (!cfg.websocket.url || cfg.websocket.url === 'REPLACE_ME') return;
  
  // Need to pass the token so the $connect authorizer succeeds
  const token = currentSession.getIdToken().getJwtToken();
  const wsUrl = `${cfg.websocket.url}?Auth=${token}`;
  
  wsConnection = new WebSocket(wsUrl);
  
  wsConnection.onopen = () => {
    console.log('[WS] Connected for real-time alerts');
  };
  
  wsConnection.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data);
      if (msg.type === 'alert' && msg.data) {
        // Show alert banner
        alertText.innerHTML = msg.data.message;
        alertBanner.classList.remove('hidden');
      }
    } catch (err) {
      console.error('[WS] Message error:', err);
    }
  };
  
  wsConnection.onclose = () => {
    console.log('[WS] Disconnected, attempting reconnect in 5s...');
    setTimeout(connectWebSocket, 5000);
  };
}

/* ── Demo Mode (Simulated fallback) ──────────────────────────────────────── */
window.SIMULATED_BARS = [36, 47, 58, 66, 72, 84, 97, 79, 63, 51, 41, 68];

function runDemoMode() {
  // Polling simulated data
  setInterval(refreshSimulatedTelemetry, 30000);

  if (refreshAllBtn) {
    refreshAllBtn.addEventListener('click', () => {
      refreshAllBtn.disabled = true;
      refreshSimulatedTelemetry(true);
    });
  }

  if (applyBtn) {
    applyBtn.addEventListener('click', () => {
      const orig = applyBtn.textContent;
      applyBtn.textContent = 'Sending to BMS...';
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

  if (exportBtn) {
    exportBtn.addEventListener('click', () => {
      alert('CSV Export is disabled in Demo Mode. Deploy AWS to enable.');
    });
  }

  setTimeout(animateBars, 300);
  startTimer();
}

function refreshSimulatedTelemetry(manual = false) {
  liveText.textContent = manual ? 'Refreshing…' : 'Updating…';
  pulseDot.style.opacity = '.5';

  setTimeout(() => {
    const demand = 842 + rand(-30, 40);
    valDemand.textContent = demand + ' kW';

    const peak = (24.2 + (rand(-5, 5) / 10)).toFixed(1);
    valPeak.textContent = peak + '%';

    const savings = 8460 + rand(-200, 300);
    valSavings.textContent = formatINR(savings);

    const eps = (1.0 + rand(0, 15) / 100).toFixed(2);
    valPrivacy.textContent = 'ε = ' + eps;

    animateBars();

    liveText.textContent = 'Demo Mode';
    pulseDot.style.opacity = '1';

    if (manual) {
      refreshAllBtn.disabled = false;
    }
  }, 700);
}


/* ── Shared Utilities ────────────────────────────────────────────────────── */

function animateBars() {
  const barEls = document.querySelectorAll('.bar');
  const barsData = window.SIMULATED_BARS;
  
  barEls.forEach((bar, i) => {
    const base  = barsData[i] ?? 50;
    const jitter = window.AWS_DEMO_MODE ? rand(-6, 6) : 0; // Only jitter in demo mode
    const pct   = Math.min(99, Math.max(8, base + jitter));
    setTimeout(() => {
      bar.style.setProperty('--h', pct + '%');
    }, i * 40);
  });
}

function rand(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function formatINR(n) {
  return '₹ ' + n.toLocaleString('en-IN');
}

// Countdown to next federation round
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

function startTimer() {
  setInterval(updateCountdown, 1000);
  updateCountdown();
}

/* ── Boot ────────────────────────────────────────────────────────────────── */
window.addEventListener('DOMContentLoaded', init);
