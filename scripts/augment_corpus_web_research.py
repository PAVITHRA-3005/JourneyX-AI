#!/usr/bin/env python3
"""
Append team-curated travel documents synthesized from public travel guidance (Nov 2025–2026).

Content is paraphrased for JourneyX KB (indicative only, no live booking/pricing).
Does NOT modify frozen eval_v1.jsonl. Updates manifest document_count and optional retrieval labels.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOCS_PATH = ROOT / "data/documents/documents.jsonl"
MANIFEST = ROOT / "data/manifest.yaml"
LABELS_PATH = ROOT / "data/eval/retrieval_labels_v1.jsonl"

# Paraphrased from public travel guides; figures are illustrative only (fares come from structured data).
RESEARCH_DOCS: list[dict] = [
    {
        "doc_id": "doc_research_jaipur_season_v1",
        "dest_id": "dest_jaipur",
        "doc_type": "faq",
        "title": "When to visit Jaipur (indicative season guide)",
        "body": (
            "Jaipur is most comfortable for sightseeing from October through March, when daytime "
            "temperatures are typically mild and nights can be cool in December–February. "
            "April–June brings strong heat; July–September is monsoon with humidity. "
            "Peak tourism is winter — plan extra time for forts and bazaars. "
            "Indicative only — check weather before travel. [cite:doc_research_jaipur_season_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11 (CNT, Lonely Planet themes)",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_jaipur_amber_v1",
        "dest_id": "dest_jaipur",
        "doc_type": "activity",
        "title": "Amber (Amer) Fort visit planner",
        "body": (
            "Allow roughly half a day for Amber Fort (poi_jaipur_amber): arrive early, see Sheesh Mahal, "
            "Diwan-i-Aam, and courtyards; pair with Jaigarh for ridge views if time permits. "
            "The fort sits about 11 km from central Jaipur — road/autorickshaw travel is common. "
            "Entry fees and elephant rides are policy-sensitive; use structured fee bands, not live rates. "
            "[cite:doc_research_jaipur_amber_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "linked_poi_id": "poi_jaipur_amber",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_jaipur_itinerary_3d_v1",
        "dest_id": "dest_jaipur",
        "doc_type": "itinerary_template",
        "title": "Jaipur 3–4 day heritage loop (template)",
        "body": (
            "Day 1: Amber Fort morning, Jaigarh optional. Day 2: City Palace, Jantar Mantar, Hawa Mahal "
            "facade stops. Day 3: Old City bazaars (Johari, Bapu) and local food walk. "
            "Pace moderately; hydrate. All timings indicative. [cite:doc_research_jaipur_itinerary_3d_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_goa_season_v1",
        "dest_id": "dest_goa",
        "doc_type": "faq",
        "title": "Goa beach season overview",
        "body": (
            "North Goa beaches are busiest November–February with dry, warm weather suited to swimming "
            "and water sports. March–April is a shoulder period with fewer crowds. "
            "Monsoon (June–September) is lush and budget-friendly but many shacks pause operations. "
            "Old Goa heritage (poi_goa_old) is visitable year-round with planning. "
            "[cite:doc_research_goa_season_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_kochi_backwater_v1",
        "dest_id": "dest_kochi",
        "doc_type": "activity",
        "title": "Kochi and backwaters planning note",
        "body": (
            "Fort Kochi heritage zone, Chinese fishing nets, and spice markets pair well with "
            "a separate Alleppey houseboat segment in Kerala itineraries. "
            "November–February is the classic pleasant window for coast and backwaters; "
            "book houseboats early for peak holidays. Indicative planning only — no booking via JourneyX. "
            "[cite:doc_research_kochi_backwater_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11 (Lonely Planet Kerala themes)",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_kerala_wellness_v1",
        "dest_id": "dest_kochi",
        "doc_type": "faq",
        "title": "Kerala monsoon and Ayurveda season (context)",
        "body": (
            "June–September monsoon is traditionally associated with Ayurveda retreats in Kerala; "
            "some travelers prefer winter for general sightseeing. Onam (Aug–Sep) features boat races "
            "and cultural events. Landslide/flood risk can affect hill routes — verify locally. "
            "[cite:doc_research_kerala_wellness_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_manali_adventure_v1",
        "dest_id": "dest_manali",
        "doc_type": "activity",
        "title": "Manali–Solang adventure window",
        "body": (
            "Solang Valley (poi_manali_solang) supports skiing and adventure sports in season; "
            "March–June is popular for mountain stays. Winter road conditions from Delhi require "
            "mode comparison via compare_transport — indicative timings only. "
            "[cite:doc_research_manali_adventure_v1]"
        ),
        "source_attribution": "team_curated_plus_web_themes",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_delhi_qutub_v1",
        "dest_id": "dest_delhi",
        "doc_type": "poi_card",
        "title": "Qutub Minar complex visit notes",
        "body": (
            "Qutub Minar (poi_delhi_qutub) is a common half-day Delhi heritage stop; "
            "pair with Humayun's Tomb or India Gate in multi-day capital itineraries. "
            "Best months align with city_delhi best_months in structured data. "
            "[cite:doc_research_delhi_qutub_v1]"
        ),
        "source_attribution": "team_curated_v1",
        "linked_poi_id": "poi_delhi_qutub",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_agra_taj_v1",
        "dest_id": "dest_agra",
        "doc_type": "activity",
        "title": "Agra Taj day-trip pattern",
        "body": (
            "Many travelers pair Agra (poi_agra_taj) as a day or overnight from Delhi or Jaipur corridors. "
            "Sunrise visits reduce heat and crowds in cooler months (October–March indicative). "
            "Use get_route_info for Delhi–Agra distance; trains common in structured transport table. "
            "[cite:doc_research_agra_taj_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_rishikesh_rafting_v1",
        "dest_id": "dest_rishikesh",
        "doc_type": "activity",
        "title": "Rishikesh rafting and yoga season",
        "body": (
            "White-water rafting on the Ganga is typically seasonal (often paused in peak monsoon). "
            "September–November and spring months are common for outdoor activities and ashram stays. "
            "Spiritual tourism respects local norms — modest dress near ghats. "
            "[cite:doc_research_rishikesh_rafting_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_shimla_hills_v1",
        "dest_id": "dest_shimla",
        "doc_type": "faq",
        "title": "Shimla hill station climate",
        "body": (
            "Shimla summer (April–June) escapes plains heat; winter brings cold and possible snow on routes. "
            "Mall Road walks and colonial-era buildings dominate a relaxed 2–3 day hill plan. "
            "Check road conditions on mountain approaches in monsoon. "
            "[cite:doc_research_shimla_hills_v1]"
        ),
        "source_attribution": "team_curated_v1",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_mumbai_coastal_v1",
        "dest_id": "dest_mumbai",
        "doc_type": "destination_guide",
        "title": "Mumbai coastal urban weekend",
        "body": (
            "Mumbai combines Gateway of India, Marine Drive, and food districts with day trips to "
            "Elephanta or beaches south of the city in dry months. November–February is a common "
            "pleasant window. Premium tier destination in KB — budget tools return indicative bands only. "
            "[cite:doc_research_mumbai_coastal_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_bangalore_hub_v1",
        "dest_id": "dest_bangalore",
        "doc_type": "faq",
        "title": "Bengaluru as weekend hub",
        "body": (
            "Bengaluru (city_bangalore) works as a tech-city base with day trips to Mysore or hill towns; "
            "year-round mild climate but traffic affects intra-city plans. "
            "Hold-out Mysore eval uses separate stub — do not overfit retrieval to hold-outs. "
            "[cite:doc_research_bangalore_hub_v1]"
        ),
        "source_attribution": "team_curated_v1",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_transport_road_diesel_v1",
        "dest_id": "dest_jaipur",
        "doc_type": "transport_guide",
        "title": "Self-drive diesel car context (indicative)",
        "body": (
            "road_diesel appears in transport_option for several corridors (e.g. Delhi–Jaipur). "
            "Compare against train and flight using compare_transport for party_size scaling. "
            "Fuel and toll costs vary — JourneyX never quotes live fuel prices. "
            "[cite:doc_research_transport_road_diesel_v1]"
        ),
        "source_attribution": "team_curated_v1",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_pack_monsoon_v1",
        "dest_id": "dest_goa",
        "doc_type": "faq",
        "title": "Monsoon packing for coastal India",
        "body": (
            "For June–September coastal travel, carry quick-dry clothing, rain cover, and insect repellent. "
            "Indoor heritage and food trails substitute for beach days. "
            "Always confirm local advisories. [cite:doc_research_pack_monsoon_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_family_hills_v1",
        "dest_id": "dest_manali",
        "doc_type": "faq",
        "title": "Family-friendly hill tips",
        "body": (
            "Families often prefer moderate pace (assemble_itinerary pace=relaxed) with shorter POI hops. "
            "Carry layers for children in Manali/Shimla; check altitude comfort. "
            "[cite:doc_research_family_hills_v1]"
        ),
        "source_attribution": "team_curated_v1",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_udaipur_lakes_v1",
        "dest_id": "dest_udaipur",
        "doc_type": "destination_guide",
        "title": "Udaipur lakes and palaces (hold-out enrichment)",
        "body": (
            "Udaipur City of Lakes: Lake Pichola boat views, City Palace, and Sahelion Ki Bari gardens. "
            "October–March is a common pleasant window. Hold-out destination for eval generalization. "
            "[cite:doc_research_udaipur_lakes_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_mysore_palace_v1",
        "dest_id": "dest_mysore",
        "doc_type": "destination_guide",
        "title": "Mysuru palace and Brindavan gardens",
        "body": (
            "Mysuru (Mysore) is known for the Amba Vilas Palace illumination weekends and nearby "
            "Chamundi Hill. Cooler months suit walking tours. Hold-out eval destination. "
            "[cite:doc_research_mysore_palace_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
    {
        "doc_id": "doc_research_varanasi_ghats_v1",
        "dest_id": "dest_varanasi",
        "doc_type": "destination_guide",
        "title": "Varanasi ghats and Ganga aarti context",
        "body": (
            "Varanasi riverfront ghats and evening Ganga aarti are cultural highlights; "
            "respect photography rules and religious customs. October–March often comfortable on the plains. "
            "Hold-out eval destination. [cite:doc_research_varanasi_ghats_v1]"
        ),
        "source_attribution": "web_research_synthesis_2025-11",
        "last_reviewed": "2025-11-15",
    },
]

NEW_RETRIEVAL_LABELS = [
    {
        "eval_id": "retrieval_research_jaipur_season",
        "query": "What months are best for Jaipur sightseeing?",
        "relevant_doc_ids": [
            "doc_research_jaipur_season_v1",
            "doc_dest_jaipur_guide_v1",
        ],
        "corpus_version": "v1",
    },
    {
        "eval_id": "retrieval_research_amber_fort",
        "query": "How long to spend at Amber Fort Jaipur?",
        "relevant_doc_ids": [
            "doc_research_jaipur_amber_v1",
            "doc_poi_jaipur_amber_v1",
        ],
        "corpus_version": "v1",
    },
    {
        "eval_id": "retrieval_research_goa_season",
        "query": "Goa peak beach season months",
        "relevant_doc_ids": ["doc_research_goa_season_v1", "doc_dest_goa_guide_v1"],
        "corpus_version": "v1",
    },
    {
        "eval_id": "retrieval_research_kochi_backwater",
        "query": "Fort Kochi and houseboat planning season",
        "relevant_doc_ids": ["doc_research_kochi_backwater_v1", "doc_dest_kochi_guide_v1"],
        "corpus_version": "v1",
    },
]


def _load_existing_ids() -> set[str]:
    ids: set[str] = set()
    if not DOCS_PATH.is_file():
        return ids
    for line in DOCS_PATH.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ids.add(json.loads(line)["doc_id"])
    return ids


def main() -> int:
    existing = _load_existing_ids()
    to_add = [d for d in RESEARCH_DOCS if d["doc_id"] not in existing]
    if not to_add:
        print("No new research documents to add (already present).")
        return 0

    DOCS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DOCS_PATH.open("a", encoding="utf-8") as f:
        for doc in to_add:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")

    # Optional retrieval labels; does not modify frozen eval_v1.
    label_ids = set()
    if LABELS_PATH.is_file():
        for line in LABELS_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip():
                label_ids.add(json.loads(line)["eval_id"])
    new_labels = [lb for lb in NEW_RETRIEVAL_LABELS if lb["eval_id"] not in label_ids]
    if new_labels:
        with LABELS_PATH.open("a", encoding="utf-8") as f:
            for lb in new_labels:
                f.write(json.dumps(lb, ensure_ascii=False) + "\n")

    manifest = yaml.safe_load(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.is_file() else {}
    total_docs = sum(1 for line in DOCS_PATH.read_text(encoding="utf-8").splitlines() if line.strip())
    manifest["document_count"] = total_docs
    manifest["research_augmented_at"] = datetime.now(timezone.utc).isoformat()
    manifest["research_docs_added"] = len(to_add)
    manifest["retrieval_label_count"] = manifest.get("retrieval_label_count", 0) + len(new_labels)
    MANIFEST.write_text(yaml.dump(manifest, sort_keys=False, allow_unicode=True), encoding="utf-8")

    print(f"Added {len(to_add)} documents; corpus now {total_docs} docs.")
    print(f"Added {len(new_labels)} retrieval labels.")
    print("Next: .venv\\Scripts\\python.exe scripts\\ingest_corpus.py")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "packages"))
    raise SystemExit(main())