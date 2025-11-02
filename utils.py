"""
Utility functions for data analysis and validation.
"""
import json
from pathlib import Path
from typing import Dict, Any, List
from collections import Counter


def load_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Load data from JSONL file."""
    data = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def validate_training_example(example: Dict[str, Any]) -> bool:
    """Validate structure of a training example."""
    required_fields = ["task", "instruction", "input", "output", "metadata"]
    
    # Check all required fields present
    for field in required_fields:
        if field not in example:
            return False
    
    # Check non-empty
    if not example["input"] or not example["output"]:
        return False
    
    # Check metadata structure
    metadata = example.get("metadata", {})
    if "issue_key" not in metadata or "project" not in metadata:
        return False
    
    return True


def analyze_dataset(filepath: str) -> Dict[str, Any]:
    """Analyze a training dataset."""
    data = load_jsonl(filepath)
    
    if not data:
        return {"error": "Empty dataset"}
    
    # Basic statistics
    stats = {
        "total_examples": len(data),
        "valid_examples": sum(1 for ex in data if validate_training_example(ex)),
        "tasks": Counter(),
        "projects": Counter(),
        "issue_types": Counter(),
        "priorities": Counter(),
        "input_lengths": [],
        "output_lengths": []
    }
    
    for example in data:
        if not validate_training_example(example):
            continue
        
        stats["tasks"][example["task"]] += 1
        
        metadata = example.get("metadata", {})
        stats["projects"][metadata.get("project", "Unknown")] += 1
        stats["issue_types"][metadata.get("issue_type", "Unknown")] += 1
        stats["priorities"][metadata.get("priority", "Unknown")] += 1
        
        stats["input_lengths"].append(len(example["input"]))
        stats["output_lengths"].append(len(example["output"]))
    
    # Calculate averages
    if stats["input_lengths"]:
        stats["avg_input_length"] = sum(stats["input_lengths"]) / len(stats["input_lengths"])
        stats["avg_output_length"] = sum(stats["output_lengths"]) / len(stats["output_lengths"])
        del stats["input_lengths"]
        del stats["output_lengths"]
    
    # Convert Counters to dicts
    stats["tasks"] = dict(stats["tasks"])
    stats["projects"] = dict(stats["projects"])
    stats["issue_types"] = dict(stats["issue_types"])
    stats["priorities"] = dict(stats["priorities"])
    
    return stats


def print_dataset_summary(filepath: str):
    """Print human-readable dataset summary."""
    stats = analyze_dataset(filepath)
    
    if "error" in stats:
        print(f"Error: {stats['error']}")
        return
    
    print("=" * 60)
    print("DATASET SUMMARY")
    print("=" * 60)
    print(f"File: {filepath}")
    print(f"Total Examples: {stats['total_examples']}")
    print(f"Valid Examples: {stats['valid_examples']}")
    print(f"Avg Input Length: {stats.get('avg_input_length', 0):.0f} chars")
    print(f"Avg Output Length: {stats.get('avg_output_length', 0):.0f} chars")
    print()
    
    print("Task Distribution:")
    for task, count in sorted(stats["tasks"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats["total_examples"]) * 100
        print(f"  {task:30s}: {count:6d} ({percentage:5.1f}%)")
    print()
    
    print("Project Distribution:")
    for project, count in sorted(stats["projects"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats["total_examples"]) * 100
        print(f"  {project:30s}: {count:6d} ({percentage:5.1f}%)")
    print()
    
    print("Issue Type Distribution:")
    for itype, count in sorted(stats["issue_types"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats["total_examples"]) * 100
        print(f"  {itype:30s}: {count:6d} ({percentage:5.1f}%)")
    print()
    
    print("Priority Distribution:")
    for priority, count in sorted(stats["priorities"].items(), key=lambda x: x[1], reverse=True):
        percentage = (count / stats["total_examples"]) * 100
        print(f"  {priority:30s}: {count:6d} ({percentage:5.1f}%)")
    print("=" * 60)


def filter_by_task(input_file: str, output_file: str, task_type: str):
    """Filter dataset by specific task type."""
    data = load_jsonl(input_file)
    filtered = [ex for ex in data if ex.get("task") == task_type]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in filtered:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"Filtered {len(filtered)} examples of type '{task_type}' to {output_file}")


def filter_by_project(input_file: str, output_file: str, project: str):
    """Filter dataset by specific project."""
    data = load_jsonl(input_file)
    filtered = [ex for ex in data if ex.get("metadata", {}).get("project") == project]
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in filtered:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"Filtered {len(filtered)} examples from project '{project}' to {output_file}")


def sample_dataset(input_file: str, output_file: str, n_samples: int, seed: int = 42):
    """Create a random sample of the dataset."""
    import random
    
    data = load_jsonl(input_file)
    random.seed(seed)
    
    if n_samples >= len(data):
        print(f"Warning: Requested {n_samples} samples but dataset only has {len(data)}")
        n_samples = len(data)
    
    sampled = random.sample(data, n_samples)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in sampled:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"Created sample of {n_samples} examples in {output_file}")


def merge_datasets(input_files: List[str], output_file: str):
    """Merge multiple JSONL datasets."""
    all_data = []
    
    for filepath in input_files:
        if Path(filepath).exists():
            data = load_jsonl(filepath)
            all_data.extend(data)
            print(f"Loaded {len(data)} examples from {filepath}")
        else:
            print(f"Warning: {filepath} not found, skipping")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        for example in all_data:
            f.write(json.dumps(example, ensure_ascii=False) + '\n')
    
    print(f"Merged {len(all_data)} total examples to {output_file}")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python utils.py analyze <file>")
        print("  python utils.py filter-task <input> <output> <task>")
        print("  python utils.py filter-project <input> <output> <project>")
        print("  python utils.py sample <input> <output> <n>")
        print("  python utils.py merge <output> <file1> <file2> ...")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "analyze":
        print_dataset_summary(sys.argv[2])
    
    elif command == "filter-task":
        filter_by_task(sys.argv[2], sys.argv[3], sys.argv[4])
    
    elif command == "filter-project":
        filter_by_project(sys.argv[2], sys.argv[3], sys.argv[4])
    
    elif command == "sample":
        sample_dataset(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    
    elif command == "merge":
        merge_datasets(sys.argv[3:], sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
