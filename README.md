# 🏆 TalentLens Ranker — Intelligent Candidate Discovery

> **Redrob AI / Hack2Skill India.RUNS — Track 1**  
> **Team:** BeyondResume

---

# 📖 Overview

TalentLens Ranker is an intelligent candidate ranking engine built for the **Redrob AI / Hack2Skill India.RUNS Hackathon**.

The system evaluates and ranks up to **100,000 candidates** for a **Senior AI Engineer (Founding Team)** role using a fully explainable statistical scoring engine.

Unlike black-box ranking systems, every score is generated from measurable candidate attributes and accompanied by factual reasoning.

### Highlights

- 🚀 Processes **100K candidates** in under one minute
- 🧠 Multi-factor statistical scoring
- 📊 Fully explainable rankings
- 🔒 Zero external API calls
- 💻 CPU-only execution
- ⚡ Lightweight and reproducible

**Performance**

| Metric | Value |
|---------|------:|
| Runtime | **44.3 sec** |
| Throughput | **3,020 candidates/sec** |
| Memory Usage | **~200 MB Peak** |
| Network Calls | **0** |
| Platform | **Python 3.11** |

---

# 🏗️ Project Structure

```text
talentlens-ranker/
│
├── utils/
│   ├── __init__.py
│   ├── honeypot.py          # Synthetic profile detection
│   ├── scorer.py            # Multi-factor scoring engine
│   └── reasoning.py         # Human-readable reasoning generation
│
├── rank.py                  # Main ranking pipeline
├── app.py                   # Streamlit demo
├── convert_to_xlsx.py       # CSV → XLSX converter
├── validate_submission.py   # Submission validator
├── requirements.txt
├── submission_metadata.yaml
└── README.md
```

---

# 🎯 Scoring Framework

Candidates are evaluated across four independent dimensions.

| Dimension | Weight | Evaluation Criteria |
|------------|--------|--------------------|
| **Skills** | **40%** | Canonical skill ontology, aliases, proficiency, duration, endorsements, assessments, rarity |
| **Career** | **30%** | Company quality, AI experience ratio, promotion history, job relevance, product experience |
| **Availability** | **20%** | Activity recency, response rate, notice period, interview completion, open-to-work |
| **Location** | **10%** | Preferred cities, relocation willingness, remote flexibility |

---

# 🧠 Scoring Methodology

The ranking engine combines multiple statistical models instead of relying on simple keyword matching.

### Skills Score

- Canonical skill normalization
- Alias mapping
- Experience duration
- Proficiency levels
- Endorsements
- Assessment scores
- Skill rarity
- Sigmoid normalization

---

### Career Score

Evaluates professional quality using:

- Company tier
- AI/ML experience ratio
- Career progression
- Promotion velocity
- Job title relevance
- Product vs consulting experience

---

### Availability Score

Computed using multiplicative weighting of:

- Response rate
- Notice period
- Recent activity
- Interview completion
- Open-to-work status

Temporal factors use exponential decay to prioritize recent candidate activity.

---

### Location Score

Considers:

- Tier-1 city preference
- Tier-2 cities
- Relocation willingness
- Remote work flexibility

---

# 🛡️ Honeypot Detection

TalentLens includes a synthetic-profile detection module that protects ranking quality.

Seven independent checks are performed:

1. Skill proficiency paradox
2. Endorsement anomalies
3. Career timeline inconsistencies
4. Company history validation
5. Response pattern analysis
6. Job title mismatch
7. Profile completeness paradox

Profiles triggering **two or more** checks receive a severe score penalty.

---

# 🔬 Technical Innovations

- 📈 Sigmoid score normalization
- 🚀 Promotion velocity detection
- ⏳ Exponential decay models
- 🎯 Multi-factor availability scoring
- 🧩 Canonical skill ontology
- 📉 Explainable statistical ranking
- 🔒 Offline deterministic execution

---

# ⚙️ Requirements

- Python **3.8+**
- 16 GB RAM (recommended for 100K candidates)
- Windows / Linux / macOS
- No GPU required
- No internet required

---

# 📦 Installation

Clone the repository:

```bash
git clone https://github.com/Nimeshdev1/talentlens-ranker.git
cd talentlens-ranker
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Or install the required package directly:

```bash
pip install openpyxl
```

---

# 🚀 Usage

## Rank Full Dataset

```bash
python rank.py \
    --candidates candidates.jsonl \
    --out submission.csv
```

---

## Rank Sample Dataset

Convert the provided sample JSON into JSONL format:

```bash
python -c "
import json

with open('sample_candidates.json') as f:
    data = json.load(f)

with open('sample_test.jsonl','w') as out:
    for candidate in data:
        out.write(json.dumps(candidate)+'\n')
"
```

Run ranking:

```bash
python rank.py \
    --candidates sample_test.jsonl \
    --out test_output.csv
```

---

## Convert CSV to XLSX

```bash
python convert_to_xlsx.py submission.csv submission.xlsx
```

---

## Validate Submission

```bash
python validate_submission.py submission.csv
```

---

# 📊 Expected Output

```csv
candidate_id,rank,score,reasoning
CAND_0065195,1,0.8927,"Senior ML Engineer with strong product AI experience..."
CAND_0018499,2,0.8926,"Applied Scientist with retrieval expertise and excellent availability..."
```

---

# 📈 Performance Benchmarks

| Metric | Value |
|---------|------:|
| Candidates Ranked | 100,000 |
| Runtime | 44.3 sec |
| Throughput | 3,020 candidates/sec |
| Peak Memory | ~200 MB |
| CPU | 8-core |
| GPU | Not Required |
| Internet | Not Required |

---

# 🖥️ Streamlit Sandbox

Launch the local demo:

```bash
streamlit run app.py
```

The sandbox allows users to upload a small JSONL file and visualize ranking results interactively.

---

# 🔄 Reproduce Results

```bash
git clone https://github.com/Nimeshdev1/talentlens-ranker.git

cd talentlens-ranker

pip install -r requirements.txt

python rank.py \
    --candidates candidates.jsonl \
    --out submission.csv

python validate_submission.py submission.csv
```

---

# 📝 AI Usage Declaration

AI-assisted development tools were used for:

- Architecture brainstorming
- Code review
- Performance optimization
- Documentation refinement

No candidate data was shared with external services during ranking.

All ranking is performed **locally**, ensuring complete privacy and reproducibility.

---

# 👥 Team

**Team Name:** BeyondResume

Hackathon Submission for:

**Redrob AI × Hack2Skill India.RUNS 2026**

---

# 📄 License

This repository is intended for the **Redrob AI / Hack2Skill India.RUNS Hackathon** submission.

---

<p align="center">
<b>Built with ❤️ for the Redrob AI Hackathon • July 2026</b>
</p>
