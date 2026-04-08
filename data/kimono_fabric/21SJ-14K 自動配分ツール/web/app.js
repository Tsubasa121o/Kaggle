(function () {
  "use strict";

  const DEFAULT_WEIGHTS = {
    feature_weights: {
      sales_qty: 0.5,
      stockout_days: 0.25,
      current_stock: -0.15,
      return_rate: -0.1
    },
    score_floor: 0.01
  };

  const WEIGHT_FEATURE_KEYS = ["sales_qty", "stockout_days", "current_stock", "return_rate"];
  const WEIGHT_ABS_TOTAL_TARGET = 1.0;
  const WEIGHT_ABS_TOTAL_TOLERANCE = 0.001;
  const WEIGHT_PRESETS = {
    balanced: {
      feature_weights: {
        sales_qty: 0.5,
        stockout_days: 0.25,
        current_stock: -0.15,
        return_rate: -0.1
      },
      score_floor: 0.01
    },
    sales_focus: {
      feature_weights: {
        sales_qty: 0.65,
        stockout_days: 0.2,
        current_stock: -0.1,
        return_rate: -0.05
      },
      score_floor: 0.01
    },
    stock_focus: {
      feature_weights: {
        sales_qty: 0.25,
        stockout_days: 0.3,
        current_stock: -0.35,
        return_rate: -0.1
      },
      score_floor: 0.01
    }
  };

  const COLUMN_ALIASES = {
    jan_code: ["jan_code", "JAN", "JANコード", "jan", "商品コード"],
    item_name: ["item_name", "商品名", "品名"],
    sales_qty: ["sales_qty", "売上数量", "販売数量", "出荷数量"],
    stockout_days: ["stockout_days", "在庫切れ日数", "在庫ゼロ日数"],
    current_stock: ["current_stock", "現在庫", "在庫数"],
    return_qty: ["return_qty", "返品数量", "返品数"],
    return_rate: ["return_rate", "返品率"],
    min_allocate: ["min_allocate", "最低配分数", "最小配分数"],
    max_allocate: ["max_allocate", "最大配分数"]
  };

  const DEFAULT_CSV_PATH = "../data/input/21SJ14K_allocation_input.csv";
  const HEADERLESS_COLUMNS = [
    "jan_code",
    "item_name",
    "sales_qty",
    "stockout_days",
    "current_stock",
    "return_qty",
    "min_allocate",
    "max_allocate"
  ];

  const state = {
    resultRows: [],
    summaryText: "",
    extraFeatureWeights: {},
    isUpdatingWeightControls: false
  };

  const el = {
    csvPath: document.getElementById("csvPath"),
    totalUnits: document.getElementById("totalUnits"),
    weightsJson: document.getElementById("weightsJson"),
    scoreFloorInput: document.getElementById("scoreFloorInput"),
    weightAbsTotal: document.getElementById("weightAbsTotal"),
    weightSignedTotal: document.getElementById("weightSignedTotal"),
    weightTotalStatus: document.getElementById("weightTotalStatus"),
    weightAdjustHint: document.getElementById("weightAdjustHint"),
    weightRanges: {
      sales_qty: document.getElementById("w_sales_qty_range"),
      stockout_days: document.getElementById("w_stockout_days_range"),
      current_stock: document.getElementById("w_current_stock_range"),
      return_rate: document.getElementById("w_return_rate_range")
    },
    weightNumbers: {
      sales_qty: document.getElementById("w_sales_qty_number"),
      stockout_days: document.getElementById("w_stockout_days_number"),
      current_stock: document.getElementById("w_current_stock_number"),
      return_rate: document.getElementById("w_return_rate_number")
    },
    presetBalancedBtn: document.getElementById("presetBalancedBtn"),
    presetSalesBtn: document.getElementById("presetSalesBtn"),
    presetStockBtn: document.getElementById("presetStockBtn"),
    syncFromFormBtn: document.getElementById("syncFromFormBtn"),
    syncToFormBtn: document.getElementById("syncToFormBtn"),
    runBtn: document.getElementById("runBtn"),
    downloadCsvBtn: document.getElementById("downloadCsvBtn"),
    downloadSummaryBtn: document.getElementById("downloadSummaryBtn"),
    log: document.getElementById("log"),
    resultTableBody: document.querySelector("#resultTable tbody")
  };

  applyWeightConfigToForm(DEFAULT_WEIGHTS);
  updateWeightValidationUi();
  syncJsonFromForm();
  if (!el.csvPath.value.trim()) {
    el.csvPath.value = DEFAULT_CSV_PATH;
  }

  WEIGHT_FEATURE_KEYS.forEach(bindWeightPair);
  el.scoreFloorInput.addEventListener("input", syncJsonFromForm);
  el.presetBalancedBtn.addEventListener("click", () => applyPreset("balanced"));
  el.presetSalesBtn.addEventListener("click", () => applyPreset("sales_focus"));
  el.presetStockBtn.addEventListener("click", () => applyPreset("stock_focus"));
  el.syncFromFormBtn.addEventListener("click", () => {
    syncJsonFromForm();
    log("フォーム内容を weights.json に反映しました。");
  });
  el.syncToFormBtn.addEventListener("click", () => {
    try {
      const parsed = JSON.parse(el.weightsJson.value);
      applyWeightConfigToForm(parsed);
      syncJsonFromForm();
      log("weights.json の内容をフォームに反映しました。");
    } catch (err) {
      log(`エラー: weights.json のJSON形式が不正です (${err.message})`);
    }
  });

  el.runBtn.addEventListener("click", handleRun);
  el.downloadCsvBtn.addEventListener("click", downloadResultCsv);
  el.downloadSummaryBtn.addEventListener("click", downloadSummary);

  function log(message) {
    el.log.textContent = message;
  }

  function parseNumber(value, defaultValue) {
    if (value === null || value === undefined || value === "") {
      return defaultValue;
    }
    const num = Number(String(value).trim());
    return Number.isFinite(num) ? num : defaultValue;
  }

  function bindWeightPair(feature) {
    const rangeEl = el.weightRanges[feature];
    const numberEl = el.weightNumbers[feature];
    if (!rangeEl || !numberEl) return;

    rangeEl.addEventListener("input", () => {
      if (state.isUpdatingWeightControls) return;
      numberEl.value = Number(rangeEl.value).toFixed(2);
      updateWeightValidationUi();
      syncJsonFromForm();
    });
    rangeEl.addEventListener("change", () => {
      if (state.isUpdatingWeightControls) return;
      updateWeightValidationUi();
      syncJsonFromForm();
    });

    numberEl.addEventListener("input", () => {
      if (state.isUpdatingWeightControls) return;
      const val = parseNumber(numberEl.value, 0);
      const min = parseNumber(rangeEl.min, -1.5);
      const max = parseNumber(rangeEl.max, 1.5);
      const clamped = Math.max(min, Math.min(max, val));
      rangeEl.value = String(clamped);
      updateWeightValidationUi();
      syncJsonFromForm();
    });
    numberEl.addEventListener("change", () => {
      if (state.isUpdatingWeightControls) return;
      updateWeightValidationUi();
      syncJsonFromForm();
    });
  }

  function getBaseWeightsFromForm() {
    const weights = {};
    WEIGHT_FEATURE_KEYS.forEach((feature) => {
      weights[feature] = parseNumber(el.weightNumbers[feature]?.value, 0);
    });
    return weights;
  }

  function setBaseWeightsToForm(weights) {
    state.isUpdatingWeightControls = true;
    WEIGHT_FEATURE_KEYS.forEach((feature) => {
      const rangeEl = el.weightRanges[feature];
      const numberEl = el.weightNumbers[feature];
      if (!rangeEl || !numberEl) return;
      const raw = parseNumber(weights[feature], 0);
      const min = parseNumber(rangeEl.min, -1.5);
      const max = parseNumber(rangeEl.max, 1.5);
      const clamped = Math.max(min, Math.min(max, raw));
      rangeEl.value = String(clamped);
      numberEl.value = Number(clamped).toFixed(2);
    });
    state.isUpdatingWeightControls = false;
  }

  function getWeightTotals(weights) {
    const absTotal = Object.values(weights).reduce((acc, v) => acc + Math.abs(parseNumber(v, 0)), 0);
    const signedTotal = Object.values(weights).reduce((acc, v) => acc + parseNumber(v, 0), 0);
    return { absTotal, signedTotal };
  }

  function isWeightTotalValid(absTotal) {
    return Math.abs(absTotal - WEIGHT_ABS_TOTAL_TARGET) <= WEIGHT_ABS_TOTAL_TOLERANCE;
  }

  function updateWeightValidationUi() {
    const base = getBaseWeightsFromForm();
    const { absTotal, signedTotal } = getWeightTotals(base);
    const valid = isWeightTotalValid(absTotal);
    const diff = WEIGHT_ABS_TOTAL_TARGET - absTotal;
    if (el.weightAbsTotal) {
      el.weightAbsTotal.textContent = absTotal.toFixed(3);
    }
    if (el.weightSignedTotal) {
      el.weightSignedTotal.textContent = signedTotal.toFixed(3);
    }
    if (el.weightTotalStatus) {
      el.weightTotalStatus.textContent = valid
        ? "OK（絶対値合計=1.000）"
        : "NG（1.000に合わせてください）";
      el.weightTotalStatus.classList.toggle("status-ok", valid);
      el.weightTotalStatus.classList.toggle("status-ng", !valid);
    }
    if (el.weightAdjustHint) {
      if (valid) {
        el.weightAdjustHint.textContent = "このまま実行できます。";
        el.weightAdjustHint.classList.add("status-ok");
        el.weightAdjustHint.classList.remove("status-ng");
      } else if (diff > 0) {
        el.weightAdjustHint.textContent = `絶対値合計が不足しています。あと +${diff.toFixed(3)}（絶対値）増やしてください。`;
        el.weightAdjustHint.classList.add("status-ng");
        el.weightAdjustHint.classList.remove("status-ok");
      } else {
        el.weightAdjustHint.textContent = `絶対値合計が超過しています。あと ${Math.abs(diff).toFixed(3)}（絶対値）減らしてください。`;
        el.weightAdjustHint.classList.add("status-ng");
        el.weightAdjustHint.classList.remove("status-ok");
      }
    }
    if (el.runBtn) {
      el.runBtn.disabled = !valid;
    }
  }

  function splitFeatureWeights(featureWeights) {
    const base = {};
    const extra = {};
    Object.entries(featureWeights || {}).forEach(([k, v]) => {
      const parsed = parseNumber(v, 0);
      if (WEIGHT_FEATURE_KEYS.includes(k)) {
        base[k] = parsed;
      } else {
        extra[k] = parsed;
      }
    });
    return { base, extra };
  }

  function normalizeWeightConfig(cfg) {
    if (!cfg || typeof cfg !== "object") {
      throw new Error("weights設定が不正です。");
    }
    if (!cfg.feature_weights || typeof cfg.feature_weights !== "object") {
      throw new Error("feature_weights が不正です。");
    }
    return {
      feature_weights: { ...cfg.feature_weights },
      score_floor: parseNumber(cfg.score_floor, 0.01)
    };
  }

  function applyWeightConfigToForm(cfg) {
    const normalized = normalizeWeightConfig(cfg);
    const { base, extra } = splitFeatureWeights(normalized.feature_weights);
    state.extraFeatureWeights = extra;
    setBaseWeightsToForm(base);

    el.scoreFloorInput.value = parseNumber(normalized.score_floor, 0.01).toFixed(3);
    updateWeightValidationUi();
  }

  function buildWeightConfigFromForm() {
    const featureWeights = { ...state.extraFeatureWeights };
    WEIGHT_FEATURE_KEYS.forEach((feature) => {
      featureWeights[feature] = parseNumber(el.weightNumbers[feature]?.value, 0);
    });
    return {
      feature_weights: featureWeights,
      score_floor: parseNumber(el.scoreFloorInput.value, 0.01)
    };
  }

  function syncJsonFromForm() {
    el.weightsJson.value = JSON.stringify(buildWeightConfigFromForm(), null, 2);
  }

  function applyPreset(presetKey) {
    const preset = WEIGHT_PRESETS[presetKey];
    if (!preset) return;
    applyWeightConfigToForm(preset);
    updateWeightValidationUi();
    syncJsonFromForm();
    log("重みプリセットを適用しました。");
  }

  function normalizeHeaderName(s) {
    return String(s ?? "").trim();
  }

  function parseCsv(text) {
    const rows = [];
    let row = [];
    let cell = "";
    let inQuotes = false;

    for (let i = 0; i < text.length; i += 1) {
      const ch = text[i];
      const next = i + 1 < text.length ? text[i + 1] : "";

      if (ch === '"') {
        if (inQuotes && next === '"') {
          cell += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
        continue;
      }

      if (ch === "," && !inQuotes) {
        row.push(cell);
        cell = "";
        continue;
      }

      if ((ch === "\n" || ch === "\r") && !inQuotes) {
        if (ch === "\r" && next === "\n") {
          i += 1;
        }
        row.push(cell);
        rows.push(row);
        row = [];
        cell = "";
        continue;
      }

      cell += ch;
    }

    if (cell.length > 0 || row.length > 0) {
      row.push(cell);
      rows.push(row);
    }

    return rows.filter((r) => r.some((v) => String(v).trim() !== ""));
  }

  function csvRowsToObjects(rows) {
    if (!rows.length) {
      return [];
    }
    const rawFirstRow = rows[0].map((h) => normalizeHeaderName(h).replace(/^\uFEFF/, ""));
    const firstCell = String(rawFirstRow[0] ?? "").trim();
    const isHeaderless = /^\d{13}$/.test(firstCell);

    let headers = rawFirstRow;
    let dataStartIndex = 1;
    if (isHeaderless) {
      headers = rawFirstRow.map((_, idx) => HEADERLESS_COLUMNS[idx] ?? `extra_col_${idx + 1}`);
      dataStartIndex = 0;
    }

    const out = [];
    for (let i = dataStartIndex; i < rows.length; i += 1) {
      const src = rows[i];
      const record = {};
      for (let c = 0; c < headers.length; c += 1) {
        record[headers[c]] = src[c] ?? "";
      }
      out.push(record);
    }
    return out;
  }

  function standardizeColumns(records) {
    if (!records.length) {
      return records;
    }
    return records.map((r) => {
      const out = { ...r };
      const keys = Object.keys(r);
      const keySet = new Set(keys);

      Object.entries(COLUMN_ALIASES).forEach(([canonical, aliases]) => {
        if (keySet.has(canonical)) {
          return;
        }
        for (const alias of aliases) {
          if (keySet.has(alias)) {
            out[canonical] = r[alias];
            break;
          }
        }
      });
      return out;
    });
  }

  function normalizeMinMax(values) {
    let minVal = Infinity;
    let maxVal = -Infinity;

    values.forEach((v) => {
      if (v < minVal) minVal = v;
      if (v > maxVal) maxVal = v;
    });

    if (maxVal === minVal) {
      return values.map(() => 1);
    }
    return values.map((v) => (v - minVal) / (maxVal - minVal));
  }

  function allocateWithLimits(scores, minAlloc, maxAlloc, totalUnits) {
    const alloc = minAlloc.slice();
    let remaining = totalUnits - alloc.reduce((a, b) => a + b, 0);
    if (remaining < 0) {
      throw new Error("最低配分数の合計が総配分数を超えています。");
    }

    let loops = 0;
    while (remaining > 0) {
      loops += 1;
      if (loops > 100000) {
        throw new Error("配分計算が収束しません。制約を見直してください。");
      }

      const eligible = [];
      for (let i = 0; i < alloc.length; i += 1) {
        if (alloc[i] < maxAlloc[i]) {
          eligible.push(i);
        }
      }
      if (!eligible.length) {
        throw new Error("最大配分数の制約により総配分数まで割り当てできません。");
      }

      const eligibleScores = eligible.map((i) => scores[i]);
      let scoreSum = eligibleScores.reduce((a, b) => a + b, 0);
      if (scoreSum <= 0) {
        for (let i = 0; i < eligibleScores.length; i += 1) {
          eligibleScores[i] = 1;
        }
        scoreSum = eligibleScores.length;
      }

      const quota = eligibleScores.map((s) => remaining * (s / scoreSum));
      let gained = 0;
      for (let p = 0; p < eligible.length; p += 1) {
        const idx = eligible[p];
        const capacity = maxAlloc[idx] - alloc[idx];
        const step = Math.max(0, Math.min(Math.floor(quota[p]), capacity));
        if (step > 0) {
          alloc[idx] += step;
          gained += step;
        }
      }
      if (gained > 0) {
        remaining -= gained;
        continue;
      }

      const order = quota
        .map((q, pos) => ({ pos, q }))
        .sort((a, b) => b.q - a.q);
      for (const item of order) {
        const idx = eligible[item.pos];
        if (alloc[idx] >= maxAlloc[idx]) continue;
        alloc[idx] += 1;
        remaining -= 1;
        if (remaining === 0) break;
      }
    }

    return alloc;
  }

  function toCsvLine(values) {
    return values
      .map((v) => {
        const s = String(v ?? "");
        if (s.includes(",") || s.includes('"') || s.includes("\n") || s.includes("\r")) {
          return `"${s.replace(/"/g, '""')}"`;
        }
        return s;
      })
      .join(",");
  }

  function buildResultCsv(rows) {
    if (!rows.length) return "";
    const headers = Object.keys(rows[0]);
    const lines = [toCsvLine(headers)];
    for (const row of rows) {
      lines.push(toCsvLine(headers.map((h) => row[h])));
    }
    return "\uFEFF" + lines.join("\r\n");
  }

  function renderTopRows(rows) {
    el.resultTableBody.innerHTML = "";
    const top = rows.slice(0, 20);
    for (const row of top) {
      const tr = document.createElement("tr");
      tr.innerHTML = [
        `<td>${escapeHtml(row.jan_code)}</td>`,
        `<td>${escapeHtml(row.item_name)}</td>`,
        `<td>${escapeHtml(row.allocation_units)}</td>`,
        `<td>${escapeHtml(row.score_total)}</td>`
      ].join("");
      el.resultTableBody.appendChild(tr);
    }
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  async function fetchCsvText(path) {
    const url = new URL(path, window.location.href);
    url.searchParams.set("_ts", Date.now().toString());
    const res = await fetch(url.toString(), { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`CSV読込に失敗しました: ${res.status} ${res.statusText}`);
    }
    return await res.text();
  }

  async function handleRun() {
    try {
      const totalUnits = Math.floor(parseNumber(el.totalUnits.value, 200));
      if (totalUnits <= 0) {
        throw new Error("総配分数は1以上を指定してください。");
      }

      const csvPath = (el.csvPath.value || DEFAULT_CSV_PATH).trim();
      if (!csvPath) {
        throw new Error("CSVパスを指定してください。");
      }

      const weightTotals = getWeightTotals(getBaseWeightsFromForm());
      if (!isWeightTotalValid(weightTotals.absTotal)) {
        throw new Error(`重みの絶対値合計を1.000にしてください（現在 ${weightTotals.absTotal.toFixed(3)}）`);
      }
      updateWeightValidationUi();
      const weightCfg = buildWeightConfigFromForm();
      if (!weightCfg.feature_weights || typeof weightCfg.feature_weights !== "object") {
        throw new Error("重み設定が不正です。");
      }
      const featureWeights = weightCfg.feature_weights;
      const scoreFloor = parseNumber(weightCfg.score_floor, 0.01);
      if (Object.keys(featureWeights).length === 0) {
        throw new Error("feature_weights に最低1つは重みを設定してください。");
      }
      syncJsonFromForm();

      log("固定パスからCSVを読込中...");
      const csvText = await fetchCsvText(csvPath);
      const records = standardizeColumns(csvRowsToObjects(parseCsv(csvText)));

      if (!records.length) {
        throw new Error("CSVが空です。");
      }
      if (!records.every((r) => "jan_code" in r)) {
        throw new Error("JAN列が見つかりません。jan_code/JAN/JANコード/商品コード を含めてください。");
      }

      const rows = records.map((r) => ({
        ...r,
        jan_code: String(r.jan_code).trim(),
        item_name: String((r.item_name ?? r.jan_code) || "").trim()
      }));

      const minAlloc = [];
      const maxAlloc = [];
      rows.forEach((r) => {
        const minValue = Math.max(0, Math.round(parseNumber(r.min_allocate, 0)));
        const rawMax = parseNumber(r.max_allocate, totalUnits);
        const maxValue = Math.max(minValue, Math.min(totalUnits, Math.round(rawMax > 0 ? rawMax : totalUnits)));
        minAlloc.push(minValue);
        maxAlloc.push(maxValue);
      });

      const minSum = minAlloc.reduce((a, b) => a + b, 0);
      const maxSum = maxAlloc.reduce((a, b) => a + b, 0);
      if (minSum > totalUnits) {
        throw new Error(`最低配分数の合計(${minSum})が総配分数(${totalUnits})を超えています。`);
      }
      if (maxSum < totalUnits) {
        throw new Error(`最大配分数の合計(${maxSum})が総配分数(${totalUnits})未満です。`);
      }

      if ("return_rate" in featureWeights) {
        rows.forEach((r) => {
          if (r.return_rate === undefined || r.return_rate === null || String(r.return_rate).trim() === "") {
            const returnQty = parseNumber(r.return_qty, 0);
            const salesQty = parseNumber(r.sales_qty, 0);
            r.return_rate = salesQty === 0 ? 0 : returnQty / salesQty;
          }
        });
      }

      const contributionByFeature = {};
      const score = new Array(rows.length).fill(0);

      for (const [feature, weightRaw] of Object.entries(featureWeights)) {
        const weight = parseNumber(weightRaw, 0);
        if (!rows.every((r) => feature in r)) {
          throw new Error(`重み対象列 '${feature}' がCSVに見つかりません。`);
        }
        const raw = rows.map((r) => parseNumber(r[feature], 0));
        const norm = normalizeMinMax(raw);
        const contrib = norm.map((n) => (weight >= 0 ? weight * n : Math.abs(weight) * (1 - n)));
        contributionByFeature[feature] = { norm, contrib };
        for (let i = 0; i < score.length; i += 1) {
          score[i] += contrib[i];
        }
      }

      const finalScore = score.map((s) => Math.max(s, scoreFloor));
      const allocation = allocateWithLimits(finalScore, minAlloc, maxAlloc, totalUnits);

      const resultRows = rows.map((r, idx) => {
        const row = {
          ...r,
          score_total: Number(finalScore[idx].toFixed(6)),
          allocation_units: allocation[idx]
        };
        for (const feature of Object.keys(featureWeights)) {
          row[`norm_${feature}`] = Number(contributionByFeature[feature].norm[idx].toFixed(6));
          row[`contrib_${feature}`] = Number(contributionByFeature[feature].contrib[idx].toFixed(6));
        }
        return row;
      });

      resultRows.sort((a, b) => {
        if (b.allocation_units !== a.allocation_units) {
          return b.allocation_units - a.allocation_units;
        }
        if (b.score_total !== a.score_total) {
          return b.score_total - a.score_total;
        }
        return String(a.jan_code).localeCompare(String(b.jan_code), "ja");
      });

      const allocatedSum = resultRows.reduce((acc, r) => acc + parseNumber(r.allocation_units, 0), 0);
      const summaryLines = [
        `source_csv_path: ${csvPath}`,
        `total_units: ${totalUnits}`,
        `rows: ${resultRows.length}`,
        `allocated_sum: ${allocatedSum}`,
        `min_allocate_sum: ${minSum}`,
        `max_allocate_sum: ${maxSum}`,
        "feature_weights:"
      ];
      for (const [k, v] of Object.entries(featureWeights)) {
        summaryLines.push(`  - ${k}: ${v}`);
      }
      summaryLines.push(`score_floor: ${scoreFloor}`);

      state.resultRows = resultRows;
      state.summaryText = summaryLines.join("\n");

      renderTopRows(resultRows);
      el.downloadCsvBtn.disabled = false;
      el.downloadSummaryBtn.disabled = false;

      log(
        [
          "配分計算が完了しました。",
          `source_csv_path: ${csvPath}`,
          `rows: ${resultRows.length}`,
          `allocated_sum: ${allocatedSum}`,
          "結果CSV/サマリTXTを保存できます。"
        ].join("\n")
      );
    } catch (err) {
      state.resultRows = [];
      state.summaryText = "";
      el.downloadCsvBtn.disabled = true;
      el.downloadSummaryBtn.disabled = true;
      renderTopRows([]);

      const originHint = window.location.protocol === "file:"
        ? "\n補足: file:// 直開きでは固定パス読込できません。ローカルサーバで開いてください。"
        : "";
      log(`エラー: ${err.message}${originHint}`);
    }
  }

  function downloadBlob(filename, content, mimeType) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function timestamp() {
    const now = new Date();
    const p = (n) => String(n).padStart(2, "0");
    return [
      now.getFullYear(),
      p(now.getMonth() + 1),
      p(now.getDate()),
      "_",
      p(now.getHours()),
      p(now.getMinutes()),
      p(now.getSeconds())
    ].join("");
  }

  function downloadResultCsv() {
    if (!state.resultRows.length) return;
    const csv = buildResultCsv(state.resultRows);
    downloadBlob(`allocation_result_${timestamp()}.csv`, csv, "text/csv;charset=utf-8");
  }

  function downloadSummary() {
    if (!state.summaryText) return;
    downloadBlob(`allocation_result_${timestamp()}_summary.txt`, state.summaryText, "text/plain;charset=utf-8");
  }
})();
