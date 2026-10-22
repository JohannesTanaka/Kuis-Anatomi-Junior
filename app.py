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
