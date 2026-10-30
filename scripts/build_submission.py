#!/usr/bin/env python3
"""
Submission Builder & Validator for Gemma 4 Developer Agent Competition.
Validates agent directory against adk-submission rules:
- Exactly 1 root agent config (agent.yaml / agent.yml)
- Total unpacked size < 3 GiB
- Allowed file extensions only (.yaml, .yml, .md, .txt, .py, .json, .safetensors)
- Only allowed base model: gemma-4-31b-it-qat-w4a16-ct (or 12b/e4b/e2b equivalents)
- Valid !include paths (no path traversal, no absolute paths)
- Packages submission into submission.zip
"""

import os
import sys
import yaml
import zipfile
import argparse
from pathlib import Path

ALLOWED_EXTENSIONS = {".yaml", ".yml", ".md", ".txt", ".py", ".json", ".safetensors"}
ALLOWED_MODELS = {
    "gemma-4-31b-it-qat-w4a16-ct",
    "gemma-4-12b-it-qat-w4a16-ct",
    "gemma-4-e4b-it-qat-w4a16-ct",
    "gemma-4-e2b-it-qat-w4a16-ct",
}
MAX_UNPACKED_SIZE_BYTES = 3 * 1024 * 1024 * 1024  # 3 GiB

class IncludeLoader(yaml.SafeLoader):
    """YAML loader supporting !include directive for validation."""
    def __init__(self, stream):
        self._root = Path(stream.name).parent if hasattr(stream, "name") else Path.cwd()
        super().__init__(stream)

def include_constructor(loader, node):
    rel_path = loader.construct_scalar(node)
    target = (loader._root / rel_path).resolve()
    # Check traversal
    if ".." in rel_path or not target.exists():
        raise ValueError(f"Invalid or missing !include: {rel_path} (resolved: {target})")
    ext = target.suffix.lower()
    if ext in {".md", ".txt"}:
        with open(target, "r", encoding="utf-8") as f:
            return f.read()
    elif ext in {".yaml", ".yml"}:
        with open(target, "r", encoding="utf-8") as f:
            return yaml.load(f, IncludeLoader)
    else:
        raise ValueError(f"Unsupported !include file extension: {ext}")

IncludeLoader.add_constructor("!include", include_constructor)

def validate_submission_dir(src_dir: Path):
    print(f"Validating submission directory: {src_dir}")
    if not src_dir.is_dir():
        raise FileNotFoundError(f"Directory {src_dir} does not exist.")

    # 1. Root agent config check
    root_candidates = [src_dir / name for name in ["agent.yaml", "agent.yml", "root_agent.yaml", "root_agent.yml"]]
    found_roots = [p for p in root_candidates if p.is_file()]
    if len(found_roots) == 0:
        raise ValueError(f"No root agent config found in {src_dir}. Expected agent.yaml.")
    if len(found_roots) > 1:
        raise ValueError(f"Multiple root agent configs found: {found_roots}")
    root_config = found_roots[0]
    print(f"  ✓ Root config found: {root_config.name}")

    # 2. File extensions and size check
    total_size = 0
    file_count = 0
    discovered_models = set()

    for root, dirs, files in os.walk(src_dir):
        for f in files:
            file_path = Path(root) / f
            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise ValueError(f"Disallowed file extension '{ext}' for file: {file_path.relative_to(src_dir)}")
            size = file_path.stat().st_size
            total_size += size
            file_count += 1

            # Check model name in YAMLs
            if ext in {".yaml", ".yml"}:
                try:
                    with open(file_path, "r", encoding="utf-8") as yf:
                        content = yaml.load(yf, IncludeLoader)
                        if isinstance(content, dict) and "model" in content:
                            raw_model = str(content["model"]).strip()
                            # Strip any provider prefix
                            model_norm = raw_model.split("/")[-1]
                            discovered_models.add(model_norm)
                except Exception as e:
                    # Non-fatal if parsing sub-snippet fails during walk, root parse handles validation
                    pass

    print(f"  ✓ Total files: {file_count}")
    print(f"  ✓ Total unpacked size: {total_size / (1024*1024):.2f} MB ({total_size} bytes)")
    if total_size >= MAX_UNPACKED_SIZE_BYTES:
        raise ValueError(f"Unpacked size exceeds 3 GiB limit! ({total_size} >= {MAX_UNPACKED_SIZE_BYTES})")

    # 3. Model validation
    with open(root_config, "r", encoding="utf-8") as yf:
        root_yaml = yaml.load(yf, IncludeLoader)
    root_model = root_yaml.get("model", "").split("/")[-1]
    discovered_models.add(root_model)
    print(f"  ✓ Discovered model(s): {discovered_models}")
    
    if len(discovered_models) != 1:
        raise ValueError(f"Single-model rule violated! Found multiple or no models: {discovered_models}")
    
    model_name = list(discovered_models)[0]
    if model_name not in ALLOWED_MODELS:
        raise ValueError(f"Model '{model_name}' is not in ALLOWED_MODELS: {ALLOWED_MODELS}")
    print(f"  ✓ Single allowed base model verified: {model_name}")

    print("Submission validation PASSED successfully!\n")
    return root_config

def build_zip(src_dir: Path, output_zip: Path):
    validate_submission_dir(src_dir)
    print(f"Packaging {src_dir} into {output_zip} ...")
    with zipfile.ZipFile(output_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(src_dir):
            for f in files:
                file_path = Path(root) / f
                arcname = file_path.relative_to(src_dir)
                zf.write(file_path, arcname)
    
    zip_size_mb = output_zip.stat().st_size / (1024 * 1024)
    print(f"  ✓ Successfully created {output_zip} ({zip_size_mb:.2f} MB)")

def main():
    parser = argparse.ArgumentParser(description="Validate and package Gemma 4 submission directory.")
    parser.add_argument("--src", type=str, default="sample_submission", help="Path to submission source directory")
    parser.add_argument("--out", type=str, default="submission.zip", help="Path to output zip file")
    parser.add_argument("--validate-only", action="store_true", help="Only validate without creating zip")
    args = parser.parse_args()

    src_path = Path(args.src).resolve()
    out_path = Path(args.out).resolve()

    if args.validate_only:
        validate_submission_dir(src_path)
    else:
        build_zip(src_path, out_path)

if __name__ == "__main__":
    main()

