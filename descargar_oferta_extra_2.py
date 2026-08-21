"""Descarga la segunda ampliación de fuentes oficiales para Oferta territorial."""
from __future__ import annotations

import os
import time
from pathlib import Path

import descargar_territorio as D
import oferta_extra_2_fix  # aplica correcciones verificadas y suma capas oficiales
from oferta_extra_2 import EXTRA_DATASETS

BASE = Path(__file__).resolve().parent
DIR = BASE / "badata"
DIR.mkdir(exist_ok=True)


def main() -> int:
    state = D.load_state()
    state.setdefault("datasets", {})
    ok, kept, failed = [], [], []
    for key, cfg in EXTRA_DATASETS.items():
        dst = DIR / cfg["filename"]
        existed = dst.exists()
        print(f"… {key:22} {cfg['dataset']}")
        try:
            pkg = D.package_show(cfg["dataset"])
            res = D.choose_resource(pkg, cfg["resource_pattern"], cfg["format"])
            url = res.get("url")
            if not url:
                raise RuntimeError("recurso sin URL")
            r = D.get(url)
            tmp = dst.with_name(f"{dst.stem}.nuevo{dst.suffix}")
            tmp.write_bytes(r.content)
            try:
                D.validate(tmp, cfg["format"])
            except Exception:
                tmp.unlink(missing_ok=True)
                raise
            os.replace(tmp, dst)
            state["datasets"][key] = {
                "dataset": cfg["dataset"],
                "resource_id": res.get("id"),
                "resource_name": res.get("name"),
                "resource_url": url,
                "source_last_modified": res.get("last_modified") or pkg.get("metadata_modified"),
                "downloaded_at": int(time.time()),
                "bytes": dst.stat().st_size,
            }
            ok.append(key)
            print(f"  ✔ {dst.name} · {dst.stat().st_size//1024} KB")
        except Exception as e:
            if existed:
                kept.append(key)
                print(f"  ~ se conserva copia anterior ({type(e).__name__}: {e})")
            else:
                failed.append(key)
                print(f"  ✘ sin copia local ({type(e).__name__}: {e})")
    state["updated_at"] = int(time.time())
    D.save_state(state)
    print(f"\nSegunda ampliación: descargados {len(ok)} · conservados {len(kept)} · sin copia {len(failed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
