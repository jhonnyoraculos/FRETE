"""
Cálculo consolidado do custo de frete a partir das métricas agregadas.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict
import unicodedata

import importlib
import threading

# Pré-carrega todos os dados necessários na importação do módulo.
DADOS: Dict[str, object] | None = None
_DADOS_LOCK = threading.Lock()

TEMPO_DESCARGA_POR_TONELADA_HORAS = 1.0
VELOCIDADE_MEDIA_KM_POR_HORA = 80.0
HORAS_TRABALHO_POR_DIA = 10.0


@dataclass
class ResultadoFrete:
    """Representa o detalhamento completo do custo de um frete."""

    placa: str
    distancia_km: float
    peso_toneladas: float
    colaboradores: int
    tempo_descarga_horas: float
    tempo_viagem_horas: float
    tempo_total_horas: float
    dias_trabalho: float
    custo_combustivel: float
    custo_manutencao: float
    custo_pedagio: float
    custo_reserva: float
    custo_mao_de_obra_total: float
    custo_total: float


def _get_frete_dados():
    return importlib.import_module("frete_dados")


def dados_carregados() -> bool:
    return DADOS is not None


def get_dados() -> Dict[str, object]:
    global DADOS
    if DADOS is None:
        with _DADOS_LOCK:
            if DADOS is None:
                DADOS = _get_frete_dados().carregar_todos_os_dados()
    return DADOS


def formatar_dias_horas(tempo_total_horas: float) -> str:
    """Converte horas em dias e horas usando 10h por dia."""
    if tempo_total_horas <= 0:
        return "0 horas"

    dias = int(tempo_total_horas // HORAS_TRABALHO_POR_DIA)
    horas_restantes = tempo_total_horas - (dias * HORAS_TRABALHO_POR_DIA)
    horas = int(round(horas_restantes))
    if horas >= int(HORAS_TRABALHO_POR_DIA):
        dias += 1
        horas = 0

    dia_label = "dia" if dias == 1 else "dias"
    hora_label = "hora" if horas == 1 else "horas"

    if dias > 0 and horas > 0:
        return f"{dias} {dia_label} e {horas} {hora_label}"
    if dias > 0:
        return f"{dias} {dia_label}"
    return f"{horas} {hora_label}"


def _normalizar_placa(placa: str) -> str:
    """Normaliza a placa para maiúsculas, removendo acentos e símbolos."""
    if not placa:
        return ""
    texto = placa.strip().upper()
    texto = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )
    texto = "".join(ch for ch in texto if ch.isalnum())
    return texto


def _buscar_componente(
    tabela: Dict[str, float],
    placa: str,
) -> float:
    """Retorna o valor da tabela para a placa informada, caindo para 0.0."""
    return float(tabela.get(placa, 0.0))


def calcular_frete(
    placa: str,
    distancia_km: float,
    peso_toneladas: float,
    colaboradores: int,
    incluir_pedagio: bool = False,
    incluir_reserva: bool = True,
) -> ResultadoFrete:
    """
    Calcula todas as componentes do custo para uma placa específica.
    """
    placa_normalizada = _normalizar_placa(placa)
    placa_exibicao = placa.strip().upper() if placa else placa_normalizada
    distancia = max(float(distancia_km), 0.0)
    peso = max(float(peso_toneladas), 0.0)
    colaboradores = max(int(colaboradores), 0)
    dados = get_dados()

    tempo_descarga_horas = peso * TEMPO_DESCARGA_POR_TONELADA_HORAS
    tempo_viagem_horas = distancia / VELOCIDADE_MEDIA_KM_POR_HORA if distancia > 0 else 0.0
    tempo_total_horas = tempo_descarga_horas + tempo_viagem_horas
    dias_trabalho = tempo_total_horas / HORAS_TRABALHO_POR_DIA if tempo_total_horas > 0 else 0.0

    custo_combustivel_por_km = _buscar_componente(
        dados.get("custo_combustivel_por_km_por_placa", {}),
        placa_normalizada,
    )
    custo_manutencao_por_km = _buscar_componente(
        dados.get("custo_manutencao_por_km_por_placa", {}),
        placa_normalizada,
    )
    custo_pedagio_por_km = (
        _buscar_componente(
            dados.get("custo_pedagio_por_km_por_placa", {}),
            placa_normalizada,
        )
        if incluir_pedagio
        else 0.0
    )

    custo_combustivel = custo_combustivel_por_km * distancia
    custo_manutencao = custo_manutencao_por_km * distancia
    custo_pedagio = custo_pedagio_por_km * distancia
    if incluir_reserva:
        custo_reserva_por_km = float(dados.get("custo_reserva_por_km", 0.0))
        fator_diarias = colaboradores / 2 if colaboradores > 0 else 0.0
        custo_reserva = custo_reserva_por_km * distancia * fator_diarias
    else:
        custo_reserva = 0.0

    custo_hora_colaborador = float(dados.get("custo_hora_colaborador", 0.0))
    custo_diaria = custo_hora_colaborador * HORAS_TRABALHO_POR_DIA
    custo_mao_de_obra_total = custo_diaria * dias_trabalho * colaboradores

    custo_total = (
        custo_combustivel
        + custo_manutencao
        + custo_pedagio
        + custo_reserva
        + custo_mao_de_obra_total
    )

    return ResultadoFrete(
        placa=placa_exibicao or placa_normalizada,
        distancia_km=distancia,
        peso_toneladas=peso,
        colaboradores=colaboradores,
        tempo_descarga_horas=tempo_descarga_horas,
        tempo_viagem_horas=tempo_viagem_horas,
        tempo_total_horas=tempo_total_horas,
        dias_trabalho=dias_trabalho,
        custo_combustivel=custo_combustivel,
        custo_manutencao=custo_manutencao,
        custo_pedagio=custo_pedagio,
        custo_reserva=custo_reserva,
        custo_mao_de_obra_total=custo_mao_de_obra_total,
        custo_total=custo_total,
    )


def _formatar_reais(valor: float) -> str:
    """Formata valores monetários em reais com duas casas decimais."""
    formatado = f"{valor:,.2f}"
    return "R$ " + formatado.replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_resultado(res: ResultadoFrete) -> str:
    """
    Retorna uma string detalhando as componentes do frete e o total em reais.
    """
    return (
        f"Placa: {res.placa}\n"
        f"Distância: {res.distancia_km:.2f} km\n"
        f"Peso: {res.peso_toneladas:.2f} t\n"
        f"Colaboradores: {res.colaboradores}\n"
        f"Tempo estimado de descarga: {res.tempo_descarga_horas:.2f} h\n"
        f"Tempo estimado de viagem (80 km/h): {res.tempo_viagem_horas:.2f} h\n"
        f"Tempo total estimado (viagem + descarga): {res.tempo_total_horas:.2f} h\n"
        f"Dias estimados de trabalho: {res.dias_trabalho:.2f}\n"
        f"Custo combustível: {_formatar_reais(res.custo_combustivel)}\n"
        f"Custo manutenção: {_formatar_reais(res.custo_manutencao)}\n"
        f"Custo pedágio: {_formatar_reais(res.custo_pedagio)}\n"
        f"Custo reserva: {_formatar_reais(res.custo_reserva)}\n"
        f"Custo mao de obra (total): {_formatar_reais(res.custo_mao_de_obra_total)}\n"
        f"Custo total: {_formatar_reais(res.custo_total)}\n"
        "Aviso: tempos sao estimativas.\n"
        "Descarga = 1 h por tonelada.\n"
        "Viagem = distancia / 80 km/h."
    )
