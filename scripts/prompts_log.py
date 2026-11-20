#!/usr/bin/env python3
"""prompts-log v0.3.0 — catat percakapan dengan AI yang mengubah file ke prompts.md repo.

  prompts_log.py hook                       # dipanggil Stop hook, JSON di stdin
  prompts_log.py backfill <repo>           # entri asli dari transcript di Mac ini
  prompts_log.py precommit [<repo>]        # dipanggil git pre-commit
  prompts_log.py gap <repo>                # commit di branch default yang belum punya entri
  prompts_log.py sintesis <repo> <hash>    # entri 🤖 sintesis; stdin: prompt, baris ---HASIL---, spesifikasi hasil

Satu entri = percakapan sejak entri sebelumnya sampai giliran AI yang mengubah file.
Tiap balasan manusia disertai pesan AI yang dibalasnya. Hanya repo org yang dicatat.
"""
import glob, json, os, re, subprocess, sys
from datetime import datetime, timezone

ORG = re.compile(r"github\.com[:/]PT-Pasifik-Hoki-Indonesia/")
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
FILE = "prompts.md"
FOLD_LINES = 6
MARK = re.compile(r"<!-- prompts-log (\{.*?\}) -->")
SKIP = re.compile(r"<!-- prompts-log-skip ([^>]*) -->")  # id entri yang sengaja dibuang (mis. percobaan), jangan ditulis ulang
HEADER = ("# Prompts\n\nCatatan percakapan dengan AI yang menghasilkan perubahan file di repo ini.\n"
          "Diisi otomatis oleh plugin `prompts-log`. Jangan diedit manual, dan jangan tempel "
          "password/token di prompt: semuanya ikut tercatat ke GitHub dan Drive.\n\n---\n\n")

# ponytail: pola rahasia yang umum saja; bentuk lain tetap bisa lolos
SECRET = re.compile(
    r"(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|xox[abp]-[A-Za-z0-9-]{10,}"
    r"|AKIA[0-9A-Z]{16}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"
    r"|-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----)")
KV_SECRET = re.compile(r"(?i)\b(password|passwd|pwd|secret|token|api[_-]?key)(\s*[:=]\s*)(\S+)")
NOISE = ("<command-", "<local-command", "<task-notification", "Caveat:", "[Request interrupted")


def git(root, *args):
    r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


_roots = {}
def repo_of(path):
    d = os.path.dirname(path)
    if d not in _roots:
        root = git(d, "rev-parse", "--show-toplevel") if os.path.isdir(d) else ""
        _roots[d] = root if root and ORG.search(git(root, "remote", "get-url", "origin")) else ""
    return _roots[d]


def clean(s):
    s = re.sub(r"<system-reminder>[\s\S]*?</system-reminder>", "", s).strip()
    s = re.sub(r"(?m)^#{1,6} +(.+)$", r"**\1**", s)  # heading di kutipan jangan menyaru jadi header entri
    s = s.replace("<!-- prompts-log", "&lt;!-- prompts-log").replace("**Status:**", "*Status:*")
    s = SECRET.sub("[DISAMARKAN]", s)
    return KV_SECRET.sub(lambda m: m[1] + m[2] + "[DISAMARKAN]", s)


def quote_ai(text, label="🤖"):
    text = clean(text)
    lines = text.splitlines()
    if len(lines) <= FOLD_LINES:
        return f"**{label}**\n\n" + text + "\n"
    first = re.sub(r"[#*`<>|]", "", next(l for l in lines if l.strip())).strip()[:90]
    return f"**{label}**\n<details><summary>{first}…</summary>\n\n{text}\n\n</details>\n"


def human_text(content):
    if isinstance(content, str):
        return content
    if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
        return None
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


PATH_IN_CMD = re.compile(r"(/(?:Users|home|private|tmp|opt|srv|var)/[^\s'\"`;|&<>()]+)")


def shell_changes(roots, since):
    """File di repo yang berubah sejak `since` (epoch): file kotor dengan mtime sesudahnya + isi commit sesudahnya."""
    # ponytail: berbasis waktu; file yang diedit manusia di IDE selama giliran yang sama ikut terhitung
    out = {}
    for root in roots:
        st = git(root, "status", "--porcelain", "--untracked-files=all")
        dirty = [l[3:].split(" -> ")[-1].strip('"') for l in st.split("\n") if l]
        changed = [f for f in dirty if os.path.exists(os.path.join(root, f)) and os.path.getmtime(os.path.join(root, f)) >= since - 1]
        me = git(root, "config", "user.email")  # commit orang lain yang masuk lewat pull di menit yang sama bukan kerja AI giliran ini
        changed += git(root, "log", "--all", f"--since=@{int(since)}", *([f"--committer={me}"] if me else []), "--name-only", "--format=").split("\n")
        changed = [f for f in dict.fromkeys(changed) if f and f not in (FILE, ".gitattributes")]
        if changed:
            out[root] = changed
    return out


def epoch(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()


def logged_ids(roots):
    ids = set()
    for root in roots:
        f = os.path.join(root, FILE)
        if os.path.exists(f):
            text = open(f).read()
            ids |= {json.loads(m)["id"] for m in MARK.findall(text)} | {i for m in SKIP.findall(text) for i in m.split()}
    return ids


def parse(path, live=False, logged=frozenset()):
    """Entri dari satu transcript: [{id, ts, cwd, branch, convo, files: {root: [rel]}}].
    live=True: giliran terakhir juga diperiksa untuk perubahan lewat shell (hanya valid tepat saat Stop)."""
    out, convo, files, last_ai, asks, cur = [], [], {}, "", {}, {"quoted": ""}

    def ai_context():
        if last_ai and last_ai != cur["quoted"]:
            convo.append(quote_ai(last_ai))
            cur["quoted"] = last_ai
    sid = os.path.basename(path)[:8]

    def close(final=False):
        if final and live and cur.get("cmds") and cur.get("turn_ts"):
            roots = {repo_of(os.path.join(p, "x") if os.path.isdir(p) else p) for c in cur["cmds"] for p in PATH_IN_CMD.findall(c)}
            roots.add(repo_of(os.path.join(cur.get("cwd", ""), "x")))
            for root, fs in shell_changes(sorted(r for r in roots if r), epoch(cur["turn_ts"])).items():
                files.setdefault(root, []).extend(fs)
                cur["ts"], cur["edited"] = cur["last_ts"], True
                cur["hasil"] = cur.get("hasil") or cur.get("turn_ai", "")  # hanya lewat shell: pesan AI terakhir giliran itu
        cur.pop("cmds", None)
        if cur.get("id") in logged and not files:  # giliran ini sudah tercatat sebelumnya (mis. perubahan lewat shell)
            cur["edited"], cur["hasil"] = True, cur.get("turn_ai", "")
            cur["quoted"] = cur["hasil"] or cur["quoted"]
        if files:
            out.append({**cur, "convo": list(convo), "files": {r: list(dict.fromkeys(f)) for r, f in files.items()}})
            cur["quoted"] = cur.get("hasil") or cur["quoted"]  # hasil sudah tampil di entri ini, jangan dikutip ulang
        cur.pop("hasil", None)
        if cur.get("edited"):
            convo.clear(); files.clear(); cur.pop("edited")

    for line in open(path, errors="replace"):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if o.get("isSidechain") or o.get("isMeta") or o.get("type") not in ("user", "assistant"):
            continue
        content = o["message"].get("content")
        if o["type"] == "assistant":
            for b in content if isinstance(content, list) else []:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "text" and b["text"].strip():
                    last_ai = cur["turn_ai"] = b["text"]
                    if cur.get("edited"):
                        cur["hasil"] = b["text"]
                elif b.get("type") == "tool_use" and b["name"] == "AskUserQuestion":
                    asks[b["id"]] = True
                elif b.get("type") == "tool_use" and b["name"] == "Bash":
                    cur.setdefault("cmds", []).append(b["input"].get("command", ""))
                elif b.get("type") == "tool_use" and b["name"] in EDIT_TOOLS:
                    cur["edited"], cur["hasil"] = True, ""
                    fp = b["input"].get("file_path") or b["input"].get("notebook_path") or ""
                    root = repo_of(fp) if fp.startswith("/") else ""
                    if root:
                        files.setdefault(root, []).append(os.path.relpath(os.path.realpath(fp), root))
                        cur["ts"] = o["timestamp"]
            cur["last_ts"] = o["timestamp"]
            continue
        for b in content if isinstance(content, list) else []:
            if isinstance(b, dict) and b.get("type") == "tool_result" and b.get("tool_use_id") in asks:
                r = b["content"] if isinstance(b["content"], str) else " ".join(x.get("text", "") for x in b["content"])
                pairs = re.findall(r'"(.+?)"="(.*?)"', r) or [("", r)]
                ai_context()
                convo += [f"**🤖 (tanya)** {clean(q)}\n\n**👤 (pilih)** {clean(a)}\n" if q else f"**👤 (pilih)** {clean(a)}\n" for q, a in pairs]
        t = human_text(content)
        if not t or not t.strip() or t.lstrip().startswith(NOISE):
            continue
        close()  # giliran baru: tutup entri kalau giliran sebelumnya mengubah file
        ai_context()
        convo.append("**👤** " + clean(t) + "\n")
        cur.update(id=f"{sid}-{o['uuid'][:8]}", cwd=o.get("cwd", ""), branch=o.get("gitBranch", ""), turn_ts=o["timestamp"], turn_ai="")
    close(final=True)
    return out


def default_branch(root):
    return git(root, "symbolic-ref", "--short", "refs/remotes/origin/HEAD") or "origin/main"


def status(root, ts, files):
    """Commit pertama sesudah waktu entri yang menyentuh file-file entri."""
    # ponytail: dicocokkan lewat waktu + file; commit lain di file yang sama pada jam yang sama bisa tertukar
    h = git(root, "log", "--all", "--reverse", f"--since={ts}", "--format=%h", "--", *files).split("\n")[0]
    if not h:
        return "⏳ belum di-commit"
    main = default_branch(root)
    if subprocess.run(["git", "-C", root, "merge-base", "--is-ancestor", h, main]).returncode == 0:
        return f"✅ sudah di {main.split('/', 1)[1]} · `{h}`"
    br = git(root, "branch", "-a", "--contains", h, "--format=%(refname:short)").split("\n")[0]
    return f"🔀 sudah di-commit, belum masuk {main.split('/', 1)[1]} · `{h}` ({br})"


def render(root, e, who):
    ts = datetime.fromisoformat(e["ts"].replace("Z", "+00:00"))
    files = e["files"][root]
    meta = json.dumps({"id": e["id"], "ts": e["ts"], "files": files}, ensure_ascii=False)
    branch = e["branch"] if e["branch"] and e["branch"] != "HEAD" else "(tidak tercatat)"
    kind = e.get("kind", "📝 asli")
    shown = files[:15] + ([f"+{len(files) - 15} lainnya"] if len(files) > 15 else [])
    who = e.get("who", who)
    return (f"## {ts.astimezone():%Y-%m-%d %H:%M} · {who} · branch {branch} · {kind}\n"
            f"<!-- prompts-log {meta} -->\n**Status:** {e.get('status') or status(root, e['ts'], files)}\n\n"
            + "\n".join(e["convo"]) + ("\n" + quote_ai(e["hasil"], "🤖 (hasil)") if e.get("hasil") else "") + "\n**Files:** " + ", ".join(f"`{f}`" for f in shown) + "\n\n---\n\n")


def refresh(text, root):
    """Perbarui baris Status entri yang belum sampai ke branch default."""
    # ponytail: baris Status diubah di tempat; dua branch yang mengubah status entri yang sama → union merge menyimpan keduanya
    def sub(m):
        meta = json.loads(m[1])
        return m[0] if m[2].startswith("✅") else f"<!-- prompts-log {m[1]} -->\n**Status:** {status(root, meta['ts'], meta['files'])}"
    return re.sub(r"<!-- prompts-log (\{.*?\}) -->\n\*\*Status:\*\* (.*)", sub, text)


GIT_HOOK = """
# prompts-log: tandai entri prompts.md yang ikut di-commit (tidak pernah memblokir commit)
S=$(ls -d "$HOME"/.claude/plugins/cache/*/prompts-log/*/scripts/prompts_log.py 2>/dev/null | sort -V | tail -1)
[ -n "$S" ] && python3 "$S" precommit . >/dev/null 2>&1 || true
"""


def install_git_hook(root):
    """Pasang pre-commit sekali per clone. Hook yang sudah ada tidak ditimpa, baris prompts-log ditambahkan di akhirnya."""
    # ponytail: kalau hook lama keluar lebih awal (exit 0 di tengah), baris ini tidak sempat jalan
    path = git(root, "rev-parse", "--git-path", "hooks/pre-commit")
    path = path if os.path.isabs(path) else os.path.join(root, path)
    old = open(path).read() if os.path.exists(path) else "#!/bin/sh\n"
    if "prompts-log" not in old:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, "w").write(old.rstrip("\n") + "\n" + GIT_HOOK)
        os.chmod(path, 0o755)


def precommit(root):
    """Dipanggil git pre-commit: entri ⏳ yang file-nya ikut commit ini jadi 📦, lalu prompts.md ikut di-stage."""
    path = os.path.join(root, FILE)
    if not os.path.exists(path):
        return
    staged = set(git(root, "diff", "--cached", "--name-only").split("\n"))
    def sub(m):
        hit = m[2].startswith("⏳") and staged & set(json.loads(m[1])["files"])
        return f"<!-- prompts-log {m[1]} -->\n**Status:** 📦 sudah di-commit (hash menyusul)" if hit else m[0]
    text = open(path).read()
    new = re.sub(r"<!-- prompts-log (\{.*?\}) -->\n\*\*Status:\*\* (.*)", sub, text)
    if new != text:
        open(path, "w").write(new)
    git(root, "add", FILE)


def write(root, entries, who, stage):
    path = os.path.join(root, FILE)
    text = open(path).read() if os.path.exists(path) else HEADER
    seen = {json.loads(m)["id"] for m in MARK.findall(text)} | {i for m in SKIP.findall(text) for i in m.split()}
    new = sorted((e for e in entries if e["id"] not in seen), key=lambda e: e["ts"])
    head, *blocks = re.split(r"(?m)^(?=## \d{4}-)", refresh(text, root) + "".join(render(root, e, who) for e in new))
    when = lambda b: datetime.fromisoformat(json.loads(MARK.search(b)[1])["ts"].replace("Z", "+00:00"))
    open(path, "w").write(head + "".join(sorted(blocks, key=when)))  # selalu urut waktu, termasuk entri backfill/sintesis
    ga = os.path.join(root, ".gitattributes")
    if f"{FILE} merge=union" not in (open(ga).read() if os.path.exists(ga) else ""):
        with open(ga, "a") as f:
            f.write(f"{FILE} merge=union\n")
    if stage and not os.environ.get("PROMPTS_LOG_NO_STAGE"):
        git(root, "add", FILE, ".gitattributes")
        install_git_hook(root)
    return len(new)


def covered(root):
    """Hash commit yang sudah terwakili entri di prompts.md (id git-… atau hash di baris Status)."""
    path = os.path.join(root, FILE)
    text = open(path).read() if os.path.exists(path) else ""
    return set(re.findall(r'"id": "git-([0-9a-f]+)"', text)) | set(re.findall(r"-->\n\*\*Status:\*\* .*?`([0-9a-f]{7,})`", text))


def gap(root):
    seen = covered(root)
    log = git(root, "log", default_branch(root), "--no-merges", "--reverse", "--format=%h%x09%ad%x09%an%x09%s", "--date=short")
    return [l for l in log.split("\n") if l and l.split("\t")[0] not in seen]


def sintesis(root, h, text):
    prompt, _, hasil = text.partition("\n---HASIL---\n")
    full, ts, an = git(root, "show", "-s", "--format=%H%x09%aI%x09%an", h).split("\t")
    h = full[:7]
    main = default_branch(root).split("/", 1)[1]
    files = [f for f in git(root, "show", "--name-only", "--format=", full).split("\n") if f]
    note = "> Prompt asli tidak tersimpan. Prompt di bawah disusun AI dari diff commit ini, bukan perintah yang benar-benar diberikan.\n"
    e = {"id": f"git-{h}", "ts": ts, "branch": main, "who": an, "kind": "🤖 sintesis",
         "status": f"✅ sudah di {main} · `{h}`", "convo": [note, "**👤 (sintesis)** " + clean(prompt) + "\n"], "files": {root: files},
         "hasil": hasil.strip()}
    return write(root, [e], an, stage=False)


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else ""
    if mode == "hook":
        inp = json.load(sys.stdin)
        by_root = {}
        first = parse(inp["transcript_path"], live=True)
        cwd_root = git(inp.get("cwd") or os.getcwd(), "rev-parse", "--show-toplevel")
        logged = logged_ids({r for e in first for r in e["files"]} | ({cwd_root} if cwd_root else set()))
        for e in parse(inp["transcript_path"], live=True, logged=logged):
            for root in e["files"]:
                by_root.setdefault(root, []).append(e)
        for root, es in by_root.items():
            for e in es:  # branch saat ini, kecuali sesi dibuka dari repo itu sendiri
                if not e["cwd"].startswith(root):
                    e["branch"] = git(root, "rev-parse", "--abbrev-ref", "HEAD")
            write(root, es, git(root, "config", "user.name") or "?", stage=True)
    elif mode == "precommit":
        precommit(git(sys.argv[2] if len(sys.argv) > 2 else ".", "rev-parse", "--show-toplevel"))
    elif mode in ("backfill", "gap", "sintesis"):
        root = git(sys.argv[2], "rev-parse", "--show-toplevel")
        if not root or not ORG.search(git(root, "remote", "get-url", "origin")):
            sys.exit(f"{sys.argv[2]}: bukan repo PT-Pasifik-Hoki-Indonesia")
        if mode == "gap":
            print("\n".join(gap(root)))
        elif mode == "sintesis":
            print(f"{sintesis(root, sys.argv[3], sys.stdin.read())} entri sintesis ditulis")
        else:
            paths = [p for p in glob.glob(os.path.expanduser("~/.claude/projects/*/*.jsonl")) if root + "/" in open(p, errors="replace").read()]
            es = [e for p in paths for e in parse(p, logged=logged_ids([root])) if root in e["files"]]
            n = write(root, es, git(root, "config", "user.name") or "?", stage=False)
            print(f"{n} entri baru ditulis ke {root}/{FILE} ({len(es)} entri ada di transcript Mac ini)")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as ex:  # hook tidak boleh mengganggu sesi
        print(f"prompts-log: {ex}", file=sys.stderr)
