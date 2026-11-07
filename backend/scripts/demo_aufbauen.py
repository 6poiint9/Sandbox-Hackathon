"""Baut einen Demo-Verein komplett über die API auf (Backend muss laufen).

    .venv\\Scripts\\python.exe scripts\\demo_aufbauen.py https://fcemmendingen.de Emmendingen --recherche 3

Schritte: Website-Analyse -> Verein -> erkannte Sponsoren -> Inventar ->
Kandidaten im Umkreis -> Recherche der besten N (wartet, bis fertig).
"""

import argparse
import sys
import time

import httpx

FREI_STANDARD = [
    "bande", "social_media", "vereinsfest", "turnier", "azubi",
    "trainingsanzug", "website", "spieltag", "businessclub", "trikot_jugend",
]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("website")
    p.add_argument("ort")
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--radius", type=float, default=10)
    p.add_argument("--zuschauer", type=int, default=150)
    p.add_argument("--recherche", type=int, default=3)
    a = p.parse_args()
    c = httpx.Client(base_url=a.api, timeout=600)

    t = time.time()
    v = c.post("/onboarding/analyse", json={"website": a.website, "ort": a.ort}).raise_for_status().json()
    print(f"Analyse: {v['name']} | {len(v['mannschaften'])} Mannschaften | {len(v['sponsoren'])} Sponsoren ({time.time()-t:.0f}s)")

    felder = ["name", "website", "ort", "sportarten", "mannschaften", "spielklasse", "mitglieder", "veranstaltungen"]
    verein = c.post(
        "/vereine",
        json={k: v[k] for k in felder} | {"radius_km": a.radius, "zuschauer_schnitt": a.zuschauer},
    ).raise_for_status().json()
    vid = verein["id"]
    c.post(
        f"/vereine/{vid}/sponsoren",
        json=[{k: s[k] for k in ("firma", "website", "gegenleistung", "gegenleistung_text")} for s in v["sponsoren"]],
    ).raise_for_status()
    vergeben = set(v["inventar_vergeben"])
    inventar = [{"katalog_id": k} for k in FREI_STANDARD if k not in vergeben]
    inventar += [{"katalog_id": k, "verfuegbar": False} for k in vergeben]
    c.put(f"/vereine/{vid}/inventar", json=inventar).raise_for_status()

    t = time.time()
    k = c.post(f"/vereine/{vid}/kandidaten?anzahl=30").raise_for_status().json()
    print(f"Kandidaten: {len(k['kandidaten'])} von {k['betriebe_gesamt']} Betrieben ({time.time()-t:.0f}s)")
    print("Lücken:", ", ".join(f"{l['branche']} ({l['betriebe']})" for l in k["luecken"][:6]))

    if a.recherche:
        t = time.time()
        c.post(f"/vereine/{vid}/recherche?anzahl={a.recherche}").raise_for_status()
        while not c.get(f"/vereine/{vid}/recherche/status").json()["fertig"]:
            time.sleep(2)
        print(f"Recherche fertig ({time.time()-t:.0f}s):", c.get(f"/vereine/{vid}/recherche/status").json()["status"])
        for kand in c.get(f"/vereine/{vid}/kandidaten").json():
            if kand["recherche_status"] not in ("fertig", "fehler"):
                continue
            u = kand["unternehmen"]
            print(f"\n{kand['score']} ({kand['sicherheit']}) {u['name']} – {u['branche']}, {kand['entfernung_km']} km")
            if kand["recherche_fehler"]:
                print("  Fehler:", kand["recherche_fehler"])
            print("  ", kand["zusammenfassung"])
            for g in kand["gruende"]:
                print("   •", g["text"], "→", g["quelle_url"])
            pe = kand["paket_empfehlung"]
            print("   Paket:", ", ".join(pe.get("namen", [])), pe.get("preis_eur"), "|", pe.get("begruendung"))
    print(f"\nVerein-ID: {vid}")


if __name__ == "__main__":
    sys.exit(main())
