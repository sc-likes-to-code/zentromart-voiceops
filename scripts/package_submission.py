"""Packaging and verification script for ZentroMart VoiceOps submission ZIP.

Creates a clean submission archive at E:\\MY PROJECTS\\zentromart-voiceops-submission.zip
with explicit file inclusion, secret scanning, integrity checks, and exclusion
of datasets, virtual environments, .git, and cache directories.
"""
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ZIP_DESTINATION = PROJECT_ROOT.parent / "zentromart-voiceops-submission.zip"

# Explicit relative files and directories to include
ROOT_FILES = [
    "README.md",
    ".env.example",
    ".gitignore",
    "requirements.txt",
    "report.pdf",
    "demo.mp4",
]

CODE_DIRS = [
    "src",
    "scripts",
    "tests",
]

EVALUATION_FILES = [
    "outputs/evaluation/baseline_evaluation_results.json",
    "outputs/evaluation/rag_evaluation_results.json",
    "outputs/evaluation/step1_vs_step2_comparison.md",
    "outputs/evaluation/phase1_audit.md",
    "outputs/evaluation/rag_evaluation_summary.md",
    "outputs/evaluation/conversation_evaluation_summary.md",
    "outputs/evaluation/conversation_evaluation_results.json",
    "outputs/evaluation/phase4_voice_summary.md",
]

SAMPLE_VOICE_DIRS = [
    "outputs/sample_outputs/voice/order_inquiry_fixed",
    "outputs/sample_outputs/voice/policy_inquiry",
]

FORBIDDEN_PATTERNS = [
    ".env",
    ".venv",
    ".git",
    "dataset",
    "__pycache__",
    ".pytest_cache",
    ".pyc",
    "outputs/index",
    "report_temp.html",
]

def scan_for_secrets(staging_dir: Path):
    """Scans all staged text files for real API keys."""
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return
    
    secrets = dotenv_values(env_file)
    active_secrets = [v.strip() for v in secrets.values() if v and len(v.strip()) > 8]
    
    for root, _, files in os.walk(staging_dir):
        for f in files:
            fp = Path(root) / f
            if fp.suffix.lower() in [".py", ".md", ".txt", ".json", ".example", ".gitignore"]:
                try:
                    content = fp.read_text(encoding="utf-8", errors="ignore")
                    for s in active_secrets:
                        if s in content:
                            raise ValueError(f"SECRET LEAK DETECTED in staged file: {fp.relative_to(staging_dir)}")
                except Exception as e:
                    if "SECRET LEAK" in str(e):
                        raise

def build_and_verify_zip():
    print("=" * 70)
    print("ZentroMart VoiceOps — Submission ZIP Packaging & Audit")
    print("=" * 70)

    # 1. Verify existence of required root files
    print("\n1. Verifying mandatory root files:")
    for rf in ROOT_FILES:
        path = PROJECT_ROOT / rf
        if not path.exists():
            raise FileNotFoundError(f"Missing mandatory root file: {path}")
        print(f"  [OK] {rf} ({path.stat().st_size:,} bytes)")

    # 2. Stage files in temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        staging = Path(temp_dir) / "zentromart-voiceops"
        staging.mkdir(parents=True, exist_ok=True)
        print(f"\n2. Staging files into temporary directory: {staging}")

        # Copy root files
        for rf in ROOT_FILES:
            shutil.copy2(PROJECT_ROOT / rf, staging / rf)

        # Copy code directories (ignoring pycache and pyc)
        for cd in CODE_DIRS:
            src_dir = PROJECT_ROOT / cd
            dest_dir = staging / cd
            dest_dir.mkdir(parents=True, exist_ok=True)
            for item in src_dir.iterdir():
                if item.name == "__pycache__" or item.suffix == ".pyc":
                    continue
                if item.is_file():
                    shutil.copy2(item, dest_dir / item.name)

        # Copy evaluation files
        for ef in EVALUATION_FILES:
            src_file = PROJECT_ROOT / ef
            if not src_file.exists():
                raise FileNotFoundError(f"Missing evaluation file: {src_file}")
            dest_file = staging / ef
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dest_file)

        # Copy sample voice outputs
        for vd in SAMPLE_VOICE_DIRS:
            src_vdir = PROJECT_ROOT / vd
            dest_vdir = staging / vd
            dest_vdir.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_vdir, dest_vdir)

        # 3. Secret scan on staged files
        print("\n3. Scanning staged files for accidental secret leaks...")
        scan_for_secrets(staging)
        print("  [PASS] Zero secret leaks detected.")

        # 4. Create ZIP archive
        print(f"\n4. Compressing archive to: {ZIP_DESTINATION}")
        if ZIP_DESTINATION.exists():
            ZIP_DESTINATION.unlink()

        total_files = 0
        total_uncompressed_bytes = 0
        with zipfile.ZipFile(ZIP_DESTINATION, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(staging):
                for f in sorted(files):
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(staging)
                    
                    # Safety check for forbidden patterns
                    rel_str = str(rel_path).replace("\\", "/")
                    if rel_str == ".env" or rel_str.startswith(".env/"):
                        raise ValueError(f"Forbidden file detected during archiving: {rel_path}")
                    for bad in FORBIDDEN_PATTERNS:
                        if bad == ".env":
                            continue
                        if bad == rel_str or rel_str.startswith(bad + "/") or ("/" + bad + "/") in rel_str or rel_str.endswith("/" + bad):
                            raise ValueError(f"Forbidden file detected during archiving: {rel_path}")

                    # Use standard ZIP_STORED for MP4 to avoid CPU churn on already compressed video
                    if f.endswith(".mp4"):
                        zf.write(file_path, arcname=str(rel_path), compress_type=zipfile.ZIP_STORED)
                    else:
                        zf.write(file_path, arcname=str(rel_path), compress_type=zipfile.ZIP_DEFLATED)
                    
                    total_files += 1
                    total_uncompressed_bytes += file_path.stat().st_size

        print(f"  [OK] Created {ZIP_DESTINATION.name} ({ZIP_DESTINATION.stat().st_size:,} bytes)")

    # 5. Verify ZIP integrity and contents
    print("\n5. Verifying archive integrity and contents:")
    with zipfile.ZipFile(ZIP_DESTINATION, "r") as zf:
        bad_file = zf.testzip()
        if bad_file:
            raise RuntimeError(f"Corrupt file in ZIP: {bad_file}")
        print("  [PASS] ZIP integrity check passed (CRC32 verified).")

        entries = zf.namelist()
        print(f"  Total archive entries: {len(entries)}")

        # Check for forbidden entries
        for e in entries:
            norm = e.replace("\\", "/")
            if norm == ".env" or norm.startswith(".env/") or "/.env" in norm:
                raise ValueError(f"Found forbidden entry in ZIP: {e}")
            if norm.endswith(".pyc"):
                raise ValueError(f"Found .pyc in ZIP: {e}")
            for forbidden in [".venv", ".git", "dataset", "__pycache__", ".pytest_cache"]:
                if norm == forbidden or norm.startswith(forbidden + "/") or f"/{forbidden}/" in norm:
                    raise ValueError(f"Found forbidden entry in ZIP: {e}")

        print("  [PASS] All forbidden paths (.env, .venv, .git, dataset, caches) confirmed ABSENT.")

        # Check required entries
        expected_keys = [
            "README.md",
            ".env.example",
            "requirements.txt",
            "report.pdf",
            "demo.mp4",
            "src/cli.py",
            "src/agent.py",
            "src/retrieval.py",
            "src/answering.py",
            "src/voice.py",
            "outputs/evaluation/baseline_evaluation_results.json",
            "outputs/evaluation/rag_evaluation_results.json",
            "outputs/evaluation/step1_vs_step2_comparison.md",
            "outputs/sample_outputs/voice/policy_inquiry/turn_01_metadata.json",
            "outputs/sample_outputs/voice/order_inquiry_fixed/turn_03_metadata.json",
        ]
        for ek in expected_keys:
            if ek not in entries:
                raise FileNotFoundError(f"Expected key entry missing from ZIP: {ek}")
            print(f"  [VERIFIED] {ek}")

    print("\n" + "=" * 70)
    print("SUBMISSION ZIP AUDIT COMPLETE: ALL CHECKS PASSED")
    print(f"Destination : {ZIP_DESTINATION}")
    print(f"File Count  : {total_files} files")
    print(f"Uncompressed: {total_uncompressed_bytes / (1024 * 1024):.2f} MB")
    print(f"Archive Size: {ZIP_DESTINATION.stat().st_size / (1024 * 1024):.2f} MB")
    print("=" * 70)
    return True

if __name__ == "__main__":
    try:
        build_and_verify_zip()
    except Exception as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
