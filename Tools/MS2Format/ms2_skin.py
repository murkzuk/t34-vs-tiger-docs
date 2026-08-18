"""Extended .ms2 reader that actually READS the two skin-related blocks the
production reader skips by size:

    0x10     per-vertex skin weights   (vertex_count x 20 bytes)
    0x10000  per-joint bind matrices   (4 + count x 80 bytes)

Capture is taken only from the committed parse branch, so the 0x40
old/new-exporter disambiguation cannot double-record (the bug in the first probe).
"""
import struct


def _cstr(data, off):
    n = struct.unpack_from('<i', data, off)[0]
    return data[off + 4:off + 4 + n].decode('ascii', 'replace'), off + 4 + n + 1


def _looks_valid(data, off):
    if off == len(data):
        return True
    if off < 0 or off + 4 > len(data):
        return False
    n = struct.unpack_from('<i', data, off)[0]
    if not (0 < n <= 64) or off + 4 + n + 1 > len(data):
        return False
    c = data[off + 4:off + 4 + n]
    return all(32 <= b < 127 for b in c) and data[off + 4 + n] == 0


def _tail(data, off, vc, fl):
    """Blocks after 0x40, in check order. Returns (end_offset, bind_block)."""
    bind = None
    if fl & 0x200:
        off += 4 + struct.unpack_from('<i', data, off)[0] * 112
    if fl & 0x400:
        off += 4 + struct.unpack_from('<i', data, off)[0] * 92
    if fl & 0x10000:
        h = struct.unpack_from('<i', data, off)[0]
        bind = (off + 4, h)
        off += 4 + h * 80
    if fl & 0x4000:
        off += 4
    if fl & 0x40000:
        off += vc * 12 * 2
    return off, bind


def _tail_safe(data, off, vc, fl):
    try:
        end, bind = _tail(data, off, vc, fl)
    except struct.error:
        return None, None
    if end < 0 or end > len(data):
        return None, None
    return end, bind


def _optional(data, off, vc, fl):
    """Returns (end_offset, skin_offset_or_None, bind_block_or_None)."""
    skin = None
    if fl & 0x800:
        off += vc * 8
    if fl & 0x10:
        skin = off
        off += vc * 20
    if fl & 0x40:
        e = struct.unpack_from('<i', data, off)[0]
        base = off + 4 + e * 52
        new_base = base + e * 2 * 4
        old_end, old_bind = _tail_safe(data, base, vc, fl)
        new_end, new_bind = _tail_safe(data, new_base, vc, fl)
        old_ok = old_end is not None and _looks_valid(data, old_end)
        new_ok = new_end is not None and _looks_valid(data, new_end)
        if new_ok and not old_ok:
            return new_end, skin, new_bind          # committed branch only
        if old_ok and not new_ok:
            return old_end, skin, old_bind
        if new_ok and old_ok:
            return new_end, skin, new_bind
        return (new_end if new_end is not None else new_base), skin, new_bind
    end, bind = _tail(data, off, vc, fl)
    return end, skin, bind


class Node:
    __slots__ = ('name', 'parent', 'flags', 'positions', 'normals', 'uvs',
                 'indices', 'weights', 'joint_idx', 'binds', 'is_empty')


def read(path):
    data = open(path, 'rb').read()
    version, count = struct.unpack_from('<2i', data, 0)
    off = 8
    nodes = []
    for _ in range(count):
        n = Node()
        n.name, off = _cstr(data, off)
        bbmin = struct.unpack_from('<3f', data, off)
        n.is_empty = bbmin[0] > 1e37
        _flag, vc, ic, other = struct.unpack_from('<4i', data, off + 40)
        off += 56
        n.positions = n.normals = n.uvs = ()
        if vc > 0:
            f = struct.unpack_from('<%df' % (vc * 3), data, off)
            n.positions = [f[i:i + 3] for i in range(0, len(f), 3)]
            off += vc * 12
            f = struct.unpack_from('<%df' % (vc * 3), data, off)
            n.normals = [f[i:i + 3] for i in range(0, len(f), 3)]
            off += vc * 12
            f = struct.unpack_from('<%df' % (vc * 2), data, off)
            n.uvs = [f[i:i + 2] for i in range(0, len(f), 2)]
            off += vc * 8
        n.indices = list(struct.unpack_from('<%dH' % ic, data, off)) if ic else []
        off += ic * 2
        off += other * 16
        n.parent, fl = struct.unpack_from('<2i', data, off)
        n.flags = fl
        off += 8
        d = struct.unpack_from('<i', data, off)[0]
        off += 4 + d * 12 + d * 16

        off, skin_off, bind = _optional(data, off, vc, fl)

        n.weights, n.joint_idx, n.binds = [], [], []
        if skin_off is not None:
            for v in range(vc):
                rec = data[skin_off + v * 20: skin_off + v * 20 + 20]
                n.weights.append(struct.unpack_from('<4f', rec, 0))
                n.joint_idx.append(struct.unpack_from('<i', rec, 16)[0])
        if bind is not None:
            boff, h = bind
            for j in range(h):
                r = data[boff + j * 80: boff + j * 80 + 80]
                n.binds.append((struct.unpack_from('<i', r, 0)[0],
                                struct.unpack_from('<16f', r, 4),
                                struct.unpack_from('<3f', r, 68)))
        nodes.append(n)
    return nodes
