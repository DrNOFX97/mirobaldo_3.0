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

    # ── Results helpers ──────────────────────────────────────────────────────

    def _parse_score(self, resultado: str):
        """Return (farense_goals, opponent_goals) or None. Result is always Farense-Opponent."""
        m = re.match(r'^(\d+)-(\d+)$', resultado.strip())
        return (int(m.group(1)), int(m.group(2))) if m else None

    def _comp_short(self, comp_name: str) -> str:
        """Strip year suffix from competition name for cleaner prose."""
        label = re.sub(r'[\s/\-]*(19|20)\d\d[\s/\-]*\d*$', '', comp_name).strip()
        # Strip trailing 2-digit/2-digit season tokens like "35/36", "23/24"
        label = re.sub(r'\s+\d{2}/\d{2}$', '', label).strip()
        # Strip trailing 4-digit years
        label = re.sub(r'\s+(19|20)\d{2}$', '', label).strip()
        return label if label else comp_name

    def _is_top_flight(self, comp_name: str) -> bool:
        """Return True if this competition is the top Portuguese division."""
        cn = comp_name.lower()
        # Check for 'I Divisão' preceded by space/start (not 'II Divisão', 'III Divisão')
        if re.search(r'(?:^|[ a])i divis', cn):
            return True
        return any(kw in cn for kw in [
            'primeira liga', 'liga nos', 'liga portugal betclic',
            'liga portuguesa', 'liga betclic', 'liganos',
        ])

    def _plural(self, n: int, singular: str, plural: str) -> str:
        return f"{n} {singular}" if n == 1 else f"{n} {plural}"

    def _local_str(self, local: str) -> str:
        return "em casa" if local == "Casa" else "fora de casa"

    def _date_pt(self, date_str: str) -> str:
        """Convert YYYY-MM-DD to DD/MM/YYYY."""
        try:
            parts = date_str.split('-')
            return f"{parts[2]}/{parts[1]}/{parts[0]}"
        except Exception:
            return date_str

    def generate_results_questions(self) -> int:
        """Generate Q&A pairs from historical match results (dados_jogos.json)."""
        results_file = self.data_dir.parent / "dados_jogos.json"
        if not results_file.exists():
            logger.warning(f"Results file not found: {results_file}")
            return 0

        with open(results_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        system_prompt = (
            "És o Mirobaldo, um assistente virtual especializado na história do "
            "Sporting Clube Farense. Respondes de forma clara e concisa em português "
            "europeu, com base nos factos históricos do clube."
        )

        pairs = []
        seasons = list(data.keys())

        for season in seasons:
            competitions = data[season]
            if not competitions:
                continue

            all_matches = []
            for comp_name, matches in competitions.items():
                for m in matches:
                    all_matches.append({**m, "_comp": comp_name})

            if not all_matches:
                continue

            # ── Q1: Season overview ────────────────────────────────────────
            comp_summaries = []
            for comp_name, matches in competitions.items():
                if not matches:
                    continue
                wins   = sum(1 for m in matches if m.get('V-E-D') == 'V')
                draws  = sum(1 for m in matches if m.get('V-E-D') == 'E')
                losses = sum(1 for m in matches if m.get('V-E-D') == 'D')
                total  = wins + draws + losses
                comp_summaries.append(
                    f"na {self._comp_short(comp_name)} disputou {self._plural(total, 'jogo', 'jogos')} "
                    f"({wins}V {draws}E {losses}D)"
                )

            if comp_summaries:
                n_comps = len(competitions)
                comps_label = self._plural(n_comps, "competição", "competições")
                overview_answer = (
                    f"Na época {season}, o Farense participou em {comps_label}: "
                    + "; ".join(comp_summaries) + "."
                )
                pairs.append({
                    "messages": [
                        {"role": "system",    "content": system_prompt},
                        {"role": "user",      "content": f"Como foi a época {season} do Farense?"},
                        {"role": "assistant", "content": overview_answer},
                    ]
                })

            # ── Q2: Biggest win of the season ──────────────────────────────
            scored_matches = [
                (m, self._parse_score(m.get('Resultado', '')))
                for m in all_matches
            ]
            wins_scored = [
                (m, score) for m, score in scored_matches
                if score and m.get('V-E-D') == 'V'
            ]
            if wins_scored:
                best_match, best_score = max(
                    wins_scored, key=lambda x: x[1][0] - x[1][1]
                )
                margin = best_score[0] - best_score[1]
                if margin >= 2:  # only mention noteworthy wins
                    score_str = f"{best_score[0]}-{best_score[1]}"
                    pairs.append({
                        "messages": [
                            {"role": "system",    "content": system_prompt},
                            {"role": "user",      "content": f"Qual foi a maior vitória do Farense na época {season}?"},
                            {"role": "assistant", "content": (
                                f"Na época {season}, a maior vitória do Farense foi por {score_str} "
                                f"frente ao {best_match['Equipa']}, a {self._date_pt(best_match['Data'])}, "
                                f"jogando {self._local_str(best_match['Local'])}."
                            )},
                        ]
                    })

            # ── Q3: Biggest loss of the season ─────────────────────────────
            losses_scored = [
                (m, score) for m, score in scored_matches
                if score and m.get('V-E-D') == 'D'
            ]
            if losses_scored:
                worst_match, worst_score = max(
                    losses_scored, key=lambda x: x[1][1] - x[1][0]
                )
                margin = worst_score[1] - worst_score[0]
                if margin >= 3:  # only mention notable defeats
                    score_str = f"{worst_score[0]}-{worst_score[1]}"
                    pairs.append({
                        "messages": [
                            {"role": "system",    "content": system_prompt},
                            {"role": "user",      "content": f"Qual foi a maior derrota do Farense na época {season}?"},
                            {"role": "assistant", "content": (
                                f"Na época {season}, a maior derrota do Farense foi por {score_str} "
                                f"frente ao {worst_match['Equipa']}, a {self._date_pt(worst_match['Data'])}, "
                                f"jogando {self._local_str(worst_match['Local'])}."
                            )},
                        ]
                    })

            # ── Q4: Per-competition record (only for named national competitions) ──
            priority_keywords = [
                'liga', 'divisão', 'primeira', 'segunda', 'i div', 'ii div',
                'ligapro', 'liganos', 'betclic', 'sabseg', 'cabovisão', 'nos '
            ]
            for comp_name, matches in competitions.items():
                if not matches:
                    continue
                comp_lower = comp_name.lower()
                if not any(kw in comp_lower for kw in priority_keywords):
                    continue  # skip cups and regional competitions
                wins   = sum(1 for m in matches if m.get('V-E-D') == 'V')
                draws  = sum(1 for m in matches if m.get('V-E-D') == 'E')
                losses = sum(1 for m in matches if m.get('V-E-D') == 'D')
                total  = wins + draws + losses
                comp_short = self._comp_short(comp_name)
                pairs.append({
                    "messages": [
                        {"role": "system",    "content": system_prompt},
                        {"role": "user",      "content": f"Qual foi o registo do Farense na {comp_short} na época {season}?"},
                        {"role": "assistant", "content": (
                            f"Na {comp_short} da época {season}, o Farense disputou "
                            f"{self._plural(total, 'jogo', 'jogos')}: "
                            f"{self._plural(wins, 'vitória', 'vitórias')}, "
                            f"{self._plural(draws, 'empate', 'empates')} e "
                            f"{self._plural(losses, 'derrota', 'derrotas')}."
                        )},
                    ]
                })

        self.qa_pairs.extend(pairs)
        logger.info(f"Generated {len(pairs)} Q&A pairs from match results ({len(seasons)} seasons)")
        return len(pairs)

    # ── Classification helpers ───────────────────────────────────────────────

    def _parse_classification_file(self, filepath) -> dict | None:
        """
        Parse a per-epoch classification markdown file.
        Returns dict with Farense's row data or None if not parseable.
        """
        try:
            with open(filepath, encoding='utf-8') as f:
                text = f.read()
        except Exception:
            return None

        season = filepath.parent.name  # e.g. "1994-95"

        # Competition name from ### header (first one found)
        comp_match = re.search(r'###\s+(.+)', text)
        comp_name = comp_match.group(1).strip() if comp_match else ""
        # Strip trailing year like "1994/95" or "1994/1995"
        comp_short = re.sub(r'\s+\d{4}/\d{2,4}$', '', comp_name).strip()
        comp_short = re.sub(r'\s+(19|20)\d{2}$', '', comp_short).strip()

        # Find Farense row: | **Pos** | **Farense** 🦁 | Pts | J | V | E | D | GM | GS |
        farense_row = re.search(
            r'\|\s*\*\*(\d+)\*\*\s*\|\s*\*\*Farense[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)',
            text
        )
        if not farense_row:
            return None

        pos, pts, j, v, e, d, gm, gs = [int(x) for x in farense_row.groups()]
        return {
            "season": season,
            "comp_name": comp_name,
            "comp_short": comp_short,
            "pos": pos, "pts": pts, "j": j,
            "v": v, "e": e, "d": d,
            "gm": gm, "gs": gs,
        }

    def _ordinal(self, n: int) -> str:
        return f"{n}º"

    def generate_classification_questions(self) -> int:
        """Generate Q&A pairs from historical league table data."""
        class_dir = self.data_dir / "classificacoes" / "por_epoca"
        essenciais_file = self.data_dir / "classificacoes" / "classificacoes_essenciais.md"

        if not class_dir.exists():
            logger.warning(f"Classification directory not found: {class_dir}")
            return 0

        system_prompt = (
            "És o Mirobaldo, um assistente virtual especializado na história do "
            "Sporting Clube Farense. Respondes de forma clara e concisa em português "
            "europeu, com base nos factos históricos do clube."
        )

        pairs = []

        # ── 1. Per-season data from por_epoca/ files ───────────────────────
        class_files = list(class_dir.rglob("*.md"))
        parsed_seasons = {}  # season → list of dicts (one per competition file)

        for cf in class_files:
            data = self._parse_classification_file(cf)
            if data:
                parsed_seasons.setdefault(data["season"], []).append(data)

        for season in sorted(parsed_seasons):
            season_data = parsed_seasons[season]
            # Use the first (main) competition file per season
            d = season_data[0]
            comp = d["comp_short"]
            pos_str = self._ordinal(d["pos"])

            # Q1: Final standing
            answer_q1 = (
                f"Na época {season}, o Farense ficou em {pos_str} lugar na {comp}, "
                f"com {d['pts']} pontos "
                f"({self._plural(d['v'], 'vitória', 'vitórias')}, "
                f"{self._plural(d['e'], 'empate', 'empates')} e "
                f"{self._plural(d['d'], 'derrota', 'derrotas')} "
                f"em {self._plural(d['j'], 'jogo', 'jogos')})."
            )
            pairs.append({
                "messages": [
                    {"role": "system",    "content": system_prompt},
                    {"role": "user",      "content": f"Em que posição ficou o Farense na época {season}?"},
                    {"role": "assistant", "content": answer_q1},
                ]
            })

            # Q2: Points tally
            answer_q2 = (
                f"Na {comp} da época {season}, o Farense fez {d['pts']} pontos, "
                f"terminando em {pos_str} lugar com "
                f"{d['v']}V {d['e']}E {d['d']}D em {d['j']} jogos "
                f"(marcou {d['gm']} golos, sofreu {d['gs']})."
            )
            pairs.append({
                "messages": [
                    {"role": "system",    "content": system_prompt},
                    {"role": "user",      "content": f"Quantos pontos fez o Farense na época {season}?"},
                    {"role": "assistant", "content": answer_q2},
                ]
            })

        # ── 2. Milestone Q&A from classificacoes_essenciais.md ────────────
        if essenciais_file.exists():
            with open(essenciais_file, encoding='utf-8') as f:
                essenciais = f.read()

            # Parse each ### section
            sections = re.split(r'\n(?=###\s+)', essenciais)
            for section in sections:
                header = re.match(r'###\s+(.+)', section)
                if not header:
                    continue
                full_title = header.group(1).strip()

                # Extract just the season year from titles like "1989/1990 - II DIVISÃO (2º escalão)"
                season_match = re.match(r'(\d{4}/\d{4}|\d{4}-\d{2})', full_title)
                season_label = season_match.group(1) if season_match else full_title

                # Extract key fields
                divisao   = re.search(r'- DIVISÃO:\s*(.+)',        section)
                classif   = re.search(r'- CLASSIFICAÇÃO:\s*(.+)',  section)
                pontos    = re.search(r'- PONTOS:\s*(.+)',         section)
                resultado = re.search(r'- RESULTADO:\s*(.+)',      section)
                treinador = re.search(r'- TREINADOR:\s*(.+)',      section)
                goleador  = re.search(r'- GOLEADOR:\s*(.+)',       section)

                if not (divisao and classif):
                    continue

                div_str     = divisao.group(1).strip()
                classif_str = classif.group(1).strip()
                pts_str     = pontos.group(1).strip()    if pontos    else ""
                result_str  = resultado.group(1).strip() if resultado else ""
                coach_str   = treinador.group(1).strip() if treinador else ""
                scorer_str  = goleador.group(1).strip()  if goleador  else ""

                # Build answer prose
                parts = [f"Na época {season_label}, o Farense competiu na {div_str} e ficou em {classif_str}."]
                if pts_str:
                    parts.append(f"Fez {pts_str}.")
                if result_str:
                    parts.append(f"Resultado: {result_str}.")
                if coach_str:
                    parts.append(f"Treinador: {coach_str}.")
                if scorer_str:
                    parts.append(f"Melhor marcador: {scorer_str}.")
                answer = " ".join(parts)

                # Q: season overview
                pairs.append({
                    "messages": [
                        {"role": "system",    "content": system_prompt},
                        {"role": "user",      "content": f"Como foi a época {season_label} do Farense?"},
                        {"role": "assistant", "content": answer},
                    ]
                })

                # Q: result/outcome of the season (if notable)
                if result_str:
                    pairs.append({
                        "messages": [
                            {"role": "system",    "content": system_prompt},
                            {"role": "user",      "content": f"Qual foi o resultado do Farense na época {season_label}?"},
                            {"role": "assistant", "content": answer},
                        ]
                    })

        # ── 3. Cross-season milestone questions ───────────────────────────
        # Best top-flight finish (only in I Divisão / Primeira Liga)
        top_flight_seasons = [
            (d["season"], d)
            for season_list in parsed_seasons.values()
            for d in season_list
            if self._is_top_flight(d["comp_name"])
        ]
        if top_flight_seasons:
            best = min(top_flight_seasons, key=lambda x: x[1]["pos"])
            s, d = best
            pairs.append({
                "messages": [
                    {"role": "system",    "content": system_prompt},
                    {"role": "user",      "content": "Qual foi a melhor classificação de sempre do Farense?"},
                    {"role": "assistant", "content": (
                        f"A melhor classificação de sempre do Farense foi na época {s}, "
                        f"quando terminou em {self._ordinal(d['pos'])} lugar na {d['comp_short']} "
                        f"com {d['pts']} pontos."
                    )},
                ]
            })

        # Promotions (1st place or 2nd in lower divisions)
        champion_seasons = [
            (d["season"], d)
            for season_list in parsed_seasons.values()
            for d in season_list
            if d["pos"] == 1
        ]
        if champion_seasons:
            titles_str = ", ".join(
                f"{s} ({d['comp_short']})" for s, d in sorted(champion_seasons)
            )
            pairs.append({
                "messages": [
                    {"role": "system",    "content": system_prompt},
                    {"role": "user",      "content": "Em que épocas foi o Farense campeão?"},
                    {"role": "assistant", "content": (
                        f"O Farense terminou em 1º lugar nas seguintes épocas: {titles_str}."
                    )},
                ]
            })

        self.qa_pairs.extend(pairs)
        logger.info(
            f"Generated {len(pairs)} Q&A pairs from classifications "
            f"({len(parsed_seasons)} seasons parsed)"
        )
        return len(pairs)

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
