from __future__ import annotations

import json
import tempfile
from pathlib import Path

from procesar_endeudamiento_bcra import procesar
from verificar_endeudamiento import verificar


def padron_line(tipo_trib: str, ident: str, tipo_personal: str, cpa: str, mov: str = "10") -> str:
    return f"{tipo_trib};{ident};{tipo_personal};12345678;PERSONA TEST;N;{cpa};{mov}"


def deuda_line(
    entidad: int,
    tipo_trib: str,
    ident: str,
    situacion: int,
    prestamos: str,
    garantias: str = "0.0",
    otros: str = "0.0",
    periodo: str = "202606",
) -> str:
    # Diseño oficial deudores.txt: 24 campos.
    row = [
        f"{entidad:05d}", periodo, tipo_trib, ident, "001", str(situacion),
        prestamos, "", garantias, otros,
        "0.0", "0.0", "0.0", "0.0", "0.0", "0.0", "0.0",
        "0", "0", "0", "0", "0", "0", "0",
    ]
    assert len(row) == 24
    return ";".join(row)


def main() -> None:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        padron = root / "20260731PADRON.TXT"
        deuda = root / "202606DEUDORES.TXT"
        territorio = root / "cpa_territorio.csv"

        padron_rows: list[str] = []
        deuda_rows: list[str] = []

        # Barrio publicable: 30 personas. Se prueba que el monto difundido sume
        # préstamos + garantías otorgadas + otros conceptos. Una persona tiene
        # además una segunda entidad y peor situación 3.
        ids_a = [f"20{100000000 + i:09d}" for i in range(30)]
        for ident in ids_a:
            padron_rows.append(padron_line("11", ident, "01", "C1000AAA"))
            deuda_rows.append(deuda_line(1, "11", ident, 1, "80.0", "10.0", "10.0"))
        deuda_rows.append(deuda_line(2, "11", ids_a[0], 3, "25.0", "15.0", "10.0"))

        # Barrio con 29 deudores: debe procesarse pero suprimirse del JSON público.
        ids_b = [f"23{200000000 + i:09d}" for i in range(29)]
        for ident in ids_b:
            padron_rows.append(padron_line("11", ident, "01", "C2000BBB"))
            deuda_rows.append(deuda_line(1, "11", ident, 4, "200.0"))

        # Persona humana CABA cuyo CPA aún no tiene cruce territorial.
        ident_unmapped = "27300000001"
        padron_rows.append(padron_line("11", ident_unmapped, "01", "C3000CCC"))
        deuda_rows.append(deuda_line(1, "11", ident_unmapped, 2, "300.0"))

        # Persona jurídica: tipo personal 00, debe excluirse aun con CPA CABA.
        pj = "30500000001"
        padron_rows.append(padron_line("11", pj, "00", "C1000AAA"))
        deuda_rows.append(deuda_line(1, "11", pj, 5, "999.0"))

        # Persona humana fuera de CABA: debe excluirse.
        fuera = "27600000001"
        padron_rows.append(padron_line("11", fuera, "01", "B1900AAA"))
        deuda_rows.append(deuda_line(1, "11", fuera, 5, "999.0"))

        padron.write_text("\n".join(padron_rows) + "\n", encoding="cp1252")
        deuda.write_text("\n".join(deuda_rows) + "\n", encoding="cp1252")
        territorio.write_text(
            "cpa,barrio,comuna\n"
            "C1000AAA,Barrio Publicable,1\n"
            "C2000BBB,Barrio Suprimido,2\n",
            encoding="utf-8",
        )

        data = procesar(deuda, padron, territorio)
        verificar(data)

        assert data["periodo"] == "2026-06"
        assert data["fuente"]["archivo_deuda"] == "202606DEUDORES.TXT"
        assert data["caba"]["deudores"] == 60
        assert data["caba"]["deudores_en_mora"] == 30  # 1 en sit.3 + 29 en sit.4
        assert data["caba"]["deuda_pesos"] == 9_150_000
        assert data["caba"]["deuda_en_mora_pesos"] == 5_850_000
        assert data["caba"]["deudores_por_situacion_maxima"] == {
            "1": 29, "2": 1, "3": 1, "4": 29, "5": 0
        }

        cov = data["cobertura_procesamiento"]
        assert cov["registros_deudores_leidos"] == len(deuda_rows)
        assert cov["personas_con_barrio_asignado"] == 59
        assert cov["celdas_barrio_suprimidas"] == 1
        assert cov["personas_en_celdas_suprimidas"] == 29
        assert len(data["barrios"]) == 1
        assert data["barrios"][0]["barrio"] == "Barrio Publicable"
        assert data["barrios"][0]["deudores"] == 30
        assert data["barrios"][0]["deudores_en_mora"] == 1

        rendered = json.dumps(data, ensure_ascii=False)
        for ident in [*ids_a, *ids_b, ident_unmapped, pj, fuera]:
            assert ident not in rendered
        assert "C1000AAA" not in rendered
        assert "C2000BBB" not in rendered
        assert "Barrio Suprimido" not in rendered

        out = root / "endeudamiento_caba.json"
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            "✔ fixture mensual sintético · 60 PH CABA · 30 en mora · "
            "1 barrio publicado · 1 celda suprimida · identificadores ausentes"
        )


if __name__ == "__main__":
    main()
