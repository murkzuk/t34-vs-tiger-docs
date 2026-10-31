"""Map the profiler's hot pages to functions, using decomp/decompiled/*.index (read-only)."""
import bisect, os, re, sys

DEC = r'K:\TvTDeepseek\decomp\decompiled'
HOT = [
    ('Objects.dll', 0x0C1800, '1.64% of all'),
    ('Objects.dll', 0x0C1C00, '1.06% of all'),
    ('Objects.dll', 0x017000, '1.60% of all'),
    ('Objects.dll', 0x002400, '1.52% of all'),
    ('Objects.dll', 0x002800, '0.90% of all'),
    ('Objects.dll', 0x01E400, '0.91% of all'),
    ('Objects.dll', 0x01F800, '0.75% of all'),
    ('Objects.dll', 0x22C800, '0.87% of all'),
    ('Objects.dll', 0x17D800, '0.54% of all'),
    ('Objects.dll', 0x014800, '0.67% of all'),
    ('Engine.dll', 0x253000, '1.54% of all'),
    ('Engine.dll', 0x229000, '1.34% of all'),
    ('Engine.dll', 0x1A8000, 'syscall caller 5.49% of syscall time'),
    ('Controls.dll', 0x0A1000, '1.34% of all'),
    ('Behavior.dll', 0x181000, '1.55% of all'),
    ('Service.dll', 0x0B0000, '1.12% of all'),
]

index = {}
for mod in ('Objects.dll', 'Engine.dll', 'Controls.dll', 'Behavior.dll', 'Service.dll'):
    p = os.path.join(DEC, mod + '.index')
    rows = []
    with open(p, encoding='utf-8', errors='replace') as f:
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) >= 2:
                try:
                    rows.append((int(parts[0], 16), parts[1]))
                except ValueError:
                    pass
    rows.sort()
    index[mod] = ([r[0] for r in rows], rows)

print('%-13s %-8s %-12s %-28s %s' % ('module', 'page', 'VA', 'function', 'weight'))
for mod, page, weight in HOT:
    va = 0x10000000 + page
    addrs, rows = index[mod]
    i = bisect.bisect_right(addrs, va) - 1
    if i < 0:
        print('%-13s +0x%06X  0x%08X  (no function)' % (mod, page, va))
        continue
    size = ''
    fn = rows[i][1]
    if i + 1 < len(rows):
        size = '%d B' % (rows[i + 1][0] - rows[i][0])
    print('%-13s +0x%06X  0x%08X  %-28s %s   %s' % (mod, page, va, fn, weight, size))
    print('               offset inside function: 0x%X' % (va - rows[i][0]))
