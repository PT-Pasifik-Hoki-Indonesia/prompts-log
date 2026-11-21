---
name: prompts-off
description: Matikan pencatatan prompts-log di repo ini (hanya di komputer ini, tidak ikut ter-commit). Pakai saat user minta prompt di repo ini tidak dicatat.
---

1. Jalankan `git config prompts-log.off true` di repo ini.
2. Laporkan ke user: mulai giliran berikutnya, prompt di repo ini tidak dicatat di komputer ini. Entri yang sudah ada
   di `docs/prompts/` tidak dihapus. Untuk menyalakan lagi: `/prompts-on`.
