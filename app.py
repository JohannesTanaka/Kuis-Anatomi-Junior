import csv
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import streamlit as st
from PIL import Image

BASE = Path(__file__).parent
DEFAULT_SPREADSHEET_ID = "1Db6qV4YxJwIl3eTF43y4t30gyrsKHMGSQlvfWrNQfIQ"
LOCAL_SERVICE_ACCOUNT = BASE / "service_account.json"
RESULTS_PATH = BASE / "hasil_kuis_lokal.csv"

SECTIONS = [
    "Skull", "Neck", "Vertebra", "Shoulder", "Humerus",
    "Elbow", "Forearm", "Hand", "Chest", "Pelvis",
    "Femur", "Genu", "Cruris", "Ankle", "Foot",
]

# Nama file gambar untuk tiap bagian. Untuk Skull, gunakan gambar yang sudah ada.
IMAGE_FILES = {
    "Skull": "gambar_tengkorak.png",
    "Neck": "gambar_neck.png",
    "Vertebra": "gambar_vertebra.png",
    "Shoulder": "gambar_shoulder.png",
    "Humerus": "gambar_humerus.png",
    "Elbow": "gambar_elbow.png",
    "Forearm": "gambar_forearm.png",
    "Hand": "gambar_hand.png",
    "Chest": "gambar_chest.png",
    "Pelvis": "gambar_pelvis.png",
    "Femur": "gambar_femur.png",
    "Genu": "gambar_genu.png",
    "Cruris": "gambar_cruris.png",
    "Ankle": "gambar_ankle.png",
    "Foot": "gambar_foot.png",
}

st.set_page_config(page_title="KUIS ANATOMI JUNIOR", page_icon="🩻", layout="wide")

st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.quiz-title { font-size: 2rem; font-weight: 800; letter-spacing: .02em; margin-bottom: .2rem; }
.quiz-subtitle { color: var(--text-color); opacity: .72; margin-bottom: 1.2rem; }
.section-card { border: 1px solid rgba(128,128,128,.28); border-radius: 12px; padding: 1rem; }
.st-key-image_panel {
    position: fixed !important;
    top: 1rem !important;
    left: max(2rem, calc((100vw - 90rem) / 2)) !important;
    width: 42rem !important;
    max-width: calc(100vw - 4rem) !important;
    max-height: calc(100vh - 2rem) !important;
    overflow-y: auto !important;
    z-index: 10 !important;
}
.st-key-image_panel [data-testid="stImage"] {
    width: auto !important;
    max-width: none !important;
}
.st-key-image_panel [data-testid="stImage"] img {
    display: block !important;
    width: 550px !important;
    max-width: none !important;
    height: auto !important;
    object-fit: contain !important;
}
@media (max-width: 600px) {
    .st-key-image_panel {
        position: static !important;
        width: 100% !important;
        max-width: none !important;
        max-height: none !important;
    }
    .st-key-image_panel [data-testid="stImage"] img {
        width: min(550px, 100%) !important;
        max-width: 100% !important;
    }
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
            spreadsheet_id = str(st.secrets.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)).strip()
    except Exception:
        pass
    if credentials_info is None and LOCAL_SERVICE_ACCOUNT.exists():
        with open(LOCAL_SERVICE_ACCOUNT, "r", encoding="utf-8") as f:
            credentials_info = json.load(f)
    return credentials_info, spreadsheet_id


@st.cache_data(ttl=60, show_spinner=False)
def read_google_sheet_rows():
    credentials_info, spreadsheet_id = get_credentials_and_sheet_id()
    if not credentials_info:
        raise RuntimeError(
            "Kredensial Google Sheets belum tersedia. Isi Settings → Secrets di Streamlit Cloud. "
            "Jangan unggah file JSON kredensial ke GitHub."
        )
    import gspread
    from google.oauth2.service_account import Credentials
    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )
    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
    return spreadsheet.sheet1.get_all_records()


def truthy(value):
    return str(value or "").strip().lower() in {"true", "1", "yes", "ya"}


def load_questions():
    try:
        rows = read_google_sheet_rows()
    except Exception as exc:
        return [], f"Gagal membaca Google Sheets. Periksa Secrets, ID spreadsheet, izin Viewer untuk service account, dan header kolom. Detail: {exc}"

    questions = []
    for row in rows:
        qid = str(row.get("id", "")).strip()
        prompt = str(row.get("pertanyaan", "")).strip()
        correct = str(row.get("jawaban_benar", "")).strip()
        section = str(row.get("bagian", "")).strip()
        if not qid or not correct or not truthy(row.get("aktif", True)):
            continue
        if not section:
            # Backward compatibility: existing questions without "bagian" are treated as Skull.
            section = "Skull"
        alternatives = [
            x.strip() for x in re.split(r"[|;\n]+", str(row.get("alternatif_jawaban", "") or ""))
            if x.strip()
        ]
        try:
            points = max(1, int(float(row.get("poin") or 1)))
        except (ValueError, TypeError):
            points = 1
        questions.append({
            "id": qid,
            "bagian": section,
            "pertanyaan": prompt,
            "jawaban_benar": correct,
            "alternatif": alternatives,
            "poin": points,
        })
    return questions, None


def answer_matches(response, item):
    accepted = [item["jawaban_benar"]] + item["alternatif"]
    return normalize(response) in {normalize(x) for x in accepted if normalize(x)}


def save_result(result):
    exists = RESULTS_PATH.exists()
    with open(RESULTS_PATH, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=list(result.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(result)


def reset_quiz():
    for key in list(st.session_state.keys()):
        if key.startswith("answer_") or key in {
            "quiz_started", "quiz_submitted", "participant_name",
            "participant_nim", "selected_section", "result", "detail",
        }:
            del st.session_state[key]


if "selected_section" not in st.session_state:
    st.session_state.selected_section = None
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False

questions, load_error = load_questions()
if load_error:
    st.error(load_error)
    st.stop()

# Stage 1: choose anatomy section.
if st.session_state.selected_section is None:
    st.markdown('<div class="quiz-title">KUIS ANATOMI JUNIOR</div>', unsafe_allow_html=True)
    st.markdown('<div class="quiz-subtitle">Pilih bagian anatomi yang ingin dikerjakan.</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    for i, section in enumerate(SECTIONS):
        with cols[i % 3]:
            if st.button(section, key=f"section_{section}", use_container_width=True):
                st.session_state.selected_section = section
                st.rerun()
    st.stop()

section = st.session_state.selected_section
section_questions = [q for q in questions if normalize(q["bagian"]) == normalize(section)]
image_path = BASE / IMAGE_FILES.get(section, "")

# Stage 2: identity before showing the image/questions.
if not st.session_state.quiz_started:
    st.markdown('<div class="quiz-title">KUIS ANATOMI JUNIOR</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="quiz-subtitle">Bagian terpilih: <b>{section}</b></div>', unsafe_allow_html=True)
    with st.form("participant_form"):
        participant_name = st.text_input("Nama")
        participant_nim = st.text_input("NIM")
        begin = st.form_submit_button("Lanjut ke soal", type="primary", use_container_width=True)
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("← Kembali memilih bagian", use_container_width=True):
            st.session_state.selected_section = None
            st.rerun()
    if begin:
        if not participant_name.strip() or not participant_nim.strip():
            st.error("Nama dan NIM wajib diisi.")
        elif not section_questions:
            st.error(
                f"Belum ada soal aktif untuk bagian {section}. Tambahkan kolom 'bagian' di Google Sheets, "
                "isi dengan nama bagian yang sesuai, dan pastikan 'aktif' bernilai TRUE."
            )
        else:
            st.session_state.participant_name = participant_name.strip()
            st.session_state.participant_nim = participant_nim.strip()
            st.session_state.quiz_started = True
            st.rerun()
    st.stop()

# Stage 3: image and questions for the selected section.
if not st.session_state.quiz_submitted:
    left, right = st.columns([1.0, 1.15], gap="large")
    with left:
        with st.container(key="image_panel"):
            if section == "Skull":
                skull_images = [
                    "gambar_tengkorak.png",
                    "gambar_tengkorak_2.png",
                ]
                shown = 0
                for filename in skull_images:
                    path = BASE / filename
                    if path.exists():
                        # Kedua gambar memakai lebar render eksplisit yang sama.
                        # Lebar 650 px menjaga ukuran kiri-ke-kanan konsisten dan proporsi asli tetap terjaga.
                        st.image(Image.open(path), width=550)
                        shown += 1
                if shown == 0:
                    st.info("Gambar Skull belum tersedia. Unggah gambar_tengkorak.png dan gambar_tengkorak_2.png ke repositori GitHub.")
                st.markdown(
                    """
                    <div style="font-size:0.875rem; line-height:1.25;">
                        Referensi: Weir &amp; Abrahams’ Imaging Atlas of Human Anatomy, Fifth Edition.<br>
                        Jawaban harus sama persis dengan istilah yang digunakan dalam buku referensi.
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            elif image_path.exists():
                st.image(Image.open(image_path), caption=f"Gambar referensi • {section}", use_container_width=True)
            else:
                st.info(
                    f"Gambar untuk bagian {section} belum tersedia. Unggah file "
                    f"`{IMAGE_FILES.get(section, 'gambar_bagian.png')}` ke repositori GitHub."
                )
    with right:
        with st.form("quiz_answers"):
            for idx, item in enumerate(section_questions, start=1):
                prompt = item["pertanyaan"] or f"Identifikasi struktur anatomi {idx}."
                st.text_input(prompt, key=f"answer_{item['id']}", placeholder="Ketik jawaban...")
            confirm = st.checkbox("Saya sudah memeriksa jawaban saya.")
            send = st.form_submit_button("Kirim jawaban dan lihat nilai", type="primary", use_container_width=True)

    if send:
        if not confirm:
            st.error("Centang konfirmasi sebelum mengirim jawaban.")
        else:
            details = []
            total_points = earned_points = correct_count = 0
            for item in section_questions:
                response = st.session_state.get(f"answer_{item['id']}", "").strip()
                points = item["poin"]
                correct = answer_matches(response, item)
                total_points += points
                earned_points += points if correct else 0
                correct_count += int(correct)
                details.append({
                    "id": item["id"],
                    "pertanyaan": item["pertanyaan"],
                    "jawaban_peserta": response,
                    "jawaban_benar": item["jawaban_benar"],
                    "benar": correct,
                    "poin": points if correct else 0,
                })
            score = round(earned_points / total_points * 100, 2) if total_points else 0
            result = {
                "waktu": datetime.now().isoformat(timespec="seconds"),
                "nama_peserta": st.session_state.participant_name,
                "nim": st.session_state.participant_nim,
                "bagian": section,
                "jumlah_soal_dinilai": len(details),
                "jawaban_benar": correct_count,
                "nilai_persen": score,
                "detail": " | ".join(f"{x['id']}={x['jawaban_peserta']}" for x in details),
            }
            try:
                save_result(result)
            except Exception:
                pass
            st.session_state.result = result
            st.session_state.detail = details
            st.session_state.quiz_submitted = True
            st.rerun()
    st.stop()

# Stage 4: concise score and answer review
result = st.session_state.result
details = st.session_state.detail

st.markdown(
    f'<div class="quiz-title">HASIL KUIS — {section.upper()}</div>',
    unsafe_allow_html=True
)

st.subheader(
    f"Jawaban Benar: {result['jawaban_benar']}/{result['jumlah_soal_dinilai']}"
)
st.write(f"Nama: {result['nama_peserta']}")
st.write(f"NIM: {result['nim']}")
st.write(f"Nilai: {result['nilai_persen']:.2f}%")

st.divider()

for idx, item in enumerate(details, start=1):
    status = "Benar" if item["benar"] else "Salah"
    st.markdown(f"**{idx}. {status}**")
    st.write(
        f"Jawaban Peserta: "
        f"{item['jawaban_peserta'].strip() or 'Tidak dijawab'}"
    )
    st.write(f"Jawaban yang Benar: {item['jawaban_benar']}")

if st.button("Kembali ke menu bagian", type="primary"):
    reset_quiz()
    st.rerun()
