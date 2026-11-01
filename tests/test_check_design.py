import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import check_design  # noqa: E402


def _tree(tmp_path, template, css=":root { --a: 1; }"):
    (tmp_path / "static/css").mkdir(parents=True, exist_ok=True)
    (tmp_path / "templates/exports").mkdir(parents=True, exist_ok=True)
    (tmp_path / "static/css/tokens.css").write_text(
        "a { color: #fff; } :root { --ok: 1; }"
    )
    (tmp_path / "static/css/base.css").write_text(css)
    (tmp_path / "templates/x.html").write_text(template)
    return check_design.scan(tmp_path)


def test_flags_each_rule(tmp_path):
    found = _tree(
        tmp_path,
        '<style>a{}</style><div class="row btn" style="color:#abc123;background:rgb(1,2,3)">'
        '<a href="#abc">x</a><i style="width:var(--nope)"></i></div>',
    )
    rules = {r for _, r, _ in found}
    assert rules == {
        "style-block",
        "style-attr",
        "bootstrap-class",
        "hex-color",
        "rgb-color",
        "undefined-var",
    }
    assert (
        "templates/x.html",
        "hex-color",
        "#abc123",
    ) in found  # href="#abc" is an anchor


def test_clean_template_and_exports_pass(tmp_path):
    assert not _tree(tmp_path, '<div class="card" data-x="var(--ok)">{# #fff #}</div>')
    (tmp_path / "templates/exports/d.html").write_text("<style>a{color:#fff}</style>")
    assert not check_design.scan(tmp_path)
    assert not _tree(
        tmp_path, '<div class="row">', css=".row{}"
    )  # defined by project CSS


def test_ratchet_fails_on_new_and_on_fixed_violations(tmp_path, monkeypatch):
    real_scan = check_design.scan
    _tree(tmp_path, '<div style="width:1px">')
    monkeypatch.setattr(check_design, "ALLOWLIST", tmp_path / "allow.txt")
    monkeypatch.setattr(check_design, "scan", lambda: real_scan(tmp_path))
    assert check_design.main([]) == 1  # new violation, empty allow-list
    assert check_design.main(["--write-allowlist"]) == 0
    assert check_design.main([]) == 0
    (tmp_path / "templates/x.html").write_text("<div>")
    assert check_design.main([]) == 1  # fixed: shrink the allow-list
