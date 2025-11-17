#!/usr/bin/env python3

import json
import hashlib
import zipfile
import sys
import os
import re
import shutil
import platform
from datetime import datetime, timezone
from pathlib import Path

EXTENSION_TYPES = ['theme', 'mapping', 'localization', 'bundle']

ALLOWED_FILE_TYPES = {
    'theme': ['themes'],
    'mapping': ['mappings'],
    'localization': ['resources'],
    'bundle': ['mappings', 'resources', 'themes']
}

REQUIRED_THEME_KEYS = ['lookAndFeelClassName', 'formatString', 'styles', 'textAreaBackground']
REQUIRED_STYLE_KEYS = ['fontName', 'fontStyle', 'fontSize', 'color']

def validate_properties_file(content):
    """Validate .properties file format (basic check)"""
    lines = content.decode('utf-8', errors='ignore').splitlines()
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith('#') or line.startswith('!'):
            continue
        if '=' not in line and ':' not in line:
            return False, f"Line {line_num}: Invalid properties format (missing = or :)"
    return True, None

def validate_mapping_file(data):
    """Validate mapping JSON structure"""
    if not isinstance(data, dict):
        return False, "Mapping must be a JSON object"

    for key in data.keys():
        if not key.isdigit():
            return False, f"Invalid book number key: '{key}' (must be numeric)"

    for book_num, book_data in data.items():
        if isinstance(book_data, list):
            if not all(isinstance(item, str) for item in book_data):
                for item in book_data:
                    if isinstance(item, dict):
                        for lang_code, names in item.items():
                            if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
                                return False, f"Book {book_num}, language {lang_code}: Must be list of strings"
                    else:
                        return False, f"Book {book_num}: All items must be strings or language objects"
        else:
            return False, f"Book {book_num}: Invalid structure"

    return True, None

def validate_theme_file(data):
    """Validate theme JSON structure"""
    if not isinstance(data, dict):
        return False, "Theme must be a JSON object"

    for key in REQUIRED_THEME_KEYS:
        if key not in data:
            return False, f"Missing required key: {key}"

    if not isinstance(data['styles'], dict):
        return False, "'styles' must be an object"

    for style_name, style_data in data['styles'].items():
        if not isinstance(style_data, dict):
            return False, f"Style '{style_name}' must be an object"
        for required_key in REQUIRED_STYLE_KEYS:
            if required_key not in style_data:
                return False, f"Style '{style_name}' missing required key: {required_key}"

    return True, None

def validate_json_file(zip_file, filename, validator_func):
    """Validate a JSON file within the zip"""
    try:
        with zip_file.open(filename) as f:
            data = json.load(f)
            return validator_func(data)
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON in {filename}: {e}"
    except Exception as e:
        return False, f"Error reading {filename}: {e}"

def validate_extension_files(zip_path, manifest):
    """Validate all files declared in manifest"""
    ext_type = manifest.get('type')
    files = manifest.get('files', {})

    errors = []

    with zipfile.ZipFile(zip_path, 'r') as zf:
        zip_contents = set(zf.namelist())

        for mapping_file in files.get('mappings', []):
            # Validate filename pattern
            if not re.match(r'.*_mapping\.json$', mapping_file):
                errors.append(f"Mapping file '{mapping_file}' must follow pattern: *_mapping.json")
                continue

            if mapping_file not in zip_contents:
                errors.append(f"Mapping file not found in zip: {mapping_file}")
            else:
                valid, error = validate_json_file(zf, mapping_file, validate_mapping_file)
                if not valid:
                    errors.append(f"Mapping validation failed for {mapping_file}: {error}")

        for theme_file in files.get('themes', []):
            # Validate filename pattern
            if not theme_file.endswith('.json'):
                errors.append(f"Theme file '{theme_file}' must end with .json")
                continue

            if theme_file not in zip_contents:
                errors.append(f"Theme file not found in zip: {theme_file}")
            else:
                valid, error = validate_json_file(zf, theme_file, validate_theme_file)
                if not valid:
                    errors.append(f"Theme validation failed for {theme_file}: {error}")

        for resource_file in files.get('resources', []):
            # Validate filename pattern
            if not re.match(r'(messages|gui)_[a-z]{2}(_[A-Z]{2})?\.properties$', resource_file):
                errors.append(f"Resource file '{resource_file}' must follow pattern: (messages|gui)_<lang>.properties or (messages|gui)_<lang>_<COUNTRY>.properties")
                continue

            if resource_file not in zip_contents:
                errors.append(f"Resource file not found in zip: {resource_file}")
            elif resource_file.endswith('.properties'):
                try:
                    content = zf.read(resource_file)
                    valid, error = validate_properties_file(content)
                    if not valid:
                        errors.append(f"Properties validation failed for {resource_file}: {error}")
                except Exception as e:
                    errors.append(f"Error reading {resource_file}: {e}")

    return errors

def validate_manifest(manifest):
    """Validate extension manifest structure"""
    required_fields = ['name', 'version', 'type', 'description', 'author', 'files']

    for field in required_fields:
        if field not in manifest:
            return False, f"Missing required field: {field}"

    ext_type = manifest['type']
    if ext_type not in EXTENSION_TYPES:
        return False, f"Invalid type '{ext_type}'. Must be one of: {', '.join(EXTENSION_TYPES)}"

    if not isinstance(manifest['files'], dict):
        return False, "'files' must be an object"

    # Validate language fields for applicable types
    if ext_type in ['localization', 'mapping', 'bundle']:
        if 'languages' in manifest or 'lang_codes' in manifest:
            if 'languages' not in manifest or 'lang_codes' not in manifest:
                return False, "Both 'languages' and 'lang_codes' must be provided together"

            if not isinstance(manifest['languages'], list) or not isinstance(manifest['lang_codes'], list):
                return False, "'languages' and 'lang_codes' must be arrays"

            if len(manifest['languages']) != len(manifest['lang_codes']):
                return False, "'languages' and 'lang_codes' must have the same length"

            if len(manifest['lang_codes']) == 0:
                return False, "'lang_codes' cannot be empty"

            # Validate BCP47 format (basic validation)
            for code in manifest['lang_codes']:
                if not re.match(r'^[a-z]{2,3}(-[A-Z]{2})?(-[a-z]+)?$', code):
                    return False, f"Invalid BCP47 language code: '{code}'"

    allowed_types = ALLOWED_FILE_TYPES[ext_type]
    declared_types = [key for key, value in manifest['files'].items() if value]

    for declared_type in declared_types:
        if declared_type not in allowed_types:
            return False, f"Extension type '{ext_type}' cannot contain '{declared_type}' files. Allowed: {', '.join(allowed_types)}"

    has_required_files = False
    for allowed_type in allowed_types:
        if manifest['files'].get(allowed_type):
            has_required_files = True
            break

    if not has_required_files:
        return False, f"Extension type '{ext_type}' must declare at least one file in: {', '.join(allowed_types)}"

    if not re.match(r'^\d+\.\d+\.\d+$', manifest['version']):
        return False, f"Invalid version format '{manifest['version']}'. Use semver: X.Y.Z"

    return True, None

def extract_manifest(zip_path):
    """Extract manifest.json from zip"""
    try:
        with zipfile.ZipFile(zip_path, 'r') as z:
            if 'manifest.json' not in z.namelist():
                return None, "No manifest.json found in zip"
            with z.open('manifest.json') as f:
                manifest = json.load(f)
                return manifest, None
    except json.JSONDecodeError as e:
        return None, f"Invalid JSON in manifest.json: {e}"
    except Exception as e:
        return None, f"Error reading extension: {e}"

def calculate_sha256(file_path):
    """Calculate SHA-256 checksum"""
    sha256 = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for block in iter(lambda: f.read(4096), b''):
            sha256.update(block)
    return sha256.hexdigest()

def get_file_size(file_path):
    """Get file size in bytes"""
    return os.path.getsize(file_path)

def find_existing_version(registry, name):
    """Find existing extension by name"""
    for ext in registry.get('extensions', []):
        if ext['name'] == name:
            return ext
    return None

def compare_versions(v1, v2):
    """Compare two semver versions. Returns: -1 if v1 < v2, 0 if equal, 1 if v1 > v2"""
    parts1 = [int(x) for x in v1.split('.')]
    parts2 = [int(x) for x in v2.split('.')]

    for p1, p2 in zip(parts1, parts2):
        if p1 < p2:
            return -1
        elif p1 > p2:
            return 1
    return 0

def get_utc_timestamp():
    """Get current UTC timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')

def update_registry(extension_data):
    """Update registry.json with new extension"""
    registry_path = 'registry.json'

    if os.path.exists(registry_path):
        with open(registry_path, 'r') as f:
            registry = json.load(f)
    else:
        registry = {
            "version": "1.0",
            "last_updated": get_utc_timestamp(),
            "extensions": []
        }

    registry['extensions'] = [
        ext for ext in registry['extensions'] 
        if ext['name'] != extension_data['name']
    ]

    registry['extensions'].append(extension_data)
    registry['last_updated'] = get_utc_timestamp()

    registry['extensions'].sort(key=lambda x: x['name'])

    with open(registry_path, 'w') as f:
        json.dump(registry, f, indent=2)

def create_commit_scripts(manifest):
    """Create commit and push scripts for different platforms"""
    os.makedirs('scripts', exist_ok=True)

    commit_message = f"Add extension: {manifest['name']} v{manifest['version']}"

    # Create shell script for Unix-like systems
    sh_content = f"""#!/bin/bash
git add extensions/ registry.json
git commit -m "{commit_message}"
git push
"""

    sh_path = 'scripts/commit-and-push.sh'
    with open(sh_path, 'w', newline='\n') as f:
        f.write(sh_content)

    # Make shell script executable
    os.chmod(sh_path, 0o755)

    # Create batch script for Windows
    cmd_content = f"""@echo off
git add extensions/ registry.json
git commit -m "{commit_message}"
git push
"""

    cmd_path = 'scripts/commit-and-push.cmd'
    with open(cmd_path, 'w', newline='\r\n') as f:
        f.write(cmd_content)

    return sh_path, cmd_path

def publish(zip_path):
    """Main publish function with validation"""
    if not os.path.exists(zip_path):
        print(f"❌ Error: {zip_path} not found")
        return False

    print(f"📦 Publishing {zip_path}...")
    print()

    manifest, error = extract_manifest(zip_path)
    if error:
        print(f"❌ Manifest error: {error}")
        return False

    valid, error = validate_manifest(manifest)
    if not valid:
        print(f"❌ Manifest validation failed: {error}")
        return False

    print(f"✅ Manifest valid")
    print(f"   Name: {manifest['name']}")
    print(f"   Version: {manifest['version']}")
    print(f"   Type: {manifest['type']}")
    print(f"   Author: {manifest['author']}")
    print()

    print("🔍 Validating extension files...")
    file_errors = validate_extension_files(zip_path, manifest)
    if file_errors:
        print("❌ File validation failed:")
        for error in file_errors:
            print(f"   - {error}")
        return False

    print("✅ All files valid")
    print()

    checksum = calculate_sha256(zip_path)
    print(f"🔐 SHA-256: {checksum}")

    size = get_file_size(zip_path)
    print(f"📏 Size: {size:,} bytes ({size/1024:.1f} KB)")
    print()

    if os.path.exists('registry.json'):
        with open('registry.json', 'r') as f:
            registry = json.load(f)
        existing = find_existing_version(registry, manifest['name'])

        if existing:
            comparison = compare_versions(manifest['version'], existing['version'])
            if comparison <= 0:
                print(f"⚠️  Warning: Extension {manifest['name']} v{existing['version']} already exists")
                if comparison == 0:
                    print(f"   New version {manifest['version']} is the same")
                else:
                    print(f"   New version {manifest['version']} is older")

                response = input("   Continue anyway? (y/N): ")
                if response.lower() != 'y':
                    print("❌ Publish cancelled")
                    return False
            else:
                print(f"🔄 Updating {manifest['name']} from v{existing['version']} to v{manifest['version']}")
                old_filename = Path(existing['download_url']).name
                response = input(f"   Remove old version ({old_filename})? (Y/n): ")
                if response.lower() != 'n':
                    old_path = f"extensions/{old_filename}"
                    if os.path.exists(old_path):
                        os.remove(old_path)
                        print(f"   ✅ Removed {old_path}")

    ext_filename = f"{manifest['name']}-{manifest['version']}.zip"
    dest_path = f"extensions/{ext_filename}"

    os.makedirs('extensions', exist_ok=True)

    if os.path.exists(dest_path):
        print(f"⚠️  File already exists: {dest_path}")
        response = input("   Overwrite? (y/N): ")
        if response.lower() != 'y':
            print("❌ Publish cancelled")
            return False

    shutil.copy2(zip_path, dest_path)
    print(f"✅ Copied to: {dest_path}")
    print()

    extension_data = {
        "name": manifest['name'],
        "version": manifest['version'],
        "type": manifest['type'],
        "description": manifest['description'],
        "author": manifest['author'],
        "files": manifest['files'],
        "download_url": f"https://github.com/mybible-cli/mybible-cli-extensions/raw/main/{dest_path}",
        "size": size,
        "sha256": checksum,
        "published_date": get_utc_timestamp()
    }

    # Add language fields if present
    if 'languages' in manifest:
        extension_data['languages'] = manifest['languages']
    if 'lang_codes' in manifest:
        extension_data['lang_codes'] = manifest['lang_codes']

    update_registry(extension_data)
    print("✅ Updated registry.json")
    print()

    # Create commit scripts
    sh_path, cmd_path = create_commit_scripts(manifest)

    print("🎉 Success! To commit and push, run:")
    print()

    current_platform = platform.system()
    if current_platform == "Windows":
        print(f"   {cmd_path}")
    else:
        print(f"   ./{sh_path}")

    return True

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: publish.py <extension.zip>")
        sys.exit(1)

    success = publish(sys.argv[1])
    sys.exit(0 if success else 1)
