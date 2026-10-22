import csv
import json
import re
import unicodedata
import uuid
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
    "Neck": "gambar_neck_1.png",
    "Vertebra": "gambar_vertebra.png",
    "Shoulder": "Shoulder1.png",
    "Humerus": "Humerus1.png",
    "Elbow": "Elbow1.png",
    "Forearm": "gambar_forearm.png",
    "Hand": "Hand1.png",
    "Chest": "Thorax1.png",
    "Pelvis": "Hip1.png",
    "Femur": "gambar_femur.png",
    "Genu": "Genu1.png",
    "Cruris": "gambar_cruris.png",
    "Ankle": "Ankle1.png",
    "Foot": "Foot1.png",
}

st.set_page_config(page_title="KUIS ANATOMI JUNIOR", page_icon="🩻", layout="wide")

st.markdown("""
<style>
/* Latar putih murni bertekstur abu-abu sangat halus — tanpa warna krem */
.stApp {
    background-color: #FFFFFF !important;
    background-image:
        radial-gradient(circle, rgba(90, 90, 90, 0.10) 0.65px, transparent 0.9px),
        radial-gradient(circle, rgba(120, 120, 120, 0.06) 0.55px, transparent 0.85px),
        radial-gradient(circle, rgba(70, 70, 70, 0.035) 0.5px, transparent 0.8px) !important;
    background-size: 5px 5px, 8px 8px, 3px 3px;
    background-position: 0 0, 2px 3px, 1px 2px;
}
[data-testid="stAppViewContainer"],
[data-testid="stMain"],
.main { background-color: transparent !important; }
[data-testid="stSidebar"] { background-color: #FFFFFF !important; }
[data-testid="stHeader"] { background-color: rgba(255, 255, 255, 0.96) !important; }
[data-testid="stForm"] {
    background-color: rgba(255, 255, 255, 0.94) !important;
    border: 1px solid #D9DDE2;
    border-radius: 12px;
}
.stTextInput input { background-color: #F3F4F6 !important; }
/* Beri jarak tambahan dari toolbar agar pertanyaan pertama tidak tertutup/terpotong. */
.block-container { padding-top: 4.5rem !important; }
.quiz-title { font-size: 2rem; font-weight: 800; letter-spacing: .02em; margin-bottom: .2rem; }
.quiz-subtitle { color: var(--text-color); opacity: .72; margin-bottom: 1.2rem; }
.section-card { border: 1px solid rgba(128,128,128,.28); border-radius: 12px; padding: 1rem; }
[class*="st-key-image_panel_stage_"] {
    position: fixed !important;
    /* Keep the fixed panel below Streamlit's top toolbar/header. */
    top: 4.5rem !important;
    left: max(2rem, calc((100vw - 90rem) / 2)) !important;
    width: 570px !important;
    max-width: calc(100vw - 2rem) !important;
    box-sizing: border-box !important;
    height: calc(100vh - 4.5rem) !important;
    max-height: calc(100vh - 4.5rem) !important;
    padding-top: 0.25rem !important;
    margin-top: 0 !important;
    overflow-y: auto !important;
    scroll-padding-top: 0 !important;
    overflow-x: hidden !important;
    scrollbar-width: thin !important;
    scrollbar-color: #b0b0b0 transparent !important;
    z-index: 10 !important;
}
[class*="st-key-image_panel_stage_"]::-webkit-scrollbar {
    width: 4px !important;
}
[class*="st-key-image_panel_stage_"]::-webkit-scrollbar-track {
    background: transparent !important;
}
[class*="st-key-image_panel_stage_"]::-webkit-scrollbar-thumb {
    background: #b0b0b0 !important;
    border-radius: 10px !important;
}
[class*="st-key-image_panel_stage_"] [data-testid="stImage"] {
    width: 100% !important;
    max-width: 100% !important;
}
[class*="st-key-image_panel_stage_"] [data-testid="stImage"] img {
    display: block !important;
    width: 550px !important;
    max-width: 100% !important;
    height: auto !important;
    object-fit: contain !important;
    object-position: top center !important;
}
@media (max-width: 900px) {
    [class*="st-key-image_panel_stage_"] {
        position: static !important;
        width: 100% !important;
        max-width: none !important;
        max-height: none !important;
    }
    [class*="st-key-image_panel_stage_"] [data-testid="stImage"] img {
        width: 100% !important;
        max-width: 100% !important;
        height: auto !important;
        object-fit: contain !important;
        object-position: top center !important;
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
    # Read raw cells so duplicate headers do not crash gspread.
    # If old columns were left on the left and the new table pasted to the right,
    # use the LAST occurrence of each header (the newer table).
    values = spreadsheet.sheet1.get_all_values()
    if not values:
        return []

    expected_headers = [
        "id", "pertanyaan", "jawaban_benar", "alternatif_jawaban",
        "poin", "aktif", "bagian", "gambar",
    ]
    actual_headers = [str(value).strip() for value in values[0]]
    header_positions = {}
    for index, header in enumerate(actual_headers):
        if header:
            header_positions[header] = index  # last duplicate wins

    missing = [h for h in ("id", "pertanyaan", "jawaban_benar") if h not in header_positions]
    if missing:
        raise RuntimeError(
            "Header wajib tidak ditemukan di baris pertama: " + ", ".join(missing)
        )

    rows = []
    for raw_row in values[1:]:
        if not any(str(cell).strip() for cell in raw_row):
            continue
        row = {}
        for header in expected_headers:
            index = header_positions.get(header)
            row[header] = (
                str(raw_row[index]).strip()
                if index is not None and index < len(raw_row)
                else ""
            )
        rows.append(row)
    return rows


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
        image_number = str(row.get("gambar", row.get("gambar_ke", row.get("tahap_gambar", "1"))).strip() or "1")
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
            "gambar": image_number,
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
    """Simpan hasil ke CSV lokal; gabungkan kolom lama dan baru agar tidak gagal."""
    existing_rows = []
    fieldnames = list(result.keys())
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)
                for field in (reader.fieldnames or []):
                    if field not in fieldnames:
                        fieldnames.append(field)
        except Exception:
            existing_rows = []
    existing_rows.append({key: str(value) for key, value in result.items()})
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(existing_rows)


def reset_quiz():
    for key in list(st.session_state.keys()):
        if key.startswith("answer_") or key in {
            "quiz_started", "quiz_submitted", "participant_name",
            "participant_nim", "selected_section", "result", "detail",
            "quiz_stage", "stage_results", "stage_detail", "attempt_id",
        }:
            del st.session_state[key]


if "selected_section" not in st.session_state:
    st.session_state.selected_section = None
if "quiz_started" not in st.session_state:
    st.session_state.quiz_started = False
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "quiz_stage" not in st.session_state:
    st.session_state.quiz_stage = 1
if "stage_results" not in st.session_state:
    st.session_state.stage_results = {}
if "stage_detail" not in st.session_state:
    st.session_state.stage_detail = {}
# Token unik untuk setiap percobaan. Perubahan token membuat semua kolom jawaban
# menjadi widget baru, sehingga nilai dari percobaan sebelumnya tidak terbawa.
if "attempt_id" not in st.session_state:
    st.session_state.attempt_id = uuid.uuid4().hex

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
all_section_questions = [q for q in questions if normalize(q["bagian"]) == normalize(section)]
quiz_stage = st.session_state.quiz_stage

# Pemetaan gambar berdasarkan nama file yang benar-benar digunakan di repositori.
# Kolom Google Sheets "gambar" menentukan tahap/gambar yang ditampilkan.
SECTION_IMAGE_FILES = {
    "skull": {i: f"gambar_tengkorak{'_' + str(i) if i > 1 else ''}.png" for i in range(1, 8)},
    "neck": {
        1: "Gambar_Neck_1.png",
        2: "Gmbar_Neck_2.png",
        3: "Gmbar_Neck_3.png",
    },
    "shoulder": {i: f"Shoulder{i}.png" for i in range(1, 10)},
    "humerus": {1: "Humerus1.png"},
    "elbow": {1: "Elbow1.png", 2: "Elbow2.png"},
    "hand": {1: "Hand1.png", 2: "Hand2.png"},
    "chest": {1: "Thorax1.png", 2: "Thorax2.png"},
    "pelvis": {1: "Hip1.png", 2: "Hip2.png", 3: "Hip3.png"},
    "genu": {1: "Genu1.png", 2: "Genu2.png", 3: "Genu3.png"},
    "ankle": {i: f"Ankle{i}.png" for i in range(1, 5)},
    "foot": {i: f"Foot{i}.png" for i in range(1, 5)},
}

section_key = normalize(section)
image_map = SECTION_IMAGE_FILES.get(section_key, {})
# Gunakan gambar yang benar-benar memiliki soal aktif pada bagian terpilih.
stages_with_questions = sorted({
    int(str(q.get("gambar", "1")).strip())
    for q in all_section_questions
    if str(q.get("gambar", "1")).strip().isdigit()
})
if not stages_with_questions:
    stages_with_questions = [1]
max_stages = max(max(image_map.keys(), default=1), max(stages_with_questions, default=1))
section_questions = [
    q for q in all_section_questions
    if str(q.get("gambar", "1")).strip() == str(quiz_stage)
]

image_filename = image_map.get(quiz_stage, IMAGE_FILES.get(section, ""))
# Kompatibilitas variasi ejaan file Neck yang mungkin sudah ada di GitHub.
if section_key == "neck":
    neck_aliases = {
        1: ["Gambar_Neck_1.png", "Gambar_neck_1.png", "gambar_neck_1.png"],
        2: ["Gmbar_Neck_2.png", "Gmbar_neck_2.png", "Gambar_Neck_2.png", "gambar_neck_2.png"],
        3: ["Gmbar_Neck_3.png", "Gmbar_neck_3.png", "Gambar_Neck_3.png", "gambar_neck_3.png"],
    }
    for candidate in neck_aliases.get(quiz_stage, []):
        if (BASE / candidate).is_file():
            image_filename = candidate
            break
image_path = BASE / image_filename if image_filename else BASE / "__missing_image__"
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
if not section_questions:
    st.warning(
        f"Soal untuk {section}, gambar {quiz_stage} belum tersedia atau belum aktif. "
        f"Tambahkan soal aktif di Google Sheets dengan bagian={section}, gambar={quiz_stage}, "
        "dan kolom jawaban_benar terisi."
    )
    nav_cols = st.columns(2)
    with nav_cols[0]:
        if quiz_stage > 1 and st.button("← Gambar Sebelumnya", use_container_width=True):
            st.session_state.quiz_stage = quiz_stage - 1
            st.session_state.quiz_submitted = False
            st.rerun()
    with nav_cols[1]:
        if quiz_stage < max_stages and st.button("Lewati ke Gambar Berikutnya →", use_container_width=True):
            st.session_state.quiz_stage = quiz_stage + 1
            st.session_state.quiz_submitted = False
            st.rerun()
    st.stop()

if not st.session_state.quiz_submitted:
    left, right = st.columns([1.0, 1.15], gap="large")
    with left:
        with st.container(key=f"image_panel_stage_{quiz_stage}"):
            if image_path.is_file():
                st.image(Image.open(image_path), use_container_width=True)
            else:
                st.info(
                    f"Gambar untuk bagian {section}, tahap {quiz_stage} belum ditemukan. "
                    f"Pastikan file `{image_filename}` sudah diunggah ke repositori GitHub "
                    "dengan nama dan huruf besar-kecil yang sama persis."
                )
            # Catatan referensi berlaku untuk semua bagian dan semua gambar.
            st.markdown(
                """
                <div style="font-size:0.875rem; line-height:1.4; margin-top:0.75rem;">
                    <b>Referensi:</b> Weir &amp; Abrahams’ Imaging Atlas of Human Anatomy, Fifth Edition.<br>
                    <b>Jawaban:</b> Gunakan istilah anatomi sesuai buku referensi.
                </div>
                """,
                unsafe_allow_html=True
            )
    with right:
        # Input di luar st.form agar jawaban tersimpan saat berpindah gambar.
        for idx, item in enumerate(section_questions, start=1):
            prompt = item["pertanyaan"] or f"Identifikasi struktur anatomi {idx}."
            answer_key = f"answer_{st.session_state.attempt_id}_{item['id']}"
            st.text_input(prompt, key=answer_key, placeholder="Ketik jawaban...")

        confirm = st.checkbox(
            "Saya sudah memeriksa jawaban saya.",
            key=f"confirm_{st.session_state.attempt_id}_{quiz_stage}",
        )
        send = st.button(
            "Kirim jawaban dan lihat nilai",
            key=f"submit_answers_{st.session_state.attempt_id}_{quiz_stage}",
            type="primary",
            use_container_width=True,
        )

        # Navigasi soal: dropdown untuk lompat langsung, serta tombol sebelumnya/selanjutnya.
        available_stages = sorted({
            int(str(q.get("gambar", "1")).strip())
            for q in all_section_questions
            if str(q.get("gambar", "1")).strip().isdigit()
        })
        if available_stages:
            st.divider()
            st.markdown("**Navigasi soal**")
            current_index = available_stages.index(quiz_stage) if quiz_stage in available_stages else 0
            nav_select_col, nav_prev_col, nav_next_col, nav_menu_col = st.columns([1.35, 1, 1, 1.1])
            select_key = f"select_stage_{section_key}_{quiz_stage}"
            with nav_select_col:
                def jump_to_selected_stage():
                    selected = st.session_state.get(select_key)
                    if selected is not None:
                        st.session_state.quiz_stage = int(selected)
                        st.session_state.quiz_submitted = False
                        st.session_state.attempt_id = uuid.uuid4().hex
                st.selectbox(
                    "Pilih gambar/soal",
                    options=available_stages,
                    index=current_index,
                    format_func=lambda n: f"Gambar/Soal {n}",
                    key=select_key,
                    on_change=jump_to_selected_stage,
                )
            with nav_prev_col:
                if current_index > 0:
                    previous_stage = available_stages[current_index - 1]
                    if st.button(f"← Sebelumnya ({previous_stage})", key=f"previous_stage_{section_key}_{quiz_stage}", use_container_width=True):
                        st.session_state.quiz_stage = previous_stage
                        st.session_state.quiz_submitted = False
                        st.rerun()
            with nav_next_col:
                if current_index < len(available_stages) - 1:
                    next_stage = available_stages[current_index + 1]
                    if st.button(f"Selanjutnya ({next_stage}) →", key=f"next_stage_{section_key}_{quiz_stage}", use_container_width=True):
                        st.session_state.quiz_stage = next_stage
                        st.session_state.quiz_submitted = False
                        st.rerun()
            with nav_menu_col:
                if st.button("Menu utama", key=f"menu_from_quiz_{section_key}_{quiz_stage}", use_container_width=True):
                    reset_quiz()
                    st.rerun()

    if send:
        if not confirm:
            st.error("Centang konfirmasi sebelum mengirim jawaban.")
        else:
            details = []
            total_points = earned_points = correct_count = 0
            for item in section_questions:
                answer_key = f"answer_{st.session_state.attempt_id}_{item['id']}"
                response = st.session_state.get(answer_key, "").strip()
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
            st.session_state.stage_results[str(quiz_stage)] = result
            st.session_state.stage_detail[str(quiz_stage)] = details
            st.session_state.result = result
            st.session_state.detail = details
            st.session_state.quiz_submitted = True
            st.rerun()
    st.stop()

# Stage 4: tampilkan pembahasan, lalu beri pilihan ulangi atau lanjut.
result = st.session_state.stage_results.get(str(quiz_stage), st.session_state.get("result", {}))
details = st.session_state.stage_detail.get(str(quiz_stage), st.session_state.get("detail", []))
st.markdown(f'<div class="quiz-title">HASIL KUIS — {section.upper()} • GAMBAR {quiz_stage}</div>', unsafe_allow_html=True)
st.subheader(f"Jawaban Benar: {result.get('jawaban_benar', 0)}/{result.get('jumlah_soal_dinilai', len(details))}")
st.write(f"Nama: {st.session_state.participant_name}")
st.write(f"NIM: {st.session_state.participant_nim}")
st.divider()
for idx, item in enumerate(details, start=1):
    if item["benar"]:
        st.markdown(f"<span style='color:#16803c;font-weight:700'>{idx}. Benar</span>", unsafe_allow_html=True)
    else:
        st.markdown(f"<span style='color:#d92d20;font-weight:700'>{idx}. Salah</span>", unsafe_allow_html=True)
    st.write(f"Jawaban Peserta: {item['jawaban_peserta'].strip() or 'Tidak dijawab'}")
    st.write(f"Jawaban yang Benar: {item['jawaban_benar']}")
st.divider()
# Navigasi halaman hasil: dropdown langsung, sebelumnya/selanjutnya, ulangi, menu utama.
available_stages = sorted({
    int(str(q.get("gambar", "1")).strip())
    for q in all_section_questions
    if str(q.get("gambar", "1")).strip().isdigit()
})
current_index = available_stages.index(quiz_stage) if quiz_stage in available_stages else 0
result_select_col, result_prev_col, result_next_col, result_retry_col, result_menu_col = st.columns([1.35, 1, 1, 1, 1.1])
result_select_key = f"result_select_stage_{section_key}_{quiz_stage}"
with result_select_col:
    def jump_to_result_stage():
        selected = st.session_state.get(result_select_key)
        if selected is not None:
            st.session_state.quiz_stage = int(selected)
            st.session_state.attempt_id = uuid.uuid4().hex
            st.session_state.quiz_submitted = str(selected) in st.session_state.stage_results
    st.selectbox(
        "Pilih gambar/soal",
        options=available_stages or [quiz_stage],
        index=(available_stages.index(quiz_stage) if quiz_stage in available_stages else 0),
        format_func=lambda n: f"Gambar/Soal {n}",
        key=result_select_key,
        on_change=jump_to_result_stage,
    )
with result_prev_col:
    if current_index > 0:
        previous_stage = available_stages[current_index - 1]
        if st.button(f"← Sebelumnya ({previous_stage})", key=f"result_previous_{section_key}_{quiz_stage}", use_container_width=True):
            st.session_state.quiz_stage = previous_stage
            st.session_state.attempt_id = uuid.uuid4().hex
            st.session_state.quiz_submitted = str(previous_stage) in st.session_state.stage_results
            st.rerun()
with result_next_col:
    if current_index < len(available_stages) - 1:
        next_stage = available_stages[current_index + 1]
        if st.button(f"Selanjutnya ({next_stage}) →", key=f"result_next_{section_key}_{quiz_stage}", use_container_width=True):
            st.session_state.quiz_stage = next_stage
            st.session_state.attempt_id = uuid.uuid4().hex
            st.session_state.quiz_submitted = str(next_stage) in st.session_state.stage_results
            st.rerun()
with result_retry_col:
    if st.button("Ulangi Lagi", key=f"retry_stage_{section_key}_{quiz_stage}", use_container_width=True):
        st.session_state.attempt_id = uuid.uuid4().hex
        st.session_state.quiz_submitted = False
        st.rerun()
with result_menu_col:
    if st.button("Menu utama", key=f"menu_result_{section_key}_{quiz_stage}", type="primary", use_container_width=True):
        reset_quiz()
        st.rerun()
