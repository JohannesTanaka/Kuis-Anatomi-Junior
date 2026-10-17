import csv
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

BASE = Path(__file__).parent
IMAGE_PATH = BASE / "gambar_tengkorak.png"
LOCAL_SERVICE_ACCOUNT = BASE / "service_account.json"
DEFAULT_SPREADSHEET_ID = "1Db6qV4YxJwIl3eTF43y4t30gyrsKHMGSQlvfWrNQfIQ"
RESULTS_PATH = BASE / "hasil_kuis_lokal.csv"

st.set_page_config(page_title="Kuis Anatomi Radiologi", page_icon="🩻", layout="wide")

st.markdown("""
<style>
.st-key-image_panel {
    position: sticky;
    top: 1rem;
    max-height: calc(100vh - 2rem);
    overflow-y: auto;
    padding: 0.4rem;
    background: var(--background-color);
    border-radius: 0.5rem;
}
.st-key-image_panel img {
    width: 100%;
    max-height: calc(100vh - 8rem);
    object-fit: contain;
}
div[data-testid="stTextInput"] input { min-height: 2.2rem; }
@media (max-width: 900px) {
    .st-key-image_panel {
        position: static;
        max-height: none;
        overflow: visible;
    }
    .st-key-image_panel img { max-height: 60vh; }
}
</style>
""", unsafe_allow_html=True)


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii").lower().strip()
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def get_credentials_and_sheet_id():
    credentials_info = None
    spreadsheet_id = DEFAULT_SPREADSHEET_ID
    try:
        if "gcp_service_account" in st.secrets:
            credentials_info = dict(st.secrets["gcp_service_account"])
            spreadsheet_id = str(
                st.secrets.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)
            ).strip()
    except Exception:
        pass

    if credentials_info is None and LOCAL_SERVICE_ACCOUNT.exists():
        with open(LOCAL_SERVICE_ACCOUNT, "r", encoding="utf-8") as file:
            credentials_info = json.load(file)
    return credentials_info, spreadsheet_id


@st.cache_data(ttl=60, show_spinner=False)
def read_google_sheet_rows():
    credentials_info, spreadsheet_id = get_credentials_and_sheet_id()
    if not credentials_info:
        raise RuntimeError(
            "Kredensial Google Sheets belum tersedia. Di Streamlit Cloud, isi "
            "Settings → Secrets. Untuk lokal, gunakan service_account.json. "
            "Jangan unggah file JSON kredensial ke GitHub."
        )

    import gspread
    from google.oauth2.service_account import Credentials

    scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
    credentials = Credentials.from_service_account_info(
        credentials_info, scopes=scopes
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.sheet1.get_all_records()


def load_keys():
    try:
        rows = read_google_sheet_rows()
    except Exception as exc:
        return {}, (
            "Gagal membaca Google Sheets. Periksa Secrets, ID spreadsheet, izin "
            "Viewer untuk service account, Google Sheets API, dan header kolom. "
            f"Detail error: {exc}"
        )

    keys = {}
    active_values = {"true", "1", "yes", "ya"}
    for row in rows:
        qid = str(row.get("id", "")).strip()
        active = str(row.get("aktif", "true")).strip().lower()
        correct = str(row.get("jawaban_benar", "")).strip()
        if not qid or active not in active_values or not correct:
            continue

        raw_alternatives = str(row.get("alternatif_jawaban", "") or "")
        alternatives = [
            item.strip()
            for item in re.split(r"[|;\n]+", raw_alternatives)
            if item.strip()
        ]
        try:
            points = max(1, int(float(row.get("poin") or 1)))
        except (ValueError, TypeError):
            points = 1

        keys[qid] = {
            "pertanyaan": str(row.get("pertanyaan", "")).strip(),
            "jawaban_benar": correct,
            "alternatif": alternatives,
            "poin": points,
        }

    if not keys:
        return {}, (
            "Tidak ada kunci jawaban aktif. Pastikan kolom aktif berisi TRUE "
            "dan jawaban_benar tidak kosong untuk soal yang ingin dinilai."
        )
    return keys, None


def answer_matches(response, item):
    accepted = [item["jawaban_benar"]] + item["alternatif"]
    return normalize(response) in {
        normalize(value) for value in accepted if normalize(value)
    }


def save_result(result):
    file_exists = RESULTS_PATH.exists()
    with open(RESULTS_PATH, "a", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(result.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(result)


# Judul besar dan pengantar di bagian atas dihilangkan sesuai permintaan.
keys, load_error = load_keys()
if load_error:
    st.error(load_error)
    st.stop()

if not IMAGE_PATH.exists():
    st.error(
        "File gambar_tengkorak.png tidak ditemukan. Unggah file tersebut ke "
        "repositori yang sama dengan app.py."
    )
    st.stop()

exam_key = keys.get("jenis_pemeriksaan")
anatomy_keys = {n: keys.get(f"anatomi_{n:02d}") for n in range(1, 26)}

if "started" not in st.session_state:
    st.session_state.started = False
if "submitted" not in st.session_state:
    st.session_state.submitted = False

if not st.session_state.started:
    name = st.text_input("Nama peserta")
    st.image(
        Image.open(IMAGE_PATH),
        caption="Radiografi tengkorak dengan penanda nomor 1–25",
        width=560,
    )
    if st.button("Mulai menjawab", type="primary"):
        if not name.strip():
            st.error("Masukkan nama peserta terlebih dahulu.")
        else:
            st.session_state.participant = name.strip()
            st.session_state.started = True
            st.rerun()

elif not st.session_state.submitted:
    image_col, form_col = st.columns([1.0, 1.25], gap="large")
    with image_col:
        with st.container(key="image_panel"):
            st.image(
                Image.open(IMAGE_PATH),
                caption="Gambar referensi • Nomor 1–25",
                use_container_width=True,
            )

    with form_col:
        st.caption(f"Peserta: {st.session_state.participant}")
        with st.form("quiz_answers"):
            if exam_key:
                st.markdown("### A. Jenis pemeriksaan")
                st.text_input(
                    "Apa jenis pemeriksaan pada gambar ini?",
                    key="answer_exam",
                    placeholder="Ketik jenis pemeriksaan...",
                )

            active_anatomy = [
                n for n in range(1, 26) if anatomy_keys.get(n) is not None
            ]
            if active_anatomy:
                st.markdown("### B. Struktur anatomi")
                for n in active_anatomy:
                    item = anatomy_keys[n]
                    prompt = item["pertanyaan"] or (
                        f"Identifikasi struktur anatomi nomor {n}."
                    )
                    st.text_input(
                        prompt,
                        key=f"answer_{n:02d}",
                        placeholder=f"Jawaban nomor {n}...",
                    )

            confirm = st.checkbox("Saya sudah memeriksa jawaban saya.")
            send = st.form_submit_button(
                "Kirim jawaban dan lihat nilai",
                type="primary",
                use_container_width=True,
            )

    if send:
        if not confirm:
            st.error("Centang konfirmasi sebelum mengirim jawaban.")
        else:
            details = []
            total_points = 0
            earned_points = 0
            correct_count = 0

            if exam_key:
                response = st.session_state.get("answer_exam", "").strip()
                points = exam_key["poin"]
                correct = answer_matches(response, exam_key)
                total_points += points
                earned_points += points if correct else 0
                correct_count += int(correct)
                details.append({
                    "nomor": "Jenis pemeriksaan",
                    "jawaban_peserta": response,
                    "jawaban_benar": exam_key["jawaban_benar"],
                    "benar": correct,
                    "poin": points if correct else 0,
                })

            for n in range(1, 26):
                item = anatomy_keys.get(n)
                if not item:
                    continue
                response = st.session_state.get(f"answer_{n:02d}", "").strip()
                points = item["poin"]
                correct = answer_matches(response, item)
                total_points += points
                earned_points += points if correct else 0
                correct_count += int(correct)
                details.append({
                    "nomor": n,
                    "jawaban_peserta": response,
                    "jawaban_benar": item["jawaban_benar"],
                    "benar": correct,
                    "poin": points if correct else 0,
                })

            if total_points == 0:
                st.error("Tidak ada soal aktif yang dapat dinilai.")
            else:
                score = round(earned_points / total_points * 100, 2)
                result = {
                    "waktu": datetime.now().isoformat(timespec="seconds"),
                    "nama_peserta": st.session_state.participant,
                    "jumlah_soal_dinilai": len(details),
                    "jawaban_benar": correct_count,
                    "nilai_persen": score,
                    "detail": " | ".join(
                        f"{item['nomor']}={item['jawaban_peserta']}"
                        for item in details
                    ),
                }
                try:
                    save_result(result)
                except Exception:
                    pass
                st.session_state.result = result
                st.session_state.detail = details
                st.session_state.submitted = True
                st.rerun()

else:
    result = st.session_state.result
    details = st.session_state.detail
    st.subheader("Hasil kuis")
    col1, col2, col3 = st.columns(3)
    col1.metric("Nilai", f"{result['nilai_persen']:.2f}%")
    col2.metric(
        "Jawaban benar",
        f"{result['jawaban_benar']} / {result['jumlah_soal_dinilai']}",
    )
    col3.metric("Peserta", result["nama_peserta"])
    st.caption(
        "Penyimpanan CSV di hosting bersifat lokal dan belum menjadi penyimpanan "
        "bersama lintas peserta."
    )
    st.markdown("## Pembahasan")
    for item in details:
        status = "Benar" if item["benar"] else "Perlu diperbaiki"
        with st.expander(f"{item['nomor']} — {status}"):
            st.write("Jawaban Anda:", item["jawaban_peserta"] or "(kosong)")
            st.write("Kunci jawaban:", item["jawaban_benar"])

    if st.button("Kembali ke awal / peserta berikutnya", type="primary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.cache_data.clear()
        st.rerun()

st.divider()
st.caption("Pastikan kunci jawaban telah diverifikasi sebelum kuis digunakan.")
