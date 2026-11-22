/**
 * Enterprise Sales Forecasting & Demand Planning Dashboard
 */

let state = {
  products: [],
  models: {},
  overview: null,
  analytics: null,
  currentTrendMetric: 'revenue',
  charts: {},
  selectedUploadFile: null,
  horizonTimeline: []
};

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  setDefaultDates();
  setupDragAndDrop();

  // Load all initial API data in parallel
  await Promise.all([
    fetchOverview(),
    fetchAnalytics(),
    fetchActualVsPredicted(),
    fetchProducts(),
    fetchModelsBenchmark()
  ]);

  // Run initial default forecast calculation
  executeSinglePrediction();
});

function getChartColors() {
  return {
    textColor: '#64748b',                   // Slate-500
    gridColor: 'rgba(226, 232, 240, 0.8)',   // Slate-200
    cardBg: '#ffffff'
  };
}

// ==========================================
// Navigation Tabs
// ==========================================
function switchTab(tabId) {
  // Update Tab Buttons
  const buttons = document.querySelectorAll('.tab-btn');
  buttons.forEach(btn => {
    if (btn.getAttribute('data-tab') === tabId) {
      btn.className = 'tab-btn active px-3.5 py-2 rounded-lg text-xs sm:text-sm font-semibold transition flex items-center space-x-1.5 text-indigo-600 bg-indigo-50 border-b-2 border-indigo-600';
    } else {
      btn.className = 'tab-btn px-3.5 py-2 rounded-lg text-xs sm:text-sm font-medium transition flex items-center space-x-1.5 text-slate-600 hover:text-slate-900 hover:bg-slate-100';
    }
  });

  // Update Tab Content sections
  const contents = document.querySelectorAll('.tab-content');
  contents.forEach(sec => sec.classList.add('hidden'));

  const activeSection = document.getElementById(`tab-${tabId}`);
  if (activeSection) {
    activeSection.classList.remove('hidden');
  }

  // Trigger chart resize if needed
  if (tabId === 'horizon' && !state.charts['horizonChart']) {
    runHorizonForecast();
  }
}

function setDefaultDates() {
  const today = new Date().toISOString().split('T')[0];
  const predDateInput = document.getElementById('predDate');
  if (predDateInput) {
    predDateInput.value = today;
  }
}

// ==========================================
// API Calls & Data Loading
// ==========================================
async function fetchOverview() {
  try {
    const res = await fetch('/api/overview');
    const data = await res.json();
    if (data.status === 'success') {
      state.overview = data;
      const s = data.summary;

      document.getElementById('kpiTotalRevenue').innerText = `$${(s.total_revenue / 1000000).toFixed(2)}M`;
      document.getElementById('kpiTotalUnits').innerText = s.total_units_sold.toLocaleString();
      document.getElementById('kpiAvgOrderValue').innerText = `$${s.average_order_value.toLocaleString()}`;
      document.getElementById('kpiDateRange').innerText = `${s.date_start} to ${s.date_end} (${s.total_records.toLocaleString()} records)`;

      renderTopProducts(data.top_products);
    }
  } catch (err) {
    console.error('Error fetching overview:', err);
  }
}

function renderTopProducts(products) {
  const container = document.getElementById('topProductsList');
  if (!container || !products) return;

  container.innerHTML = products.map((p, idx) => `
    <div class="flex items-center justify-between p-2.5 rounded-lg bg-slate-50 border border-slate-200/80 hover:border-indigo-300 transition">
      <div class="flex items-center space-x-3">
        <span class="w-6 h-6 rounded-md bg-indigo-100 text-indigo-700 font-bold text-xs flex items-center justify-center">${idx + 1}</span>
        <div>
          <p class="text-xs font-semibold text-slate-800 leading-tight">${p.name}</p>
          <span class="text-[10px] text-slate-500">${p.category} • Base: $${p.avg_price}</span>
        </div>
      </div>
      <div class="text-right">
        <p class="text-xs font-bold text-emerald-600">$${(p.revenue / 1000).toFixed(1)}k</p>
        <p class="text-[10px] text-slate-500">${p.units.toLocaleString()} units</p>
      </div>
    </div>
  `).join('');
}

async function fetchAnalytics() {
  try {
    const res = await fetch('/api/analytics');
    const data = await res.json();
    if (data.status === 'success') {
      state.analytics = data;
      renderMonthlyTrendChart();
      renderCategoryChart();
      renderRegionChart();
      renderDOWChart();

      if (data.promo_impact) {
        const boostPct = Math.round(((data.promo_impact.promo.avg_units - data.promo_impact.non_promo.avg_units) / data.promo_impact.non_promo.avg_units) * 100);
        const promoText = document.getElementById('promoBoostText');
        if (promoText) {
          promoText.innerText = `+${boostPct}% unit sales on promotional days`;
        }
      }
    }
  } catch (err) {
    console.error('Error fetching analytics:', err);
  }
}

async function fetchActualVsPredicted() {
  try {
    const res = await fetch('/api/actual_vs_predicted');
    const data = await res.json();
    if (data.status === 'success') {
      renderActualVsPredictedChart(data);
    }
  } catch (err) {
    console.error('Error fetching actual vs predicted:', err);
  }
}

async function fetchProducts() {
  try {
    const res = await fetch('/api/products');
    const data = await res.json();
    if (data.status === 'success') {
      state.products = data.products;
      const select = document.getElementById('predProduct');
      if (select) {
        select.innerHTML = data.products.map(p => `
          <option value="${p.name}" data-price="${p.base_price}" data-category="${p.category}">
            ${p.name} ($${p.base_price})
          </option>
        `).join('');
        onProductSelectChange();
      }
    }
  } catch (err) {
    console.error('Error fetching products:', err);
  }
}

function onProductSelectChange() {
  const select = document.getElementById('predProduct');
  if (!select || !select.selectedOptions.length) return;
  const opt = select.selectedOptions[0];
  const price = opt.getAttribute('data-price');
  const cat = opt.getAttribute('data-category');

  const priceInput = document.getElementById('predUnitPrice');
  const catDisplay = document.getElementById('predCategoryDisplay');

  if (priceInput) priceInput.value = price;
  if (catDisplay) catDisplay.innerText = `Category: ${cat}`;
}

async function fetchModelsBenchmark() {
  try {
    const res = await fetch('/api/models');
    const data = await res.json();
    if (data.status === 'success') {
      state.models = data.models;
      renderModelsTable(data.models);
      renderFeatureImportanceChart(data.feature_importances);

      // Update KPI Card 4 with best model
      for (const [mName, m] of Object.entries(data.models)) {
        if (m.is_best) {
          document.getElementById('kpiModelR2').innerText = `${(m.r2_score * 100).toFixed(1)}% R²`;
          break;
        }
      }
    }
  } catch (err) {
    console.error('Error fetching models:', err);
  }
}

function renderModelsTable(models) {
  const tbody = document.getElementById('modelsTableBody');
  if (!tbody || !models) return;

  tbody.innerHTML = Object.entries(models).map(([name, m]) => `
    <tr class="hover:bg-slate-50 transition">
      <td class="p-3 font-semibold text-slate-900 flex items-center space-x-2">
        <span>${name}</span>
      </td>
      <td class="p-3 text-center">
        ${m.is_best ? '<span class="px-2 py-0.5 rounded text-[11px] bg-emerald-50 text-emerald-700 font-bold border border-emerald-200">★ Best Performer</span>' : '<span class="text-xs text-slate-400">Benchmark</span>'}
      </td>
      <td class="p-3 text-right font-mono font-bold ${m.is_best ? 'text-emerald-600' : 'text-slate-700'}">${(m.r2_score * 100).toFixed(2)}%</td>
      <td class="p-3 text-right font-mono text-slate-700">${m.rmse.toFixed(3)}</td>
      <td class="p-3 text-right font-mono text-slate-700">${m.mae.toFixed(3)}</td>
      <td class="p-3 text-right font-mono text-slate-700">${m.mape.toFixed(2)}%</td>
      <td class="p-3 text-right font-mono font-semibold text-indigo-600">${(m.rev_r2 * 100).toFixed(2)}%</td>
    </tr>
  `).join('');
}

// ==========================================
// Chart Rendering Functions
// ==========================================
function renderMonthlyTrendChart() {
  const ctx = document.getElementById('monthlyTrendChart');
  if (!ctx || !state.analytics) return;

  if (state.charts['monthlyTrend']) {
    state.charts['monthlyTrend'].destroy();
  }

  const { textColor, gridColor } = getChartColors();
  const m = state.analytics.monthly;

  let datasetConfig = {};
  if (state.currentTrendMetric === 'revenue') {
    datasetConfig = {
      label: 'Monthly Revenue ($)',
      data: m.revenue,
      borderColor: '#4f46e5',
      backgroundColor: 'rgba(79, 70, 229, 0.08)',
      fill: true,
      tension: 0.35,
      borderWidth: 2.5
    };
  } else if (state.currentTrendMetric === 'units') {
    datasetConfig = {
      label: 'Units Sold',
      data: m.units,
      borderColor: '#059669',
      backgroundColor: 'rgba(5, 150, 105, 0.08)',
      fill: true,
      tension: 0.35,
      borderWidth: 2.5
    };
  } else {
    datasetConfig = {
      label: 'Gross Profit ($)',
      data: m.profit,
      borderColor: '#7c3aed',
      backgroundColor: 'rgba(124, 58, 237, 0.08)',
      fill: true,
      tension: 0.35,
      borderWidth: 2.5
    };
  }

  state.charts['monthlyTrend'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: m.labels,
      datasets: [datasetConfig]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#ffffff',
          bodyColor: '#cbd5e1',
          padding: 10,
          borderColor: '#334155',
          borderWidth: 1,
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: ${state.currentTrendMetric === 'units' ? ctx.raw.toLocaleString() : '$' + ctx.raw.toLocaleString()}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 10 }, maxRotation: 45 }
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { size: 10 },
            callback: (v) => state.currentTrendMetric === 'units' ? (v >= 1000 ? v / 1000 + 'k' : v) : '$' + (v >= 1000000 ? (v / 1000000).toFixed(1) + 'M' : v / 1000 + 'k')
          }
        }
      }
    }
  });
}

function setTrendMetric(metric) {
  state.currentTrendMetric = metric;
  ['Rev', 'Units', 'Profit'].forEach(m => {
    const btn = document.getElementById(`trend${m}Btn`);
    if (btn) {
      if (metric.toLowerCase().startsWith(m.toLowerCase())) {
        btn.className = 'px-2.5 py-1 text-xs rounded-md bg-indigo-600 text-white font-semibold shadow-sm';
      } else {
        btn.className = 'px-2.5 py-1 text-xs rounded-md bg-slate-100 text-slate-600 hover:bg-slate-200 font-medium';
      }
    }
  });
  renderMonthlyTrendChart();
}

function renderActualVsPredictedChart(data) {
  const ctx = document.getElementById('actualVsPredChart');
  if (!ctx) return;

  if (state.charts['actualVsPred']) {
    state.charts['actualVsPred'].destroy();
  }

  const { textColor, gridColor } = getChartColors();

  state.charts['actualVsPred'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.dates,
      datasets: [
        {
          label: 'Ground Truth Revenue ($)',
          data: data.actual_revenue,
          borderColor: '#059669',
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.25
        },
        {
          label: 'Model Predicted Revenue ($)',
          data: data.pred_revenue,
          borderColor: '#d97706',
          borderDash: [4, 4],
          borderWidth: 2,
          pointRadius: 2,
          tension: 0.25
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: { color: '#334155', font: { size: 11, weight: 'bold' } }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#fff',
          callbacks: {
            label: (ctx) => `${ctx.dataset.label}: $${ctx.raw.toLocaleString()}`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 10 }, maxRotation: 45 }
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { size: 10 },
            callback: (v) => '$' + (v >= 1000 ? (v / 1000).toFixed(0) + 'k' : v)
          }
        }
      }
    }
  });
}

function renderCategoryChart() {
  const ctx = document.getElementById('categoryChart');
  if (!ctx || !state.analytics) return;

  if (state.charts['category']) {
    state.charts['category'].destroy();
  }

  const c = state.analytics.category;

  state.charts['category'] = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: c.labels,
      datasets: [{
        data: c.revenue,
        backgroundColor: [
          '#4f46e5', '#059669', '#d97706', '#db2777', '#7c3aed', '#0891b2'
        ],
        borderWidth: 2,
        borderColor: '#ffffff'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'right',
          labels: { color: '#334155', boxWidth: 10, font: { size: 10 } }
        },
        tooltip: {
          callbacks: {
            label: (ctx) => ` $${(ctx.raw / 1000000).toFixed(2)}M (${ctx.label})`
          }
        }
      },
      cutout: '68%'
    }
  });
}

function renderRegionChart() {
  const ctx = document.getElementById('regionChart');
  if (!ctx || !state.analytics) return;

  if (state.charts['region']) {
    state.charts['region'].destroy();
  }

  const { textColor, gridColor } = getChartColors();
  const r = state.analytics.region;

  state.charts['region'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: r.labels,
      datasets: [{
        label: 'Revenue ($)',
        data: r.revenue,
        backgroundColor: '#4f46e5',
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 10 } }
        },
        y: {
          grid: { color: gridColor },
          ticks: {
            color: textColor,
            font: { size: 10 },
            callback: (v) => '$' + (v / 1000000).toFixed(1) + 'M'
          }
        }
      }
    }
  });
}

function renderDOWChart() {
  const ctx = document.getElementById('dowChart');
  if (!ctx || !state.analytics) return;

  if (state.charts['dow']) {
    state.charts['dow'].destroy();
  }

  const { textColor, gridColor } = getChartColors();
  const d = state.analytics.day_of_week;

  state.charts['dow'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
      datasets: [{
        label: 'Avg Units',
        data: d.avg_units,
        backgroundColor: d.labels.map(l => (l === 'Saturday' || l === 'Sunday') ? '#059669' : '#4f46e5'),
        borderRadius: 6
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Avg: ${ctx.raw} units/day`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 10 } }
        },
        y: {
          grid: { color: gridColor },
          ticks: { color: textColor, font: { size: 10 } }
        }
      }
    }
  });
}

function renderFeatureImportanceChart(features) {
  const ctx = document.getElementById('featureImportanceChart');
  if (!ctx) return;

  const dataList = features || (state.models.feature_importances);
  if (!dataList || !dataList.length) return;

  if (state.charts['featureImportance']) {
    state.charts['featureImportance'].destroy();
  }

  const { textColor, gridColor } = getChartColors();

  state.charts['featureImportance'] = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: dataList.map(f => f.feature.replace('Category_', '').replace('Store_Type_', '')),
      datasets: [{
        label: 'Weight',
        data: dataList.map(f => (f.importance * 100).toFixed(1)),
        backgroundColor: '#7c3aed',
        borderRadius: 6
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: (ctx) => ` Relative Importance: ${ctx.raw}%`
          }
        }
      },
      scales: {
        x: {
          grid: { color: gridColor },
          ticks: { color: textColor, font: { size: 10 }, callback: v => v + '%' }
        },
        y: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 10 } }
        }
      }
    }
  });
}

// ==========================================
// Interactive Prediction Functionality
// ==========================================
function updateDiscountSlider(val) {
  const display = document.getElementById('discountValDisplay');
  if (display) {
    display.innerText = `${val}% Off`;
  }
}

async function executeSinglePrediction() {
  const date = document.getElementById('predDate').value || new Date().toISOString().split('T')[0];
  const productSelect = document.getElementById('predProduct');
  const productName = productSelect ? productSelect.value : 'Smartphone Pro Max';
  const region = document.getElementById('predRegion').value || 'North';
  const storeType = document.getElementById('predStoreType').value || 'Online Flagship';
  const unitPrice = parseFloat(document.getElementById('predUnitPrice').value || 999.0);
  const discountPct = parseFloat(document.getElementById('predDiscountRange').value || 0);
  const modelName = document.getElementById('predModel').value || 'Gradient Boosting';

  const payload = {
    date: date,
    product_name: productName,
    region: region,
    store_type: storeType,
    unit_price: unitPrice,
    discount_percent: discountPct,
    promotion_active: discountPct > 0 ? 1 : 0,
    model_name: modelName
  };

  try {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      const f = data.forecast;
      
      document.getElementById('resQuantity').innerText = f.predicted_quantity.toLocaleString();
      document.getElementById('resConfidence').innerText = `95% Range: [ ${f.confidence_interval.lower_units} to ${f.confidence_interval.upper_units} units ]`;
      document.getElementById('resRevenue').innerText = `$${f.predicted_revenue.toLocaleString()}`;
      document.getElementById('resEffPrice').innerText = `Eff. Price: $${f.effective_price}`;
      document.getElementById('resProfit').innerText = `$${f.estimated_profit.toLocaleString()}`;
      document.getElementById('resMargin').innerText = `Margin: ${f.profit_margin_percent}%`;

      document.getElementById('resSafetyStock').innerText = f.inventory.recommended_safety_stock;
      document.getElementById('resReorderPoint').innerText = f.inventory.reorder_point;
      document.getElementById('resInventoryAction').innerText = f.inventory.inventory_action;

      const riskBadge = document.getElementById('resRiskBadge');
      riskBadge.innerText = f.inventory.stockout_risk;
      if (f.inventory.stockout_risk.includes('High')) {
        riskBadge.className = 'text-xs font-bold px-2 py-0.5 rounded bg-rose-50 text-rose-700 border border-rose-200';
      } else if (f.inventory.stockout_risk.includes('Moderate')) {
        riskBadge.className = 'text-xs font-bold px-2 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200';
      } else {
        riskBadge.className = 'text-xs font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200';
      }

      document.getElementById('outputModelBadge').innerText = modelName;
      document.getElementById('resTimestamp').innerText = new Date().toLocaleTimeString();
    }
  } catch (err) {
    console.error('Error during prediction:', err);
  }
}

// ==========================================
// Multi-Day Horizon Demand Planner
// ==========================================
async function runHorizonForecast() {
  const productSelect = document.getElementById('predProduct');
  const productName = productSelect ? productSelect.value : 'Smartphone Pro Max';
  const region = document.getElementById('predRegion').value || 'North';
  const storeType = document.getElementById('predStoreType').value || 'Online Flagship';
  const horizonDays = parseInt(document.getElementById('hzDays').value || 30);
  const scenario = document.getElementById('hzScenario').value || 'promo_weekends';
  const unitPrice = parseFloat(document.getElementById('predUnitPrice').value || 999.0);
  const modelName = document.getElementById('predModel').value || 'Gradient Boosting';

  const payload = {
    product_name: productName,
    region: region,
    store_type: storeType,
    horizon_days: horizonDays,
    promo_scenario: scenario,
    unit_price: unitPrice,
    model_name: modelName
  };

  try {
    const res = await fetch('/api/forecast_horizon', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === 'success') {
      state.horizonTimeline = data.timeline;
      const agg = data.aggregate;

      document.getElementById('hzAggUnits').innerText = agg.total_forecasted_units.toLocaleString();
      document.getElementById('hzAggRevenue').innerText = `$${agg.total_forecasted_revenue.toLocaleString()}`;
      document.getElementById('hzPeakDate').innerText = agg.peak_demand_date;
      document.getElementById('hzPeakUnits').innerText = `${agg.peak_demand_units} units peak`;
      document.getElementById('hzRecommendedStock').innerText = `${agg.recommended_total_inventory.toLocaleString()} units`;

      renderHorizonChart(data.timeline);
      renderHorizonTable(data.timeline);
    }
  } catch (err) {
    console.error('Error simulating horizon:', err);
  }
}

function renderHorizonChart(timeline) {
  const ctx = document.getElementById('horizonChart');
  if (!ctx) return;

  if (state.charts['horizonChart']) {
    state.charts['horizonChart'].destroy();
  }

  const { textColor, gridColor } = getChartColors();

  state.charts['horizonChart'] = new Chart(ctx, {
    type: 'line',
    data: {
      labels: timeline.map(t => `${t.date.slice(5)} (${t.day_name})`),
      datasets: [
        {
          label: 'Upper 90% Bound',
          data: timeline.map(t => t.upper_quantity),
          borderColor: 'transparent',
          backgroundColor: 'rgba(79, 70, 229, 0.08)',
          fill: '+1',
          pointRadius: 0
        },
        {
          label: 'Forecast Quantity (Units)',
          data: timeline.map(t => t.predicted_quantity),
          borderColor: '#4f46e5',
          backgroundColor: 'transparent',
          borderWidth: 2.5,
          pointRadius: 3,
          pointBackgroundColor: timeline.map(t => t.is_weekend ? '#059669' : '#4f46e5'),
          tension: 0.3
        },
        {
          label: 'Lower 90% Bound',
          data: timeline.map(t => t.lower_quantity),
          borderColor: 'transparent',
          backgroundColor: 'transparent',
          fill: false,
          pointRadius: 0
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: true,
          labels: { color: '#334155', font: { size: 10 } }
        },
        tooltip: {
          backgroundColor: '#0f172a',
          titleColor: '#fff',
          callbacks: {
            label: (ctx) => ` Predicted: ${ctx.raw} units`
          }
        }
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: textColor, font: { size: 10 }, maxRotation: 45 }
        },
        y: {
          grid: { color: gridColor },
          ticks: { color: textColor, font: { size: 10 } }
        }
      }
    }
  });
}

function renderHorizonTable(timeline) {
  const tbody = document.getElementById('horizonTableBody');
  if (!tbody || !timeline) return;

  tbody.innerHTML = timeline.map(t => `
    <tr class="hover:bg-slate-50 transition">
      <td class="p-2.5 font-mono text-slate-700">${t.date}</td>
      <td class="p-2.5">
        <span class="${t.is_weekend ? 'text-emerald-600 font-bold' : 'text-slate-600'}">${t.day_name}</span>
      </td>
      <td class="p-2.5">
        ${t.is_promo ? `<span class="bg-indigo-50 text-indigo-700 border border-indigo-200 px-1.5 py-0.5 rounded text-[10px] font-semibold">${t.discount_pct}% Promo</span>` : '<span class="text-slate-400">Regular</span>'}
      </td>
      <td class="p-2.5 text-right font-bold text-slate-900">${t.predicted_quantity}</td>
      <td class="p-2.5 text-right font-mono text-slate-500">[${t.lower_quantity} - ${t.upper_quantity}]</td>
      <td class="p-2.5 text-right font-mono text-emerald-600 font-bold">$${t.predicted_revenue.toLocaleString()}</td>
    </tr>
  `).join('');
}

function exportHorizonTableToCSV() {
  if (!state.horizonTimeline || !state.horizonTimeline.length) {
    alert('No horizon data to export.');
    return;
  }

  const headers = ['Date', 'Day', 'IsWeekend', 'IsPromo', 'DiscountPct', 'PredictedQuantity', 'LowerBound', 'UpperBound', 'PredictedRevenue'];
  const rows = state.horizonTimeline.map(t => [
    t.date,
    t.day_name,
    t.is_weekend ? 1 : 0,
    t.is_promo ? 1 : 0,
    t.discount_pct,
    t.predicted_quantity,
    t.lower_quantity,
    t.upper_quantity,
    t.predicted_revenue
  ]);

  let csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
  const encodedUri = encodeURI(csvContent);
  const link = document.createElement("a");
  link.setAttribute("href", encodedUri);
  link.setAttribute("download", `sales_forecast_horizon_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// ==========================================
// CSV Upload & Retraining Handlers
// ==========================================
function setupDragAndDrop() {
  const dropZone = document.getElementById('dropZone');
  const fileInput = document.getElementById('csvFileInput');

  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('click', () => fileInput.click());

  dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.classList.add('drag-over');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('drag-over');
  });

  dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files.length) {
      handleFileSelected({ target: { files: e.dataTransfer.files } });
    }
  });
}

function handleFileSelected(event) {
  const files = event.target.files;
  if (!files || !files.length) return;
  state.selectedUploadFile = files[0];

  const infoCard = document.getElementById('fileInfoCard');
  const nameLabel = document.getElementById('selectedFileName');

  if (infoCard && nameLabel) {
    nameLabel.innerText = `${state.selectedUploadFile.name} (${(state.selectedUploadFile.size / 1024).toFixed(1)} KB)`;
    infoCard.classList.remove('hidden');
  }
}

async function uploadAndRetrain() {
  if (!state.selectedUploadFile) return;

  const btn = document.getElementById('uploadBtn');
  const statusDiv = document.getElementById('uploadStatusMessage');

  btn.disabled = true;
  btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin mr-1"></i> Processing & Retraining...`;

  const formData = new FormData();
  formData.append('file', state.selectedUploadFile);

  try {
    const res = await fetch('/api/upload_csv', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();

    statusDiv.classList.remove('hidden');
    if (data.status === 'success') {
      statusDiv.className = 'text-xs p-4 rounded-xl border bg-emerald-50 border-emerald-200 text-emerald-800';
      statusDiv.innerHTML = `
        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div class="flex items-center space-x-2">
              <i class="fa-solid fa-circle-check text-emerald-600 text-base"></i>
              <strong class="text-slate-900 text-sm">Upload & Retraining Complete!</strong>
            </div>
            <p class="text-xs text-slate-600 mt-1">${data.message}</p>
            <p class="text-[11px] text-emerald-700 mt-0.5 font-medium">Active Range: <strong>${data.date_range[0]}</strong> to <strong>${data.date_range[1]}</strong> (${data.records_count.toLocaleString()} total transactions).</p>
          </div>
          <button onclick="switchTab('overview')" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg font-semibold text-xs transition shadow-sm whitespace-nowrap flex items-center justify-center space-x-1.5">
            <span>View Updated Analytics</span>
            <i class="fa-solid fa-arrow-right"></i>
          </button>
        </div>
      `;

      // Render uploaded preview table if provided
      if (data.preview && data.preview.length) {
        renderUploadedPreview(data.preview);
      }

      // Automatically refresh all analytical views, dropdowns, and benchmarks
      await Promise.all([
        fetchOverview(),
        fetchAnalytics(),
        fetchActualVsPredicted(),
        fetchProducts(),
        fetchModelsBenchmark()
      ]);
    } else {
      statusDiv.className = 'text-xs p-3 rounded-lg border bg-rose-50 border-rose-200 text-rose-700';
      statusDiv.innerHTML = `<strong>Upload Failed:</strong> ${data.message}`;
    }
  } catch (err) {
    statusDiv.classList.remove('hidden');
    statusDiv.className = 'text-xs p-3 rounded-lg border bg-rose-50 border-rose-200 text-rose-700';
    statusDiv.innerHTML = `<strong>Error:</strong> ${err.message}`;
  } finally {
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-arrows-rotate mr-1"></i> Upload & Retrain`;
  }
}

function renderUploadedPreview(rows) {
  const container = document.getElementById('uploadedPreviewSection');
  const tbody = document.getElementById('uploadedPreviewBody');
  if (!container || !tbody || !rows) return;

  container.classList.remove('hidden');
  tbody.innerHTML = rows.map(r => `
    <tr class="hover:bg-slate-50 transition">
      <td class="p-2 font-mono text-slate-600">${r.Date}</td>
      <td class="p-2 font-semibold text-slate-900">${r.Product_Name}</td>
      <td class="p-2 text-slate-500">${r.Category}</td>
      <td class="p-2 text-right font-mono text-slate-700">$${r.Unit_Price.toFixed(2)}</td>
      <td class="p-2 text-right font-bold text-indigo-600">${r.Quantity_Sold}</td>
      <td class="p-2 text-right font-mono text-emerald-600 font-bold">$${r.Sales_Amount.toLocaleString()}</td>
    </tr>
  `).join('');
}
