#!/usr/bin/env python3
"""wv-editor capture JSON -> pseudo-C# source tree.

Usage: python3 wv2cs.py capture.json [outdir] [--single out.cs]
"""
import json, os, re, sys, collections

# ---------- name helpers ----------

PRIMS = {
    "System.Void": "void", "System.Int32": "int", "System.Single": "float",
    "System.Boolean": "bool", "System.String": "string", "System.Object": "object",
    "System.Double": "double", "System.Int64": "long", "System.Byte": "byte",
    "System.Collections.IEnumerator": "IEnumerator",
}

def short_type(t):
    if t is None:
        return "var"
    t = t.strip()
    if t in PRIMS:
        return PRIMS[t]
    m = re.match(r"^(.*?)`\d+<(.*)>$", t)
    if m:
        base = m.group(1).split(".")[-1]
        inner = ", ".join(short_type(x) for x in split_args(m.group(2)))
        return "%s<%s>" % (base, inner)
    if "<" in t and t.endswith(">"):
        base, inner = t.split("<", 1)
        return "%s<%s>" % (short_type(base), ", ".join(short_type(x) for x in split_args(inner[:-1])))
    return t.split(".")[-1]

def split_args(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "," and depth == 0:
            out.append(cur); cur = ""; continue
        if ch in "<[": depth += 1
        elif ch in ">]": depth -= 1
        cur += ch
    if cur.strip():
        out.append(cur)
    return [x.strip() for x in out]

SIG_RE = re.compile(r"^(?P<ret>[^ ]+) (?P<decl>[^:]+)::(?P<name>[^(]+)\((?P<params>.*)\)$")

def parse_sig(sig):
    """'System.Void NS.T::M(System.Int32)' -> dict."""
    m = SIG_RE.match(sig or "")
    if not m:
        return {"ret": "void", "decl": "", "name": sig or "?", "params": [], "raw": sig}
    return {
        "ret": m.group("ret"),
        "decl": m.group("decl"),
        "name": m.group("name"),
        "params": split_args(m.group("params")),
        "raw": sig,
    }

def is_generated(sig):
    return bool(re.search(r"/<|>d__|<>c__|<>\d", sig or ""))

def decl_short(sig):
    p = parse_sig(sig)
    return "%s.%s" % (p["decl"].split(".")[-1], p["name"])

def method_decl(sig):
    p = parse_sig(sig)
    params = ", ".join("%s %s" % (short_type(t), "p%d" % i) for i, t in enumerate(p["params"]))
    name = p["name"]
    ret = short_type(p["ret"])
    if name == ".ctor":
        return "%s(%s)" % (p["decl"].split(".")[-1], params)
    if name.startswith("get_"):
        return "%s %s { get; }" % (ret, name[4:])
    if name.startswith("set_"):
        return "%s %s { set; }" % (short_type(p["params"][0]) if p["params"] else "var", name[4:])
    return "%s %s(%s)" % (ret, name, params)

# ---------- expression builders ----------

def call_expr(c):
    sig = c.get("target") or ""
    p = parse_sig(sig)
    args = c.get("args")
    args = args if args else ""
    recv = c.get("receiver")
    where = c.get("receiverWhere")
    tname = p["decl"].split(".")[-1]
    name = p["name"]

    if name == ".ctor":
        return "new %s(%s)" % (tname, args)
    if name.startswith("get_"):
        base = recv or (tname if where == "static" else ("this" if where == "this" else tname))
        return "%s.%s" % (base, name[4:])
    if name.startswith("set_"):
        base = recv or (tname if where == "static" else ("this" if where == "this" else tname))
        return "%s.%s = %s" % (base, name[4:], args or "/* ? */")

    if recv:
        base = recv
    elif where == "this":
        base = None            # implicit this
    elif where == "static":
        base = tname
    elif where and where.startswith("arg:"):
        base = "p" + where.split(":")[1]
    else:
        base = tname
    inner = "%s(%s)" % (name, args) if base is None else "%s.%s(%s)" % (base, name, args)
    if short_type(p["ret"]) == "IEnumerator":
        return "StartCoroutine(%s)" % inner
    return inner

def effect_stmt(e):
    k, t, d = e.get("kind"), e.get("target"), e.get("detail")
    val = d if d else "/* ? */"
    if k in ("write", "ui-value", "transform"):
        return "%s = %s;" % (t, val)
    if k == "active-state":
        return "%s.SetActive(%s);" % (t, val)
    if k == "animation":
        return "%s.%s;" % (t, d) if d else "%s.Play();" % t
    if k == "audio":
        return "%s.%s();" % (t, d or "Play")
    if k == "instantiate":
        return "Instantiate(%s);" % t
    if k == "destroy":
        return "Destroy(%s);" % t
    if k == "scene":
        return 'SceneManager.LoadScene("%s");' % t
    if k == "saved":
        return 'Save("%s", %s);' % (t, val)
    return "/* %s %s = %s */" % (k, t, val)

KEY_PHASE = {"down": "GetKeyDown", "up": "GetKeyUp", "held": "GetKey", "hold": "GetKey"}
MOUSE_PHASE = {"down": "GetMouseButtonDown", "up": "GetMouseButtonUp", "held": "GetMouseButton"}

def input_expr(i):
    k = i.get("kind")
    neg = "!" if i.get("absent") else ""
    if k == "key":
        fn = KEY_PHASE.get(i.get("phase"), "GetKey")
        return "%sInput.%s(KeyCode.%s)" % (neg, fn, i.get("control"))
    if k == "mouse":
        fn = MOUSE_PHASE.get(i.get("phase"), "GetMouseButton")
        ctl = i.get("control")
        btn = {"left": 0, "right": 1, "middle": 2}.get(str(ctl).lower(), ctl)
        return "%sInput.%s(%s)" % (neg, fn, btn)
    return "%s/* input:%s %s */" % (neg, k, i.get("control"))

def cond_expr(c):
    if not c:
        return None
    k = c.get("kind")
    if k == "always":
        return None
    if k == "test":
        return "%s %s %s" % (c.get("left"), c.get("operator"), c.get("right"))
    if k in ("every", "either"):
        join = " && " if k == "every" else " || "
        parts = [cond_expr(p) for p in c.get("parts", [])]
        parts = [p for p in parts if p]
        if not parts:
            return None
        return join.join("(%s)" % p if " " in p else p for p in parts)
    if k == "gesture":
        return "/* gesture: %s */" % json.dumps(
            {x: y for x, y in c.items() if x != "kind"}, ensure_ascii=False)
    return "/* %s */" % k

LAMBDA_RE = re.compile(r"<(?P<outer>[^>]+)>b__[\w\d_]+$")

def handler_name(handler):
    if not handler:
        return "?"
    p = parse_sig(handler)
    m = LAMBDA_RE.match(p["name"])
    if m:
        return "() => /* lambda in %s */" % m.group("outer")
    return decl_short(handler)


def handle_stmt(h):
    ch, handler = h.get("channel"), h.get("handler")
    hname = handler_name(handler)
    if ch:
        return "%s.%s(%s);" % (ch, h.get("member") or "AddListener", hname)
    return "yield return new WaitUntil(%s);" % hname

# ---------- body ----------

def build_body(rec):
    """Ordered statements from a record, merged by IL offset."""
    items = []
    for i in rec.get("inputs", []):
        items.append((i.get("offset", 0), 0, "if (%s) { ... }" % input_expr(i)))
    for c in rec.get("calls", []):
        if is_generated(c.get("target")):
            continue
        items.append((c.get("offset", 0), 1, call_expr(c) + ";"))
    for e in rec.get("effects", []):
        items.append((e.get("offset", 0), 2, effect_stmt(e)))
    for h in rec.get("handles", []):
        items.append((h.get("offset", 0), 3, handle_stmt(h)))
    items.sort(key=lambda x: (x[0], x[1]))
    lines = ["%-58s // IL_%04X" % (s, off) for off, _, s in items]
    if rec.get("loopsBackTo") is not None:
        lines.append("goto IL_%04X;                                              // loop" % rec["loopsBackTo"])
    if rec.get("handedOverTo"):
        lines.append("// control handed to %s @ IL_%04X"
                     % (short_type(parse_sig(rec['handedOverTo'] + '()')["decl"]) or rec["handedOverTo"],
                        rec.get("handedOverAt") or 0))
    return lines

def variant_key(rec):
    return (cond_expr(rec.get("condition")), tuple(build_body(rec)))


def first_offset(rec):
    offs = [x.get("offset") for key in ("inputs", "calls", "effects", "handles")
            for x in rec.get(key, []) if x.get("offset") is not None]
    return min(offs) if offs else 1 << 30

# ---------- rendering ----------

def render_method(sig, records, indent="        "):
    out = []
    p = parse_sig(sig)
    trig = sorted({r.get("triggerKind") for r in records if r.get("triggerKind")})
    conf = sorted({r.get("confidence") for r in records if r.get("confidence")})
    gaps = sorted({g for r in records for g in r.get("gaps", [])})
    entries = []
    for r in records:
        for e in [r.get("entry")] + [a.get("entry") for a in r.get("alsoReachedBy", [])]:
            if e and decl_short(e) not in entries:
                entries.append(decl_short(e))
    callers = sorted({c.split("|")[1] + "." + c.split("|")[2]
                      for r in records for c in r.get("calledBy", []) if c.count("|") >= 2})

    for t in trig:
        out.append(indent + "[%s]" % {"lifecycle": "UnityLifecycle", "unity-event": "UnityEvent"}.get(t, t))
    if entries and entries != [decl_short(sig)]:
        out.append(indent + "// reached from: " + ", ".join(entries))
    if callers:
        out.append(indent + "// called by: " + ", ".join(callers))
    meta = []
    if conf:
        meta.append("confidence " + "/".join(conf))
    if gaps:
        meta.append("gaps: " + ", ".join(gaps))
    if meta:
        out.append(indent + "// " + "; ".join(meta))

    out.append(indent + method_decl(sig))
    out.append(indent + "{")

    variants = collections.OrderedDict()
    for r in records:
        variants.setdefault(variant_key(r), []).append(r)
    if len(variants) > 1:  # a state-machine stub adds nothing next to a real body
        nonempty = collections.OrderedDict(
            (k, v) for k, v in variants.items() if k[0] or k[1])
        if nonempty:
            variants = nonempty

    ordered = sorted(variants.items(), key=lambda kv: min(first_offset(r) for r in kv[1]))
    paths_of = lambda recs: sorted(
        {" -> ".join(decl_short(s) for s in r.get("callPath", [])) for r in recs})
    all_paths = {tuple(paths_of(recs)) for _, recs in ordered}

    body = []
    multi = len(ordered) > 1
    show_path = multi and len(all_paths) > 1
    for (cond, lines), recs in ordered:
        blk = []
        if show_path:
            paths = paths_of(recs)
            blk.append("// path: " + " | ".join(paths))
        if cond:
            blk.append("if (%s)" % cond)
            blk.append("{")
            blk += ["    " + l for l in (list(lines) or ["// no observed statements"])]
            blk.append("}")
        else:
            blk += list(lines)
        if not blk:
            blk = ["// no observed statements"]
        body += blk
        if multi:
            body.append("")
    while body and body[-1] == "":
        body.pop()
    out += [indent + "    " + l if l else "" for l in body]
    out.append(indent + "}")
    return out

STATE_MACHINE_RE = re.compile(r"^(?P<owner>[^/]+)/<(?P<outer>[^>]+)>d__\d+$")

def logical_sig(rec, sig_by_name):
    """Fold compiler state machines (<M>d__N::MoveNext) back into method M."""
    sig = rec.get("source") or rec.get("entry")
    p = parse_sig(sig)
    m = STATE_MACHINE_RE.match(p["decl"])
    if not m:
        return sig
    key = (m.group("owner"), m.group("outer"))
    return sig_by_name.get(key, "System.Collections.IEnumerator %s::%s()" % key)


def render_type(type_name, records, extra_header=()):
    ns, _, cls = type_name.rpartition(".")
    sig_by_name = {}
    for r in records:
        sig = r.get("source") or r.get("entry")
        p = parse_sig(sig)
        if not STATE_MACHINE_RE.match(p["decl"]):
            sig_by_name.setdefault((p["decl"], p["name"]), sig)
    by_method = collections.OrderedDict()
    for r in records:
        by_method.setdefault(logical_sig(r, sig_by_name), []).append(r)

    lines = ["// generated from wv-editor capture -- pseudo-C#, not compilable",
             "// evidence-derived: bodies show only observed statements, in IL offset order"]
    lines += list(extra_header)
    lines.append("")
    lines.append("using UnityEngine;")
    lines.append("using UnityEngine.SceneManagement;")
    lines.append("using System.Collections;")
    lines.append("")
    ind = ""
    if ns:
        lines.append("namespace %s" % ns)
        lines.append("{")
        ind = "    "
    lines.append(ind + "class %s : MonoBehaviour" % cls)
    lines.append(ind + "{")
    first = True
    for sig, recs in by_method.items():
        if not first:
            lines.append("")
        first = False
        lines += render_method(sig, recs, indent=ind + "    ")
    lines.append(ind + "}")
    if ns:
        lines.append("}")
    return "\n".join(lines) + "\n"

def render_scene_graph(objects, scenes):
    out = ["// scene object graph -- pseudo-code view of the captured hierarchy", ""]
    by_scene = collections.OrderedDict((s, []) for s in scenes)
    for o in objects:
        by_scene.setdefault(o.get("scene"), []).append(o)
    for scene, objs in by_scene.items():
        out.append("scene %s" % scene)
        out.append("{")
        for o in objs:
            out.append('    GameObject "%s"   // %s%s' % (
                o.get("path"), o.get("selector"), "" if o.get("active", True) else "  [inactive]"))
            out.append("    {")
            for v in o.get("visuals", []):
                out.append("        %s.%s = %s;" % (short_type(v.get("type")), v.get("role"), v.get("value")))
            for comp in o.get("components", []):
                ctype = short_type(comp.get("type"))
                for c in comp.get("calls", []):
                    ev = (c.get("event") or "").lstrip("m_")
                    ev = ev[0].lower() + ev[1:] if ev else "onEvent"
                    out.append("        %s.%s += %s.%s;   // target %s" % (
                        ctype, ev, short_type(c.get("targetType")), c.get("method"), c.get("targetPath")))
                for r in comp.get("refs", []):
                    note = "asset" if r.get("asset") else (r.get("path") or "?")
                    if r.get("carries"):
                        note += " carries " + ", ".join(short_type(c) for c in r["carries"])
                    out.append('        %s %s.%s = "%s";   // %s' % (
                        short_type(r.get("type")), ctype, r.get("field", "?"),
                        r.get("name"), note))
                if not comp.get("calls") and not comp.get("refs"):
                    out.append("        %s;" % ctype)
            out.append("    }")
        out.append("}")
        out.append("")
    return "\n".join(out)

# ---------- main ----------

def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("--")]
    single = "--single" in sys.argv
    src = argv[0]
    outdir = argv[1] if len(argv) > 1 else os.path.splitext(src)[0] + ".cs.d"
    d = json.load(open(src, encoding="utf-8"))

    b = d.get("build", {})
    header = ["// capture=%s schema=%s unity=%s platform=%s backend=%s sdk=%s"
              % (d.get("capture"), d.get("schema"), b.get("unity"), b.get("platform"),
                 b.get("backend"), b.get("sdk"))]

    files = {}
    for tname, recs in d.get("types", {}).items():
        files["%s.cs" % tname] = render_type(tname, recs, header)
    for tname, blob in d.get("unplaced", {}).items():
        extra = list(header) + ["// UNPLACED: no scene object proven to host this type"]
        if blob.get("createdBy"):
            extra.append("// created by: " + ", ".join(blob["createdBy"]))
        files["_unplaced/%s.cs" % tname] = render_type(tname, blob.get("evidence", []), extra)
    scenes = list(d.get("scenes", []))
    persistent = d.get("persistentObjects", []) or []
    for o in persistent:
        if o.get("scene") not in scenes:
            scenes.append(o.get("scene"))
    files["_SceneGraph.cs"] = render_scene_graph(
        list(d.get("objects", [])) + persistent, scenes)

    notes = ["// capture notes", ""] + header + [""]
    notes.append("// scenes: " + ", ".join(d.get("scenes", [])))
    notes.append("// capabilities: " + ", ".join(d.get("capabilities", [])))
    for g in d.get("gaps", []):
        notes.append("// gap: %s" % g)
    files["_Notes.cs"] = "\n".join(notes) + "\n"

    if single:
        path = outdir if outdir.endswith(".cs") else outdir + ".cs"
        with open(path, "w", encoding="utf-8") as f:
            for name in sorted(files):
                f.write("// ===== %s =====\n%s\n" % (name, files[name]))
        print(path)
        return

    for name, text in files.items():
        p = os.path.join(outdir, name)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(text)
    print("%s  (%d files)" % (outdir, len(files)))

if __name__ == "__main__":
    main()
