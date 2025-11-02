"""
Data transformer to convert raw Jira data into LLM-ready format.
"""
import json
import re
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging


class DataTransformer:
    """
    Transforms raw Jira data into structured JSONL format suitable for LLM training.
    Creates multiple training examples from each issue (summarization, classification, QnA, etc.)
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Initialize transformer.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
    
    def clean_text(self, text: Optional[str]) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Remove Jira markup
        text = re.sub(r'\{[^}]+\}', '', text)  # Remove {code}, {quote}, etc.
        text = re.sub(r'\[~[^\]]+\]', '', text)  # Remove user mentions
        text = re.sub(r'\[[^\]]*\|[^\]]*\]', '', text)  # Remove links
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()
        
        return text
    
    def extract_metadata(self, issue: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract key metadata from issue.
        
        Args:
            issue: Raw issue data
            
        Returns:
            Extracted metadata
        """
        fields = issue.get("fields", {})
        
        # Safe extraction with defaults
        def safe_get(obj, *keys, default=""):
            for key in keys:
                if isinstance(obj, dict):
                    obj = obj.get(key, default)
                else:
                    return default
            return obj if obj is not None else default
        
        metadata = {
            "issue_key": issue.get("key", ""),
            "issue_id": issue.get("id", ""),
            "project": safe_get(fields, "project", "key"),
            "project_name": safe_get(fields, "project", "name"),
            "issue_type": safe_get(fields, "issuetype", "name"),
            "status": safe_get(fields, "status", "name"),
            "priority": safe_get(fields, "priority", "name"),
            "resolution": safe_get(fields, "resolution", "name"),
            "reporter": safe_get(fields, "reporter", "displayName"),
            "assignee": safe_get(fields, "assignee", "displayName"),
            "created": fields.get("created", ""),
            "updated": fields.get("updated", ""),
            "resolved": fields.get("resolutiondate", ""),
            "labels": fields.get("labels", []),
            "components": [c.get("name", "") for c in fields.get("components", [])],
            "versions": [v.get("name", "") for v in fields.get("versions", [])],
            "fix_versions": [v.get("name", "") for v in fields.get("fixVersions", [])],
        }
        
        return metadata
    
    def extract_content(self, issue: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract text content from issue.
        
        Args:
            issue: Raw issue data
            
        Returns:
            Extracted content (summary, description, comments)
        """
        fields = issue.get("fields", {})
        
        summary = self.clean_text(fields.get("summary", ""))
        description = self.clean_text(fields.get("description", ""))
        
        # Extract comments
        comments = []
        for comment in issue.get("comments_data", []):
            comment_text = self.clean_text(comment.get("body", ""))
            if comment_text:
                comment_author = comment.get("author", {}).get("displayName", "Unknown")
                comment_date = comment.get("created", "")
                comments.append({
                    "author": comment_author,
                    "date": comment_date,
                    "text": comment_text
                })
        
        # Combine all comments into text
        comments_text = "\n\n".join([
            f"[{c['author']} on {c['date']}]: {c['text']}"
            for c in comments
        ])
        
        return {
            "summary": summary,
            "description": description,
            "comments": comments_text,
            "comments_list": comments
        }
    
    def generate_training_examples(self, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generate multiple training examples from a single issue.
        
        Args:
            issue: Raw issue data
            
        Returns:
            List of training examples in different formats
        """
        metadata = self.extract_metadata(issue)
        content = self.extract_content(issue)
        
        examples = []
        
        # Skip if no meaningful content
        if not content["summary"] and not content["description"]:
            return examples
        
        # 1. Issue Summarization Task
        if content["description"]:
            examples.append({
                "task": "summarization",
                "instruction": "Summarize the following software issue in one sentence.",
                "input": content["description"],
                "output": content["summary"],
                "metadata": metadata
            })
        
        # 2. Issue Classification Task
        examples.append({
            "task": "classification",
            "instruction": "Classify the type and priority of this software issue.",
            "input": f"Title: {content['summary']}\n\nDescription: {content['description']}",
            "output": f"Type: {metadata['issue_type']}, Priority: {metadata['priority']}, Status: {metadata['status']}",
            "metadata": metadata
        })
        
        # 3. Question Answering - What is the issue about?
        if content["description"]:
            examples.append({
                "task": "question_answering",
                "instruction": "Answer the question based on the issue details.",
                "input": f"Question: What is this issue about?\n\nIssue: {content['summary']}\n\nDescription: {content['description']}",
                "output": content["description"][:500] + "..." if len(content["description"]) > 500 else content["description"],
                "metadata": metadata
            })
        
        # 4. Resolution Extraction (if resolved)
        if metadata["resolution"] and metadata["resolution"] != "Unresolved":
            resolution_comments = [c for c in content["comments_list"] 
                                  if "fix" in c["text"].lower() or "resolv" in c["text"].lower()]
            if resolution_comments:
                examples.append({
                    "task": "resolution_extraction",
                    "instruction": "Extract how this issue was resolved.",
                    "input": f"Issue: {content['summary']}\n\nComments: {content['comments']}",
                    "output": f"Resolution: {metadata['resolution']}\n\nDetails: {resolution_comments[0]['text'][:300]}",
                    "metadata": metadata
                })
        
        # 5. Technical Discussion Generation
        if len(content["comments_list"]) >= 2:
            examples.append({
                "task": "discussion_summary",
                "instruction": "Summarize the technical discussion in this issue thread.",
                "input": f"Issue: {content['summary']}\n\nDiscussion: {content['comments'][:1000]}",
                "output": f"This issue involves {metadata['issue_type'].lower()} with {len(content['comments_list'])} comments discussing the problem and potential solutions.",
                "metadata": metadata
            })
        
        # 6. Component/Label Prediction
        if metadata["components"] or metadata["labels"]:
            examples.append({
                "task": "component_prediction",
                "instruction": "Predict the relevant components and labels for this issue.",
                "input": f"Title: {content['summary']}\n\nDescription: {content['description'][:500]}",
                "output": f"Components: {', '.join(metadata['components'])}\nLabels: {', '.join(metadata['labels'])}",
                "metadata": metadata
            })
        
        # 7. Full Context Example (for instruction tuning)
        full_context = f"""Issue: {metadata['issue_key']}
Project: {metadata['project_name']}
Type: {metadata['issue_type']}
Priority: {metadata['priority']}
Status: {metadata['status']}

Summary: {content['summary']}

Description: {content['description']}

Comments ({len(content['comments_list'])}):
{content['comments'][:1000]}
"""
        
        examples.append({
            "task": "full_context",
            "instruction": "Analyze this software issue and provide a comprehensive overview.",
            "input": full_context,
            "output": f"This is a {metadata['priority'].lower()} priority {metadata['issue_type'].lower()} in the {metadata['project_name']} project. {content['summary']}",
            "metadata": metadata
        })
        
        return examples
    
    def transform_issue(self, issue: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform a single issue into multiple training examples.
        
        Args:
            issue: Raw issue data
            
        Returns:
            List of transformed training examples
        """
        try:
            examples = self.generate_training_examples(issue)
            return examples
        except Exception as e:
            self.logger.error(f"Error transforming issue {issue.get('key', 'unknown')}: {str(e)}")
            return []
    
    def transform_batch(self, issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform a batch of issues.
        
        Args:
            issues: List of raw issues
            
        Returns:
            List of all training examples
        """
        all_examples = []
        
        for issue in issues:
            examples = self.transform_issue(issue)
            all_examples.extend(examples)
        
        self.logger.info(f"Transformed {len(issues)} issues into {len(all_examples)} training examples")
        
        return all_examples
    
    def save_to_jsonl(self, examples: List[Dict[str, Any]], output_path: str):
        """
        Save training examples to JSONL file.
        
        Args:
            examples: List of training examples
            output_path: Output file path
        """
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                for example in examples:
                    json.dump(example, f, ensure_ascii=False)
                    f.write('\n')
            
            self.logger.info(f"Saved {len(examples)} examples to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Error saving to JSONL: {str(e)}")
            raise
    
    def create_dataset_stats(self, examples: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate statistics about the dataset.
        
        Args:
            examples: List of training examples
            
        Returns:
            Statistics dictionary
        """
        from collections import Counter
        
        stats = {
            "total_examples": len(examples),
            "tasks": Counter([ex["task"] for ex in examples]),
            "projects": Counter([ex["metadata"]["project"] for ex in examples]),
            "issue_types": Counter([ex["metadata"]["issue_type"] for ex in examples]),
            "priorities": Counter([ex["metadata"]["priority"] for ex in examples]),
            "statuses": Counter([ex["metadata"]["status"] for ex in examples]),
        }
        
        return stats
