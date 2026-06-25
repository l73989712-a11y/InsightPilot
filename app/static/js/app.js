function csrfToken() {
  return document.querySelector('meta[name="csrf-token"]')?.content || '';
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken()
    },
    body: JSON.stringify(payload)
  });
  let data = {};
  try {
    data = await response.json();
  } catch (_error) {
    data = {ok: false, message: `请求失败（HTTP ${response.status}）`};
  }
  if (!response.ok && data.ok === undefined) data.ok = false;
  return data;
}

function setMessage(id, text, cls) {
  const el = document.getElementById(id);
  if (!el) return;
  el.className = `small mt-3 ${cls || ''}`;
  el.textContent = text;
}

function echartsLikeToPlotly(option) {
  if (!option || Object.keys(option).length === 0) return null;
  const title = option.title?.text || '';
  const xAxis = option.xAxis || {};
  const yAxis = option.yAxis || {};
  const series = option.series || [];
  const layout = {
    title: {text: title, font: {size: 18}},
    margin: {l: 60, r: 30, t: 70, b: 70},
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    hovermode: 'closest',
    xaxis: {title: xAxis.name || '', automargin: true},
    yaxis: {title: yAxis.name || '', automargin: true},
    legend: {orientation: 'h', y: 1.08}
  };

  if (series[0]?.type === 'heatmap') {
    const xLabels = xAxis.data || [];
    const yLabels = yAxis.data || [];
    const z = yLabels.map(() => xLabels.map(() => null));
    (series[0].data || []).forEach(item => {
      const [x, y, value] = item;
      if (z[y]) z[y][x] = value;
    });
    return {
      traces: [{type: 'heatmap', x: xLabels, y: yLabels, z, zmin: -1, zmax: 1, colorscale: 'RdBu', reversescale: true, texttemplate: '%{z:.2f}'}],
      layout
    };
  }

  const traces = series.map(item => {
    if (item.type === 'scatter') {
      const points = item.data || [];
      return {
        name: item.name || '',
        type: 'scatter',
        mode: 'markers',
        x: points.map(p => Array.isArray(p) ? p[0] : p),
        y: points.map(p => Array.isArray(p) ? p[1] : null),
        marker: {size: 9}
      };
    }
    if (item.type === 'line') {
      const points = item.data || [];
      const paired = points.length && Array.isArray(points[0]);
      return {
        name: item.name || '',
        type: 'scatter',
        mode: item.showSymbol === false ? 'lines' : 'lines+markers',
        x: paired ? points.map(p => p[0]) : (xAxis.data || points.map((_, i) => i + 1)),
        y: paired ? points.map(p => p[1]) : points,
        line: {shape: item.smooth ? 'spline' : 'linear'}
      };
    }
    return {
      name: item.name || '',
      type: 'bar',
      x: xAxis.data || (item.data || []).map((_, i) => i + 1),
      y: item.data || []
    };
  });
  return {traces, layout};
}

function renderChart(id, option) {
  const el = document.getElementById(id);
  if (!el) return;
  const converted = echartsLikeToPlotly(option);
  if (!converted) {
    el.innerHTML = '<div class="empty-state">该分析暂未生成图表。</div>';
    return;
  }
  Plotly.react(el, converted.traces, converted.layout, {
    responsive: true,
    displaylogo: false,
    locale: 'zh-CN',
    modeBarButtonsToRemove: ['lasso2d', 'select2d']
  });
}

function renderResultTable(id, result) {
  const box = document.getElementById(id);
  if (!box) return;
  if (!result) {
    box.innerHTML = '<div class="empty-state">暂无结果。</div>';
    return;
  }
  if (Array.isArray(result.records) && Array.isArray(result.columns)) {
    const head = result.columns.map(c => `<th>${escapeHtml(c)}</th>`).join('');
    const rows = result.records.map(row =>
      `<tr>${result.columns.map(c => `<td>${escapeHtml(row[c] ?? '')}</td>`).join('')}</tr>`
    ).join('');
    box.innerHTML = `<table class="table table-sm table-hover"><thead><tr>${head}</tr></thead><tbody>${rows}</tbody></table>`;
  } else {
    box.innerHTML = `<pre class="plan-box">${escapeHtml(JSON.stringify(result, null, 2))}</pre>`;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;').replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}
