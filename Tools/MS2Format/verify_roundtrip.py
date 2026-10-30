"""
Round-trip every .ms2 under the given folders through the add-on's own reader and writer.

    python verify_roundtrip.py [folder ...]

Defaults to the two installs below. This is the check that must stay green before any edit to
the writer: it proves the tool reproduces every byte of a file it has not been asked to change.
See notes/project_tvt_ms2_blender_tool_v13_recovered.md.
"""
import glob
import hashlib
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ADDON = os.path.join(HERE, "blender_addon", "ms2_importer")
sys.path.insert(0, ADDON)

import ms2_reader as R          # noqa: E402
import ms2_writer as W          # noqa: E402

DEFAULTS = [r"M:\T34vsTiger\Models", r"M:\TvT_INJECT_SANDBOX\Models"]


def main(folders):
    files = []
    for f in folders:
        files += sorted(glob.glob(os.path.join(f, "**", "*.ms2"), recursive=True))
    print("models found: %d" % len(files))

    ok = ident = differ = rfail = wfail = 0
    nodes_total = 0
    problems = []
    for p in files:
        try:
            nodes = R.read_ms2(p)
        except Exception as ex:
            rfail += 1
            problems.append(("READ", p, ex))
            continue
        ok += 1
        nodes_total += len(nodes)

        tmp = os.path.join(tempfile.gettempdir(), "rt_verify.ms2")
        try:
            W.rewrite(p, tmp, None)
            same = (hashlib.sha256(open(p, "rb").read()).hexdigest()
                    == hashlib.sha256(open(tmp, "rb").read()).hexdigest())
            if same:
                ident += 1
            else:
                differ += 1
                problems.append(("DIFF", p, "round-trip changed bytes"))
        except Exception as ex:
            wfail += 1
            problems.append(("WRITE", p, ex))
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)

    print("parsed        : %d of %d   (%d nodes total)" % (ok, len(files), nodes_total))
    print("round-trip    : %d byte-identical, %d differ" % (ident, differ))
    print("read failures : %d" % rfail)
    print("write failures: %d" % wfail)
    for kind, path, err in problems:
        print("  %-5s %s  %s" % (kind, os.path.basename(path), err))

    bad = rfail + wfail + differ
    print("RESULT:", "PASS" if bad == 0 and ok else "FAIL (%d)" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or DEFAULTS))
