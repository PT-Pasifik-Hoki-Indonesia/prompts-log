---
name: prompts-backfill
description: Isi riwayat prompts.md repo ini - entri asli dari transcript Claude Code di Mac ini, lalu entri sintesis (prompt disusun dari diff) untuk commit yang tidak punya transcript. Pakai saat user minta backfill / isi riwayat prompts.md.
---

`S` = `<base directory skill ini>/../../scripts/prompts_log.py`, `R` = `$(git rev-parse --show-toplevel)`.

1. Entri asli: `python3 S backfill R`. Laporkan jumlahnya.
2. Daftar commit tanpa entri: `python3 S gap R` (urut lama → baru). Laporkan jumlahnya; kalau banyak, tanya user
   mau semua atau sebagian dulu.
3. Untuk tiap commit: baca `git show <hash>` (lewati lockfile dan file hasil generate), lalu tulis prompt yang
   kira-kira menghasilkan perubahan itu, dalam bahasa Indonesia, gaya perintah developer ke AI:
   - maksud dan perilaku yang diminta, batasan/keputusan penting, test dan dokumen yang ikut diubah;
   - jangan menyalin kode, jangan mengarang alasan yang tidak terlihat di diff/pesan commit/catatan rilis;
   - commit kecil → prompt satu kalimat.
   Simpan: `python3 S sintesis R <hash> <<'EOF' … EOF`.
4. Cek `cleanupPeriodDays` di `~/.claude/settings.json`. Kalau belum ada atau < 3650, tawarkan menambah
   `"cleanupPeriodDays": 3650` (bawaan Claude Code menghapus transcript setelah 30 hari). Ubah hanya kalau user setuju.
5. Ingatkan user untuk commit `prompts.md` dan `.gitattributes`. Jangan commit sendiri.
