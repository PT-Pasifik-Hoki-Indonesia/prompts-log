# prompts-log

Plugin Claude Code yang mencatat otomatis setiap prompt yang mengubah file di repo PT Pasifik Hoki Indonesia
ke folder `docs/prompts/` di repo itu. Satu file per entri, dengan nama sesuai waktu entri (`YYYYMMDD-HHMMSS.md`).

**Kenapa:** kode sekarang banyak ditulis AI. Tanpa prompt-nya, kita tidak tahu *kenapa* kode itu dibuat
begitu dan tidak bisa membangunnya ulang. Dengan log ini, tiap perubahan bisa ditelusuri ke permintaan
aslinya, ikut tersimpan di git, lalu di-backup harian ke Drive.

## Cara pakai

1. Pastikan Claude Code sudah terpasang: `claude --version`. Kalau belum, install dari
   https://claude.ai/download. Pengguna Windows juga perlu Git for Windows dan Python 3.
2. Pasang plugin (sekali per komputer):
   ```
   claude plugin marketplace add PT-Pasifik-Hoki-Indonesia/prompts-log
   claude plugin install prompts-log@psg
   claude plugin list        # harus ada prompts-log@psg, enabled
   ```
   Tutup sesi Claude Code yang masih terbuka, lalu buka sesi baru.
3. Pindah ke folder project. Pastikan berada di `main` atau branch yang nanti di-merge ke main.
4. Jalankan `claude`, lalu ketik `/prompts-backfill`. Kalau ditanya, pilih **semua commit**.
   Setelah selesai, commit `docs/prompts/`.
5. Selanjutnya berjalan otomatis: kerja dan commit seperti biasa, entri baru sudah di-stage dan ikut ter-commit.

Update plugin: `claude plugin marketplace update psg && claude plugin update prompts-log@psg`, lalu buka sesi baru.

**Jangan** menempelkan password, token, atau isi `.env` di prompt, karena semuanya ikut tercatat.
**Jangan** mengedit file di `docs/prompts/` secara manual (lihat [Membuang entri](#membuang-entri)).

## Cara kerja

- Hook `Stop` jalan tiap AI selesai menjawab. Kalau giliran itu mengubah file di repo yang remote-nya
  `github.com/PT-Pasifik-Hoki-Indonesia/…`, file entri baru ditulis ke `docs/prompts/` repo itu lalu di-`git add`.
- Semua branch ikut tercatat. Entri dianggap final setelah masuk branch default (yang dibaca backup ke Drive).
- File per entri: merge antar-branch tidak konflik, kecuali dua branch sama-sama mengubah baris Status entri yang sama.
- Repo yang masih punya `prompts.md` (v0.3): `/prompts-backfill` memecahnya otomatis (`prompts_log.py migrate`).

## Format entri

- Satu entri = percakapan sejak entri sebelumnya sampai giliran AI yang mengubah file.
- Tiap balasan manusia disertai pesan AI yang dibalasnya (yang panjang dilipat `<details>`). Pilihan menu ikut dicatat.
- Pesan AI sesudah mengubah file dicatat sebagai **🤖 (hasil)**. Jalannya tool tidak dicatat: detailnya ada di diff git.
- Entri sintesis juga punya **🤖 (hasil)**: spesifikasi (API, skema DB, modul, test, keputusan) yang cukup untuk
  membangun ulang perilaku yang sama. Kode identik tetap hanya bisa dari git.
- Label: `📝 asli` (dari transcript, prompt persis) atau `🤖 sintesis` (prompt disusun AI dari diff commit karena
  transcript-nya sudah hilang — maksud perubahan, bukan perintah yang benar-benar diberikan).
- Status: `⏳ belum di-commit` → `📦 sudah di-commit (hash menyusul)` → `🔀 sudah di-commit, belum masuk main · <hash>`
  → `✅ sudah di main · <hash>`.
  - 📦 dipasang git hook `pre-commit` (dipasang otomatis di clone saat entri pertama ditulis, menambah hook yang sudah
    ada tanpa menimpanya, tidak pernah memblokir commit). Berlaku untuk commit manual maupun commit oleh AI.
  - Hash dan 🔀/✅ diisi saat hook Claude Code jalan lagi di repo itu, dan selalu dihitung ulang oleh backup Hermes.
- Rahasia berpola umum (token `sk-…`, `ghp_…`, JWT, private key, `password=…`) disamarkan. Bentuk lain bisa lolos —
  jangan tempel rahasia di prompt.

## Membuang entri

Entri percobaan atau perubahan yang dibatalkan: hapus file entrinya, lalu tambahkan id-nya (dari baris
`<!-- prompts-log {"id": …} -->`) ke `docs/prompts/.skip`, satu id per baris.
Tanpa itu, backfill berikutnya akan menulisnya lagi dari transcript.

## Tes

`python3 scripts/test_prompts_log.py`

## Batas yang diketahui

- Hanya Claude Code. Cursor/Codex/ChatGPT tidak tercatat.
- Perubahan lewat shell (`sed`, `>`, `git commit`) dideteksi dari waktu modifikasi file dan commit selama giliran itu.
  Akibatnya file yang Anda edit sendiri di IDE pada saat AI sedang bekerja ikut tercatat di entri tersebut.
- Edit oleh subagent tidak tercatat.
- Status dicocokkan lewat waktu + file: commit lain di file yang sama pada jam yang sama bisa tertukar.
