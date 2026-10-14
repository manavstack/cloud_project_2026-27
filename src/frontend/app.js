const $ = (selector) => document.querySelector(selector);
const numberFormat = new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 });
const integerFormat = new Intl.NumberFormat();
let dashboard = null;
let modelMetrics = null;

function formatNumber(value) {
  return value == null || !Number.isFinite(Number(value)) ? "—" : numberFormat.format(Number(value));
}

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString();
}

function formatUtcTimestamp(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : `${date.toISOString().replace("T", " ").slice(0, 16)} UTC`;
}

async function request(url, options) {
  const response = await fetch(url, options);
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}

function showMessage(selector, message, error = false) {
  const element = $(selector);
  element.textContent = message;
  element.classList.toggle("error", error);
}

function drawChart(svg, points, { valueKey, timeKey, colorClass = "series-line", forecast = false } = {}) {
  if (!points?.length) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" class="axis-label">No data available</text>';
    return;
  }
  const width = svg.viewBox.baseVal.width || 960;
  const height = svg.viewBox.baseVal.height || 300;
  const pad = { left: 55, right: 14, top: 18, bottom: 34 };
  const values = points.map((point) => Number(point[valueKey])).filter(Number.isFinite);
  if (!values.length) {
    svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" class="axis-label">No numeric values to chart</text>';
    return;
  }
  const min = Math.min(0, ...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const x = (index) => pad.left + index * (width - pad.left - pad.right) / Math.max(points.length - 1, 1);
  const y = (value) => pad.top + (height - pad.top - pad.bottom) * (1 - (value - min) / span);
  const path = points.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(Number(point[valueKey])).toFixed(1)}`).join(" ");
  const grid = Array.from({ length: 4 }, (_, index) => {
    const gridY = pad.top + index * (height - pad.top - pad.bottom) / 3;
    const value = max - index * span / 3;
    return `<line x1="${pad.left}" y1="${gridY}" x2="${width - pad.right}" y2="${gridY}" class="grid-line"/><text x="${pad.left - 8}" y="${gridY + 3}" text-anchor="end" class="axis-label">${formatNumber(value)}</text>`;
  }).join("");
  const labels = [0, Math.floor((points.length - 1) / 2), points.length - 1]
    .filter((index, position, list) => list.indexOf(index) === position)
    .map((index) => `<text x="${x(index)}" y="${height - 8}" text-anchor="middle" class="axis-label">${forecast ? new Date(points[index][timeKey]).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", timeZone: "UTC", timeZoneName: "short" }) : formatDate(points[index][timeKey])}</text>`)
    .join("");
  const area = forecast ? "" : `<path d="${path} L${x(points.length - 1)},${height - pad.bottom} L${x(0)},${height - pad.bottom} Z" class="series-area"/>`;
  const dots = forecast ? points.map((point, index) => `<circle cx="${x(index)}" cy="${y(Number(point[valueKey]))}" r="2.2" class="forecast-dot"><title>${formatUtcTimestamp(point[timeKey])}: ${formatNumber(point[valueKey])}</title></circle>`).join("") : "";
  const gradient = forecast ? "" : '<defs><linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#6fe0bb" stop-opacity=".62"/><stop offset="1" stop-color="#6fe0bb" stop-opacity="0"/></linearGradient></defs>';
  svg.innerHTML = `${gradient}${grid}${area}<path d="${path}" class="${colorClass}"/>${dots}${labels}`;
}

function renderDashboard(data) {
  dashboard = data;
  const group = data.groups.find((item) => item.key === data.selected_group_key);
  if (!group) throw new Error("Selected dataset summary was not returned");
  $("#stat-observations").textContent = integerFormat.format(group.observations);
  $("#stat-assets").textContent = integerFormat.format(group.assets);
  $("#stat-average").textContent = formatNumber(group.mean);
  $("#stat-date-range").textContent = `${formatDate(group.first_reading)} — ${formatDate(group.last_reading)}`;
  $("#stat-unit").textContent = `${group.unit} · ${group.energy_vector} · ${group.interval_minutes}-minute cadence`;
  $("#chart-unit").textContent = group.unit;
  $("#asset-count-label").textContent = `${integerFormat.format(data.assets.length)} assets`;
  document.querySelectorAll(".unit-label").forEach((element) => { element.textContent = group.unit; });
  const quality = data.quality;
  $("#quality-zeros").textContent = integerFormat.format(quality.zero_readings);
  $("#quality-negatives").textContent = integerFormat.format(quality.negative_readings);
  $("#quality-p95").textContent = formatNumber(quality.p95);
  $("#quality-gaps").textContent = integerFormat.format(quality.off_cadence_transitions);
  $("#quality-largest-gap").textContent = quality.largest_gap_hours == null ? "—" : `${formatNumber(quality.largest_gap_hours)} h`;
  $("#quality-recommendation").textContent = quality.off_cadence_transitions
    ? `${integerFormat.format(quality.off_cadence_transitions)} transitions do not match the nominal cadence; the largest gap is ${formatNumber(quality.largest_gap_hours)} hours. Lag features use prior observed rows rather than interpolated readings. Review outages and zero values before operational use.`
    : "Observed timestamps match the nominal cadence. Review zero readings and outliers with source documentation before operational use.";

  const sourceSelect = $("#source-select");
  sourceSelect.replaceChildren(...data.groups.map((item) => new Option(item.label, item.key)));
  sourceSelect.value = data.selected_group_key;
  const assetSelect = $("#asset-select");
  const sourceAssets = data.assets.filter((asset) => asset.source === group.source);
  assetSelect.replaceChildren(...sourceAssets.map((asset) => new Option(asset.asset_id, asset.asset_id)));
  assetSelect.disabled = sourceAssets.length === 0;

  const rows = $("#asset-rows");
  rows.replaceChildren(...sourceAssets.map((asset) => {
    const tr = document.createElement("tr");
    const cells = [
      asset.asset_id, integerFormat.format(asset.observations), formatDate(asset.first_reading),
      formatDate(asset.last_reading), formatNumber(asset.mean), formatNumber(asset.minimum), formatNumber(asset.maximum),
    ];
    cells.forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.append(td);
    });
    return tr;
  }));

  const daily = data.daily;
  $("#daily-caption").textContent = `Daily sums across ${group.assets} asset${group.assets === 1 ? "" : "s"} · ${group.unit}`;
  drawChart($("#history-chart"), daily, { valueKey: "total", timeKey: "day" });
}

function renderFederated(data) {
  const participants = data.participants || [];
  const excluded = data.excluded_datasets || [];
  $("#federated-client-count").textContent = integerFormat.format(participants.length);
  $("#federated-round-count").textContent = integerFormat.format(data.training.rounds);
  $("#federated-observation-count").textContent = integerFormat.format(
    participants.reduce((total, client) => total + client.train_observations, 0),
  );
  $("#federated-excluded-count").textContent = integerFormat.format(excluded.length);
  const baseline = data.global_weights || [];
  const names = data.global_weight_names || [];
  $("#federated-weight-rows").replaceChildren(...names.map((name, index) => {
    const row = document.createElement("tr");
    const label = document.createElement("td");
    label.textContent = name;
    const value = document.createElement("td");
    value.textContent = formatNumber(baseline[index]);
    row.append(label, value);
    return row;
  }));
  const roundHeader = document.createElement("tr");
  ["Round", ...names].forEach((name) => {
    const cell = document.createElement("th");
    cell.textContent = name;
    roundHeader.append(cell);
  });
  $("#federated-round-header").replaceChildren(roundHeader);
  $("#federated-round-rows").replaceChildren(...(data.round_history || []).map((round) => {
    const row = document.createElement("tr");
    [integerFormat.format(round.round), ...round.global_weights.map(formatNumber)].forEach((text) => {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.append(cell);
    });
    return row;
  }));
  $("#federated-client-rows").replaceChildren(...participants.map((client) => {
    const row = document.createElement("tr");
    const values = [
      client.client_id,
      `${client.source} · ${client.target_unit}`,
      `${integerFormat.format(client.train_observations)} / ${integerFormat.format(client.test_observations)}`,
      formatNumber(client.metrics.normalized_mae),
    ];
    values.forEach((text) => {
      const cell = document.createElement("td");
      cell.textContent = text;
      row.append(cell);
    });
    return row;
  }));
  $("#federated-exclusions").replaceChildren(...(excluded.length ? excluded : [{ dataset: "None", reason: "All discovered datasets participated." }]).map((item) => {
    const entry = document.createElement("li");
    entry.textContent = `${item.dataset}: ${item.reason}`;
    return entry;
  }));
  showMessage(
    "#federated-message",
    `${data.model} · ${data.federation_mode}. Local target values are normalized before aggregation; absolute scale remains campus-local.`,
  );
}

async function loadFederated() {
  try {
    renderFederated(await request("/api/federated"));
  } catch (error) {
    showMessage("#federated-message", error.message, true);
  }
}

function renderModelStatus() {
  if (!modelMetrics) {
    $("#stat-model").textContent = "Not trained";
    $("#stat-model-note").textContent = "Train with a chronological holdout";
    $("#metric-mae").textContent = "—";
    $("#metric-baseline").textContent = "—";
    $("#metric-rmse").textContent = "—";
    $("#metric-test-count").textContent = "—";
    return;
  }
  $("#stat-model").textContent = modelMetrics.model_beats_baseline ? "Beats baseline" : "Baseline leads";
  $("#stat-model-note").textContent = `${integerFormat.format(modelMetrics.test_observations)} held-out readings`;
  $("#metric-mae").textContent = formatNumber(modelMetrics.metrics.mae);
  $("#metric-baseline").textContent = formatNumber(modelMetrics.baseline_metrics.mae);
  $("#metric-rmse").textContent = formatNumber(modelMetrics.metrics.rmse);
  $("#metric-test-count").textContent = integerFormat.format(modelMetrics.test_observations);
  if (modelMetrics.data_is_current === false) {
    $("#stat-model").textContent = "Retrain needed";
    $("#stat-model-note").textContent = "Stored data changed since training";
    $("#analysis-callout").textContent = "The stored dataset changed after this experiment. Retrain before interpreting these metrics or requesting a forecast.";
    return;
  }
  $("#analysis-callout").textContent = modelMetrics.model_beats_baseline
    ? `On ${integerFormat.format(modelMetrics.test_observations)} later-in-time readings, the model’s MAE was ${formatNumber(modelMetrics.metrics.mae)} ${modelMetrics.unit}, compared with ${formatNumber(modelMetrics.baseline_metrics.mae)} ${modelMetrics.unit} for the 24-step seasonal baseline.`
    : `The model did not outperform the 24-step seasonal baseline on held-out data: MAE ${formatNumber(modelMetrics.metrics.mae)} ${modelMetrics.unit} versus ${formatNumber(modelMetrics.baseline_metrics.mae)} ${modelMetrics.unit}. Treat the baseline as the current stronger option.`;
}

async function loadDashboard() {
  $("#refresh-button").disabled = true;
  try {
    const groupKey = $("#source-select").value;
    const query = groupKey ? `?group=${encodeURIComponent(groupKey)}` : "";
    renderDashboard(await request(`/api/dashboard${query}`));
    const statusQuery = new URLSearchParams({ group: $("#source-select").value });
    const status = await request(`/api/model/status?${statusQuery}`);
    modelMetrics = status.trained ? status : null;
    renderModelStatus();
    if (modelMetrics && modelMetrics.data_is_current === false) {
      showMessage("#model-message", "The stored data changed since this model was trained. Retrain before forecasting.", true);
    } else if (modelMetrics) {
      showMessage("#model-message", `Saved experiment ${modelMetrics.experiment_id} · chronological cutoff ${formatDate(modelMetrics.cutoff)}.`);
    }
    $("#connection-label").textContent = "PostgreSQL connected";
    $(".pulse").classList.add("online");
  } catch (error) {
    showMessage("#model-message", error.message, true);
    $("#connection-label").textContent = "Database unavailable";
    $(".pulse").classList.remove("online");
  } finally {
    $("#refresh-button").disabled = false;
  }
}

async function train() {
  const button = $("#train-button");
  button.disabled = true;
  button.textContent = "Training…";
  showMessage("#model-message", "Training and evaluating on a chronological holdout. Larger datasets may take a little while.");
  try {
    modelMetrics = await request("/api/train", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ group_key: $("#source-select").value }),
    });
    modelMetrics.data_is_current = true;
    renderModelStatus();
    showMessage("#model-message", `Trained on ${integerFormat.format(modelMetrics.train_observations)} observations; evaluated on a later ${integerFormat.format(modelMetrics.test_observations)}. Split cutoff: ${formatDate(modelMetrics.cutoff)}.`);
    await predict();
  } catch (error) {
    showMessage("#model-message", error.message, true);
  } finally {
    button.disabled = false;
    button.textContent = "Train & evaluate";
  }
}

async function predict() {
  const groupKey = $("#source-select").value;
  const asset = $("#asset-select").value;
  const horizon = $("#horizon-select").value;
  if (!groupKey || !asset) {
    showMessage("#forecast-message", "Select a source and asset first.", true);
    return;
  }
  $("#forecast-button").disabled = true;
  showMessage("#forecast-message", "Generating forecast…");
  try {
    const query = new URLSearchParams({ group: groupKey, asset, horizon });
    const result = await request(`/api/model?${query}`);
    drawChart($("#forecast-chart"), result.predictions, { valueKey: "value", timeKey: "time", colorClass: "forecast-line", forecast: true });
    $("#forecast-rows").replaceChildren(...result.predictions.map((item) => {
      const row = document.createElement("tr");
      const time = document.createElement("td");
      time.textContent = formatUtcTimestamp(item.time);
      const value = document.createElement("td");
      value.textContent = `${formatNumber(item.value)} ${result.unit}`;
      row.append(time, value);
      return row;
    }));
    showMessage("#forecast-message", `${result.horizon} nominal ${result.interval_minutes}-minute steps for ${result.asset_id} · ${result.unit} · from the latest stored observation at ${formatUtcTimestamp(result.forecast_origin)}. This is a historical projection, not a current live forecast.`);
  } catch (error) {
    showMessage("#forecast-message", error.message, true);
    $("#forecast-rows").innerHTML = '<tr><td colspan="2" class="empty-cell">No forecast available</td></tr>';
  } finally {
    $("#forecast-button").disabled = false;
  }
}

$("#refresh-button").addEventListener("click", loadDashboard);
$("#source-select").addEventListener("change", async () => {
  modelMetrics = null;
  renderModelStatus();
  await loadDashboard();
  $("#forecast-chart").innerHTML = "";
  $("#forecast-rows").innerHTML = '<tr><td colspan="2" class="empty-cell">Train the selected source to generate predictions</td></tr>';
  showMessage("#forecast-message", "Train the selected source to enable forecasts.");
});
$("#train-button").addEventListener("click", train);
$("#forecast-button").addEventListener("click", predict);

request("/health")
  .then(() => Promise.all([loadDashboard(), loadFederated()]))
  .catch((error) => {
    $("#connection-label").textContent = "Database unavailable";
    $(".pulse").classList.remove("online");
    showMessage("#model-message", error.message, true);
    loadFederated();
  });
