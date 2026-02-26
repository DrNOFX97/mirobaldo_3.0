"""
Generate Q&A pairs for LoRA fine-tuning (Phase 3)
Creates training data from biographies, results, and classifications
"""

import json
import logging
from pathlib import Path
from typing import List, Dict
import re
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

class QAPairGenerator:
    """Generate Q&A pairs for LoRA training"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / "data" / "chatbot_dados"
        self.data_dir = Path(data_dir)
        self.qa_pairs = []

    def extract_name_from_biography(self, text: str) -> str:
        """Extract player name from biography text (markdown header or first line)"""
        # Try markdown header first
        match = re.search(r'#\s+([^:\n]+)', text)
        if match:
            return match.group(1).split(':')[0].strip()
        # Fallback: first non-empty line that looks like a name
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith('#') and len(line) < 80:
                return line.split(':')[0].strip()
        return "Desconhecido"

    def _is_structured_markdown(self, text: str) -> bool:
        """
        Detect if biography is *structured metadata* markdown (vs narrative prose).
        Only classify as structured if it has the player metadata header pattern:
          **DD/MM/YYYY, Place** | **Position**
        Narrative .md files with section headers but no metadata header are treated as prose.
        """
        # Must have the structured birth-date/position metadata line
        has_metadata_header = bool(re.search(
            r'\*{1,2}\d{2}/\d{2}/\d{4}[^*]+\*{1,2}\s*\|',
            text
        ))
        return has_metadata_header

    def _synthesize_from_markdown(self, text: str) -> List[str]:
        """
        Convert structured markdown biography into natural prose paragraphs.
        Handles the common format:
          # Name: Title
          **DD/MM/YYYY, Place** | **Position**
          ## Club: Description (Years)
          - bullet info
          ---
          **Carreira:** ...  **Títulos:** ...
        """
        paragraphs = []

        # ── Extract header metadata ──────────────────────────────────────────
        name = self.extract_name_from_biography(text)

        # Birth date, place, position: **DD/MM/YYYY, Place** | **Position**
        birth_match = re.search(
            r'\*{1,2}(\d{2}/\d{2}/\d{4}),\s*([^*|]+)\*{1,2}\s*\|\s*\*{1,2}([^*\n]+)\*{1,2}',
            text
        )
        birth_str = ""
        if birth_match:
            date, place, position = [x.strip() for x in birth_match.groups()]
            birth_str = f"nasceu a {date} em {place} e foi {position}"

        # ── Extract summary section (after ---) ──────────────────────────────
        summary_section = ""
        if "---" in text:
            summary_section = text.split("---", 1)[-1]

        # Clubs from summary: **Club** (years) or lines after **Clubes:**
        clubs = []
        clubs_match = re.search(r'\*\*Clubes?:\*\*\s*\n?(.*?)(?:\n\n|\*\*[A-Z]|\Z)',
                                 summary_section, re.DOTALL)
        if clubs_match:
            raw = clubs_match.group(1)
            for line in raw.splitlines():
                line = re.sub(r'[*🏆🇧🇷🇵🇹⚽️]', '', line).strip()
                line = line.strip(' -•').strip()
                if line and len(line) > 3:
                    clubs.append(line)

        # Career span: **Carreira:** Years
        career_match = re.search(r'\*\*Carreira:\*\*\s*([^\n]+)', summary_section)
        if career_match:
            career_span = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', career_match.group(1))
            career_span = re.sub(r'\([^)]*\)', '', career_span).strip(' .,')
        else:
            career_span = ""

        # Titles: lines with 🏆 — normalise and deduplicate
        titles_raw = re.findall(r'🏆[^\n]+', text)
        seen_norm, titles = set(), []
        for line in titles_raw:
            line = re.sub(r'[🏆*!🇧🇷🇵🇹⚽️]', '', line)
            line = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', line).strip(' -•')
            norm = re.sub(r'[\s()\-/]', '', line).upper()
            if line and norm not in seen_norm:
                seen_norm.add(norm)
                titles.append(line.strip())

        # ── Build prose paragraphs ────────────────────────────────────────────
        # Paragraph 1: intro
        if birth_str:
            intro = f"{name} {birth_str}."
            if career_span:
                intro += f" A sua carreira decorreu entre {career_span}."
            paragraphs.append(intro)
        elif career_span:
            paragraphs.append(f"{name} teve uma carreira que decorreu entre {career_span}.")

        # Paragraph 2: clubs
        if clubs:
            clubs_clean = [c.split(':')[0].strip() for c in clubs[:8]]
            clubs_str   = ', '.join(clubs_clean)
            paragraphs.append(
                f"Ao longo da sua carreira, representou os seguintes clubes: {clubs_str}."
            )

        # Paragraph 3: titles
        if titles:
            if len(titles) == 1:
                paragraphs.append(f"Conquistou o seguinte título: {titles[0]}.")
            else:
                titles_str = '; '.join(titles[:5])
                paragraphs.append(
                    f"Conquistou {len(titles)} título(s): {titles_str}."
                )

        return paragraphs if paragraphs else []

    def summarize_biography(self, text: str, max_words: int = 300) -> List[str]:
        """
        Extract clean prose from a biography.
        - Prose files (.txt): extracts first paragraphs directly
        - Structured markdown (.md): synthesises prose from metadata
        """
        if self._is_structured_markdown(text):
            return self._synthesize_from_markdown(text)

        # ── Prose extraction ──────────────────────────────────────────────────
        clean = re.sub(r'#{1,6}\s+', '', text)
        clean = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', clean)
        clean = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', clean)
        clean = re.sub(r'^[-*•]\s+', '', clean, flags=re.MULTILINE)
        clean = re.sub(r'<[^>]+>', '', clean)
        clean = re.sub(r'\n{3,}', '\n\n', clean).strip()

        paragraphs = [
            p.strip() for p in clean.split('\n\n')
            # Must be long enough, multi-word, AND contain sentence-ending punctuation
            # (filters out title/header residuals that have no '.' or '!' or '?')
            if len(p.strip()) > 40
            and len(p.strip().split()) >= 8
            and any(c in p for c in '.!?;')
        ]

        result = []
        total_words = 0
        for p in paragraphs:
            words = p.split()
            if total_words + len(words) > max_words:
                remaining = max_words - total_words
                if remaining > 20:
                    result.append(' '.join(words[:remaining]))
                break
            result.append(p)
            total_words += len(words)

        return result

    def generate_biography_questions(self, name: str, bio_text: str) -> List[Dict]:
        """
        Generate Q&A pairs with concise, role-appropriate answers.

        Different question types get different answer depths:
        - "Quem foi?"       → 1 paragraph (who + role + key fact)
        - "Conta-me sobre"  → 2 paragraphs (broader overview)
        - Career/conquest   → 2-3 paragraphs focused on achievements
        """
        system_prompt = (
            "És o Mirobaldo, um assistente virtual especializado na história do "
            "Sporting Clube Farense. Respondes de forma clara e concisa em português "
            "europeu, sem listas excessivas, com base nos factos históricos do clube."
        )

        paragraphs = self.summarize_biography(bio_text, max_words=300)
        if not paragraphs:
            return []

        intro   = paragraphs[0]
        overview = '\n\n'.join(paragraphs[:2])
        detail   = '\n\n'.join(paragraphs[:3])

        qa_map = [
            (f"Quem foi {name}?",                intro),
            (f"Podes apresentar {name}?",         intro),
            (f"Conta-me sobre {name}.",           overview),
            (f"Fala-me de {name}.",               overview),
            (f"Qual foi a carreira de {name}?",   detail),
            (f"O que fez {name} pelo Farense?",   detail),
            (f"Quais foram as conquistas de {name}?", detail),
            (f"Quando jogou {name}?",             overview),
        ]

        pairs = []
        for question, answer in qa_map:
            pairs.append({
                "messages": [
                    {"role": "system",    "content": system_prompt},
                    {"role": "user",      "content": question},
                    {"role": "assistant", "content": answer},
                ]
            })
        return pairs

    def load_biographies(self) -> int:
        """Load and process all biographies"""
        bio_dir = self.data_dir / "biografias"

        if not bio_dir.exists():
            logger.error(f"Biography directory not found: {bio_dir}")
            return 0

        # Find all biography files (recursively)
        all_bio_files = list(bio_dir.rglob("*.txt")) + list(bio_dir.rglob("*.md"))
        logger.info(f"Found {len(all_bio_files)} raw biography files")

        # Read all files and deduplicate by extracted player name.
        # When multiple files reference the same player, keep the source with
        # the most prose content (plain-text characters after stripping markdown).
        def _prose_score(text: str) -> int:
            """Count non-markdown characters as a quality proxy."""
            import re as _re
            stripped = _re.sub(r'[#*_`\[\]\(\)\-|]', '', text)
            return len(stripped.strip())

        # Map: normalised_name → (bio_text, score, file_path)
        best_by_name: dict = {}
        placeholder_markers = ["não disponív", "informações: n/a", "sem informação", "sem dados"]

        for bio_file in all_bio_files:
            try:
                with open(bio_file, 'r', encoding='utf-8') as f:
                    bio_text = f.read().strip()
                if len(bio_text) < 50:
                    continue
                lower = bio_text.lower()
                if any(p in lower for p in placeholder_markers):
                    logger.debug(f"Skipping placeholder: {bio_file.name}")
                    continue
                name = self.extract_name_from_biography(bio_text)
                # Normalise name for deduplication (lowercase, strip punctuation)
                import re as _re
                norm = _re.sub(r'[^a-záàâãéèêíïóôõúüç\s]', '', name.lower()).strip()
                score = _prose_score(bio_text)
                if norm not in best_by_name or score > best_by_name[norm][1]:
                    best_by_name[norm] = (name, score, bio_text)
            except Exception as e:
                logger.warning(f"Error reading {bio_file}: {e}")

        logger.info(f"Found {len(best_by_name)} unique players after deduplication")

        pairs_count = 0

        for norm_name, (name, score, bio_text) in tqdm(best_by_name.items(), desc="Processing biographies"):
            try:
                # Generate Q&A pairs
                pairs = self.generate_biography_questions(name, bio_text)

                # Skip if summarizer produced nothing useful
                if not pairs:
                    continue
                self.qa_pairs.extend(pairs)
                pairs_count += len(pairs)

            except Exception as e:
                logger.warning(f"Error processing {name}: {e}")

        logger.info(f"Generated {pairs_count} Q&A pairs from {len(best_by_name)} unique players")
        return pairs_count

    def generate_results_questions(self) -> int:
        """Generate Q&A pairs from historical results"""
        # TODO: Implement when we understand the results data format
        logger.info("Results Q&A generation: TODO")
        return 0

    def generate_classification_questions(self) -> int:
        """Generate Q&A pairs from classifications"""
        # TODO: Implement when we understand the classification data format
        logger.info("Classification Q&A generation: TODO")
        return 0

    def save_training_data(self, output_file: str = "training_data_lora.jsonl"):
        """Save Q&A pairs in JSONL format for LoRA training"""
        output_path = Path(output_file)

        logger.info(f"Saving {len(self.qa_pairs)} Q&A pairs to {output_path}")

        with open(output_path, 'w', encoding='utf-8') as f:
            for pair in self.qa_pairs:
                f.write(json.dumps(pair, ensure_ascii=False) + '\n')

        logger.info(f"✅ Training data saved: {output_path}")
        logger.info(f"   Total examples: {len(self.qa_pairs)}")

        # Calculate statistics
        total_tokens = 0
        for pair in self.qa_pairs:
            for msg in pair['messages']:
                total_tokens += len(msg['content'].split())

        avg_tokens = total_tokens / len(self.qa_pairs) if self.qa_pairs else 0
        logger.info(f"   Average tokens per example: {avg_tokens:.0f}")
        logger.info(f"   Total tokens: {total_tokens:,}")

        # Show sample
        if self.qa_pairs:
            logger.info("\n📝 Sample Q&A pair:")
            sample = self.qa_pairs[0]
            for msg in sample['messages']:
                role = msg['role'].upper()
                content = msg['content'][:150] + "..." if len(msg['content']) > 150 else msg['content']
                logger.info(f"   {role}: {content}")

    def generate_all(self):
        """Generate all Q&A pairs"""
        logger.info("\n" + "="*60)
        logger.info("GENERATING Q&A PAIRS FOR LORA TRAINING - PHASE 3")
        logger.info("="*60 + "\n")

        # 1. Biographies
        bio_count = self.load_biographies()

        # 2. Results (TODO)
        results_count = self.generate_results_questions()

        # 3. Classifications (TODO)
        class_count = self.generate_classification_questions()

        # Summary
        logger.info("\n" + "="*60)
        logger.info("GENERATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Biographies Q&A pairs: {bio_count}")
        logger.info(f"Results Q&A pairs: {results_count}")
        logger.info(f"Classifications Q&A pairs: {class_count}")
        logger.info(f"TOTAL Q&A pairs: {len(self.qa_pairs)}")

        return len(self.qa_pairs)


def main():
    """Main execution"""
    generator = QAPairGenerator()

    # Generate all Q&A pairs
    total_pairs = generator.generate_all()

    if total_pairs > 0:
        # Save to backend/ directory (same as script location)
        output = Path(__file__).parent / "training_data_lora.jsonl"
        generator.save_training_data(str(output))

        logger.info("\n✅ Phase 3 complete!")
        logger.info(f"   Generated {total_pairs} Q&A pairs ready for LoRA training")
        logger.info("   Next: Phase 4 - Fine-tune Qwen2.5-3B with LoRA")
        return 0
    else:
        logger.error("\n❌ No Q&A pairs generated!")
        return 1


if __name__ == "__main__":
    exit(main())
