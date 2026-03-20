#!/usr/bin/env python3
"""Download base VM images and build layered test images for integration tests.

Usage:
    python tests/build_test_images.py              # everything (download + build all)
    python tests/build_test_images.py base          # download base images only
    python tests/build_test_images.py overlays      # build overlays only (base must exist)
    python tests/build_test_images.py hello-http    # build just the hello-http overlay
    python tests/build_test_images.py --clean       # remove all overlay images (keeps base)
    python tests/build_test_images.py --clean-all   # remove everything including base images
    python tests/build_test_images.py --list        # list available targets

This script:
  1. Downloads base cloud images into tests/data/ (skips if already present)
  2. Creates thin qcow2 overlay images layered on top of the base, each
     containing only the files needed for a specific test scenario

The overlay images are tiny (a few KB-MB) because qcow2 copy-on-write
layering only stores the delta from the base. This means we can create
many test scenarios without duplicating the full base image.

Requires: python3-libguestfs, curl

Test images created:
  - hello-http.qcow2: Minimal Python HTTP hello-world server on port 80.
    This is the litmus test for the entire vm2micro pipeline. If vm2micro
    can analyze this image and produce a working OpenShift deployment
    (single container, port 80, python3 base image), the core flow works.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable

DATA_DIR = Path(__file__).parent

# Base images to download. Each entry is (filename, url).
BASE_IMAGES = [
    (
        "Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2",
        "https://dl.fedoraproject.org/pub/fedora/linux/releases/43/Cloud/x86_64/images/"
        "Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2",
    ),
]

# Default base image for overlays
DEFAULT_BASE = "Fedora-Cloud-Base-Generic-43-1.6.x86_64.qcow2"

# Registry of overlay builders: name -> (filename, builder_function)
# Populated by @overlay decorator below
OVERLAYS: dict[str, tuple[str, Callable[[], None]]] = {}


def overlay(name: str, filename: str) -> Callable[[Callable[[], None]], Callable[[], None]]:
    """Register an overlay builder function."""

    def decorator(fn: Callable[[], None]) -> Callable[[], None]:
        OVERLAYS[name] = (filename, fn)
        return fn

    return decorator


# ---------------------------------------------------------------------------
# Base image management
# ---------------------------------------------------------------------------


def download_base_images() -> None:
    """Download base images that aren't already present."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for filename, url in BASE_IMAGES:
        dest = DATA_DIR / filename
        if dest.exists():
            size_mb = dest.stat().st_size / 1024 / 1024
            print(f"  [skip] {filename} already exists ({size_mb:.0f}MB)")
            continue

        print(f"  [download] {filename} ...")
        subprocess.run(
            ["curl", "-L", "-o", str(dest), url],
            check=True,
        )
        size_mb = dest.stat().st_size / 1024 / 1024
        print(f"  [done] {filename} ({size_mb:.0f}MB)")


# ---------------------------------------------------------------------------
# Overlay helpers
# ---------------------------------------------------------------------------


def _create_overlay(name: str, base: str = DEFAULT_BASE) -> "guestfs.GuestFS":  # type: ignore[name-defined]  # noqa: F821
    """Create a qcow2 overlay on top of a base image and return a writable GuestFS handle.

    The caller must call g.shutdown() and g.close() when done writing.
    The backing file path is stored as relative (just the filename) so the
    overlay and base must live in the same directory.
    """
    import guestfs

    overlay_path = str(DATA_DIR / name)
    base_path = str(DATA_DIR / base)

    if not os.path.exists(base_path):
        print(f"  [error] Base image not found: {base_path}", file=sys.stderr)
        print("  Run: python tests/build_test_images.py base", file=sys.stderr)
        sys.exit(1)

    # Create overlay with relative backing file reference
    g = guestfs.GuestFS(python_return_dict=True)
    g.disk_create(overlay_path, "qcow2", -1, backingfile=base, backingformat="qcow2")

    # Open it read-write
    g.add_drive(overlay_path)
    g.launch()

    roots = g.inspect_os()
    if not roots:
        g.shutdown()
        g.close()
        print(f"  [error] No OS found in base image: {base}", file=sys.stderr)
        sys.exit(1)

    mp = g.inspect_get_mountpoints(roots[0])
    for mountpoint in sorted(mp.keys(), key=len):
        g.mount(mp[mountpoint], mountpoint)

    return g


def _build_overlay(name: str, filename: str, builder: Callable[[], None]) -> None:
    """Build an overlay if it doesn't already exist."""
    dest = DATA_DIR / filename
    if dest.exists():
        size_kb = dest.stat().st_size / 1024
        print(f"  [skip] {name} ({filename}) already exists ({size_kb:.0f}KB)")
        return

    print(f"  [build] {name} ({filename}) ...")
    builder()
    size_kb = dest.stat().st_size / 1024
    print(f"  [done] {name} ({filename}) ({size_kb:.0f}KB)")


# ---------------------------------------------------------------------------
# Overlay definitions
# ---------------------------------------------------------------------------


@overlay("hello-http", "hello-http.qcow2")
def build_hello_http() -> None:
    """Litmus test: minimal Python HTTP hello-world server on port 80.

    This is the simplest possible vm2micro target. If vm2micro can analyze
    this image and produce a working OpenShift deployment (single container,
    port 80, python3 base image), the core pipeline works end-to-end.

    Contents:
      - /opt/hello/app.py: Python http.server serving "<h1>Hello, World!</h1>"
      - /etc/systemd/system/hello.service: systemd unit running the app

    Expected vm2micro analysis:
      - OS: Fedora 43
      - Service detected: custom systemd unit (hello.service)
      - Stack: Python (python3 in ExecStart)
      - Decomposition: single container
      - Dockerfile: FROM ubi9/python-312, COPY app.py, EXPOSE 80
      - OpenShift: Deployment + Service + Route
    """
    g = _create_overlay("hello-http.qcow2")

    g.mkdir_p("/opt/hello")
    g.write(
        "/opt/hello/app.py",
        (
            "from http.server import HTTPServer, BaseHTTPRequestHandler\n"
            "\n"
            "\n"
            "class Handler(BaseHTTPRequestHandler):\n"
            "    def do_GET(self):\n"
            "        self.send_response(200)\n"
            '        self.send_header("Content-Type", "text/html")\n'
            "        self.end_headers()\n"
            '        self.wfile.write(b"<h1>Hello, World!</h1>")\n'
            "\n"
            "\n"
            'HTTPServer(("0.0.0.0", 80), Handler).serve_forever()\n'
        ),
    )

    g.write(
        "/etc/systemd/system/hello.service",
        (
            "[Unit]\n"
            "Description=Hello World HTTP Server\n"
            "After=network.target\n"
            "\n"
            "[Service]\n"
            "ExecStart=/usr/bin/python3 /opt/hello/app.py\n"
            "Restart=always\n"
            "\n"
            "[Install]\n"
            "WantedBy=multi-user.target\n"
        ),
    )

    g.shutdown()
    g.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def print_summary() -> None:
    """Print sizes of all images in tests/data/."""
    if not DATA_DIR.exists():
        print("  (no tests/data/ directory)")
        return
    images = sorted(DATA_DIR.glob("*.qcow2"))
    if not images:
        print("  (no images)")
        return
    for f in images:
        size = f.stat().st_size
        if size > 1024 * 1024:
            print(f"  {f.name}: {size / 1024 / 1024:.0f}MB")
        else:
            print(f"  {f.name}: {size / 1024:.0f}KB")


def clean_overlays() -> None:
    """Remove all overlay images (keep base images)."""
    base_filenames = {name for name, _ in BASE_IMAGES}
    if not DATA_DIR.exists():
        return
    for f in DATA_DIR.glob("*.qcow2"):
        if f.name not in base_filenames:
            print(f"  [remove] {f.name}")
            f.unlink()


def clean_all() -> None:
    """Remove all images including base images."""
    if not DATA_DIR.exists():
        return
    for f in DATA_DIR.glob("*.qcow2"):
        print(f"  [remove] {f.name}")
        f.unlink()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download base VM images and build layered test images.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "targets",
        nargs="*",
        default=[],
        help="Targets to build: 'base', 'overlays', or specific overlay names. "
        "If none specified, builds everything.",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Remove overlay images (keep base images)",
    )
    parser.add_argument(
        "--clean-all",
        action="store_true",
        help="Remove all images including base",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List available targets",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rebuild overlays even if they already exist",
    )
    args = parser.parse_args()

    if args.list:
        print("Available targets:")
        print("  base       - Download base cloud images")
        print("  overlays   - Build all overlay images")
        for name, (filename, fn) in OVERLAYS.items():
            doc = (fn.__doc__ or "").strip().split("\n")[0]
            print(f"  {name:12s} - {doc} [{filename}]")
        return

    if args.clean_all:
        print("=== Cleaning all images ===")
        clean_all()
        return

    if args.clean:
        print("=== Cleaning overlay images ===")
        clean_overlays()
        return

    targets = args.targets or ["base", "overlays"]

    if "base" in targets:
        print("=== Downloading base images ===")
        download_base_images()

    if "overlays" in targets:
        print("\n=== Building all overlay images ===")
        for name, (filename, builder) in OVERLAYS.items():
            if args.force:
                dest = DATA_DIR / filename
                if dest.exists():
                    dest.unlink()
            _build_overlay(name, filename, builder)
    else:
        # Build specific overlays
        overlay_targets = [t for t in targets if t != "base"]
        if overlay_targets:
            print("\n=== Building selected overlay images ===")
            for target in overlay_targets:
                if target not in OVERLAYS:
                    print(f"  [error] Unknown target: {target}", file=sys.stderr)
                    print(
                        f"  Available: {', '.join(OVERLAYS.keys())}",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                filename, builder = OVERLAYS[target]
                if args.force:
                    dest = DATA_DIR / filename
                    if dest.exists():
                        dest.unlink()
                _build_overlay(target, filename, builder)

    print("\n=== Summary ===")
    print_summary()


if __name__ == "__main__":
    main()
