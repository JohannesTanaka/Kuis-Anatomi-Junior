                        if not any(
                            str(q.get("gambar", "1")).strip() == str(next_stage_form)
                            for q in all_section_questions
                        ):
                            st.warning(
                                f"Soal gambar {next_stage_form} belum tersedia. "
                                f"Tambahkan soal di Google Sheets dengan bagian={section} dan gambar={next_stage_form}."
                            )
                        else:
                            st.session_state.quiz_stage = next_stage_form
                            st.session_state.quiz_submitted = False
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
# Navigasi sesi: peserta dapat kembali ke gambar sebelumnya untuk mengerjakan ulang.
if max_stages > 1 and quiz_stage > 1:
    back_col, retry_col, next_col = st.columns(3)
else:
    retry_col, next_col = st.columns(2)
    back_col = None

if back_col is not None:
    with back_col:
        previous_stage = quiz_stage - 1
        if st.button(f"← Kembali ke Gambar {previous_stage}", use_container_width=True):
            st.session_state.quiz_stage = previous_stage
            st.session_state.attempt_id = uuid.uuid4().hex
            st.session_state.quiz_submitted = False
            st.rerun()

with retry_col:
    if st.button("Ulangi Lagi", use_container_width=True):
        # Mulai percobaan baru dengan kunci widget yang benar-benar baru.
        st.session_state.attempt_id = uuid.uuid4().hex
        st.session_state.quiz_submitted = False
        st.rerun()
with next_col:
    if quiz_stage < max_stages:
        next_stage = quiz_stage + 1
        if st.button(f"Lanjut ke Gambar {next_stage}", type="primary", use_container_width=True):
            if not any(str(q.get("gambar", "1")).strip() == str(next_stage) for q in all_section_questions):
                st.error(f"Soal gambar {next_stage} belum tersedia. Tambahkan soal di Google Sheets dengan bagian={section} dan gambar={next_stage}.")
            else:
                # Setiap gambar/tahap baru menggunakan sesi input baru.
                st.session_state.attempt_id = uuid.uuid4().hex
                st.session_state.quiz_stage = next_stage
                st.session_state.quiz_submitted = False
                st.rerun()
    else:
        if st.button("Selesai / Kembali ke menu", type="primary", use_container_width=True):
            reset_quiz()
            st.rerun()
