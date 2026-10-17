
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

st.set_page_config(
    page_title="KUIS ANATOMI JUNIOR",
    page_icon="🩻",
    layout="wide",
)

st.markdown("""
<style>
.block-container { padding-top: 2rem; }
.quiz-title {
    font-size: 2rem;
    font-weight: 800;
    letter-spacing: .02em;
    margin-bottom: .2rem;
}
.quiz-subtitle {
    color: var(--text-color);
    opacity: .72;
    margin-bottom: 1.2rem;
}
.section-card {
    border: 1px solid rgba(128,128,128,.28);
    border-radius: 12px;
    padding: 1rem;
}
[class*="st-key-image_panel_stage_"] {
    position: fixed !important;
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
            spreadsheet_id = str(
                st.secrets.get("spreadsheet_id", DEFAULT_SPREADSHEET_ID)
            ).strip()
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
            "Kredensial Google Sheets belum tersedia. Isi Settings → Secrets "
            "di Streamlit Cloud. Jangan unggah file JSON kredensial ke GitHub."
        )

    import gspread
    from google.oauth2.service_account import Credentials

    credentials = Credentials.from_service_account_info(
        credentials_info,
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )

    client = gspread.authorize(credentials)
    spreadsheet = client.open_by_key(spreadsheet_id)
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
            header_positions[header] = index

    missing = [
        h for h in ("id", "pertanyaan", "jawaban_benar")
        if h not in header_positions
    ]

    if missing:
        raise RuntimeError(
            "Header wajib tidak ditemukan di baris pertama: "
            + ", ".join(missing)
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
    return str(value or "").strip().lower() in {
        "true", "1", "yes", "ya"
    }


def load_questions():
    try:
        rows = read_google_sheet_rows()
    except Exception as exc:
        return [], (
            "Gagal membaca Google Sheets. Periksa Secrets, ID spreadsheet, "
            "izin akses service account, dan header kolom. Detail: "
            f"{exc}"
        )

    questions = []

    for row in rows:
        qid = str(row.get("id", "")).strip()
        prompt = str(row.get("pertanyaan", "")).strip()
        correct = str(row.get("jawaban_benar", "")).strip()
        section = str(row.get("bagian", "")).strip()

        image_number = str(
            row.get("gambar", row.get("gambar_ke", row.get("tahap_gambar", "1")))
        ).strip() or "1"

        if not qid or not correct or not truthy(row.get("aktif", True)):
            continue

        if not section:
            section = "Skull"

        alternatives = [
            x.strip()
            for x in re.split(
                r"[|;\n]+",
                str(row.get("alternatif_jawaban", "") or ""),
            )
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
    accepted_normalized = {
        normalize(x) for x in accepted if normalize(x)
    }
    return normalize(response) in accepted_normalized


def save_result(result):
    existing_rows = []
    fieldnames = list(result.keys())

    if RESULTS_PATH.exists():
        try:
            with open(
                RESULTS_PATH, "r", newline="", encoding="utf-8-sig"
            ) as f:
                reader = csv.DictReader(f)
                existing_rows = list(reader)

                for field in (reader.fieldnames or []):
                    if field not in fieldnames:
                        fieldnames.append(field)
        except Exception:
            existing_rows = []

    existing_rows.append({key: str(value) for key, value in result.items()})

    with open(RESULTS_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
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

if "attempt_id" not in st.session_state:
    st.session_state.attempt_id = uuid.uuid4().hex


questions, load_error = load_questions()

if load_error:
    st.error(load_error)
    st.stop()


# TAHAP 1: PILIH BAGIAN ANATOMI
if st.session_state.selected_section is None:
    st.markdown(
        '<div class="quiz-title">KUIS ANATOMI JUNIOR</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="quiz-subtitle">Pilih bagian anatomi yang ingin dikerjakan.</div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(3)

    for i, section in enumerate(SECTIONS):
        with cols[i % 3]:
            if st.button(
                section,
                key=f"section_{section}",
                use_container_width=True,
            ):
                st.session_state.selected_section = section
                st.rerun()

    st.stop()


section = st.session_state.selected_section

all_section_questions = [
    q for q in questions
    if normalize(q["bagian"]) == normalize(section)
]

quiz_stage = st.session_state.quiz_stage

if normalize(section) == "skull":
    section_questions = [
        q for q in all_section_questions
        if str(q.get("gambar", "1")).strip() == str(quiz_stage)
    ]

    image_filename = {
        1: "gambar_tengkorak.png",
        2: "gambar_tengkorak_2.png",
        3: "gambar_tengkorak_3.png",
    }.get(quiz_stage, "gambar_tengkorak.png")
else:
    section_questions = all_section_questions
    image_filename = IMAGE_FILES.get(section, "")

image_path = BASE / image_filename


# TAHAP 2: IDENTITAS PESERTA
if not st.session_state.quiz_started:
    st.markdown(
        '<div class="quiz-title">KUIS ANATOMI JUNIOR</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="quiz-subtitle">Bagian terpilih: <b>{section}</b></div>',
        unsafe_allow_html=True,
    )

    with st.form("participant_form"):
        participant_name = st.text_input(
            "Nama",
            autocomplete="off",
        )
        participant_nim = st.text_input(
            "NIM",
            autocomplete="off",
        )

        begin = st.form_submit_button(
            "Lanjut ke soal",
            type="primary",
            use_container_width=True,
        )

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button(
            "← Kembali memilih bagian",
            use_container_width=True,
        ):
            st.session_state.selected_section = None
            st.rerun()

    if begin:
        if not participant_name.strip() or not participant_nim.strip():
            st.error("Nama dan NIM wajib diisi.")
        elif not section_questions:
            st.error(
                f"Belum ada soal aktif untuk bagian {section}. "
                "Pastikan kolom 'bagian' dan 'aktif' sudah benar."
            )
        else:
            st.session_state.participant_name = participant_name.strip()
            st.session_state.participant_nim = participant_nim.strip()
            st.session_state.quiz_started = True
            st.rerun()

    st.stop()


# TAHAP 3: GAMBAR DAN INPUT JAWABAN
if (
    normalize(section) == "skull"
    and quiz_stage in (2, 3)
    and not section_questions
):
    st.warning(
        f"Belum ada soal untuk gambar {quiz_stage}. "
        f"Tambahkan soal dengan bagian=Skull dan gambar={quiz_stage}."
    )

    if st.button("Kembali ke Gambar 1"):
        st.session_state.quiz_stage = 1
        st.session_state.quiz_submitted = False
        st.rerun()

    st.stop()


if not st.session_state.quiz_submitted:
    left, right = st.columns([1.0, 1.15], gap="large")

    with left:
        with st.container(key=f"image_panel_stage_{quiz_stage}"):
            if section == "Skull":
                if image_path.exists():
                    st.image(Image.open(image_path), width=550)
                else:
                    st.warning(
                        f"Gambar tahap {quiz_stage} belum tersedia: "
                        f"{image_filename}"
                    )

                st.markdown(
                    """
                    <div style="font-size:0.875rem; line-height:1.25;">
                        Referensi: Weir &amp; Abrahams’ Imaging Atlas of Human Anatomy,
                        Fifth Edition.<br>
                        Jawaban harus sama persis dengan istilah yang digunakan
                        dalam buku referensi.
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            elif image_path.exists():
                st.image(
                    Image.open(image_path),
                    caption=f"Gambar referensi • {section}",
                    use_container_width=True,
                )
            else:
                st.info(
                    f"Gambar untuk bagian {section} belum tersedia. "
                    f"Unggah file `{IMAGE_FILES.get(section, 'gambar_bagian.png')}` "
                    "ke repositori GitHub."
                )

    with right:
        with st.form("quiz_answers"):
            for idx, item in enumerate(section_questions, start=1):
                prompt = (
                    item["pertanyaan"]
                    or f"Identifikasi struktur anatomi {idx}."
                )

                # ID widget unik untuk setiap percobaan.
                answer_key = (
                    f"answer_{st.session_state.attempt_id}_{item['id']}"
                )

                st.text_input(
                    prompt,
                    key=answer_key,
                    placeholder="Ketik jawaban...",
                    autocomplete="off",
                )

            confirm = st.checkbox(
                "Saya sudah memeriksa jawaban saya."
            )

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

            for item in section_questions:
                answer_key = (
                    f"answer_{st.session_state.attempt_id}_{item['id']}"
                )

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

            score = (
                round(earned_points / total_points * 100, 2)
                if total_points else 0
            )

            result = {
                "waktu": datetime.now().isoformat(timespec="seconds"),
                "nama_peserta": st.session_state.participant_name,
                "nim": st.session_state.participant_nim,
                "bagian": section,
                "jumlah_soal_dinilai": len(details),
                "jawaban_benar": correct_count,
                "nilai_persen": score,
                "detail": " | ".join(
                    f"{x['id']}={x['jawaban_peserta']}" for x in details
                ),
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


# TAHAP 4: HASIL KUIS
result = st.session_state.stage_results.get(
    str(quiz_stage),
    st.session_state.get("result", {}),
)
details = st.session_state.stage_detail.get(
    str(quiz_stage),
    st.session_state.get("detail", []),
)

st.markdown(
    f'<div class="quiz-title">HASIL KUIS — {section.upper()} • GAMBAR {quiz_stage}</div>',
    unsafe_allow_html=True,
)

st.subheader(
    f"Jawaban Benar: "
    f"{result.get('jawaban_benar', 0)}/"
    f"{result.get('jumlah_soal_dinilai', len(details))}"
)

st.write(f"Nama: {st.session_state.participant_name}")
st.write(f"NIM: {st.session_state.participant_nim}")
st.divider()

for idx, item in enumerate(details, start=1):
    if item["benar"]:
        st.markdown(
            f"<span style='color:#16803c;font-weight:700'>{idx}. Benar</span>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<span style='color:#d92d20;font-weight:700'>{idx}. Salah</span>",
            unsafe_allow_html=True,
        )

    st.write(
        f"Jawaban Peserta: "
        f"{item['jawaban_peserta'].strip() or 'Tidak dijawab'}"
    )
    st.write(f"Jawaban yang Benar: {item['jawaban_benar']}")

st.divider()

retry_col, next_col = st.columns(2)

with retry_col:
    if st.button("Ulangi Lagi", use_container_width=True):
        st.session_state.attempt_id = uuid.uuid4().hex
        st.session_state.quiz_submitted = False
        st.rerun()

with next_col:
    if normalize(section) == "skull" and quiz_stage in (1, 2):
        next_stage = quiz_stage + 1

        if st.button(
            f"Lanjut ke Gambar {next_stage}",
            type="primary",
            use_container_width=True,
        ):
            if not any(
                str(q.get("gambar", "1")).strip() == str(next_stage)
                for q in all_section_questions
            ):
                st.error(
                    f"Soal gambar {next_stage} belum tersedia. "
                    "Tambahkan soal di Google Sheets."
                )
            else:
                st.session_state.attempt_id = uuid.uuid4().hex
                st.session_state.quiz_stage = next_stage
                st.session_state.quiz_submitted = False
                st.rerun()
    else:
        if st.button(
            "Selesai / Kembali ke menu",
            type="primary",
            use_container_width=True,
        ):
            reset_quiz()
            st.rerun()
