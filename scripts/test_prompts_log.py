"""Tes cepat: python3 scripts/test_prompts_log.py — repo + transcript palsu, tanpa jaringan."""
import json, os, subprocess, sys, tempfile, time
from datetime import datetime, timezone

S = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts_log.py")
tmp = tempfile.mkdtemp()
repo, other = os.path.join(tmp, "repo"), os.path.join(tmp, "luar")
for r, url in ((repo, "https://github.com/PT-Pasifik-Hoki-Indonesia/x.git"), (other, "https://github.com/orang-lain/y.git")):
    os.makedirs(r)
    for c in (["init", "-q", "-b", "main"], ["remote", "add", "origin", url], ["config", "user.name", "Tester"],
              ["config", "user.email", "t@example.com"], ["commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", "-C", r, *c], check=True)

iso = lambda t: datetime.fromtimestamp(t, timezone.utc).isoformat().replace("+00:00", "Z")
t0 = time.time() - 5
user = lambda u, text, t: {"type": "user", "uuid": u, "timestamp": iso(t), "cwd": tmp, "message": {"content": text}}
ai = lambda t, *blocks: {"type": "assistant", "timestamp": iso(t), "message": {"content": list(blocks)}}
tool = lambda name, **inp: {"type": "tool_use", "id": name + str(len(inp)), "name": name, "input": inp}
txt = lambda s: {"type": "text", "text": s}

def run(lines):
    tr = os.path.join(tmp, "abcdef12-sesi.jsonl")
    open(tr, "w").write("\n".join(json.dumps(l) for l in lines))
    subprocess.run([sys.executable, S, "hook"], input=json.dumps({"transcript_path": tr}), text=True, check=True,
                   env={**os.environ, "PROMPTS_LOG_NO_STAGE": "1"})
    p = os.path.join(repo, "prompts.md")
    return open(p).read() if os.path.exists(p) else ""

# 1. Edit tool + konteks: "ya lanjut" harus membawa usulan AI yang dijawabnya; rahasia disamarkan
lines = [user("u1aaaaaaaa", "tambah fitur X, password=rahasia123", t0), ai(t0 + 1, txt("Ada dua opsi: A atau B. Lanjut?")),
         user("u2bbbbbbbb", "ya lanjut A", t0 + 2),
         ai(t0 + 3, tool("Edit", file_path=os.path.join(repo, "a.js"))), ai(t0 + 3, tool("Edit", file_path=os.path.join(other, "z.js")))]
out = run(lines)
assert "ya lanjut A" in out and "Ada dua opsi" in out and "`a.js`" in out, out
assert "rahasia123" not in out and "z.js" not in out, "rahasia bocor / repo luar org ikut tercatat"
assert "⏳ belum di-commit" in out and out.count("## ") == 1

# 1b. Pesan AI sesudah edit tercatat sebagai hasil
lines.append(ai(t0 + 4, txt("Selesai: a.js dibuat dengan fungsi foo().")))
assert "**🤖 (hasil)**" in run(lines) or True  # entri sudah tertulis di run sebelumnya; diuji di bawah lewat entri baru

# 2. Perubahan lewat shell di giliran terakhir ikut tercatat
t1 = time.time()
open(os.path.join(repo, "b.txt"), "w").write("x")
lines += [user("u3cccccccc", "ubah b lewat sed", t1 - 1), ai(t1, tool("Bash", command=f"sed -i '' s/a/b/ {repo}/b.txt"))]
out = run(lines)
assert "ubah b lewat sed" in out and "`b.txt`" in out, out
lines.append(ai(time.time(), txt("Selesai: b.txt diubah lewat sed.")))
os.remove(os.path.join(repo, "prompts.md"))
out = run(lines)
assert "**🤖 (hasil)**\n\nSelesai: a.js dibuat" in out and "**🤖 (hasil)**\n\nSelesai: b.txt" in out, out
assert out.count("Selesai: a.js dibuat") == 1, "hasil dikutip ulang di entri berikutnya"
assert out.count("## ") == 2, "entri dobel"

# 2b. File yang SUDAH ter-track diubah lewat shell (baris status git diawali spasi) juga tercatat
subprocess.run(["git", "-C", repo, "add", "b.txt"], check=True); subprocess.run(["git", "-C", repo, "commit", "-qm", "b"], check=True)
t1b = time.time()
open(os.path.join(repo, "b.txt"), "w").write("y")
msg = {**user("u3bbbbbbbb", "ubah b yang sudah di-commit", t1b - 1), "cwd": repo}  # path relatif: repo dikenali dari cwd sesi
tracked = lines + [msg, ai(t1b, tool("Bash", command="sed -i '' s/x/y/ b.txt"))]
out_t = run(tracked)
assert "ubah b yang sudah di-commit" in out_t and out_t.count("`b.txt`") >= 2, out_t
subprocess.run(["git", "-C", repo, "checkout", "-q", "b.txt"], check=True)
lines = tracked

# 3. Jalan ulang tidak menambah entri (idempoten), .gitattributes terpasang
assert run(lines).count("## ") == 3
assert "prompts.md merge=union" in open(os.path.join(repo, ".gitattributes")).read()
# 4. Jawaban menu: pertanyaan + jawaban, pesan AI lama tidak dikutip ulang; hash yang dikutip tidak dianggap tercatat
t2 = time.time()
ask = {"type": "tool_use", "id": "ask1", "name": "AskUserQuestion", "input": {}}
ans = {"type": "user", "uuid": "u5eeeeeeee", "timestamp": iso(t2), "message": {"content": [{"type": "tool_result", "tool_use_id": "ask1",
       "content": 'User has answered your questions: "Isinya apa?"="yang singkat". Read the answers carefully.'}]}}
lines += [user("u4dddddddd", "buat c.md, tanya dulu. contoh status: **Status:** ✅ sudah di main · `deadbee`", t2 - 1), ai(t2, ask), ans,
          ai(t2 + 1, tool("Write", file_path=os.path.join(repo, "c.md")))]
out = run(lines)
e4 = out[out.index("buat c.md"):]
assert "**🤖 (tanya)** Isinya apa?" in e4 and "**👤 (pilih)** yang singkat" in e4 and "Read the answers" not in e4, e4
assert out.count("ubah b lewat sed") == 1 and out.count("Selesai: b.txt") == 1 and out.count("**🤖**") == 1, "percakapan/pesan AI dikutip ulang"
sys.dont_write_bytecode = True; sys.argv = ["x"]; sys.path.insert(0, os.path.dirname(S)); import prompts_log
assert "deadbee" not in prompts_log.covered(repo), "hash di kutipan dianggap sudah tercatat"
# 5. Entri yang dibuang lewat prompts-log-skip tidak ditulis ulang
p = os.path.join(repo, "prompts.md")
txt = open(p).read()
i = txt.index("## ", txt.index("buat c.md") - 400)
open(p, "w").write(txt[:i].replace("---\n\n", "---\n<!-- prompts-log-skip abcdef12-u4dddddd -->\n\n", 1))
assert "buat c.md" not in run(lines)
# 6. pre-commit: entri ⏳ yang file-nya di-stage jadi 📦 dan prompts.md ikut di-stage; hook git terpasang
open(os.path.join(repo, "a.js"), "w").write("x"); subprocess.run(["git", "-C", repo, "add", "a.js"], check=True)
subprocess.run([sys.executable, S, "precommit", repo], check=True)
out = open(os.path.join(repo, "prompts.md")).read()
blk = {f: next(x for x in out.split("\n## ")[1:] if f"**Files:** `{f}`" in x) for f in ("a.js", "b.txt")}
assert "📦 sudah di-commit" in blk["a.js"], "entri a.js tidak jadi 📦"
assert "📦" not in blk["b.txt"], "entri b.txt (tidak di-stage) ikut berubah"
staged = subprocess.run(["git", "-C", repo, "diff", "--cached", "--name-only"], capture_output=True, text=True).stdout
assert "prompts.md" in staged, staged
sys.argv = ["x"]; prompts_log.install_git_hook(repo); prompts_log.install_git_hook(repo)
hook = open(os.path.join(repo, ".git/hooks/pre-commit")).read()
assert hook.count("prompts-log: tandai") == 1 and os.access(os.path.join(repo, ".git/hooks/pre-commit"), os.X_OK)
assert subprocess.run(["git", "-C", repo, "commit", "-qm", "c"]).returncode == 0, "hook memblokir commit"
print("ok")
