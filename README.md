# prompts-log

Standar `prompts.md` PT Pasifik Hoki Indonesia: setiap percakapan dengan AI yang **mengubah file** di repo org
dicatat otomatis ke `prompts.md` di akar repo, supaya kode bisa ditelusuri dan dibangun ulang dari prompt-nya.

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
  `github.com/PT-Pasifik-Hoki-Indonesia/…`, entri baru ditambahkan ke `prompts.md` repo itu lalu di-`git add`.
- Semua branch ikut tercatat. `prompts.md` dianggap final setelah masuk branch default (yang dibaca backup ke Drive).
- `.gitattributes` diberi `prompts.md merge=union` supaya merge antar-branch tidak konflik.

## Format entri

- Satu entri = percakapan sejak entri sebelumnya sampai giliran AI yang mengubah file.
- Tiap balasan manusia disertai pesan AI yang dibalasnya (yang panjang dilipat `<details>`). Pilihan menu ikut dicatat.
- Pesan AI sesudah mengubah file dicatat sebagai **🤖 (hasil)**. Jalannya tool tidak dicatat: detailnya ada di diff git.
- Entri sintesis juga punya **🤖 (hasil)**: spesifikasi (API, skema DB, modul, test, keputusan) yang cukup untuk
  membangun ulang perilaku yang sama. Kode identik tetap hanya bisa dari git.
- Label: `📝 asli` (dari transcript, prompt persis) atau `🤖 sintesis` (prompt disusun AI dari diff commit karena
  transcript-nya sudah hilang — maksud perubahan, bukan perintah yang benar-benar diberikan).
- Status: `⏳ belum di-commit` → `🔀 sudah di-commit, belum masuk main` → `✅ sudah di main`. Diperbarui tiap hook jalan.
- Rahasia berpola umum (token `sk-…`, `ghp_…`, JWT, private key, `password=…`) disamarkan. Bentuk lain bisa lolos —
  jangan tempel rahasia di prompt.

## Membuang entri

Entri percobaan atau perubahan yang dibatalkan: hapus blok entrinya, lalu tambahkan id-nya (dari baris
`<!-- prompts-log {"id": …} -->`) ke satu baris `<!-- prompts-log-skip id1 id2 -->` di bawah judul file.
Tanpa itu, backfill berikutnya akan menulisnya lagi dari transcript.

## Tes

`python3 scripts/test_prompts_log.py`

## Batas yang diketahui

- Hanya Claude Code. Cursor/Codex/ChatGPT tidak tercatat.
- Perubahan lewat shell (`sed`, `>`, `git commit`) dideteksi dari waktu modifikasi file dan commit selama giliran itu.
  Akibatnya file yang Anda edit sendiri di IDE pada saat AI sedang bekerja ikut tercatat di entri tersebut.
- Edit oleh subagent tidak tercatat.
- Status dicocokkan lewat waktu + file: commit lain di file yang sama pada jam yang sama bisa tertukar.
