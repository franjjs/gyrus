#!/usr/bin/env python3
"""Simple version bumper for semantic versioning with git tagging."""

import re
import subprocess
import sys
from pathlib import Path

PYPROJECT = Path(__file__).parent.parent / "pyproject.toml"

def check_git_status():
    """Verify we're on main branch and repo is clean."""
    try:
        # Check branch
        branch = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            check=True,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        if branch != 'main':
            raise ValueError(f"❌ You must be on 'main' branch (currently on '{branch}')")
        
        # Check for uncommitted changes
        status = subprocess.run(
            ['git', 'status', '--porcelain'],
            check=True,
            capture_output=True,
            text=True
        ).stdout.strip()
        
        if status:
            raise ValueError("❌ Uncommitted changes detected. Commit or stash them first.")
        
        print("✅ Git status OK (on main, clean)")
    except subprocess.CalledProcessError as e:
        raise ValueError(f"Git error: {e}") from e

def parse_version(version_str):
    """Parse version string into (major, minor, patch)."""
    parts = version_str.split('.')
    return tuple(int(p) for p in parts)

def bump_version(version_str, bump_type):
    """Bump version according to type (major, minor, patch)."""
    major, minor, patch = parse_version(version_str)
    
    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

def update_version(bump_type):
    """Update version in pyproject.toml."""
    content = PYPROJECT.read_text()
    
    # Find current version
    match = re.search(r'version = "([^"]+)"', content)
    if not match:
        raise ValueError("Could not find version in pyproject.toml")
    
    current_version = match.group(1)
    new_version = bump_version(current_version, bump_type)
    
    # Update content
    new_content = content.replace(
        f'version = "{current_version}"',
        f'version = "{new_version}"'
    )
    
    # Write back
    PYPROJECT.write_text(new_content)
    
    print(f"✅ Version bumped: {current_version} → {new_version}")
    return new_version

def create_git_tag(version):
    """Create git tag for release."""
    try:
        tag_name = f"v{version}"
        # Commit pyproject.toml
        subprocess.run(['git', 'add', 'pyproject.toml'], check=True, capture_output=True)
        subprocess.run(['git', 'commit', '-m', f'🔖 Release v{version}'], check=True, capture_output=True)
        # Create tag
        subprocess.run(['git', 'tag', '-a', tag_name, '-m', f'Release {version}'], check=True, capture_output=True)
        print(f"✅ Git tag created: {tag_name}")
        print("   Push with: git push origin main --tags")
        return tag_name
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Warning: Could not create git tag: {e}")
        print("   Make sure you're in a git repository and have no uncommitted changes")
        return None

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bump_version.py [major|minor|patch]")
        sys.exit(1)
    
    bump_type = sys.argv[1]
    try:
        check_git_status()
        new_version = update_version(bump_type)
        create_git_tag(new_version)
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


