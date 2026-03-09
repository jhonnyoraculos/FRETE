from __future__ import annotations

from html import escape
from pathlib import Path

import streamlit as st

import frete_calculo
import frete_dados


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
LOGO_FILE = ROOT / "logo-jr.png"
PLATES_FILE = ROOT / "placas_permitidas.txt"

RESULT_KEY = "resultado_frete"
SUMMARY_KEY = "resumo_frete"
STATUS_TEXT_KEY = "status_texto"
STATUS_LEVEL_KEY = "status_nivel"
HAS_FUEL_DATA_KEY = "placa_tem_dados"
DIAGNOSTIC_KEY = "diagnostico_placa"

DEFAULT_STATE = {
    "placa_input": "",
    "distancia_input": "",
    "peso_input": "",
    "colaboradores_input": "",
    "pedagio_input": False,
    "reserva_input": True,
}


@st.cache_data(show_spinner=False)
def load_allowed_plates() -> list[str]:
    if PLATES_FILE.exists():
        plates: list[str] = []
        seen: set[str] = set()
        for line in PLATES_FILE.read_text(encoding="utf-8").splitlines():
            plate = line.strip().replace(" ", "").upper()
            if not plate or plate in seen:
                continue
            plates.append(plate)
            seen.add(plate)
        return plates
    return frete_dados.get_lista_placas()


@st.cache_resource(show_spinner="Carregando planilhas e metricas...")
def load_base_data() -> dict[str, object]:
    return frete_calculo.get_dados()


def clear_data_caches() -> None:
    load_base_data.clear()
    load_allowed_plates.clear()
    frete_calculo.limpar_cache_dados()


def ensure_session_state() -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)


def reset_form_state() -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value
    for key in (RESULT_KEY, SUMMARY_KEY, STATUS_TEXT_KEY, STATUS_LEVEL_KEY, HAS_FUEL_DATA_KEY, DIAGNOSTIC_KEY):
        st.session_state.pop(key, None)


def format_currency(value: float) -> str:
    inteiro, decimal = f"{value:,.2f}".split(".")
    inteiro = inteiro.replace(",", ".")
    return f"R$ {inteiro},{decimal}"


def format_decimal(value: float, suffix: str = "") -> str:
    inteiro, decimal = f"{value:,.2f}".split(".")
    inteiro = inteiro.replace(",", ".")
    if suffix:
        return f"{inteiro},{decimal} {suffix}"
    return f"{inteiro},{decimal}"


def normalize_plate(value: str) -> str:
    text = value.strip().upper()
    return "".join(ch for ch in text if ch.isalnum())


def parse_positive_float(value: str) -> float | None:
    text = value.strip().replace(",", ".")
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def parse_positive_int(value: str) -> int | None:
    text = value.strip()
    if not text:
        return None
    if not text.isdigit():
        return None
    parsed = int(text)
    return parsed if parsed > 0 else None


def build_metric_card(label: str, value: str) -> str:
    return (
        "<div class='metric-card'>"
        f"<span>{label}</span>"
        f"<strong>{value}</strong>"
        "</div>"
    )


def build_diagnostic_html(diagnostic: dict[str, float | int]) -> str:
    return (
        "<div class='summary-shell'>"
        "<section class='summary-group'>"
        "<h4>Custos brutos encontrados na base</h4>"
        "<div class='summary-item'><span>Abastecimentos lancados</span>"
        f"<strong>{int(diagnostic.get('combustivel_lancamentos', 0))}</strong></div>"
        "<div class='summary-item'><span>Custo bruto de combustivel</span>"
        f"<strong>{escape(format_currency(float(diagnostic.get('combustivel_custo_total', 0.0))))}</strong></div>"
        "<div class='summary-item'><span>Km rodados validos preenchidos</span>"
        f"<strong>{escape(format_decimal(float(diagnostic.get('combustivel_km_total', 0.0)), 'km'))}</strong></div>"
        "<div class='summary-item'><span>Lancamentos de manutencao</span>"
        f"<strong>{int(diagnostic.get('manutencao_lancamentos', 0))}</strong></div>"
        "<div class='summary-item'><span>Custo bruto de manutencao</span>"
        f"<strong>{escape(format_currency(float(diagnostic.get('manutencao_custo_total', 0.0))))}</strong></div>"
        "<div class='summary-item'><span>Lancamentos de pedagio</span>"
        f"<strong>{int(diagnostic.get('pedagio_lancamentos', 0))}</strong></div>"
        "<div class='summary-item'><span>Custo bruto de pedagio</span>"
        f"<strong>{escape(format_currency(float(diagnostic.get('pedagio_custo_total', 0.0))))}</strong></div>"
        "</section>"
        "</div>"
    )


def build_summary_text(resultado: frete_calculo.ResultadoFrete) -> str:
    return "\n".join(
        [
            "RESUMO DO FRETE",
            "",
            "Dados informados",
            f"- Placa: {resultado.placa}",
            f"- Distancia: {format_decimal(resultado.distancia_km, 'km')}",
            f"- Peso: {format_decimal(resultado.peso_toneladas, 't')}",
            f"- Colaboradores: {resultado.colaboradores}",
            "",
            "Estimativa operacional",
            f"- Tempo de descarga: {format_decimal(resultado.tempo_descarga_horas, 'h')}",
            f"- Tempo de viagem: {format_decimal(resultado.tempo_viagem_horas, 'h')}",
            f"- Tempo total estimado: {format_decimal(resultado.tempo_total_horas, 'h')}",
            f"- Dias estimados de trabalho: {frete_calculo.formatar_dias_horas(resultado.tempo_total_horas)}",
            "",
            "Composicao do custo",
            f"- Combustivel: {format_currency(resultado.custo_combustivel)}",
            f"- Manutencao: {format_currency(resultado.custo_manutencao)}",
            f"- Pedagio: {format_currency(resultado.custo_pedagio)}",
            f"- Hospedagem (quarto duplo rateado): {format_currency(resultado.custo_reserva)}",
            f"- Mao de obra total: {format_currency(resultado.custo_mao_de_obra_total)}",
            f"- Custo total: {format_currency(resultado.custo_total)}",
            "",
            "Observacoes",
            "- Os tempos sao estimativas.",
            "- Descarga considerada: 1 hora por tonelada.",
            "- Viagem considerada: distancia dividida por 80 km/h.",
            "- Hospedagem usa valores de quartos duplos da planilha, com meia diaria por colaborador.",
        ]
    )


def build_summary_html(resultado: frete_calculo.ResultadoFrete) -> str:
    sections = [
        (
            "Dados informados",
            [
                ("Placa", escape(resultado.placa)),
                ("Distancia", format_decimal(resultado.distancia_km, "km")),
                ("Peso", format_decimal(resultado.peso_toneladas, "t")),
                ("Colaboradores", str(resultado.colaboradores)),
            ],
        ),
        (
            "Estimativa operacional",
            [
                ("Tempo de descarga", format_decimal(resultado.tempo_descarga_horas, "h")),
                ("Tempo de viagem", format_decimal(resultado.tempo_viagem_horas, "h")),
                ("Tempo total estimado", format_decimal(resultado.tempo_total_horas, "h")),
                ("Dias de trabalho", frete_calculo.formatar_dias_horas(resultado.tempo_total_horas)),
            ],
        ),
        (
            "Composicao do custo",
            [
                ("Combustivel", format_currency(resultado.custo_combustivel)),
                ("Manutencao", format_currency(resultado.custo_manutencao)),
                ("Pedagio", format_currency(resultado.custo_pedagio)),
                ("Hospedagem (quarto duplo rateado)", format_currency(resultado.custo_reserva)),
                ("Mao de obra total", format_currency(resultado.custo_mao_de_obra_total)),
                ("Custo total", format_currency(resultado.custo_total)),
            ],
        ),
    ]

    blocks: list[str] = ["<div class='summary-shell'>"]
    for title, items in sections:
        blocks.append("<section class='summary-group'>")
        blocks.append(f"<h4>{title}</h4>")
        for label, value in items:
            blocks.append(
                "<div class='summary-item'>"
                f"<span>{label}</span>"
                f"<strong>{escape(value)}</strong>"
                "</div>"
            )
        blocks.append("</section>")

    blocks.append(
        "<section class='summary-group summary-note'>"
        "<h4>Observacoes</h4>"
        "<ul>"
        "<li>Os tempos apresentados sao estimativas.</li>"
        "<li>A descarga considera 1 hora por tonelada.</li>"
        "<li>A viagem considera velocidade media de 80 km/h.</li>"
        "<li>Hospedagem considera quartos duplos da planilha, com meia diaria por colaborador.</li>"
        "</ul>"
        "</section>"
    )
    blocks.append("</div>")
    return "".join(blocks)


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at top left, rgba(217, 111, 51, 0.18), transparent 26%),
                radial-gradient(circle at bottom right, rgba(47, 108, 90, 0.16), transparent 24%),
                linear-gradient(180deg, #f4eee5 0%, #efe6da 100%);
            color: #142025;
        }
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
            max-width: 1200px;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #172127 0%, #1d2a31 100%);
        }
        [data-testid="stSidebar"] * {
            color: #f4eee5;
        }
        div[data-testid="stMetric"] {
            background: rgba(255, 250, 242, 0.82);
            border: 1px solid rgba(180, 92, 46, 0.14);
            padding: 1rem 1.1rem;
            border-radius: 18px;
            box-shadow: 0 18px 40px rgba(95, 67, 42, 0.08);
        }
        div.stButton > button,
        div.stDownloadButton > button,
        div[data-testid="baseButton-secondary"] > button {
            border-radius: 999px;
            min-height: 2.9rem;
            border: 1px solid rgba(180, 92, 46, 0.18);
        }
        div.stButton > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #d96f33, #b85c2e);
            color: white;
        }
        .hero-card {
            padding: 1.6rem 1.7rem;
            border-radius: 28px;
            border: 1px solid rgba(180, 92, 46, 0.16);
            background:
                linear-gradient(135deg, rgba(217, 111, 51, 0.16), transparent 42%),
                linear-gradient(120deg, rgba(47, 108, 90, 0.14), transparent 55%),
                rgba(255, 250, 242, 0.76);
            box-shadow: 0 26px 70px rgba(87, 59, 36, 0.12);
            margin-bottom: 1rem;
        }
        .hero-card h1 {
            margin: 0;
            font-size: 2.4rem;
            line-height: 0.95;
            color: #142025;
        }
        .hero-kicker {
            margin: 0 0 0.45rem 0;
            font-size: 0.78rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            color: #b85c2e;
            font-weight: 700;
        }
        .hero-copy {
            margin: 0.75rem 0 0 0;
            color: #51636b;
            line-height: 1.6;
        }
        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.55rem;
            margin-top: 1rem;
        }
        .pill {
            display: inline-flex;
            align-items: center;
            padding: 0.45rem 0.8rem;
            border-radius: 999px;
            background: rgba(20, 32, 37, 0.06);
            border: 1px solid rgba(20, 32, 37, 0.08);
            color: #46575e;
            font-size: 0.82rem;
        }
        .section-card {
            padding: 1.1rem 1.15rem 0.4rem 1.15rem;
            border-radius: 24px;
            border: 1px solid rgba(180, 92, 46, 0.12);
            background: rgba(255, 250, 242, 0.78);
            box-shadow: 0 18px 45px rgba(87, 59, 36, 0.08);
        }
        .section-card h3 {
            margin: 0 0 0.25rem 0;
            color: #142025;
        }
        .section-card p {
            margin: 0;
            color: #5c6b72;
        }
        .summary-shell {
            display: grid;
            gap: 0.9rem;
        }
        .summary-group {
            padding: 1rem 1.1rem;
            border-radius: 22px;
            border: 1px solid rgba(20, 32, 37, 0.08);
            background: #152126;
            color: #f4eee5;
            box-shadow: 0 18px 42px rgba(19, 30, 34, 0.22);
        }
        .summary-group h4 {
            margin: 0 0 0.8rem 0;
            color: #f6c08b;
            font-size: 0.92rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .summary-item {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            padding: 0.52rem 0;
            border-top: 1px solid rgba(244, 238, 229, 0.08);
        }
        .summary-item:first-of-type {
            border-top: 0;
            padding-top: 0;
        }
        .summary-item span {
            color: #a9bcc1;
        }
        .summary-item strong {
            color: #f4eee5;
            text-align: right;
            font-weight: 700;
        }
        .summary-note ul {
            margin: 0;
            padding-left: 1rem;
            color: #d8e2e4;
            line-height: 1.6;
        }
        .metric-card {
            padding: 1rem;
            border-radius: 18px;
            border: 1px solid rgba(180, 92, 46, 0.12);
            background: rgba(255, 250, 242, 0.82);
            box-shadow: 0 14px 34px rgba(87, 59, 36, 0.07);
            min-height: 112px;
        }
        .metric-card span {
            display: block;
            margin-bottom: 0.5rem;
            font-size: 0.78rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #6a7a81;
        }
        .metric-card strong {
            font-size: 1.08rem;
            color: #142025;
            line-height: 1.35;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_header(plates: list[str]) -> None:
    status = "Base carregada" if frete_calculo.dados_carregados() else "Base sera carregada no primeiro calculo"
    st.markdown(
        f"""
        <div class="hero-card">
            <p class="hero-kicker">Streamlit Edition</p>
            <h1>Calculadora de Frete JR</h1>
            <p class="hero-copy">
                O app roda direto em Python e usa as planilhas da pasta <code>data/</code>.
                Quando quiser atualizar a base, basta trocar os arquivos Excel e recarregar o cache.
            </p>
            <div class="pill-row">
                <span class="pill">Ano base: {frete_dados.ANO_REFERENCIA}</span>
                <span class="pill">Placas: {len(plates)}</span>
                <span class="pill">{status}</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(plates: list[str]) -> None:
    with st.sidebar:
        if LOGO_FILE.exists():
            st.image(str(LOGO_FILE), width=90)

        if st.button("Recarregar planilhas", use_container_width=True):
            clear_data_caches()
            st.session_state.pop(RESULT_KEY, None)
            st.session_state.pop(SUMMARY_KEY, None)
            st.session_state.pop(HAS_FUEL_DATA_KEY, None)
            st.session_state.pop(DIAGNOSTIC_KEY, None)
            st.session_state[STATUS_TEXT_KEY] = "Cache limpo. A base sera recarregada no proximo calculo."
            st.session_state[STATUS_LEVEL_KEY] = "success"
            st.rerun()


def render_status() -> None:
    text = st.session_state.get(STATUS_TEXT_KEY)
    if not text:
        return

    level = st.session_state.get(STATUS_LEVEL_KEY, "info")
    if level == "error":
        st.error(text)
    elif level == "warning":
        st.warning(text)
    elif level == "success":
        st.success(text)
    else:
        st.info(text)


def render_metrics(
    resultado: frete_calculo.ResultadoFrete,
    incluir_pedagio: bool,
    incluir_reserva: bool,
    dados_base: dict[str, object],
) -> None:
    if resultado.distancia_km <= 0:
        st.info("Distancia invalida; nao foi possivel calcular metricas por km.")
        return

    cards = [
        ("Combustivel por km", format_currency(resultado.custo_combustivel / resultado.distancia_km)),
        ("Manutencao por km", format_currency(resultado.custo_manutencao / resultado.distancia_km)),
        (
            "Pedagio por km",
            format_currency(resultado.custo_pedagio / resultado.distancia_km) if incluir_pedagio else "Desativado",
        ),
        (
            "Reserva por km",
            format_currency(resultado.custo_reserva / resultado.distancia_km) if incluir_reserva else "Desativado",
        ),
        ("Mao de obra por km", format_currency(resultado.custo_mao_de_obra_total / resultado.distancia_km)),
        ("Tempo medio de viagem", f"{resultado.tempo_viagem_horas:.2f} h"),
        ("Tempo total medio", f"{resultado.tempo_total_horas:.2f} h"),
        ("Dias estimados", frete_calculo.formatar_dias_horas(resultado.tempo_total_horas)),
    ]

    if incluir_reserva and resultado.colaboradores > 0:
        diaria_quarto_duplo = float(dados_base.get("custo_reserva_por_km", 0.0)) * 500.0
        cards.append(("Diaria de hotel por colaborador", format_currency(diaria_quarto_duplo / 2)))
        cards.append(("Hospedagem total por colaborador", format_currency(resultado.custo_reserva / resultado.colaboradores)))

    if resultado.dias_trabalho > 0 and resultado.colaboradores > 0:
        diaria = resultado.custo_mao_de_obra_total / (resultado.dias_trabalho * resultado.colaboradores)
        cards.append(("Diaria de mao de obra por colaborador", format_currency(diaria)))

    columns = st.columns(2, gap="medium")
    for index, (label, value) in enumerate(cards):
        with columns[index % 2]:
            st.markdown(build_metric_card(label, value), unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(
        page_title="Calculadora de Frete JR",
        page_icon="🚚",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()
    ensure_session_state()

    try:
        plates = load_allowed_plates()
    except Exception as exc:
        st.error(f"Nao foi possivel carregar as placas: {exc}")
        return

    render_sidebar(plates)
    render_header(plates)
    render_status()

    left, right = st.columns([0.95, 1.05], gap="large")

    with left:
        st.markdown(
            """
            <div class="section-card">
                <h3>Parametros do frete</h3>
                <p>Preencha os dados e calcule o custo total da viagem.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        plate_options = [""] + plates

        with st.form("frete_form", clear_on_submit=False):
            st.selectbox(
                "Placa",
                options=plate_options,
                format_func=lambda value: "Selecione uma placa" if value == "" else value,
                key="placa_input",
            )
            col_a, col_b = st.columns(2)
            with col_a:
                st.text_input("Distancia (km)", key="distancia_input", placeholder="Ex: 120")
                st.text_input("Peso (t)", key="peso_input", placeholder="Ex: 2,5")
            with col_b:
                st.text_input("Colaboradores", key="colaboradores_input", placeholder="Ex: 2")
                st.markdown("")
                st.checkbox("Incluir pedagio", key="pedagio_input")
                st.checkbox("Incluir hoteis", key="reserva_input")

            action_left, action_right = st.columns(2)
            calcular = action_left.form_submit_button("Calcular custo", type="primary", use_container_width=True)
            limpar = action_right.form_submit_button("Limpar", use_container_width=True)

        if limpar:
            reset_form_state()
            st.rerun()

        if calcular:
            plate = st.session_state["placa_input"]
            distance = parse_positive_float(st.session_state["distancia_input"])
            weight = parse_positive_float(st.session_state["peso_input"])
            workers = parse_positive_int(st.session_state["colaboradores_input"])

            invalid_fields: list[str] = []
            if not plate:
                invalid_fields.append("placa")
            if distance is None:
                invalid_fields.append("distancia")
            if weight is None:
                invalid_fields.append("peso")
            if workers is None:
                invalid_fields.append("colaboradores")

            if invalid_fields:
                joined = ", ".join(invalid_fields)
                st.session_state[STATUS_TEXT_KEY] = f"Confira os campos invalidos: {joined}."
                st.session_state[STATUS_LEVEL_KEY] = "error"
                st.session_state.pop(RESULT_KEY, None)
                st.session_state.pop(SUMMARY_KEY, None)
                st.session_state.pop(HAS_FUEL_DATA_KEY, None)
                st.session_state.pop(DIAGNOSTIC_KEY, None)
                st.rerun()

            try:
                with st.spinner("Calculando custo do frete..."):
                    data = load_base_data()
                    result = frete_calculo.calcular_frete(
                        placa=plate,
                        distancia_km=distance,
                        peso_toneladas=weight,
                        colaboradores=workers,
                        incluir_pedagio=st.session_state["pedagio_input"],
                        incluir_reserva=st.session_state["reserva_input"],
                    )
                diagnostic = frete_dados.get_diagnostico_placa(plate)
                normalized_plate = normalize_plate(plate)
                has_fuel_data = normalized_plate in data.get("custo_combustivel_por_km_por_placa", {})

                st.session_state[RESULT_KEY] = result
                st.session_state[SUMMARY_KEY] = build_summary_text(result)
                st.session_state[HAS_FUEL_DATA_KEY] = has_fuel_data
                st.session_state[DIAGNOSTIC_KEY] = diagnostic
                if has_fuel_data:
                    st.session_state[STATUS_TEXT_KEY] = "Calculo de custo concluido."
                    st.session_state[STATUS_LEVEL_KEY] = "success"
                elif (
                    int(diagnostic.get("combustivel_lancamentos", 0)) > 0
                    and float(diagnostic.get("combustivel_km_total", 0.0)) <= 0
                ):
                    st.session_state[STATUS_TEXT_KEY] = (
                        "A placa tem abastecimentos lancados, mas o campo Km Rodados esta vazio ou zerado. "
                        "Por isso combustivel, manutencao e pedagio por km ficaram zerados."
                    )
                    st.session_state[STATUS_LEVEL_KEY] = "warning"
                else:
                    st.session_state[STATUS_TEXT_KEY] = (
                        f"Aviso: placa sem dados de combustivel em {frete_dados.ANO_REFERENCIA}."
                    )
                    st.session_state[STATUS_LEVEL_KEY] = "warning"
                st.rerun()
            except Exception as exc:
                st.session_state[STATUS_TEXT_KEY] = f"Erro ao calcular o custo: {exc}"
                st.session_state[STATUS_LEVEL_KEY] = "error"
                st.session_state.pop(RESULT_KEY, None)
                st.session_state.pop(SUMMARY_KEY, None)
                st.session_state.pop(HAS_FUEL_DATA_KEY, None)
                st.session_state.pop(DIAGNOSTIC_KEY, None)
                st.rerun()

    with right:
        st.markdown(
            """
            <div class="section-card">
                <h3>Resumo do custo</h3>
                <p>Resultado consolidado com total, composicao do frete e metricas operacionais.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        result = st.session_state.get(RESULT_KEY)
        summary = st.session_state.get(SUMMARY_KEY, "Aguardando calculo.")
        diagnostic = st.session_state.get(DIAGNOSTIC_KEY)

        if result is None:
            st.metric("Total do custo", "R$ 0,00")
            st.info("A calculadora vai carregar as planilhas da pasta data/ no primeiro calculo.")
            st.markdown(
                """
                <div class='summary-shell'>
                    <section class='summary-group'>
                        <h4>Resumo</h4>
                        <div class='summary-item'>
                            <span>Status</span>
                            <strong>Aguardando calculo</strong>
                        </div>
                    </section>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.metric("Total do custo", format_currency(result.custo_total))
            base_data = load_base_data()
            st.download_button(
                "Baixar resumo em TXT",
                data=summary,
                file_name="resumo_frete.txt",
                mime="text/plain",
                use_container_width=True,
            )
            st.markdown(build_summary_html(result), unsafe_allow_html=True)

            if diagnostic and (
                int(diagnostic.get("combustivel_lancamentos", 0)) > 0
                and float(diagnostic.get("combustivel_km_total", 0.0)) <= 0
            ):
                st.markdown("### Diagnostico da base")
                st.markdown(build_diagnostic_html(diagnostic), unsafe_allow_html=True)

            st.markdown("### Metricas")
            render_metrics(
                result,
                incluir_pedagio=st.session_state["pedagio_input"],
                incluir_reserva=st.session_state["reserva_input"],
                dados_base=base_data,
            )


if __name__ == "__main__":
    main()
