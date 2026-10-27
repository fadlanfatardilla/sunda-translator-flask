"""Aplikasi Flask: penerjemah Basa Sunda loma -> lemes keur batur.

Jalankan dari folder utama sunda-translator/:
    pip install -r requirements.txt
    python app/app.py
Lalu buka http://127.0.0.1:5000

Model dibaca dari models/best_model (hasil training di Colab).
Lokasi lain bisa diatur lewat variabel lingkungan MODEL_DIR.
"""
import os
from pathlib import Path

import torch
from flask import Flask, jsonify, render_template, request
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, ByT5Tokenizer

ROOT = Path(__file__).resolve().parent.parent
MODEL_DIR = Path(os.environ.get("MODEL_DIR", ROOT / "models" / "best_model"))
MAX_CHARS = 200
MAX_TOKENS = 192

app = Flask(__name__)


def load_model():
    if not (MODEL_DIR / "config.json").exists():
        raise FileNotFoundError(
            f"Model tidak ditemukan di {MODEL_DIR}. Salin folder best_model dari "
            "Google Drive ke sunda-translator/models/best_model."
        )
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_DIR)
    model.eval()
    try:
        tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    except OSError:
        # File tokenizer tidak ikut tersalin. ByT5 bekerja per byte tanpa file kosakata,
        # jadi tokenizer bawaannya identik dengan yang dipakai saat training.
        if model.config.vocab_size != 384:
            raise
        print("Peringatan: file tokenizer tidak ada di", MODEL_DIR, "- memakai ByT5Tokenizer bawaan.")
        tokenizer = ByT5Tokenizer()
    return tokenizer, model


# dimuat sekali saat aplikasi start, bukan di setiap permintaan
print("Memuat model dari", MODEL_DIR, "... (bisa 10-60 detik, tunggu sampai muncul 'Model siap')", flush=True)
tokenizer, model = load_model()
print("Model siap.", flush=True)


def translate(text: str) -> str:
    enc = tokenizer([text], max_length=MAX_TOKENS, truncation=True, return_tensors="pt")
    with torch.no_grad():
        ids = model.generate(**enc, num_beams=4, max_new_tokens=MAX_TOKENS)
    return tokenizer.batch_decode(ids, skip_special_tokens=True)[0].strip()


@app.get("/")
def index():
    return render_template("index.html", max_chars=MAX_CHARS)


@app.post("/translate")
def translate_route():
    payload = request.get_json(silent=True) or {}
    text = " ".join(str(payload.get("text", "")).split())
    if not text:
        return jsonify(error="Tulis kalimat dulu."), 400
    if len(text) > MAX_CHARS:
        return jsonify(error=f"Kalimat terlalu panjang. Maksimal {MAX_CHARS} karakter."), 400
    return jsonify(translation=translate(text))


if __name__ == "__main__":
    print("Buka http://127.0.0.1:5000 di browser. Tekan Ctrl+C untuk berhenti.", flush=True)
    app.run(host="127.0.0.1", port=5000, debug=False)
