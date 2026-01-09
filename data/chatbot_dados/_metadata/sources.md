# 📚 Data Sources Documentation

## Overview
This document describes the origins, collection methods, and status of all data in the Sporting Clube Farense repository.

**Last Updated:** 2025-10-31
**Repository Version:** 1.0.0
**Total Data Age Range:** 1913-2025 (112 years of club history)

---

## 1. Match Results (`resultados_completos.md`)

### Origin
- **Source Type:** Historical records + Modern data integration
- **Collection Period:** 1913-2025
- **Primary File:** `/dados/resultados/resultados_completos.md` (188 KB)

### Data Structure
```markdown
# ⚽ Resultados Completos - Sporting Clube Farense

## 📅 Resultados por Época/Competição

### [Season]/[Competition]
- Data: Match date
- Hora: Kick-off time
- Local: Home/Away indicator
- Adversário: Opponent name
- Resultado: Match score (e.g., "2-1")
- V-E-D: Win/Draw/Loss indicator
```

### Coverage
- **Early Era (1913-1929):** Regional tournaments and friendly matches
- **Professional Era (1934+):** National championships and cup competitions
- **Modern Era (1990+):** Complete matches with detailed information
- **Recent (2020+):** Daily updates

### Data Quality
- **Historical accuracy:** High for post-1990 matches, estimated for early years
- **Completeness:** ~99% of official records
- **Last Updated:** 2025-10-31
- **Format:** Markdown with emoji indicators for quick visual reference

### Used By
- `EpocaDetalhadaAgent`: Extracts season-specific results
- `ResultadosAgent`: Queries specific match information
- `epocasCompletoAgent`: Provides complete season overviews

---

## 2. League Classifications (`classificacoes_completas.md`)

### Origin
- **Source Type:** Official league records + compiled season tables
- **Collection Period:** 1913-2025
- **Primary File:** `/dados/classificacoes/classificacoes_completas.md` (83 KB)

### Data Structure
```markdown
# 🏆 Classificações - Sporting Clube Farense

### Época [Year]/[Competition]
| Posição | Pts | J | V | E | D | GM | GS | DG |
|---------|-----|---|---|---|---|----|----|-----|
| 1       | 52  | 24| 18| 4 | 2 | 45 | 15 | +30 |
```

### Coverage
- **Leagues Tracked:** Primeira Divisão, Segunda Divisão, Divisões Regionais
- **Competitions:** Campeonato Nacional, Taça de Portugal, Regional Cups
- **Time Period:** 112 years of standing records

### Data Quality
- **Official Status:** Confirmed with official league sources
- **Completeness:** 100% for top-tier competitions, 85% for regional
- **Last Updated:** 2025-10-30

### Used By
- `EpocaDetalhadaAgent`: Provides final standings for season queries
- `epocasCompletoAgent`: Comprehensive season classifications

---

## 3. Photographs (`fotografias/`)

### Organization
```
fotografias/
├── equipas/          (16 team squad photos)
│   ├── 1939-40.webp
│   ├── 1990-91.webp
│   └── 2024-25.webp
├── jogadores/        (32 player photos)
│   ├── Antonio_Gago.webp
│   ├── Hassan_Nader.webp
│   └── [30 others]
└── presidentes/      (3 president/board photos)
    ├── Francisco_Tavares_Bello.webp
    └── [2 others]
```

### Source Information
- **Team Photos:** Club archives, newspaper archives, official records
- **Player Photos:** Official player cards, newspaper archives, club records
- **President Photos:** Official portraits, historical documentation
- **Format Migration:** Recently converted to WebP for optimization

### Image Quality
- **Resolution:** 1200x800px (standard) to 2000x1500px (high quality)
- **Format:** WebP (primary) with PNG backups
- **Total Size:** ~750 MB
- **Completeness:** 100% for modern era (1990+), 60% for earlier periods

### Synchronization Status
- **Last Sync:** 2025-10-31 (Photo consolidation completed)
- **Source of Truth:** `/dados/fotografias/` (replicated to `/public/fotografias/` during build)
- **Status:** COMPLETE_AND_SYNCED

### Used By
- `EpocaDetalhadaAgent`: Displays team photo when querying season results
- Agent-based queries for player information
- Frontend image serving via CDN

---

## 4. Biographies (`biografias/`)

### Organization
```
biografias/
├── jogadores/              (150+ player biographies)
│   ├── historia_joao_gralho.md
│   ├── historia_hassan_nader.md
│   └── [150 others]
├── presidentes/            (2 president biographies)
│   └── historia_francisco_tavares_bello.md
├── outras_figuras/         (1 other figure)
│   └── historia_miguel_cruz.md
└── [DEPRECATED - Root bio files]
    ├── bio_antonio_gago.txt (should be deleted)
    ├── bio_hassan_nader.json (should be deleted)
    └── bio_joao_gralho.txt (should be deleted)
```

### Source Information
- **Player Bios:** Club archives, newspaper interviews, official records
- **President Bios:** Official club history, board records, public documentation
- **Format History:** Originally mixed TXT/JSON, migrated to Markdown

### Data Quality Status ⚠️
- **Current Status:** NEEDS_CONSOLIDATION
- **Format Inconsistency:** Mix of .md, .txt, and .json files
- **Duplicate Entries:** Some players have multiple versions
- **Naming Convention:** Mostly follows `historia_[name_lowercase].md`

### Known Issues
1. Root biography files (`bio_*.txt/json`) should be moved to subdirectories
2. Some duplicates exist (e.g., `bio_antonio_gago_formatado.md`)
3. Inconsistent metadata structure between files
4. Missing standardized fields (birth date, career timeline, etc.)

### Used By
- Biography lookup agents
- Player detail pages
- Historical context generation

---

## 5. Player Registry (`jogadores/`)

### Organization
```
jogadores/
├── por_posição/         (Players organized by position)
├── por_época/           (Players organized by season)
└── histórico/           (Historical player records)
```

### Coverage
- **Total Players:** 500+ registered across all seasons
- **Information Tracked:** Name, position, seasons active, statistics
- **Format:** Mixed JSON and Markdown

### Data Quality
- **Status:** PARTIALLY_ORGANIZED
- **Completeness:** 70% for modern era, 30% for historical

---

## 6. Other Data (`outros/`)

### Subdirectories
- **treinadores/:** Coach and manager records (minimal data)
- **arbitros/:** Referee and official information (minimal data)
- **curiosidades/:** Historical facts and trivia (limited scope)

### Status
- **Current State:** SPARSE
- **Recommendation:** Expand if relevant to chatbot queries

---

## 7. Extended History (`historia/`)

### Content
- Long-form historical narratives about club evolution
- Major milestones and achievements
- Notable seasons and memorable moments

### Coverage
- **Files:** 8 documents
- **Format:** Markdown and JSON
- **Status:** BASIC

---

## Data Flow Architecture

```
┌─────────────────────────────────────────────────────────┐
│          SOURCE DATA (dados/)                           │
│  - resultados_completos.md                              │
│  - classificacoes_completas.md                          │
│  - fotografias/ (51 images)                             │
│  - biografias/ (150+ biographies)                       │
│  - jogadores/ (player registry)                         │
└─────────────────────────────────────────────────────────┘
                    ↓
        [npm run build process]
                    ↓
┌─────────────────────────────────────────────────────────┐
│       BUILD OUTPUT (public/)                            │
│  - All dados/ content copied to public/                 │
│  - Static files ready for deployment                   │
└─────────────────────────────────────────────────────────┘
                    ↓
        [Netlify Functions]
                    ↓
┌─────────────────────────────────────────────────────────┐
│     RUNTIME ACCESS (Agents)                             │
│  - EpocaDetalhadaAgent reads:                           │
│    • resultados_completos.md                           │
│    • classificacoes_completas.md                       │
│    • fotografias/equipas/                              │
│  - Other agents read specialized subsets              │
└─────────────────────────────────────────────────────────┘
```

---

## Data Update Procedures

### Regular Updates
1. **Match Results:** Added after each match completion
2. **Classifications:** Updated at season end or mid-season updates
3. **Photos:** New photos added as available
4. **Biographies:** Updated with new information as discovered

### Build & Deployment
```bash
# 1. Update data files in dados/
# 2. Run build
npm run build

# 3. Files automatically copied to public/
# 4. Deployed to production via Netlify
netlify deploy
```

### Synchronization
- All source files live in `dados/` directory
- `public/` directory is a mirror created during build
- Build script handles all copying and preprocessing

---

## Data Validation Status

### Validated ✅
- [ ] Match results formatting
- [ ] Classification table structures
- [ ] Image file presence and naming
- [ ] File encoding (UTF-8)

### Needs Validation 🚧
- [ ] Biography data completeness
- [ ] Player registry accuracy
- [ ] Missing information detection
- [ ] Duplicate detection

### Issues Logged
1. Root biography files need consolidation
2. Inconsistent biography formats
3. Some duplicate player entries
4. Missing metadata in some records

---

## Recommended Data Maintenance

### Weekly
- Verify latest match results are added
- Check for any file corruption

### Monthly
- Review biography entries for accuracy
- Update player statistics
- Clean up any broken links

### Quarterly
- Audit data for duplicates
- Validate file formats
- Generate statistics report

### Annually
- Comprehensive data quality review
- Archive historical versions
- Update documentation

---

## Data Privacy & Attribution

- All data represents publicly available information
- Historical records sourced from:
  - Club official archives
  - Portuguese Football Federation (FPF) records
  - Historical newspaper archives
  - Official club publications

- Player and figure biographies compiled from:
  - Public interviews
  - Official announcements
  - Historical documentation
  - Media coverage

---

## Future Data Infrastructure

### Planned Improvements
1. **Structured Database:** Migrate from files to relational DB
2. **Automated Validation:** Implement data quality checks
3. **API Layer:** Create REST endpoints for data access
4. **Caching:** Add Redis for frequently accessed data
5. **Backup System:** Implement automated daily backups

### Timeline
- **Q4 2025:** Database schema design
- **Q1 2026:** Initial migration of results data
- **Q2 2026:** Complete API implementation
- **Q3 2026:** Full production deployment

---

## Contact & Support

For data-related questions or updates:
- Review `/dados/_metadata/` for schema information
- Check `/dados/_metadata/manifest.json` for file inventory
- Refer to agent implementations for usage examples
