"""
Ferramentas de leitura e cálculo de métricas relacionadas ao custo de frete.

Este módulo centraliza o carregamento das planilhas fornecidas e expõe funções
de agregação por placa para apoiar o sistema de cálculo de frete.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import unicodedata
from typing import Dict, List
import re

import openpyxl
import pandas as pd

BASE_DIRETORIO_DADOS = Path(__file__).resolve().parent / "data"
CAMINHO_COMBUSTIVEL = BASE_DIRETORIO_DADOS / "combustivel.xlsx"
CAMINHO_MANUTENCAO = BASE_DIRETORIO_DADOS / "manutencao.xlsx"
CAMINHO_RESERVA = BASE_DIRETORIO_DADOS / "reserva de hoteis.xlsx"
CAMINHO_FUNCIONARIO = BASE_DIRETORIO_DADOS / "gasto por funcionario.xlsx"
CAMINHO_PEDAGIO = BASE_DIRETORIO_DADOS / "pedagio seguro e ipva.xlsx"

COL_PLACA_COMBUSTIVEL = "PLACA"
COL_KM_RODADO = "Km Rodados"
COL_LITROS = "Litros"
COL_CUSTO = "Custo"

COL_MANUT_PLACA = "PLACAS"
COL_MANUT_CUSTO = "Custo"

COL_PEDAGIO_PLACA = "PLACA"
COL_PEDAGIO_TIPO = "TIPO"
COL_PEDAGIO_CUSTO = "Custo"

COL_FUNC_MES = "MÊS"
COL_FUNC_VALOR = "VALOR"
COL_FUNC_COLABORADORES = "COLABORADORES"

COL_RESERVA_VALOR = "VALOR"

HORAS_TRABALHADAS_POR_MES = 220
DIAS_TRABALHO_POR_MES = 22
KM_POR_DOIS_DIAS_VIAGEM = 517
ANO_REFERENCIA = 2025


def _normalizar_texto(valor: object) -> str:
    """Normaliza texto removendo acentos e espaços extras."""
    if valor is None:
        return ""
    texto = str(valor).strip().upper()
    texto = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", texto)
        if not unicodedata.combining(caractere)
    )
    return texto


def _normalizar_coluna_placa(
    df: pd.DataFrame, coluna: str = COL_PLACA_COMBUSTIVEL
) -> pd.Series:
    """Normaliza a coluna de placas para facilitar junções entre planilhas."""
    serie = (
        df[coluna]
        .astype(str)
        .str.strip()
        .str.upper()
        .str.replace(r"[^A-Z0-9]", "", regex=True)
        .replace({"": pd.NA, "NAN": pd.NA, "NONE": pd.NA})
    )
    return serie


def _validar_colunas(df: pd.DataFrame, colunas: List[str]) -> None:
    """Garante que todas as colunas necessárias existem."""
    ausentes = [coluna for coluna in colunas if coluna not in df.columns]
    if ausentes:
        raise KeyError(f"As colunas {ausentes} não foram encontradas na planilha.")


def _converter_mes_ano_para_datetime(serie: pd.Series) -> pd.Series:
    """Converte valores de mês/ano (ex: jan/25) para datetime."""
    meses = {
        "JAN": 1,
        "FEV": 2,
        "MAR": 3,
        "ABR": 4,
        "MAI": 5,
        "JUN": 6,
        "JUL": 7,
        "AGO": 8,
        "SET": 9,
        "OUT": 10,
        "NOV": 11,
        "DEZ": 12,
    }

    def _parse_valor(valor: object) -> pd.Timestamp | pd.NaT:
        if valor is None or (isinstance(valor, float) and pd.isna(valor)):
            return pd.NaT
        texto = _normalizar_texto(valor)
        match = re.search(r"([A-Z]{3}).*?(\d{2,4})", texto)
        if not match:
            return pd.NaT
        mes = meses.get(match.group(1))
        if not mes:
            return pd.NaT
        ano = int(match.group(2))
        if ano < 100:
            ano += 2000
        return pd.Timestamp(ano, mes, 1)

    return serie.map(_parse_valor)


def _filtrar_por_ano(df: pd.DataFrame, colunas_data: List[str]) -> pd.DataFrame:
    """Filtra o DataFrame pelo ano de referência."""
    for coluna in colunas_data:
        if coluna not in df.columns:
            continue
        serie = df[coluna]
        if pd.api.types.is_datetime64_any_dtype(serie):
            serie_dt = serie
        else:
            serie_dt = pd.to_datetime(serie, errors="coerce", dayfirst=True)
            if serie_dt.isna().all():
                serie_dt = _converter_mes_ano_para_datetime(serie)
        if serie_dt.notna().any():
            return df[serie_dt.dt.year == ANO_REFERENCIA].copy()
    return df

def _normalizar_coluna_monetaria(serie: pd.Series) -> pd.Series:
    """Converte valores monetários em floats, aceitando formatos locais."""
    def _limpar(valor: object) -> object:
        if isinstance(valor, str):
            texto = (
                valor.replace("R$", "")
                .replace(" ", "")
                .replace(".", "")
                .replace(",", ".")
                .strip()
            )
            return texto or pd.NA
        return valor

    serie_normalizada = serie.map(_limpar)
    return pd.to_numeric(serie_normalizada, errors="coerce")


def _detectar_indice_cabecalho(arquivo: Path) -> int:
    """Identifica a linha (zero-based) onde o cabeçalho está localizado."""
    wb = openpyxl.load_workbook(arquivo, read_only=True, data_only=True)
    try:
        ws = wb.active
        for idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            if any((celula is not None) and str(celula).strip() for celula in row):
                return idx - 1  # pandas usa índice zero-based
    finally:
        wb.close()
    return 0


def _ler_planilha(caminho: str | Path) -> pd.DataFrame:
    """Lê um arquivo Excel e garante que o caminho exista."""
    arquivo = Path(caminho)
    if not arquivo.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {arquivo}")
    indice_cabecalho = _detectar_indice_cabecalho(arquivo)
    return pd.read_excel(arquivo, header=indice_cabecalho)


@lru_cache(maxsize=1)
def carregar_planilha_combustivel() -> pd.DataFrame:
    """Carrega a planilha de combustível (cache simples)."""
    return _ler_planilha(CAMINHO_COMBUSTIVEL)


@lru_cache(maxsize=1)
def carregar_planilha_manutencao() -> pd.DataFrame:
    """Carrega a planilha de manutenção de veículos (cache simples)."""
    return _ler_planilha(CAMINHO_MANUTENCAO)


@lru_cache(maxsize=1)
def carregar_planilha_reserva() -> pd.DataFrame:
    """Carrega a planilha de reservas de hotéis (cache simples)."""
    return _ler_planilha(CAMINHO_RESERVA)


@lru_cache(maxsize=1)
def carregar_planilha_funcionarios() -> pd.DataFrame:
    """Carrega a planilha de custos por funcionário (cache simples)."""
    return _ler_planilha(CAMINHO_FUNCIONARIO)


@lru_cache(maxsize=1)
def carregar_planilha_pedagio() -> pd.DataFrame:
    """Carrega a planilha com pedágio, seguro e IPVA (cache simples)."""
    return _ler_planilha(CAMINHO_PEDAGIO)


def limpar_cache_planilhas() -> None:
    """Limpa os caches das planilhas para forcar nova leitura do disco."""
    carregar_planilha_combustivel.cache_clear()
    carregar_planilha_manutencao.cache_clear()
    carregar_planilha_reserva.cache_clear()
    carregar_planilha_funcionarios.cache_clear()
    carregar_planilha_pedagio.cache_clear()


def _obter_km_total_por_placa() -> pd.Series:
    """Retorna a série com o total de KM rodado por placa."""
    df = carregar_planilha_combustivel().copy()
    df = _filtrar_por_ano(df, ["Data", "MÊS"])
    _validar_colunas(df, [COL_PLACA_COMBUSTIVEL, COL_KM_RODADO])
    df["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(df, COL_PLACA_COMBUSTIVEL)
    df[COL_KM_RODADO] = pd.to_numeric(df[COL_KM_RODADO], errors="coerce")
    df_filtrado = df.dropna(subset=["PLACA_NORMALIZADA", COL_KM_RODADO])
    df_filtrado = df_filtrado[df_filtrado[COL_KM_RODADO] > 0]
    if df_filtrado.empty:
        return pd.Series(dtype=float)
    return df_filtrado.groupby("PLACA_NORMALIZADA")[COL_KM_RODADO].sum()


def get_lista_placas() -> List[str]:
    """
    Retorna a lista de placas existentes na planilha de combustível,
    ordenada alfabeticamente e sem duplicados.
    """
    df = carregar_planilha_combustivel().copy()
    df = _filtrar_por_ano(df, ["Data", "MÊS"])
    _validar_colunas(df, [COL_PLACA_COMBUSTIVEL])
    placas = _normalizar_coluna_placa(df, COL_PLACA_COMBUSTIVEL).dropna()
    placas = sorted(placas.drop_duplicates())
    return placas


def get_media_km_por_litro_por_placa() -> Dict[str, float]:
    """
    Calcula o consumo médio de combustível (km/l) para cada placa.
    """
    df = carregar_planilha_combustivel().copy()
    df = _filtrar_por_ano(df, ["Data", "MÊS"])
    _validar_colunas(df, [COL_PLACA_COMBUSTIVEL, COL_KM_RODADO, COL_LITROS])
    df["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(df, COL_PLACA_COMBUSTIVEL)
    df[COL_KM_RODADO] = pd.to_numeric(df[COL_KM_RODADO], errors="coerce")
    df[COL_LITROS] = pd.to_numeric(df[COL_LITROS], errors="coerce")
    df_valido = df.dropna(subset=["PLACA_NORMALIZADA", COL_KM_RODADO, COL_LITROS])
    df_valido = df_valido[(df_valido[COL_LITROS] > 0) & (df_valido[COL_KM_RODADO] > 0)]
    if df_valido.empty:
        return {}
    df_valido["km_por_litro"] = df_valido[COL_KM_RODADO] / df_valido[COL_LITROS]
    medias = df_valido.groupby("PLACA_NORMALIZADA")["km_por_litro"].mean()
    return {placa: float(valor) for placa, valor in medias.items()}


def get_custo_combustivel_por_litro_por_placa() -> Dict[str, float]:
    """
    Calcula o custo médio do combustível por litro para cada placa.
    """
    df = carregar_planilha_combustivel().copy()
    df = _filtrar_por_ano(df, ["Data", "MÊS"])
    _validar_colunas(df, [COL_PLACA_COMBUSTIVEL, COL_LITROS, COL_CUSTO])
    df["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(df, COL_PLACA_COMBUSTIVEL)
    df[COL_LITROS] = pd.to_numeric(df[COL_LITROS], errors="coerce")
    df[COL_CUSTO] = pd.to_numeric(df[COL_CUSTO], errors="coerce")
    df_valido = df.dropna(subset=["PLACA_NORMALIZADA", COL_LITROS, COL_CUSTO])
    df_valido = df_valido[(df_valido[COL_LITROS] > 0) & (df_valido[COL_CUSTO] >= 0)]
    if df_valido.empty:
        return {}
    df_valido["custo_por_litro"] = df_valido[COL_CUSTO] / df_valido[COL_LITROS]
    medias = df_valido.groupby("PLACA_NORMALIZADA")["custo_por_litro"].mean()
    return {placa: float(valor) for placa, valor in medias.items()}


def get_custo_combustivel_por_km_por_placa() -> Dict[str, float]:
    """
    Calcula o custo médio do combustível por quilômetro rodado para cada placa.
    """
    df = carregar_planilha_combustivel().copy()
    df = _filtrar_por_ano(df, ["Data", "MÊS"])
    _validar_colunas(df, [COL_PLACA_COMBUSTIVEL, COL_KM_RODADO, COL_CUSTO])
    df["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(df, COL_PLACA_COMBUSTIVEL)
    df[COL_KM_RODADO] = pd.to_numeric(df[COL_KM_RODADO], errors="coerce")
    df[COL_CUSTO] = pd.to_numeric(df[COL_CUSTO], errors="coerce")
    df_valido = df.dropna(subset=["PLACA_NORMALIZADA", COL_KM_RODADO, COL_CUSTO])
    df_valido = df_valido[(df_valido[COL_KM_RODADO] > 0) & (df_valido[COL_CUSTO] >= 0)]
    if df_valido.empty:
        return {}
    df_valido["custo_por_km"] = df_valido[COL_CUSTO] / df_valido[COL_KM_RODADO]
    medias = df_valido.groupby("PLACA_NORMALIZADA")["custo_por_km"].mean()
    return {placa: float(valor) for placa, valor in medias.items()}


def get_custo_manutencao_por_km_por_placa() -> Dict[str, float]:
    """
    Calcula o custo de manutenção por quilômetro rodado para cada placa.
    """
    manutencao = carregar_planilha_manutencao().copy()
    manutencao = _filtrar_por_ano(manutencao, ["MÊS"])
    _validar_colunas(manutencao, [COL_MANUT_PLACA, COL_MANUT_CUSTO])
    manutencao["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(manutencao, COL_MANUT_PLACA)
    manutencao[COL_MANUT_CUSTO] = pd.to_numeric(manutencao[COL_MANUT_CUSTO], errors="coerce")
    manutencao = manutencao.dropna(subset=["PLACA_NORMALIZADA", COL_MANUT_CUSTO])
    manutencao_agrupada = manutencao.groupby("PLACA_NORMALIZADA")[COL_MANUT_CUSTO].sum()

    km_por_placa = _obter_km_total_por_placa()

    placas = sorted(set(manutencao_agrupada.index).union(km_por_placa.index))
    resultado: Dict[str, float] = {}

    for placa in placas:
        custo = float(manutencao_agrupada.get(placa, 0.0))
        km_total = float(km_por_placa.get(placa, 0.0))
        resultado[placa] = custo / km_total if km_total > 0 else 0.0

    return resultado


def get_custo_pedagio_por_km_por_placa() -> Dict[str, float]:
    """
    Calcula o custo de pedágio por quilômetro rodado para cada placa.
    """
    df = carregar_planilha_pedagio().copy()
    df = _filtrar_por_ano(df, ["MÊS"])
    if COL_PEDAGIO_PLACA not in df.columns:
        for alternativa in ("PLACAS", "placas", "Placas"):
            if alternativa in df.columns:
                df = df.rename(columns={alternativa: COL_PEDAGIO_PLACA})
                break
    _validar_colunas(df, [COL_PEDAGIO_PLACA, COL_PEDAGIO_TIPO, COL_PEDAGIO_CUSTO])
    df["TIPO_NORMALIZADO"] = df[COL_PEDAGIO_TIPO].apply(_normalizar_texto)
    df = df[df["TIPO_NORMALIZADO"] == "PEDAGIO"]
    if df.empty:
        return {}
    df["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(df, COL_PEDAGIO_PLACA)
    df[COL_PEDAGIO_CUSTO] = pd.to_numeric(df[COL_PEDAGIO_CUSTO], errors="coerce")
    df = df.dropna(subset=["PLACA_NORMALIZADA", COL_PEDAGIO_CUSTO])
    df = df[df[COL_PEDAGIO_CUSTO] >= 0]
    if df.empty:
        return {}

    pedagio_por_placa = df.groupby("PLACA_NORMALIZADA")[COL_PEDAGIO_CUSTO].sum()
    km_por_placa = _obter_km_total_por_placa()

    resultado: Dict[str, float] = {}
    for placa, custo_total in pedagio_por_placa.items():
        km_total = float(km_por_placa.get(placa, 0.0))
        custo_total = float(custo_total)
        resultado[placa] = custo_total / km_total if km_total > 0 else 0.0

    return resultado


def get_custo_reserva_por_km() -> float:
    """
    Calcula o custo médio de hospedagem distribuído por quilômetro rodado.

    Regra: a cada 500 km é contada 1 diária.
    """
    df = carregar_planilha_reserva().copy()
    df = _filtrar_por_ano(df, ["DATA", "Data"])
    if COL_RESERVA_VALOR not in df.columns:
        raise KeyError("A planilha de reservas não possui a coluna 'VALOR'.")

    df[COL_RESERVA_VALOR] = _normalizar_coluna_monetaria(df[COL_RESERVA_VALOR])
    df = df.dropna(subset=[COL_RESERVA_VALOR])
    if df.empty:
        return 0.0

    total_valor = float(df[COL_RESERVA_VALOR].sum())
    custo_diaria_medio = total_valor / len(df)
    custo_por_km = custo_diaria_medio / 500.0
    return float(custo_por_km)


def get_custo_hora_colaborador() -> float:
    """
    Calcula o custo médio por hora de um colaborador.
    """
    df = carregar_planilha_funcionarios().copy()
    df = _filtrar_por_ano(df, ["MÊS"])
    _validar_colunas(df, [COL_FUNC_MES, COL_FUNC_VALOR, COL_FUNC_COLABORADORES])
    df[COL_FUNC_VALOR] = pd.to_numeric(df[COL_FUNC_VALOR], errors="coerce")
    df[COL_FUNC_COLABORADORES] = pd.to_numeric(df[COL_FUNC_COLABORADORES], errors="coerce")
    df = df.dropna(subset=[COL_FUNC_VALOR, COL_FUNC_COLABORADORES])
    df = df[df[COL_FUNC_COLABORADORES] > 0]
    if df.empty:
        return 0.0
    df["custo_por_colaborador"] = df[COL_FUNC_VALOR] / df[COL_FUNC_COLABORADORES]
    custo_medio_mensal = df["custo_por_colaborador"].mean()
    return float(custo_medio_mensal / HORAS_TRABALHADAS_POR_MES) if custo_medio_mensal else 0.0


def get_custo_colaborador_por_km() -> float:
    """
    Calcula o custo de mão de obra por quilômetro rodado (por colaborador).
    Assume que a cada 517 km são necessários 2 dias de trabalho.
    """
    custo_hora = get_custo_hora_colaborador()
    if not custo_hora:
        return 0.0
    horas_por_dia = HORAS_TRABALHADAS_POR_MES / DIAS_TRABALHO_POR_MES
    horas_por_km = (horas_por_dia * 2) / KM_POR_DOIS_DIAS_VIAGEM
    return float(custo_hora * horas_por_km)


def get_diagnostico_placa(placa: str) -> Dict[str, float | int]:
    """
    Retorna um resumo bruto da placa nas planilhas para apoiar mensagens de diagnÃ³stico.
    """
    placa_normalizada = _normalizar_texto(placa)
    placa_normalizada = "".join(ch for ch in placa_normalizada if ch.isalnum())

    diagnostico: Dict[str, float | int] = {
        "combustivel_lancamentos": 0,
        "combustivel_custo_total": 0.0,
        "combustivel_km_total": 0.0,
        "combustivel_linhas_com_km": 0,
        "manutencao_lancamentos": 0,
        "manutencao_custo_total": 0.0,
        "pedagio_lancamentos": 0,
        "pedagio_custo_total": 0.0,
    }

    combustivel = carregar_planilha_combustivel().copy()
    combustivel = _filtrar_por_ano(combustivel, ["Data", "MÃŠS"])
    _validar_colunas(combustivel, [COL_PLACA_COMBUSTIVEL, COL_CUSTO])
    combustivel["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(combustivel, COL_PLACA_COMBUSTIVEL)
    combustivel[COL_CUSTO] = pd.to_numeric(combustivel[COL_CUSTO], errors="coerce")
    combustivel[COL_KM_RODADO] = pd.to_numeric(combustivel.get(COL_KM_RODADO), errors="coerce")
    combustivel_placa = combustivel[combustivel["PLACA_NORMALIZADA"] == placa_normalizada].copy()
    if not combustivel_placa.empty:
        diagnostico["combustivel_lancamentos"] = int(len(combustivel_placa))
        diagnostico["combustivel_custo_total"] = float(combustivel_placa[COL_CUSTO].fillna(0).sum())
        km_validos = combustivel_placa[COL_KM_RODADO].dropna()
        diagnostico["combustivel_linhas_com_km"] = int((km_validos > 0).sum())
        diagnostico["combustivel_km_total"] = float(km_validos[km_validos > 0].sum()) if not km_validos.empty else 0.0

    manutencao = carregar_planilha_manutencao().copy()
    manutencao = _filtrar_por_ano(manutencao, ["MÃŠS"])
    _validar_colunas(manutencao, [COL_MANUT_PLACA, COL_MANUT_CUSTO])
    manutencao["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(manutencao, COL_MANUT_PLACA)
    manutencao[COL_MANUT_CUSTO] = pd.to_numeric(manutencao[COL_MANUT_CUSTO], errors="coerce")
    manutencao_placa = manutencao[manutencao["PLACA_NORMALIZADA"] == placa_normalizada].copy()
    if not manutencao_placa.empty:
        diagnostico["manutencao_lancamentos"] = int(len(manutencao_placa))
        diagnostico["manutencao_custo_total"] = float(manutencao_placa[COL_MANUT_CUSTO].fillna(0).sum())

    pedagio = carregar_planilha_pedagio().copy()
    pedagio = _filtrar_por_ano(pedagio, ["MÃŠS"])
    if COL_PEDAGIO_PLACA not in pedagio.columns:
        for alternativa in ("PLACAS", "placas", "Placas"):
            if alternativa in pedagio.columns:
                pedagio = pedagio.rename(columns={alternativa: COL_PEDAGIO_PLACA})
                break
    _validar_colunas(pedagio, [COL_PEDAGIO_PLACA, COL_PEDAGIO_TIPO, COL_PEDAGIO_CUSTO])
    pedagio["PLACA_NORMALIZADA"] = _normalizar_coluna_placa(pedagio, COL_PEDAGIO_PLACA)
    pedagio["TIPO_NORMALIZADO"] = pedagio[COL_PEDAGIO_TIPO].apply(_normalizar_texto)
    pedagio[COL_PEDAGIO_CUSTO] = pd.to_numeric(pedagio[COL_PEDAGIO_CUSTO], errors="coerce")
    pedagio_placa = pedagio[
        (pedagio["PLACA_NORMALIZADA"] == placa_normalizada) & (pedagio["TIPO_NORMALIZADO"] == "PEDAGIO")
    ].copy()
    if not pedagio_placa.empty:
        diagnostico["pedagio_lancamentos"] = int(len(pedagio_placa))
        diagnostico["pedagio_custo_total"] = float(pedagio_placa[COL_PEDAGIO_CUSTO].fillna(0).sum())

    return diagnostico


def carregar_todos_os_dados() -> Dict[str, object]:
    """
    Carrega todas as planilhas e calcula os principais dicionários e métricas.
    """
    media_km_por_litro = get_media_km_por_litro_por_placa()
    custo_combustivel_por_km = get_custo_combustivel_por_km_por_placa()
    custo_manutencao_por_km = get_custo_manutencao_por_km_por_placa()
    custo_pedagio_por_km = get_custo_pedagio_por_km_por_placa()
    custo_reserva_por_km = get_custo_reserva_por_km()
    custo_hora_colaborador = get_custo_hora_colaborador()
    custo_colaborador_por_km = get_custo_colaborador_por_km()

    return {
        "media_km_por_litro_por_placa": media_km_por_litro,
        "custo_combustivel_por_km_por_placa": custo_combustivel_por_km,
        "custo_manutencao_por_km_por_placa": custo_manutencao_por_km,
        "custo_pedagio_por_km_por_placa": custo_pedagio_por_km,
        "custo_hora_colaborador": custo_hora_colaborador,
        "custo_reserva_por_km": custo_reserva_por_km,
        "custo_colaborador_por_km": custo_colaborador_por_km,
    }
