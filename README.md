# prompts-log

Standar log prompt PT Pasifik Hoki Indonesia: setiap percakapan dengan AI yang **mengubah file** di repo org
dicatat otomatis ke `docs/prompts/`, **satu file per entri** bernama waktu entri
(`YYYYMMDD-HHMMSS.md`, jam lokal; detik yang sama diberi akhiran `-2`), supaya kode bisa ditelusuri dan dibangun ulang dari prompt-nya.

## Pasang (sekali per developer, berlaku di semua repo org)

```
gh auth login                      # perlu kalau repo ini private
/plugin marketplace add PT-Pasifik-Hoki-Indonesia/prompts-log
/plugin install prompts-log@psg
```

Lalu di tiap repo yang Anda pegang, sekali: `/prompts-backfill` (entri asli dari transcript di Mac Anda, entri
sintesis untuk commit yang transcript-nya sudah hilang),
dan set `"cleanupPeriodDays": 3650` di `~/.claude/settings.json` supaya transcript tidak terhapus setelah 30 hari.

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
