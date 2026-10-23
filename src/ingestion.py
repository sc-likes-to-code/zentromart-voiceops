"""Knowledge base ingestion and chunking pipeline for ZentroMart VoiceOps."""
import csv
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import KB_DIR, DATA_DIR, SUPERSEDED_RETURNS_POLICY


@dataclass
class DocumentChunk:
    chunk_id: str
    source_file: str
    doc_id: str
    title: str
    doc_type: str
    status: str
    effective_from: str
    section_id: str
    heading: str
    text: str
    is_authoritative: bool = True
    metadata: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "DocumentChunk":
        return cls(**data)



class KnowledgeBaseIngestion:
    """Ingests Markdown KB files and product catalog into structured chunks."""

    def __init__(self, kb_dir: Optional[Path] = None, data_dir: Optional[Path] = None):
        self.kb_dir = Path(kb_dir or KB_DIR)
        self.data_dir = Path(data_dir or DATA_DIR)
        self.ingestion_errors: List[str] = []

    def parse_frontmatter(self, content: str) -> Tuple[Dict[str, str], str]:
        """Parses YAML-like frontmatter enclosed in --- at the start of a markdown file."""
        metadata = {}
        body = content
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm_text = parts[1]
                body = parts[2].strip()
                for line in fm_text.strip().splitlines():
                    if ":" in line:
                        key, val = line.split(":", 1)
                        metadata[key.strip()] = val.strip()
        return metadata, body

    def parse_markdown_sections(
        self,
        source_file: str,
        content: str,
        metadata: Dict[str, str]
    ) -> List[DocumentChunk]:
        """Extracts sections marked with ## [SECTION-ID] and creates structured chunks."""
        chunks: List[DocumentChunk] = []
        doc_id = metadata.get("doc_id", Path(source_file).stem)
        doc_type = metadata.get("doc_type", "document")
        status = metadata.get("status", "current")
        effective_from = metadata.get("effective_from", "")
        title = metadata.get("title", doc_id)
        is_auth = (status == "current" and source_file != SUPERSEDED_RETURNS_POLICY)

        # Split on section headings: ## [SECTION-ID] Heading Title
        pattern = r"^##\s*\[([^\]]+)\]\s*(.+)$"
        lines = content.splitlines()
        
        current_section_id = f"{doc_id}-INTRO"
        current_heading = title
        current_lines: List[str] = []
        section_count = 0

        for line in lines:
            match = re.match(pattern, line)
            if match:
                # Flush previous section if it has non-whitespace content
                prev_text = "\n".join(current_lines).strip()
                if prev_text:
                    cid = f"{source_file}:{current_section_id}:{section_count}"
                    chunk_text = (
                        f"Document: {title} ({source_file})\n"
                        f"Section: [{current_section_id}] {current_heading}\n"
                        f"Status: {status} | Effective: {effective_from}\n\n"
                        f"{prev_text}"
                    )
                    chunks.append(DocumentChunk(
                        chunk_id=cid,
                        source_file=source_file,
                        doc_id=doc_id,
                        title=title,
                        doc_type=doc_type,
                        status=status,
                        effective_from=effective_from,
                        section_id=current_section_id,
                        heading=current_heading,
                        text=chunk_text,
                        is_authoritative=is_auth,
                        metadata={**metadata, "title": title}
                    ))
                    section_count += 1
                current_section_id = match.group(1).strip()
                current_heading = match.group(2).strip()
                current_lines = []
            else:
                current_lines.append(line)

        # Flush final section
        final_text = "\n".join(current_lines).strip()
        if final_text:
            cid = f"{source_file}:{current_section_id}:{section_count}"
            chunk_text = (
                f"Document: {title} ({source_file})\n"
                f"Section: [{current_section_id}] {current_heading}\n"
                f"Status: {status} | Effective: {effective_from}\n\n"
                f"{final_text}"
            )
            chunks.append(DocumentChunk(
                chunk_id=cid,
                source_file=source_file,
                doc_id=doc_id,
                title=title,
                doc_type=doc_type,
                status=status,
                effective_from=effective_from,
                section_id=current_section_id,
                heading=current_heading,
                text=chunk_text,
                is_authoritative=is_auth,
                metadata={**metadata, "title": title}
            ))

        return chunks

    def ingest_kb_documents(self, exclude_superseded: bool = True) -> List[DocumentChunk]:
        """Ingests all markdown documents in the KB directory."""
        all_chunks: List[DocumentChunk] = []
        if not self.kb_dir.exists():
            self.ingestion_errors.append(f"KB directory not found: {self.kb_dir}")
            return all_chunks

        md_files = sorted(self.kb_dir.glob("*.md"))
        for file_path in md_files:
            fname = file_path.name
            try:
                content = file_path.read_text(encoding="utf-8")
                if not content.strip():
                    self.ingestion_errors.append(f"Empty document skipped: {fname}")
                    continue

                metadata, body = self.parse_frontmatter(content)
                status = metadata.get("status", "current")

                # Handle superseded policy exclusion
                if exclude_superseded and (fname == SUPERSEDED_RETURNS_POLICY or status == "superseded"):
                    continue

                chunks = self.parse_markdown_sections(fname, body, metadata)
                all_chunks.extend(chunks)
            except Exception as e:
                self.ingestion_errors.append(f"Error reading {fname}: {e}")

        return all_chunks

    def ingest_product_catalog(self) -> List[DocumentChunk]:
        """Ingests products.csv as catalog reference chunks for product-specific queries."""
        product_chunks: List[DocumentChunk] = []
        products_file = self.data_dir / "products.csv"
        if not products_file.exists():
            self.ingestion_errors.append(f"products.csv not found: {products_file}")
            return product_chunks

        try:
            with open(products_file, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    sku = row["sku"]
                    title = row["title"]
                    brand = row["brand"]
                    category = row["return_category"]
                    price = row["price_inr"]
                    fulfilled = row["fulfilled_by"]
                    assured = "Yes" if row["assured"] == "True" else "No"
                    warranty = row["warranty_months"]
                    desc = row["description"]

                    text = (
                        f"Product Catalog Entry: {sku}\n"
                        f"Title: {title} | Brand: {brand}\n"
                        f"Return Category: {category} | Price: ₹{price}\n"
                        f"Fulfilled by: {fulfilled} | ZentroMart Assured: {assured}\n"
                        f"Brand Warranty: {warranty} months\n"
                        f"Description: {desc}"
                    )

                    chunk = DocumentChunk(
                        chunk_id=f"products.csv:{sku}",
                        source_file="products.csv",
                        doc_id="products.csv",
                        title=title,
                        doc_type="catalog",
                        status="current",
                        effective_from="2026-08-01",
                        section_id=f"products.csv:{sku}",
                        heading=f"Product SKU {sku}: {title}",
                        text=text,
                        is_authoritative=True,
                        metadata={
                            "sku": sku,
                            "title": title,
                            "brand": brand,
                            "return_category": category,
                            "price_inr": price,
                            "warranty_months": warranty,
                            "assured": assured,
                        }
                    )
                    product_chunks.append(chunk)
        except Exception as e:
            self.ingestion_errors.append(f"Error reading products.csv: {e}")

        return product_chunks

    def ingest_all(self, exclude_superseded: bool = True) -> List[DocumentChunk]:
        """Loads and chunks all KB documents and product catalog entries."""
        kb_chunks = self.ingest_kb_documents(exclude_superseded=exclude_superseded)
        prod_chunks = self.ingest_product_catalog()
        return kb_chunks + prod_chunks
