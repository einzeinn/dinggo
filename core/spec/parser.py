"""Specification parser for Dinggo Product Factory."""
import os
import re
import yaml
from typing import Dict, Any, List, Optional
from core.spec.models import (
    ProductSpec,
    RequirementItem,
    ArchitectureSpec,
    AcceptanceCriteria,
    DinggoConfig,
)


class SpecParser:
    """Parses and validates the structured spec/ directory into a ProductSpec instance."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = os.path.abspath(root_dir)
        self.spec_dir = os.path.join(self.root_dir, "spec")
        self.config_path = os.path.join(self.root_dir, "dinggo.yaml")

    def spec_exists(self) -> bool:
        """Check if spec directory exists and contains files."""
        if not os.path.isdir(self.spec_dir):
            return False
        with os.scandir(self.spec_dir) as it:
            return any(it)

    def has_specs(self) -> bool:
        """Alias for spec_exists."""
        return self.spec_exists()

    def load_config(self) -> DinggoConfig:
        """Load dinggo.yaml configuration if present, otherwise default."""
        if os.path.isfile(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                return DinggoConfig(**data)
            except Exception:
                pass
        return DinggoConfig()

    def parse(self) -> ProductSpec:
        """Parse all specification files into a unified ProductSpec."""
        raw_files: Dict[str, str] = {}
        if not os.path.isdir(self.spec_dir):
            return ProductSpec(name=os.path.basename(self.root_dir), summary="No spec directory found.")

        # Read all markdown/yaml files in spec/
        for filename in sorted(os.listdir(self.spec_dir)):
            file_path = os.path.join(self.spec_dir, filename)
            if os.path.isfile(file_path):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_files[filename] = f.read()
                except Exception:
                    continue

        product_info = self._parse_product_md(raw_files.get("product.md", ""))
        requirements = self._parse_requirements_md(raw_files.get("requirements.md", ""))
        architecture = self._parse_architecture_md(raw_files.get("architecture.md", ""))
        acceptance = self._parse_acceptance_md(raw_files.get("acceptance.md", ""))

        spec = ProductSpec(
            name=product_info.get("name") or os.path.basename(self.root_dir),
            version=product_info.get("version", "0.1.0"),
            summary=product_info.get("summary", ""),
            target_users=product_info.get("target_users", []),
            key_features=product_info.get("key_features", []),
            scope=product_info.get("scope", []),
            requirements=requirements,
            architecture=architecture,
            acceptance_criteria=acceptance,
            ui_spec={"content": raw_files.get("ui.md", "")},
            api_spec={"content": raw_files.get("api.md", "")},
            data_model_spec={"content": raw_files.get("data-model.md", "")},
            raw_files=raw_files
        )
        return spec

    def _parse_product_md(self, content: str) -> Dict[str, Any]:
        """Extract high-level product metadata from product.md."""
        info: Dict[str, Any] = {
            "name": "",
            "version": "0.1.0",
            "summary": "",
            "target_users": [],
            "key_features": [],
            "scope": []
        }
        if not content:
            return info

        # Parse title
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            info["name"] = title_match.group(1).strip()

        # Parse sections
        sections = re.split(r"^##\s+", content, flags=re.MULTILINE)
        for sec in sections:
            sec_lines = sec.strip().splitlines()
            if not sec_lines:
                continue
            header = sec_lines[0].lower()
            body = "\n".join(sec_lines[1:]).strip()

            if "summary" in header or "vision" in header or "overview" in header:
                info["summary"] = body
            elif "target" in header or "user" in header:
                info["target_users"] = [line.lstrip("*-• ").strip() for line in body.splitlines() if line.strip().startswith(("-", "*", "•"))]
            elif "feature" in header:
                info["key_features"] = [line.lstrip("*-• ").strip() for line in body.splitlines() if line.strip().startswith(("-", "*", "•"))]
            elif "scope" in header:
                info["scope"] = [line.lstrip("*-• ").strip() for line in body.splitlines() if line.strip().startswith(("-", "*", "•"))]

        if not info["summary"] and content:
            # Fallback summary: first non-header paragraph
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip() and not p.strip().startswith("#")]
            if paragraphs:
                info["summary"] = paragraphs[0]

        return info

    def _parse_requirements_md(self, content: str) -> List[RequirementItem]:
        """Parse structured requirements from requirements.md (supporting YAML block and Markdown lists)."""
        items: List[RequirementItem] = []
        if not content:
            return items

        # 1. Attempt YAML block extraction (e.g. ```yaml ... ```)
        yaml_blocks = re.findall(r"```(?:yaml|yml)?\s*([\s\S]*?)```", content, re.IGNORECASE)
        for block in yaml_blocks:
            try:
                data = yaml.safe_load(block)
                if isinstance(data, dict) and "requirements" in data and isinstance(data["requirements"], list):
                    for req in data["requirements"]:
                        if isinstance(req, dict) and "id" in req:
                            items.append(RequirementItem(
                                id=str(req.get("id")),
                                title=str(req.get("title") or req.get("id")),
                                description=str(req.get("description", "")),
                                priority=req.get("priority", "medium") if req.get("priority") in ("critical", "high", "medium", "low") else "medium",
                                category=str(req.get("category", "functional")),
                                acceptance_criteria=req.get("acceptance_criteria", []) if isinstance(req.get("acceptance_criteria"), list) else []
                            ))
            except Exception:
                continue

        # 2. Markdown regex extraction for patterns like:
        # ### AUTH-001: User Login or - [ ] **AUTH-001**: Description
        id_pattern = r"(?:###|\-|\*)\s*(?:\[\s*\]\s*)?(?:\*\*)?([A-Z]{2,10}-\d{2,5})(?:\*\*)?[:\s]+([^\n]+)"
        for match in re.finditer(id_pattern, content):
            req_id, desc = match.group(1).strip(), match.group(2).strip()
            # Avoid duplicating IDs already captured via YAML
            if not any(item.id.upper() == req_id.upper() for item in items):
                items.append(RequirementItem(
                    id=req_id,
                    title=desc[:50],
                    description=desc,
                    priority="medium",
                    category="functional"
                ))

        return items

    def _parse_architecture_md(self, content: str) -> ArchitectureSpec:
        """Parse architectural specifications from architecture.md."""
        spec = ArchitectureSpec()
        if not content:
            return spec

        # Try YAML block
        yaml_blocks = re.findall(r"```(?:yaml|yml)?\s*([\s\S]*?)```", content, re.IGNORECASE)
        for block in yaml_blocks:
            try:
                data = yaml.safe_load(block)
                if isinstance(data, dict):
                    return ArchitectureSpec(**data)
            except Exception:
                pass

        # Regex fallback
        framework_match = re.search(r"(?:framework|stack)[:\s]+([^\n]+)", content, re.IGNORECASE)
        if framework_match:
            spec.framework = framework_match.group(1).strip()

        runtime_match = re.search(r"(?:runtime|language)[:\s]+([^\n]+)", content, re.IGNORECASE)
        if runtime_match:
            spec.runtime = runtime_match.group(1).strip()

        db_match = re.search(r"(?:database|db)[:\s]+([^\n]+)", content, re.IGNORECASE)
        if db_match:
            spec.database = db_match.group(1).strip()

        return spec

    def _parse_acceptance_md(self, content: str) -> List[AcceptanceCriteria]:
        """Parse acceptance criteria items from acceptance.md."""
        criteria: List[AcceptanceCriteria] = []
        if not content:
            return criteria

        # Pattern for ACC-001 or criteria bullet points
        pattern = r"(?:###|\-|\*)\s*(?:\[\s*\]\s*)?(?:\*\*)?([A-Z]{2,10}-\d{2,5}|ACC-\d{2,5})?(?:\*\*)?[:\s]*([^\n]+)"
        idx = 1
        for match in re.finditer(pattern, content):
            raw_id, text = match.group(1), match.group(2).strip()
            crit_id = raw_id.strip() if raw_id else f"ACC-{idx:03d}"
            criteria.append(AcceptanceCriteria(
                id=crit_id,
                description=text
            ))
            idx += 1

        return criteria
