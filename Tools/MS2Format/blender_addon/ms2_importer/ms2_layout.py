"""ms2_layout.py - where every block of a node lives, for the add-on.

[2026-10-30] ms2_writer knows the GEOMETRY span of each node, which is all a
byte-substitution edit needs. Writing a node whose vertex count CHANGED needs
more: the whole record has to be rebuilt, so every block has to be located and
named. That is what this returns, per node, as byte ranges.

The walk is the same one the standalone inspector in ms2_tool uses; it lives here
too because a Blender add-on has to install on its own and cannot reach outside
its own folder.
"""
import struct

from . import ms2_reader as R


def _cstring(data, o):
    n = struct.unpack_from("<i", data, o)[0]
    if n < 0 or o + 4 + n + 1 > len(data):
        raise ValueError("name length %d at 0x%X is out of range" % (n, o))
    return o + 4 + n + 1


def _plausible(data, o):
    if o == len(data):
        return True
    if o < 0 or o + 5 > len(data):
        return False
    n = struct.unpack_from("<i", data, o)[0]
    if not (0 < n <= 64) or o + 4 + n + 1 > len(data):
        return False
    body = data[o + 4:o + 4 + n]
    return all(32 <= b < 127 for b in body) and data[o + 4 + n] == 0


def _after_040(data, o, vcount, flags, spans):
    if flags & 0x200:
        n = struct.unpack_from("<i", data, o)[0]
        spans["opt 0x200"] = (o, 4 + n * 112)
        o += 4 + n * 112
    if flags & 0x400:
        n = struct.unpack_from("<i", data, o)[0]
        spans["opt 0x400"] = (o, 4 + n * 92)
        o += 4 + n * 92
    if flags & 0x10000:
        n = struct.unpack_from("<i", data, o)[0]
        spans["opt 0x10000"] = (o, 4 + n * 80)
        o += 4 + n * 80
    if flags & 0x4000:
        spans["opt 0x4000"] = (o, 4)
        o += 4
    if flags & 0x40000:
        spans["opt 0x40000"] = (o, vcount * 24)
        o += vcount * 24
    return o


def walk(data):
    """Returns a list of dicts, one per node, in file order. Each has "start",
    "end", "name", "flags", "vcount", "icount", "other_count", "d_count" and a
    "spans" map of label -> (offset, size)."""
    version, node_count = struct.unpack_from("<2i", data, 0)
    if version != 0:
        raise ValueError("format_version %d, not 0" % version)
    nodes = []
    o = 8
    for _ in range(node_count):
        node_start = o
        spans = {}
        o2 = _cstring(data, o)
        spans["name"] = (o, o2 - o)
        o = o2
        spans["bbox min"] = (o, 12)
        spans["bbox max"] = (o + 12, 12)
        spans["bounding sphere"] = (o + 24, 16)
        spans["counts"] = (o + 40, 16)
        _flag, vcount, icount, other_count = struct.unpack_from("<4i", data, o + 40)
        o += 56
        if vcount > 0:
            spans["positions"] = (o, vcount * 12)
            o += vcount * 12
            spans["normals"] = (o, vcount * 12)
            o += vcount * 12
            spans["uvs"] = (o, vcount * 8)
            o += vcount * 8
        if icount > 0:
            spans["indices"] = (o, icount * 2)
            o += icount * 2
        if other_count > 0:
            spans["submesh"] = (o, other_count * 16)
            o += other_count * 16
        spans["node_id"] = (o, 4)
        spans["flags_bitmask"] = (o + 4, 4)
        node_id, flags = struct.unpack_from("<2i", data, o)
        o += 8
        d_raw = struct.unpack_from("<i", data, o)[0]
        d_count = d_raw & 0xFFFF
        spans["d_count"] = (o, 4)
        o += 4
        if d_count > 0:
            spans["anim track"] = (o, d_count * 28)
            o += d_count * 28
        if flags & 0x800:
            spans["opt 0x800"] = (o, vcount * 8)
            o += vcount * 8
        if flags & 0x10:
            spans["opt 0x10"] = (o, vcount * 20)
            o += vcount * 20
        if flags & 0x40:
            n = struct.unpack_from("<i", data, o)[0]
            old_end = o + 4 + n * 52
            new_end = old_end + n * 8
            try:
                old_ok = _plausible(data, _after_040(data, old_end, vcount, flags, {}))
            except struct.error:
                old_ok = False
            try:
                new_ok = _plausible(data, _after_040(data, new_end, vcount, flags, {}))
            except struct.error:
                new_ok = False
            if new_ok or not old_ok:
                spans["opt 0x40"] = (o, 4 + n * 52 + n * 8)
                o = new_end
            else:
                spans["opt 0x40"] = (o, 4 + n * 52)
                o = old_end
        o = _after_040(data, o, vcount, flags, spans)
        nodes.append({"start": node_start, "end": o, "parent": node_id, "flags": flags,
                      "vcount": vcount, "icount": icount, "other_count": other_count,
                      "d_count": d_count, "spans": spans})
    return nodes
