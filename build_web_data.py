from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json

import frete_calculo
import frete_dados


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "web-data.js"
PLATES_FILE = ROOT / "placas_permitidas.txt"


def load_allowed_plates() -> list[str]:
    if not PLATES_FILE.exists():
        return frete_dados.get_lista_placas()

    plates: list[str] = []
    seen: set[str] = set()
    for line in PLATES_FILE.read_text(encoding="utf-8").splitlines():
        plate = line.strip().replace(" ", "").upper()
        if not plate or plate in seen:
            continue
        plates.append(plate)
        seen.add(plate)
    return plates


def normalize_payload() -> dict[str, object]:
    dados = frete_calculo.get_dados()

    return {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "year_reference": frete_dados.ANO_REFERENCIA,
        "constants": {
            "tempo_descarga_por_tonelada_horas": frete_calculo.TEMPO_DESCARGA_POR_TONELADA_HORAS,
            "velocidade_media_km_por_hora": frete_calculo.VELOCIDADE_MEDIA_KM_POR_HORA,
            "horas_trabalho_por_dia": frete_calculo.HORAS_TRABALHO_POR_DIA,
        },
        "plates": load_allowed_plates(),
        "metrics": {
            key: {plate: float(value) for plate, value in sorted(value_map.items())}
            if isinstance(value_map, dict)
            else float(value_map)
            for key, value_map in dados.items()
        },
    }


def main() -> None:
    payload = normalize_payload()
    contents = "window.FRETE_WEB_DATA = " + json.dumps(payload, ensure_ascii=True, separators=(",", ":")) + ";\n"
    OUTPUT.write_text(contents, encoding="utf-8")
    print(f"Arquivo gerado: {OUTPUT}")
    print(f"Placas exportadas: {len(payload['plates'])}")


if __name__ == "__main__":
    main()
