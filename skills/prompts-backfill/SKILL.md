---
name: prompts-backfill
description: Isi riwayat prompts.md repo ini - entri asli dari transcript Claude Code di Mac ini, lalu entri sintesis (prompt disusun dari diff) untuk commit yang tidak punya transcript. Pakai saat user minta backfill / isi riwayat prompts.md.
---

`S` = `<base directory skill ini>/../../scripts/prompts_log.py`, `R` = `$(git rev-parse --show-toplevel)`.

1. Entri asli: `python3 S backfill R`. Laporkan jumlahnya.
2. Daftar commit tanpa entri: `python3 S gap R` (urut lama → baru). Laporkan jumlahnya; kalau banyak, tanya user
   mau semua atau sebagian dulu.
3. Untuk tiap commit: baca **seluruh** `git show <hash>` (lewati lockfile, file hasil generate, dan biner), termasuk
   test dan catatan rilis. Tulis dua bagian, dalam bahasa Indonesia:

   **Prompt**: perintah developer ke AI yang kira-kira menghasilkan perubahan ini. Maksud, perilaku yang diminta,
   batasan dan keputusan penting. Jangan menyalin kode. Jangan mengarang alasan yang tidak terlihat di diff, pesan
   commit, komentar kode, atau catatan rilis. Commit kecil cukup satu kalimat.

   Sumber kebenaran adalah **kode** di diff. Kalau pesan commit, komentar, atau catatan rilis bilang lain dari kodenya,
   tulis yang sesuai kode, lalu catat selisihnya di Hasil ("Catatan rilis menyebut X, kodenya Y").

   **Hasil**: spesifikasi yang cukup untuk membangun ulang perilaku yang sama tanpa melihat kode aslinya. Tulis yang
   relevan saja dari daftar ini, sebagai poin singkat:
   - API/route: method, path, body/parameter, respons dan kode error, middleware/guard
   - skema DB: migration (tabel, kolom, tipe, default, index), perubahan seed
   - modul/fungsi utama: nama, file, apa yang dilakukan (urutan langkah kalau urutannya penting)
   - UI: halaman/komponen, teks/locale baru
   - konfigurasi: variabel `.env` baru (nama saja, tanpa nilai) dan default-nya
   - test: file dan daftar kasus yang dicek
   - keputusan desain dan batasan yang sengaja dibiarkan
   - versi/catatan rilis yang ikut berubah

   Simpan (baris `---HASIL---` memisahkan keduanya):
   ```
   python3 S sintesis R <hash> <<'EOF'
   <prompt>
   ---HASIL---
   <hasil>
   EOF
   ```
4. Cek `cleanupPeriodDays` di `~/.claude/settings.json`. Kalau belum ada atau < 3650, tawarkan menambah
   `"cleanupPeriodDays": 3650` (bawaan Claude Code menghapus transcript setelah 30 hari). Ubah hanya kalau user setuju.
5. Ingatkan user untuk commit `prompts.md` dan `.gitattributes`. Jangan commit sendiri.
