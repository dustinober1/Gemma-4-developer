#!/usr/bin/env python3
"""
Deep EDA & Task Characterization for Gemma 4 Developer Agent tasks.jsonl.
Analyzes task complexity, repository distribution, patch size distributions,
and generates a stratified mini-dev split (24 tasks).
"""

import json
import re
from pathlib import Path
from collections import Counter, defaultdict

def parse_patch_details(patch_str: str):
    # Count modified files
    added_files = re.findall(r"^--- /dev/null\n\+\+\+ b/(.*)$", patch_str, re.M)
    modified_files = re.findall(r"^\+\+\+ b/(.*)$", patch_str, re.M)
    
    # Net lines added and deleted
    added_lines = 0
    deleted_lines = 0
    for line in patch_str.splitlines():
        if line.startswith("+") and not line.startswith("+++"):
            added_lines += 1
        elif line.startswith("-") and not line.startswith("---"):
            deleted_lines += 1
            
    return {
        "files_count": len(modified_files),
        "files": modified_files,
        "new_files": added_files,
        "added_lines": added_lines,
        "deleted_lines": deleted_lines,
        "total_lines_changed": added_lines + deleted_lines,
    }

def main():
    tasks_file = Path("tasks.jsonl")
    if not tasks_file.exists():
        print("tasks.jsonl not found!")
        return

    with open(tasks_file, "r") as f:
        tasks = [json.loads(line) for line in f]

    print(f"Loaded {len(tasks)} tasks.")
    
    repo_counts = Counter(t["repo"] for t in tasks)
    print("\n=== Repository Breakdown ===")
    for repo, count in repo_counts.most_common():
        print(f"  {repo:<20}: {count} ({count/len(tasks)*100:.1f}%)")

    task_stats = []
    repo_stats = defaultdict(list)

    for t in tasks:
        patch_info = parse_patch_details(t["patch"])
        test_info = parse_patch_details(t["test_patch"])
        
        stat = {
            "instance_id": t["instance_id"],
            "repo": t["repo"],
            "base_commit": t["base_commit"],
            "patch_files_count": patch_info["files_count"],
            "patch_files": patch_info["files"],
            "patch_added_lines": patch_info["added_lines"],
            "patch_deleted_lines": patch_info["deleted_lines"],
            "patch_total_lines": patch_info["total_lines_changed"],
            "test_files_count": test_info["files_count"],
            "test_added_lines": test_info["added_lines"],
            "problem_len_chars": len(t["problem_statement"]),
            "hints_len_chars": len(t.get("hints_text", "").strip()),
            "touches_docs_src": any("docs_src" in f for f in patch_info["files"]),
            "creates_new_file": len(patch_info["new_files"]) > 0,
        }
        task_stats.append(stat)
        repo_stats[t["repo"]].append(stat)

    print("\n=== Patch Size & File Metrics Across All Tasks ===")
    file_counts = Counter(s["patch_files_count"] for s in task_stats)
    print("Files touched per task:")
    for num_f, count in sorted(file_counts.items()):
        print(f"  {num_f} file(s): {count} tasks ({count/len(task_stats)*100:.1f}%)")

    total_lines = [s["patch_total_lines"] for s in task_stats]
    total_lines.sort()
    n = len(total_lines)
    p25 = total_lines[int(n * 0.25)]
    p50 = total_lines[int(n * 0.50)]
    p75 = total_lines[int(n * 0.75)]
    p90 = total_lines[int(n * 0.90)]
    print(f"\nLines changed per patch (distribution):")
    print(f"  Min: {total_lines[0]}, P25: {p25}, Median: {p50}, P75: {p75}, P90: {p90}, Max: {total_lines[-1]}")

    docs_src_cnt = sum(1 for s in task_stats if s["touches_docs_src"])
    new_files_cnt = sum(1 for s in task_stats if s["creates_new_file"])
    print(f"\nSpecial task categories:")
    print(f"  Modifies docs_src: {docs_src_cnt} ({docs_src_cnt/n*100:.1f}%)")
    print(f"  Creates new file: {new_files_cnt} ({new_files_cnt/n*100:.1f}%)")

    # Stratified Mini-Dev Selection (24 tasks)
    # Stratify by repo proportions:
    # fastapi: 67/129 -> ~12 tasks
    # rich: 48/129 -> ~9 tasks
    # requests: 13/129 -> ~2 tasks
    # httpx: 1/129 -> 1 task
    target_counts = {
        "fastapi/fastapi": 12,
        "Textualize/rich": 9,
        "psf/requests": 2,
        "encode/httpx": 1,
    }

    minidev_ids = set()

    for repo, count in target_counts.items():
        candidates = repo_stats[repo]
        # Sort candidates to pick diverse range: 1-file small, 1-file med, multi-file, docs_src, new_file
        # Sort by total lines changed
        candidates.sort(key=lambda s: s["patch_total_lines"])
        
        selected = []
        if repo == "encode/httpx":
            selected = candidates
        else:
            # Spread selection across quantiles
            step = len(candidates) / count
            for i in range(count):
                idx = min(int(i * step), len(candidates) - 1)
                selected.append(candidates[idx])
        
        for s in selected:
            minidev_ids.add(s["instance_id"])

    print(f"\nSelected {len(minidev_ids)} tasks for stratified mini-dev benchmark.")
    
    # Save mini-dev dataset
    minidev_tasks = [t for t in tasks if t["instance_id"] in minidev_ids]
    with open("data/tasks_minidev.jsonl", "w") as f:
        for t in minidev_tasks:
            f.write(json.dumps(t) + "\n")
    print("Saved mini-dev tasks to data/tasks_minidev.jsonl")

    # Save summary analysis report
    report = {
        "total_tasks": len(tasks),
        "repos": dict(repo_counts),
        "file_distribution": dict(file_counts),
        "lines_percentiles": {"min": total_lines[0], "p25": p25, "median": p50, "p75": p75, "p90": p90, "max": total_lines[-1]},
        "special_categories": {"touches_docs_src": docs_src_cnt, "creates_new_file": new_files_cnt},
        "minidev_instances": list(minidev_ids)
    }
    with open("data/eda_summary.json", "w") as f:
        json.dump(report, f, indent=2)
    print("Saved summary report to data/eda_summary.json")

if __name__ == "__main__":
    main()

