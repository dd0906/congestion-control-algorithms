#!/usr/bin/env python3
"""One-time patch for /root/install-p4-dev.sh inside the FairFlow-Ubuntu2204 WSL
distro: fixes package-name drift for this later Ubuntu 22.04 point release, and
skips FRRouting/Sphinx-docs (not needed for this replication). See
docs/OBSERVATIONS.md for why each change was made.
"""
path = "/root/install-p4-dev.sh"
with open(path) as f:
    content = f.read()

orig = content
content = content.replace("libgc1c2 \\", "libgc1 \\")
content = content.replace("    linux-headers-$KERNEL \\\n", "")
content = content.replace("FRROUTING=true", "FRROUTING=false")
content = content.replace("DOCUMENTATION=true", "DOCUMENTATION=false")

assert content != orig, "no changes were made — patterns did not match"
assert "libgc1c2" not in content
assert "linux-headers-$KERNEL" not in content
assert "FRROUTING=false" in content
assert "DOCUMENTATION=false" in content

with open(path, "w") as f:
    f.write(content)

print("Patched successfully:")
print("  libgc1c2 -> libgc1")
print("  removed linux-headers-$KERNEL line")
print("  FRROUTING=false, DOCUMENTATION=false")
