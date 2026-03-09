const data = window.FRETE_WEB_DATA;

const refs = {
  form: document.getElementById("freteForm"),
  placa: document.getElementById("placaInput"),
  distancia: document.getElementById("distanciaInput"),
  peso: document.getElementById("pesoInput"),
  colaboradores: document.getElementById("colaboradoresInput"),
  pedagio: document.getElementById("pedagioInput"),
  reserva: document.getElementById("reservaInput"),
  limpar: document.getElementById("limparBtn"),
  copiar: document.getElementById("copiarBtn"),
  message: document.getElementById("statusMessage"),
  total: document.getElementById("totalOutput"),
  summary: document.getElementById("summaryOutput"),
  metrics: document.getElementById("metricsOutput"),
  yearBadge: document.getElementById("yearBadge"),
  plateBadge: document.getElementById("plateBadge"),
  dataBadge: document.getElementById("dataBadge"),
  generatedAt: document.getElementById("generatedAt"),
};

const DEFAULT_SUMMARY = "Aguardando calculo.";

function init() {
  if (!data) {
    setMessage("Base ausente. Rode python build_web_data.py antes de publicar.", true);
    refs.dataBadge.textContent = "Base indisponivel";
    refs.copiar.disabled = true;
    refs.form.querySelector("button[type='submit']").disabled = true;
    return;
  }

  populatePlates();
  hydrateMeta();
  renderSummary(DEFAULT_SUMMARY, 0);
  renderEmptyMetrics();
  bindEvents();
  setMessage("Base pronta para uso.", false);
}

function bindEvents() {
  refs.form.addEventListener("submit", handleSubmit);
  refs.limpar.addEventListener("click", handleClear);
  refs.copiar.addEventListener("click", handleCopy);

  [refs.placa, refs.distancia, refs.peso, refs.colaboradores].forEach((field) => {
    field.addEventListener("input", () => field.classList.remove("is-invalid"));
    field.addEventListener("change", () => field.classList.remove("is-invalid"));
  });
}

function populatePlates() {
  const plates = data.plates?.length
    ? data.plates
    : Object.keys(data.metrics.custo_combustivel_por_km_por_placa || {}).sort();

  const fragment = document.createDocumentFragment();
  for (const plate of plates) {
    const option = document.createElement("option");
    option.value = plate;
    option.textContent = plate;
    fragment.appendChild(option);
  }

  refs.placa.appendChild(fragment);
}

function hydrateMeta() {
  refs.yearBadge.textContent = `Base ${data.year_reference}`;
  refs.plateBadge.textContent = `${data.plates.length} placas`;
  refs.dataBadge.textContent = "Base carregada";
  refs.generatedAt.textContent = `Ultima geracao: ${formatDateTime(data.generated_at)}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
    timeZone: "America/Sao_Paulo",
  }).format(date);
}

function setMessage(text, isError = false) {
  refs.message.textContent = text;
  refs.message.classList.toggle("is-error", isError);
  refs.message.classList.toggle("is-success", !isError);
}

function clearMessage() {
  refs.message.textContent = "";
  refs.message.classList.remove("is-error", "is-success");
}

function handleSubmit(event) {
  event.preventDefault();
  clearMessage();

  const payload = validateForm();
  if (!payload) {
    setMessage("Confira os campos em destaque e tente novamente.", true);
    return;
  }

  const result = calculateFrete(payload);
  renderSummary(formatSummary(result), result.custoTotal);
  renderMetrics(result, payload);

  if (!result.hasFuelData) {
    setMessage(`Aviso: placa sem dados de combustivel em ${data.year_reference}.`, true);
    return;
  }

  setMessage("Calculo de custo concluido.", false);
}

function handleClear() {
  refs.form.reset();
  [refs.placa, refs.distancia, refs.peso, refs.colaboradores].forEach((field) => {
    field.classList.remove("is-invalid");
  });
  renderSummary(DEFAULT_SUMMARY, 0);
  renderEmptyMetrics();
  setMessage("Campos limpos.", false);
}

async function handleCopy() {
  const text = refs.summary.textContent.trim();
  if (!text || text === DEFAULT_SUMMARY) {
    setMessage("Nao ha resumo para copiar.", true);
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    setMessage("Resumo copiado para a area de transferencia.", false);
  } catch (error) {
    setMessage("Nao foi possivel copiar o resumo neste navegador.", true);
  }
}

function validateForm() {
  const placa = refs.placa.value.trim();
  const distancia = parseLocaleNumber(refs.distancia.value);
  const peso = parseLocaleNumber(refs.peso.value);
  const colaboradores = parseInt(refs.colaboradores.value, 10);

  const invalidPlate = !placa;
  const invalidDistance = !Number.isFinite(distancia) || distancia <= 0;
  const invalidWeight = !Number.isFinite(peso) || peso <= 0;
  const invalidCollaborators = !Number.isInteger(colaboradores) || colaboradores <= 0;

  refs.placa.classList.toggle("is-invalid", invalidPlate);
  refs.distancia.classList.toggle("is-invalid", invalidDistance);
  refs.peso.classList.toggle("is-invalid", invalidWeight);
  refs.colaboradores.classList.toggle("is-invalid", invalidCollaborators);

  if (invalidPlate || invalidDistance || invalidWeight || invalidCollaborators) {
    return null;
  }

  return {
    placa,
    distanciaKm: distancia,
    pesoToneladas: peso,
    colaboradores,
    incluirPedagio: refs.pedagio.checked,
    incluirReserva: refs.reserva.checked,
  };
}

function parseLocaleNumber(value) {
  if (!value) {
    return Number.NaN;
  }

  const normalized = value.replace(",", ".").trim();
  const numeric = Number(normalized);
  return Number.isFinite(numeric) ? numeric : Number.NaN;
}

function normalizePlate(value) {
  return value
    .trim()
    .toUpperCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Z0-9]/g, "");
}

function lookupMetric(table, plate) {
  return Number(table?.[plate] ?? 0);
}

function calculateFrete(payload) {
  const plate = normalizePlate(payload.placa);
  const metrics = data.metrics;
  const constants = data.constants;

  const tempoDescargaHoras = payload.pesoToneladas * constants.tempo_descarga_por_tonelada_horas;
  const tempoViagemHoras = payload.distanciaKm > 0
    ? payload.distanciaKm / constants.velocidade_media_km_por_hora
    : 0;
  const tempoTotalHoras = tempoDescargaHoras + tempoViagemHoras;
  const diasTrabalho = tempoTotalHoras > 0
    ? tempoTotalHoras / constants.horas_trabalho_por_dia
    : 0;

  const custoCombustivelPorKm = lookupMetric(metrics.custo_combustivel_por_km_por_placa, plate);
  const custoManutencaoPorKm = lookupMetric(metrics.custo_manutencao_por_km_por_placa, plate);
  const custoPedagioPorKm = payload.incluirPedagio
    ? lookupMetric(metrics.custo_pedagio_por_km_por_placa, plate)
    : 0;
  const custoReservaPorKm = payload.incluirReserva
    ? Number(metrics.custo_reserva_por_km ?? 0)
    : 0;
  const custoHoraColaborador = Number(metrics.custo_hora_colaborador ?? 0);

  const custoCombustivel = custoCombustivelPorKm * payload.distanciaKm;
  const custoManutencao = custoManutencaoPorKm * payload.distanciaKm;
  const custoPedagio = custoPedagioPorKm * payload.distanciaKm;
  const fatorDiarias = payload.colaboradores > 0 ? payload.colaboradores / 2 : 0;
  const custoReserva = custoReservaPorKm * payload.distanciaKm * fatorDiarias;
  const custoDiaria = custoHoraColaborador * constants.horas_trabalho_por_dia;
  const custoMaoDeObraTotal = custoDiaria * diasTrabalho * payload.colaboradores;
  const custoTotal = custoCombustivel + custoManutencao + custoPedagio + custoReserva + custoMaoDeObraTotal;

  return {
    placa: payload.placa.trim().toUpperCase(),
    placaNormalizada: plate,
    distanciaKm: payload.distanciaKm,
    pesoToneladas: payload.pesoToneladas,
    colaboradores: payload.colaboradores,
    tempoDescargaHoras,
    tempoViagemHoras,
    tempoTotalHoras,
    diasTrabalho,
    custoCombustivel,
    custoManutencao,
    custoPedagio,
    custoReserva,
    custoMaoDeObraTotal,
    custoTotal,
    hasFuelData: Object.prototype.hasOwnProperty.call(metrics.custo_combustivel_por_km_por_placa || {}, plate),
  };
}

function formatCurrency(value) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(value || 0);
}

function formatNumber(value, digits = 2) {
  return new Intl.NumberFormat("pt-BR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value || 0);
}

function formatDaysHours(totalHours) {
  const hoursPerDay = Number(data.constants.horas_trabalho_por_dia || 10);
  if (totalHours <= 0) {
    return "0 horas";
  }

  let days = Math.floor(totalHours / hoursPerDay);
  let hours = Math.round(totalHours - days * hoursPerDay);

  if (hours >= hoursPerDay) {
    days += 1;
    hours = 0;
  }

  const dayLabel = days === 1 ? "dia" : "dias";
  const hourLabel = hours === 1 ? "hora" : "horas";

  if (days > 0 && hours > 0) {
    return `${days} ${dayLabel} e ${hours} ${hourLabel}`;
  }
  if (days > 0) {
    return `${days} ${dayLabel}`;
  }
  return `${hours} ${hourLabel}`;
}

function formatSummary(result) {
  return [
    `Placa: ${result.placa || result.placaNormalizada}`,
    `Distancia: ${formatNumber(result.distanciaKm)} km`,
    `Peso: ${formatNumber(result.pesoToneladas)} t`,
    `Colaboradores: ${result.colaboradores}`,
    `Tempo estimado de descarga: ${formatNumber(result.tempoDescargaHoras)} h`,
    `Tempo estimado de viagem (80 km/h): ${formatNumber(result.tempoViagemHoras)} h`,
    `Tempo total estimado (viagem + descarga): ${formatNumber(result.tempoTotalHoras)} h`,
    `Dias estimados de trabalho: ${formatNumber(result.diasTrabalho)}`,
    `Custo combustivel: ${formatCurrency(result.custoCombustivel)}`,
    `Custo manutencao: ${formatCurrency(result.custoManutencao)}`,
    `Custo pedagio: ${formatCurrency(result.custoPedagio)}`,
    `Custo reserva: ${formatCurrency(result.custoReserva)}`,
    `Custo mao de obra (total): ${formatCurrency(result.custoMaoDeObraTotal)}`,
    `Custo total: ${formatCurrency(result.custoTotal)}`,
    "Aviso: tempos sao estimativas.",
    "Descarga = 1 h por tonelada.",
    "Viagem = distancia / 80 km/h.",
  ].join("\n");
}

function renderSummary(text, total) {
  refs.summary.textContent = text;
  refs.total.textContent = formatCurrency(total);
}

function renderEmptyMetrics() {
  refs.metrics.innerHTML = "";
  const empty = document.createElement("article");
  empty.className = "metric-card metric-empty";
  empty.innerHTML = "<span>Preencha os dados para ver as metricas do frete.</span>";
  refs.metrics.appendChild(empty);
}

function renderMetrics(result, payload) {
  const cards = [
    {
      label: "Combustivel por km",
      value: formatCurrency(result.custoCombustivel / result.distanciaKm),
    },
    {
      label: "Manutencao por km",
      value: formatCurrency(result.custoManutencao / result.distanciaKm),
    },
    {
      label: "Pedagio por km",
      value: payload.incluirPedagio
        ? formatCurrency(result.custoPedagio / result.distanciaKm)
        : "Desativado",
    },
    {
      label: "Reserva por km",
      value: payload.incluirReserva
        ? formatCurrency(result.custoReserva / result.distanciaKm)
        : "Desativado",
    },
    {
      label: "Mao de obra por km",
      value: formatCurrency(result.custoMaoDeObraTotal / result.distanciaKm),
    },
    {
      label: "Tempo medio de viagem",
      value: `${formatNumber(result.tempoViagemHoras)} h`,
    },
    {
      label: "Tempo total medio",
      value: `${formatNumber(result.tempoTotalHoras)} h`,
    },
    {
      label: "Dias estimados",
      value: formatDaysHours(result.tempoTotalHoras),
    },
  ];

  if (result.diasTrabalho > 0 && result.colaboradores > 0) {
    const custoDiaria = result.custoMaoDeObraTotal / (result.diasTrabalho * result.colaboradores);
    cards.push({
      label: "Diaria por colaborador",
      value: formatCurrency(custoDiaria),
    });
  }

  refs.metrics.innerHTML = "";
  for (const card of cards) {
    const article = document.createElement("article");
    article.className = "metric-card";
    article.innerHTML = `<label>${card.label}</label><strong>${card.value}</strong>`;
    refs.metrics.appendChild(article);
  }
}

init();
