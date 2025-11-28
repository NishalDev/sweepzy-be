#!/usr/bin/env python3
import os
import sys
import re
import argparse
from importlib import metadata

def parse_requirements(path):
    pkgs = []
    line_re = re.compile(r'^\s*([A-Za-z0-9_\-]+)')
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = line_re.match(line)
            if m:
                pkgs.append(m.group(1))
    return pkgs

def get_dist_location(pkg_name, site_packages):
    try:
        dist = metadata.distribution(pkg_name)
        # dist.locate_file('') gives the root installation location
        return os.path.join(site_packages, pkg_name)
    except metadata.PackageNotFoundError:
        return None

def get_size(path):
    total = 0
    for root, dirs, files in os.walk(path):
        for fn in files:
            fp = os.path.join(root, fn)
            try:
                total += os.path.getsize(fp)
            except OSError:
                pass
    return total

def sizeof_fmt(num, suffix='B'):
    for unit in ['','K','M','G','T']:
        if abs(num) < 1024.0:
            return f"{num:3.1f}{unit}{suffix}"
        num /= 1024.0
    return f"{num:.1f}Y{suffix}"

def main():
    parser = argparse.ArgumentParser(description="Report sizes of installed packages")
    parser.add_argument('--req', default='requirements.txt',
                        help='Path to requirements.txt')
    parser.add_argument('--site-packages', required=True,
                        help='Path to site-packages directory')
    args = parser.parse_args()

    if not os.path.isfile(args.req):
        print(f"❗️ {args.req} not found", file=sys.stderr)
        sys.exit(1)
    if not os.path.isdir(args.site_packages):
        print(f"❗️ site‑packages dir {args.site_packages} not found", file=sys.stderr)
        sys.exit(1)

    pkgs = parse_requirements(args.req)
    results = []
    for pkg in pkgs:
        pkg_path = get_dist_location(pkg, args.site_packages)
        if pkg_path and os.path.exists(pkg_path):
            size = get_size(pkg_path)
            results.append((pkg, size))
        else:
            results.append((pkg, None))

    results.sort(key=lambda x: x[1] or 0, reverse=True)
    print(f"{'Package':<20} {'Size':>10}")
    print("-"*31)
    for pkg, size in results:
        size_str = sizeof_fmt(size) if size is not None else "Not found"
        print(f"{pkg:<20} {size_str:>10}")

if __name__ == "__main__":
    main()
