KUIS ANATOMI RADIOLOGI — GOOGLE SHEETS

Perubahan:
- app.py membaca soal dan kunci dari worksheet pertama pada Google Sheets.
- Spreadsheet ID sudah diisi.
- Gambar tetap berada di panel kiri.
- Hasil peserta masih disimpan lokal; rekap lintas peserta perlu integrasi terpisah.

Header worksheet yang diperlukan:
id | pertanyaan | jawaban_benar | alternatif_jawaban | poin | aktif

Google Sheets:
1Db6qV4YxJwIl3eTF43y4t30gyrsKHMGSQlvfWrNQfIQ

LOKAL:
1. Install dependencies: python -m pip install -r requirements.txt
2. Letakkan service account JSON dengan nama service_account.json di folder aplikasi.
3. Pastikan email service account diberi akses Viewer ke spreadsheet.
4. Jalankan: python -m streamlit run app.py

HOSTING STREAMLIT:
1. Commit app.py dan requirements.txt ke GitHub.
2. Hapus kunci_jawaban.csv dari repository publik setelah integrasi teruji.
3. Streamlit Cloud → App settings → Secrets: masukkan isi secrets_template.toml yang sudah diisi dengan nilai dari JSON service account.
4. Jangan pernah mengunggah service_account.json atau secrets ke GitHub.

Catatan:
- Aplikasi hanya menggunakan Google Sheets sebagai sumber kunci; tidak ada fallback ke CSV, untuk menghindari penggunaan file kunci publik secara tidak sengaja.
- Kunci jawaban saat ini tetap ditampilkan setelah peserta submit sebagai pembahasan.
- Hasil peserta belum dikirim ke Google Sheets; fitur itu membutuhkan integrasi terpisah.
