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

# Nama file gambar yang benar-benar ada di repositori GitHub.
# Resolusi dilakukan berdasarkan nama bagian dan nomor gambar (tahap).
IMAGE_CANDIDATES = {
    "skull": {
        1: ["gambar_tengkorak.png"],
        2: ["gambar_tengkorak_2.png"],
        3: ["gambar_tengkorak_3.png"],
        4: ["gambar_tengkorak_4.png"],
        5: ["gambar_tengkorak_5.png"],
        6: ["gambar_tengkorak_6.png"],
        7: ["gambar_tengkorak_7.png"],
    },
    "neck": {
        1: ["gambar_neck_1.png", "Gambar_Neck_1.png", "Gambar_neck_1.png"],
        2: ["gambar_neck_2.png", "Gambar_Neck_2.png", "Gmbar_Neck_2.png", "Gmbar_neck_2.png"],
        3: ["gambar_neck_3.png", "Gambar_Neck_3.png", "Gmbar_Neck_3.png", "Gmbar_neck_3.png"],
    },
    "shoulder": {i: [f"Shoulder{i}.png", f"shoulder{i}.png", f"gambar_shoulder_{i}.png"] for i in range(1, 10)},
    "humerus": {1: ["Humerus1.png", "humerus1.png", "gambar_humerus.png"]},
    "elbow": {i: [f"Elbow{i}.png", f"elbow{i}.png", f"gambar_elbow_{i}.png"] for i in range(1, 3)},
    "hand": {i: [f"Hand{i}.png", f"hand{i}.png", f"gambar_hand_{i}.png"] for i in range(1, 3)},
    "chest": {i: [f"Thorax{i}.png", f"thorax{i}.png", f"Chest{i}.png", f"chest{i}.png", f"gambar_chest_{i}.png"] for i in range(1, 3)},
    "pelvis": {i: [f"Hip{i}.png", f"hip{i}.png", f"Pelvis{i}.png", f"pelvis{i}.png", f"gambar_pelvis_{i}.png"] for i in range(1, 4)},
    "genu": {i: [f"Genu{i}.png", f"genu{i}.png", f"gambar_genu_{i}.png"] for i in range(1, 4)},
    "ankle": {i: [f"Ankle{i}.png", f"ankle{i}.png", f"gambar_ankle_{i}.png"] for i in range(1, 5)},
    "foot": {i: [f"Foot{i}.png", f"foot{i}.png", f"gambar_foot_{i}.png"] for i in range(1, 5)},
    # Alias untuk file tambahan yang terlihat di repositori.
    "abdomen": {1: ["Abdomen1.png", "abdomen1.png"]},
    "vertebra": {1: ["Vertebra1.png", "vertebra1.png", "gambar_vertebra.png"]},
    "forearm": {1: ["Forearm1.png", "forearm1.png", "gambar_forearm.png"]},
    "femur": {1: ["Femur1.png", "femur1.png", "gambar_femur.png"]},
    "cruris": {1: ["Cruris1.png", "cruris1.png", "gambar_cruris.png"]},
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
.block-container { padding-top: 2rem; }
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
