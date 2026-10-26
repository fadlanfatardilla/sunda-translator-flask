"""Baseline berbasis kamus: loma -> lemes keur batur.

Jalankan:  python src/baseline.py   (dari folder utama sunda-translator/)
Butuh:     pip install pandas sacrebleu
File:      data/dataset_sunda_loma_lemes_v2.csv, data/kamus_sunda_loma_lemes_v1.csv, data/kamus_sunda_loma_lemes_v2.csv
Output:    results/hasil_baseline.csv, results/predictions_baseline.csv
"""
import re
from pathlib import Path

import pandas as pd
from sacrebleu.metrics import BLEU, CHRF

ROOT = Path(__file__).resolve().parent.parent  # folder sunda-translator/
RESULTS = ROOT / "results"
DATA = ROOT / "data" / "dataset_sunda_loma_lemes_v2.csv"
KAMUS_V1 = ROOT / "data" / "kamus_sunda_loma_lemes_v1.csv"  # dari 100 baris awal (dibekukan)
KAMUS_V2 = ROOT / "data" / "kamus_sunda_loma_lemes_v2.csv"  # v1 + kata dari baris train 101-300
SAPAAN = {"bapa", "ibu", "akang", "teteh", "aki", "nini", "guru", "lurah", "mamang", "bibi"}

TOKEN = re.compile(r"[\wéèÉ'-]+|[^\w\s]", re.UNICODE)


def load_lexicon(path):
    k = pd.read_csv(path)
    # lemes_batur bisa berisi beberapa pilihan "a / b" -> ambil yang pertama
    first = lambda s: s.split("/")[0].strip()
    batur = {r.loma.lower(): first(r.lemes_batur) for r in k.itertuples()}
    sorangan = {r.loma.lower(): first(r.lemes_sorangan) for r in k.itertuples()}
    return batur, sorangan


def match_case(src, tgt):
    return tgt.capitalize() if src[:1].isupper() else tgt


def translate(sentence, batur, sorangan):
    """Substitusi kata per kata.
    Aturan tambahan:
    1. Klausa (dipisah koma) yang memuat 'kuring' memakai kolom lemes_sorangan.
    2. 'keur' + sapaan (mis. 'keur Ibu') berarti 'untuk' -> 'kanggo'.
    """
    out_clauses = []
    for clause in sentence.split(","):
        tokens = TOKEN.findall(clause)
        use_self = any(t.lower() == "kuring" for t in tokens)
        lex = sorangan if use_self else batur
        res = []
        for i, t in enumerate(tokens):
            low = t.lower()
            nxt = tokens[i + 1].lower() if i + 1 < len(tokens) else ""
            if low == "keur" and nxt in SAPAAN:
                new = "kanggo"
            else:
                new = lex.get(low, t)
            res.append(match_case(t, new))
        text = ""
        for t in res:
            text += t if (not text or re.fullmatch(r"[^\w\s]", t)) else " " + t
        out_clauses.append(text.strip())
    return ", ".join(out_clauses)


def score(refs, hyps):
    chrf = CHRF(word_order=2)  # chrF++
    bleu = BLEU()
    return {
        "chrF++": round(chrf.corpus_score(hyps, [refs]).score, 2),
        "BLEU": round(bleu.corpus_score(hyps, [refs]).score, 2),
        "exact_match_%": round(100 * sum(h == r for h, r in zip(hyps, refs)) / len(refs), 1),
    }


if __name__ == "__main__":
    RESULTS.mkdir(exist_ok=True)
    df = pd.read_csv(DATA)
    df["pred_salin"] = df.sumber_loma
    for nama, path in [("kamus_v1", KAMUS_V1), ("kamus_v2", KAMUS_V2)]:
        b, so = load_lexicon(path)
        df["pred_" + nama] = [translate(x, b, so) for x in df.sumber_loma]

    # id > 100 = kalimat baru yang TIDAK dipakai menyusun kamus_v1 -> evaluasi paling jujur
    baru = df.id > 100
    sets = {
        "test_baru (id>100)": df[baru & (df.split == "test")],
        "val_baru (id>100)": df[baru & (df.split == "val")],
        "test_semua": df[df.split == "test"],
    }
    rows = []
    for sname, sub in sets.items():
        for sys_name, col in [("salin_sumber", "pred_salin"), ("kamus_v1", "pred_kamus_v1"), ("kamus_v2", "pred_kamus_v2")]:
            rows.append({"set": sname, "sistem": sys_name, "n": len(sub),
                         **score(sub.target_lemes_batur.tolist(), sub[col].tolist())})
    tb = sets["test_baru (id>100)"]
    for col in ["campuran_sorangan", "tipe_kalimat"]:
        for g, sub in tb.groupby(col):
            rows.append({"set": f"test_baru | {col}={g}", "sistem": "kamus_v2", "n": len(sub),
                         **score(sub.target_lemes_batur.tolist(), sub.pred_kamus_v2.tolist())})
    res = pd.DataFrame(rows)
    print(res.to_string(index=False))
    res.to_csv(RESULTS / "hasil_baseline.csv", index=False)
    df[["id", "split", "sumber_loma", "target_lemes_batur", "pred_kamus_v1", "pred_kamus_v2"]].to_csv(
        RESULTS / "predictions_baseline.csv", index=False)

    print("\nKesalahan kamus_v2 pada test_baru:")
    err = tb[tb.pred_kamus_v2 != tb.target_lemes_batur]
    print(f"{len(err)} dari {len(tb)} kalimat salah\n")
    for r in err.itertuples():
        print(f"[{r.id}] SRC : {r.sumber_loma}\n      REF : {r.target_lemes_batur}\n      PRED: {r.pred_kamus_v2}")
