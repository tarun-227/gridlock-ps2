"""Step 2 — Extract structured features from the free-text `description` column.

Uses a LOCAL Ollama model (qwen2.5:3b, multilingual: ~13% of notes are Kannada, ~87%
English/Kanglish) via Ollama's native REST API. This processes data already in the
dataset (the officer's note recorded at report time) — no external data is introduced.

Output per description:
  severity_score        : 1 (trivial) .. 5 (severe / road-blocking)
  blocking_lanes        : bool — does the note imply lane(s) blocked / road blocked
  vehicles_involved     : int  — number of vehicles mentioned (0 if none)
  requires_tow          : bool — does it imply a tow / crane / recovery is needed
  incident_subtype      : one of config.LLM_SUBTYPES

Results are cached by SHA1(description) in a JSON file so this never re-runs and is
resume-safe. Run:  python -m src.llm_extract            (full, cached)
                   python -m src.llm_extract --limit 20  (smoke test)
"""
from __future__ import annotations
import sys
import json
import time
import hashlib
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import pandas as pd

from . import config as C

OLLAMA_CHAT = C.OLLAMA_CHAT_URL

SYSTEM_PROMPT = (
    "You are a Bengaluru traffic-incident analyst. You read a short officer's field "
    "note (English, transliterated Kannada/Kanglish, or Kannada script). Tokens like "
    "[LOCATION], [PERSON], [ORG] are anonymization placeholders — treat them as a "
    "place/person name. Extract structured facts. Respond with ONLY a JSON object."
)

USER_TEMPLATE = """Officer note: "{desc}"

Return a JSON object with exactly these keys:
- "severity_score": integer 1-5 (1=minor/slow movement, 3=notable obstruction, 5=road blocked/severe)
- "blocking_lanes": true/false (does it imply one or more lanes / the road are blocked?)
- "vehicles_involved": integer (count of vehicles mentioned; 0 if none)
- "requires_tow": true/false (does it imply a tow truck/crane/vehicle recovery is needed?)
- "incident_subtype": one of {subtypes}

JSON only, no explanation."""

DEFAULTS = {
    "severity_score": 3,
    "blocking_lanes": False,
    "vehicles_involved": 0,
    "requires_tow": False,
    "incident_subtype": "other",
}


def _hash(desc: str) -> str:
    return hashlib.sha1(desc.strip().encode("utf-8")).hexdigest()


def _coerce(raw: dict) -> dict:
    out = dict(DEFAULTS)
    try:
        s = int(round(float(raw.get("severity_score", 3))))
        out["severity_score"] = min(5, max(1, s))
    except Exception:
        pass
    out["blocking_lanes"] = bool(raw.get("blocking_lanes", False))
    out["requires_tow"] = bool(raw.get("requires_tow", False))
    try:
        v = int(round(float(raw.get("vehicles_involved", 0))))
        out["vehicles_involved"] = min(20, max(0, v))
    except Exception:
        pass
    st = str(raw.get("incident_subtype", "other")).strip().lower()
    out["incident_subtype"] = st if st in C.LLM_SUBTYPES else "other"
    return out


def call_ollama(desc: str, timeout: int = 90) -> dict:
    payload = {
        "model": C.OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(
                desc=desc[:500], subtypes=C.LLM_SUBTYPES)},
        ],
        "format": "json",
        "stream": False,
        "options": {"temperature": 0, "num_predict": 160},
    }
    for attempt in range(2):
        try:
            r = requests.post(OLLAMA_CHAT, json=payload, timeout=timeout)
            r.raise_for_status()
            content = r.json()["message"]["content"]
            return _coerce(json.loads(content))
        except Exception:
            if attempt == 0:
                time.sleep(1.0)
                continue
            return dict(DEFAULTS)  # safe fallback


# --------------------------------------------------------------------------- Groq backend
def provider() -> str:
    return "groq" if C.groq_api_key() else "ollama"


def call_groq(desc: str, timeout: int = 40) -> dict:
    """Single-note extraction via Groq (used for the dashboard live path)."""
    key = C.groq_api_key()
    payload = {
        "model": C.GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": USER_TEMPLATE.format(
                desc=desc[:500], subtypes=C.LLM_SUBTYPES)},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0, "max_tokens": 160,
    }
    for attempt in range(4):
        try:
            r = requests.post(C.GROQ_CHAT_URL, headers={"Authorization": f"Bearer {key}"},
                              json=payload, timeout=timeout)
            if r.status_code == 429:
                time.sleep(min(float(r.headers.get("retry-after", 2)) + 0.5, 30)); continue
            r.raise_for_status()
            return _coerce(json.loads(r.json()["choices"][0]["message"]["content"]))
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return dict(DEFAULTS)


BATCH_SYSTEM = (
    "You are a Bengaluru traffic-incident analyst reading short officer field notes "
    "(English, transliterated Kannada/Kanglish, or Kannada script). [LOCATION]/[PERSON]/[ORG] "
    "are anonymization placeholders. Respond with ONLY a JSON object."
)


def call_groq_batch(descs: list[str], timeout: int = 60) -> list[dict]:
    """Extract a batch of notes in one request (token-efficient under rate limits).

    Falls back to the rule-based extractor for any item if the batch fails or the
    returned array length doesn't match.
    """
    from .text_features import rule_extract
    key = C.groq_api_key()
    numbered = "\n".join(f"{i+1}) {d[:300]}" for i, d in enumerate(descs))
    user = (
        f"Extract structured facts for EACH of the {len(descs)} notes below. Return ONLY a "
        f'JSON object {{"results": [...]}} with exactly {len(descs)} items in the SAME order.\n'
        f"Each item keys: severity_score (int 1-5; 1=minor/slow,5=road blocked), "
        f"blocking_lanes (bool), vehicles_involved (int, 0 if none), requires_tow (bool), "
        f"incident_subtype (one of {C.LLM_SUBTYPES}).\n\nNotes:\n{numbered}"
    )
    payload = {
        "model": C.GROQ_MODEL,
        "messages": [{"role": "system", "content": BATCH_SYSTEM},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0, "max_tokens": 90 * len(descs) + 80,
    }
    for attempt in range(4):
        try:
            r = requests.post(C.GROQ_CHAT_URL, headers={"Authorization": f"Bearer {key}"},
                              json=payload, timeout=timeout)
            if r.status_code == 429:
                time.sleep(min(float(r.headers.get("retry-after", 2)) + 0.5, 30)); continue
            r.raise_for_status()
            arr = json.loads(r.json()["choices"][0]["message"]["content"]).get("results", [])
            if len(arr) == len(descs):
                return [_coerce(x) for x in arr]
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return [rule_extract(d) for d in descs]   # robust fallback


def extract_one(desc: str) -> dict:
    return call_groq(desc) if provider() == "groq" else call_ollama(desc)


def load_cache() -> dict:
    if C.LLM_CACHE.exists():
        try:
            return json.loads(C.LLM_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_cache(cache: dict):
    C.LLM_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def build_cache(limit: int | None = None, batch_size: int = 10, workers: int = 4):
    df = pd.read_parquet(C.CLEAN_PARQUET, columns=["description"])
    descs = (df["description"].dropna().astype(str).map(str.strip))
    descs = sorted(d for d in descs.unique() if d)
    cache = load_cache()
    todo = [d for d in descs if _hash(d) not in cache]
    if limit:
        todo = todo[:limit]
    prov = provider()
    print(f"provider={prov} | unique: {len(descs)} | cached: {len(cache)} | "
          f"to process: {len(todo)}", flush=True)
    if not todo:
        return cache
    t0 = time.time()

    if prov == "groq":
        # batched + concurrent: ~batch_size notes per request, token-efficient under limits
        batches = [todo[i:i + batch_size] for i in range(0, len(todo), batch_size)]
        done = 0
        with ThreadPoolExecutor(max_workers=workers) as ex:
            futs = {ex.submit(call_groq_batch, b): b for b in batches}
            for fut in as_completed(futs):
                b = futs[fut]
                for d, res in zip(b, fut.result()):
                    cache[_hash(d)] = res
                done += len(b)
                if done % (batch_size * 5) < batch_size:
                    save_cache(cache)
                    rate = done / (time.time() - t0)
                    eta = (len(todo) - done) / rate / 60 if rate else 0
                    print(f"  {done}/{len(todo)}  ({rate:.1f}/s, eta {eta:.1f} min)", flush=True)
    else:
        for i, d in enumerate(todo, 1):
            cache[_hash(d)] = call_ollama(d)
            if i % 25 == 0:
                save_cache(cache)
                rate = i / (time.time() - t0)
                print(f"  {i}/{len(todo)}  ({rate:.1f}/s, "
                      f"eta {(len(todo)-i)/rate/60:.1f} min)", flush=True)

    save_cache(cache)
    print(f"done. cache size: {len(cache)}  ({time.time()-t0:.0f}s)", flush=True)
    return cache


def apply_to_df(df: pd.DataFrame) -> pd.DataFrame:
    """Map description features onto each row.

    Prefers the cached LLM result (best quality, incl. Kannada notes). For descriptions
    not yet in the cache, falls back to the instant deterministic rule-based extractor so
    the pipeline always has full coverage regardless of how much of the LLM run finished.
    Reports the source mix via a `_llm_source` attr for transparency.
    """
    from .text_features import rule_extract, DEFAULTS as RULE_DEFAULTS
    cache = load_cache()
    rows, n_llm, n_rule = [], 0, 0
    for desc in df["description"]:
        if pd.isna(desc) or not str(desc).strip():
            rows.append(dict(RULE_DEFAULTS))
            continue
        h = _hash(str(desc).strip())
        if h in cache:
            rows.append(cache[h]); n_llm += 1
        else:
            rows.append(rule_extract(str(desc))); n_rule += 1
    feats = pd.DataFrame(rows, index=df.index)
    feats.attrs["llm_source"] = {"llm": n_llm, "rule": n_rule}
    feats = feats.rename(columns={
        "severity_score": "llm_severity_score",
        "blocking_lanes": "llm_blocking_lanes",
        "vehicles_involved": "llm_vehicles_involved",
        "requires_tow": "llm_requires_tow",
        "incident_subtype": "llm_subtype",
    })
    feats["llm_blocking_lanes"] = feats["llm_blocking_lanes"].astype(int)
    feats["llm_requires_tow"] = feats["llm_requires_tow"].astype(int)
    return feats


# ------------------------------------------------------------------- duration estimation
DURATION_SYSTEM = (
    "You are a Bengaluru traffic incident expert. Estimate incident clearance times. "
    "Respond with ONLY JSON."
)
DURATION_USER = """Estimate clearance time in minutes for each of the {n} Bengaluru traffic notes below.
Guidelines: minor breakdown moved aside=20-60; tow truck needed=60-120; heavy vehicle/crane=120-360;
VIP/procession=60-180; construction/utility=120-480; pothole/waterlogging=120-600; return 0 if note gives no clues.

Notes:
{numbered}

Return ONLY: {{"results": [<int>, ...]}} with exactly {n} integers."""


def call_groq_duration_batch(descs: list[str], timeout: int = 60) -> list[int]:
    """Estimate clearance minutes for a batch of descriptions. Returns 0 for unknown."""
    from .text_features import rule_extract
    key = C.groq_api_key()
    numbered = "\n".join(f"{i+1}) {d[:300]}" for i, d in enumerate(descs))
    user = DURATION_USER.format(n=len(descs), numbered=numbered)
    payload = {
        "model": C.GROQ_MODEL,
        "messages": [{"role": "system", "content": DURATION_SYSTEM},
                     {"role": "user", "content": user}],
        "response_format": {"type": "json_object"},
        "temperature": 0, "max_tokens": 20 * len(descs) + 40,
    }
    for attempt in range(4):
        try:
            r = requests.post(C.GROQ_CHAT_URL, headers={"Authorization": f"Bearer {key}"},
                              json=payload, timeout=timeout)
            if r.status_code == 429:
                time.sleep(min(float(r.headers.get("retry-after", 2)) + 0.5, 30)); continue
            r.raise_for_status()
            arr = json.loads(r.json()["choices"][0]["message"]["content"]).get("results", [])
            if len(arr) == len(descs):
                return [max(0, min(int(round(float(x))), 10080)) for x in arr]
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return [0] * len(descs)


def load_duration_cache() -> dict:
    if C.LLM_DURATION_CACHE.exists():
        try:
            return json.loads(C.LLM_DURATION_CACHE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_duration_cache(cache: dict):
    C.LLM_DURATION_CACHE.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")


def build_duration_cache(limit: int | None = None, batch_size: int = 10, workers: int = 4):
    """Extract duration estimates (separate cache, does not affect feature extraction cache)."""
    df = pd.read_parquet(C.CLEAN_PARQUET, columns=["description"])
    descs = sorted(d for d in df["description"].dropna().astype(str).map(str.strip).unique() if d)
    cache = load_duration_cache()
    todo = [d for d in descs if _hash(d) not in cache]
    if limit:
        todo = todo[:limit]
    print(f"duration cache | unique={len(descs)} cached={len(cache)} todo={len(todo)}", flush=True)
    if not todo:
        return cache
    t0 = time.time()
    batches = [todo[i:i + batch_size] for i in range(0, len(todo), batch_size)]
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(call_groq_duration_batch, b): b for b in batches}
        for fut in as_completed(futs):
            b = futs[fut]
            for d, est in zip(b, fut.result()):
                cache[_hash(d)] = {"estimated_duration_min": est}
            done += len(b)
            if done % (batch_size * 5) < batch_size:
                save_duration_cache(cache)
                rate = done / (time.time() - t0)
                eta = (len(todo) - done) / rate / 60 if rate else 0
                print(f"  {done}/{len(todo)}  ({rate:.1f}/s, eta {eta:.1f} min)", flush=True)
    save_duration_cache(cache)
    print(f"duration done. cache={len(cache)}  ({time.time()-t0:.0f}s)", flush=True)
    return cache


def apply_duration_to_df(df: pd.DataFrame) -> pd.Series:
    """Map LLM duration estimates onto each row (0 = unknown/no-signal description)."""
    cache = load_duration_cache()
    out = []
    for desc in df["description"]:
        if pd.isna(desc) or not str(desc).strip():
            out.append(0)
            continue
        h = _hash(str(desc).strip())
        out.append(cache.get(h, {}).get("estimated_duration_min", 0))
    return pd.Series(out, index=df.index, dtype=float)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="process only N new descriptions")
    ap.add_argument("--duration", action="store_true", help="run duration estimation cache instead")
    args = ap.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    if args.duration:
        build_duration_cache(limit=args.limit)
    else:
        build_cache(limit=args.limit)


if __name__ == "__main__":
    main()
