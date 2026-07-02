"""
WINNING VERSION - Optimized Statistical Multi-Factor Scoring Engine
Performance: ~25-30s for 100K candidates (no math.log/math.exp in hot path)
"""

from datetime import datetime, date
from typing import Dict, List, Tuple, Any, Set, Optional
import re
from utils.honeypot import CONSULTING_PATTERNS

# ============================================================================
# FAST MATH APPROXIMATIONS
# ============================================================================

_SIGMOID_TABLE = {}
for i in range(-200, 201):
    x = i / 100.0
    try:
        _SIGMOID_TABLE[round(x, 2)] = 1.0 / (1.0 + 2.718281828459045 ** (-8.0 * (x - 0.5)))
    except:
        _SIGMOID_TABLE[round(x, 2)] = 1.0 if x > 0.5 else 0.0

def _fast_sigmoid(x: float, midpoint: float = 0.5, steepness: float = 8.0) -> float:
    adjusted = (x - midpoint) * (steepness / 8.0) + 0.5
    key = round(min(max(adjusted, -2.0), 2.0), 2)
    return _SIGMOID_TABLE.get(key, 0.5)

_LOG_LIKE = {}
for i in range(0, 101):
    _LOG_LIKE[i] = 0.0 if i <= 1 else min((i / 100.0) ** 0.5, 1.0)

def _fast_log_normalize(value: float, max_val: float) -> float:
    if value <= 0:
        return 0.0
    ratio = min(value / max_val, 1.0)
    idx = int(ratio * 100)
    return _LOG_LIKE.get(min(idx, 100), ratio)

_EXP_DECAY = {}
for days in range(0, 366):
    _EXP_DECAY[days] = 1.0 / (1.0 + days / 14.0)

def _fast_exp_decay(days: float) -> float:
    return _EXP_DECAY.get(min(int(days), 365), 0.01)

_NOTICE_DECAY = {}
for days in range(0, 181):
    _NOTICE_DECAY[days] = 1.0 / (1.0 + days / 46.0)

def _fast_notice_decay(days: float) -> float:
    return _NOTICE_DECAY.get(min(int(days), 180), 0.1)

# ============================================================================
# SKILL ONTOLOGY
# ============================================================================

SKILL_ONTOLOGY = {
    "vector_search": {
        "aliases": ["vector search", "vector database", "vectordb", "vector db",
                   "faiss", "pinecone", "weaviate", "qdrant", "milvus",
                   "pgvector", "chromadb", "vespa", "vald", "nmslib",
                   "annoy", "scann", "vector", "vectors", "vector indexing",
                   "approximate nearest neighbor", "ann"],
        "tier": "A", "rarity": 0.95, "jd_relevance": 1.0
    },
    "embeddings": {
        "aliases": ["embeddings", "embedding", "sentence transformers",
                   "sentence-transformers", "text embeddings", "word embeddings",
                   "bert embeddings", "openai embeddings", "cohere embeddings",
                   "text-embedding", "embedding model", "dense embeddings",
                   "sparse embeddings", "embedding generation"],
        "tier": "A", "rarity": 0.90, "jd_relevance": 1.0
    },
    "information_retrieval": {
        "aliases": ["information retrieval", "retrieval", "ir", "search",
                   "semantic search", "hybrid search", "dense retrieval",
                   "sparse retrieval", "bm25", "tf-idf", "elasticsearch",
                   "opensearch", "solr", "reranking", "re-ranking", "ranking",
                   "learning to rank", "ltr", "ndcg", "map", "precision@k",
                   "retrieval augmented generation", "rag", "search engine",
                   "query understanding", "query expansion", "relevance feedback"],
        "tier": "A", "rarity": 0.85, "jd_relevance": 1.0
    },
    "reranking": {
        "aliases": ["reranking", "re-ranking", "cross-encoder", "bi-encoder",
                   "two-stage retrieval", "ranking model", "ranking algorithm",
                   "relevance scoring", "score normalization", "fusion"],
        "tier": "A", "rarity": 0.92, "jd_relevance": 0.95
    },
    "llm": {
        "aliases": ["llm", "large language model", "large language models",
                   "gpt", "claude", "gemini", "llama", "mistral", "falcon",
                   "generative ai", "genai", "gen ai", "chatgpt", "openai",
                   "language model", "language models", "gpt-3", "gpt-4",
                   "gpt-4o", "foundation model", "frontier model"],
        "tier": "B", "rarity": 0.75, "jd_relevance": 0.85
    },
    "nlp": {
        "aliases": ["nlp", "natural language processing", "natural language understanding",
                   "nlu", "text processing", "text analytics", "computational linguistics",
                   "text classification", "named entity recognition", "ner",
                   "sentiment analysis", "text summarization", "question answering"],
        "tier": "B", "rarity": 0.65, "jd_relevance": 0.80
    },
    "fine_tuning": {
        "aliases": ["fine-tuning", "fine tuning", "finetuning", "lora", "qlora",
                   "peft", "prompt engineering", "prompt tuning", "instruction tuning",
                   "rlhf", "dpo", "model training", "transfer learning",
                   "adapter", "parameter efficient", "few-shot", "zero-shot"],
        "tier": "B", "rarity": 0.80, "jd_relevance": 0.75
    },
    "transformers": {
        "aliases": ["transformers", "hugging face", "huggingface", "bert",
                   "roberta", "t5", "gpt-2", "attention mechanism", "transformer",
                   "encoder-decoder", "self-attention", "cross-attention",
                   "multi-head attention", "positional encoding"],
        "tier": "B", "rarity": 0.60, "jd_relevance": 0.70
    },
    "recommendation": {
        "aliases": ["recommendation", "recommender", "recommendation system",
                   "collaborative filtering", "matrix factorization", "two-tower",
                   "personalization", "recommendation engine", "content-based",
                   "hybrid recommender", "candidate generation"],
        "tier": "B", "rarity": 0.70, "jd_relevance": 0.65
    },
    "mlops": {
        "aliases": ["mlops", "ml ops", "model deployment", "model serving",
                   "mlflow", "kubeflow", "bentoml", "sagemaker", "vertex ai",
                   "model monitoring", "ci/cd ml", "model registry",
                   "feature store", "model versioning", "a/b testing"],
        "tier": "B", "rarity": 0.68, "jd_relevance": 0.60
    },
    "deep_learning": {
        "aliases": ["deep learning", "neural networks", "cnn", "rnn", "lstm",
                   "deep neural", "neural network", "backpropagation",
                   "gradient descent", "activation function", "dropout",
                   "batch normalization", "resnet", "transformer architecture"],
        "tier": "B", "rarity": 0.50, "jd_relevance": 0.55
    },
    "python": {
        "aliases": ["python", "python3", "python programming", "cpython"],
        "tier": "C", "rarity": 0.10, "jd_relevance": 0.40
    },
    "pytorch": {
        "aliases": ["pytorch", "torch", "pytorch lightning", "torchscript"],
        "tier": "C", "rarity": 0.30, "jd_relevance": 0.50
    },
    "tensorflow": {
        "aliases": ["tensorflow", "tf", "keras", "tflite"],
        "tier": "C", "rarity": 0.30, "jd_relevance": 0.45
    },
    "cloud": {
        "aliases": ["aws", "gcp", "azure", "google cloud", "amazon web services",
                   "cloud computing", "ec2", "s3", "lambda", "bigquery"],
        "tier": "C", "rarity": 0.20, "jd_relevance": 0.35
    },
    "distributed": {
        "aliases": ["distributed systems", "kafka", "spark", "ray", "dask",
                   "distributed computing", "microservices", "hadoop",
                   "mapreduce", "parallel computing", "grpc", "message queue"],
        "tier": "C", "rarity": 0.50, "jd_relevance": 0.40
    },
    "infrastructure": {
        "aliases": ["docker", "kubernetes", "k8s", "terraform", "ci/cd",
                   "fastapi", "flask", "redis", "postgresql", "mongodb",
                   "api", "rest api", "grpc", "graphql", "nginx"],
        "tier": "C", "rarity": 0.20, "jd_relevance": 0.30
    },
    "ml_algorithms": {
        "aliases": ["machine learning", "ml", "supervised learning",
                   "unsupervised learning", "xgboost", "random forest",
                   "svm", "gradient boosting", "scikit-learn", "sklearn",
                   "classification", "regression", "clustering",
                   "ensemble methods", "decision tree", "lightgbm", "catboost"],
        "tier": "C", "rarity": 0.15, "jd_relevance": 0.35
    },
    "data_processing": {
        "aliases": ["pandas", "numpy", "data analysis", "data preprocessing",
                   "feature engineering", "etl", "sql", "data pipeline",
                   "data wrangling", "data cleaning", "exploratory data analysis"],
        "tier": "C", "rarity": 0.10, "jd_relevance": 0.25
    },
}

SKILL_TO_CANONICAL: Dict[str, str] = {}
for canonical, info in SKILL_ONTOLOGY.items():
    for alias in info["aliases"]:
        SKILL_TO_CANONICAL[alias.lower()] = canonical

# ============================================================================
# COMPANY TIERS
# ============================================================================

COMPANY_TIERS = {
    1: {
        "google", "deepmind", "openai", "microsoft", "meta", "facebook",
        "amazon", "apple", "nvidia", "anthropic", "cohere", "mistral",
        "stability ai", "hugging face", "databricks", "snowflake",
        "netflix", "spotify", "uber", "airbnb", "linkedin", "twitter",
        "stripe", "plaid", "notion", "figma", "canva", "linear",
        "vercel", "supabase", "hashicorp", "confluent", "mongodb inc",
        "elastic", "cockroach labs", "planetscale"
    },
    2: {
        "swiggy", "zomato", "razorpay", "phonepe", "meesho", "flipkart",
        "groww", "dream11", "cred", "zepto", "nykaa", "paytm", "ola",
        "unacademy", "sharechat", "urban company", "cure.fit",
        "atlassian", "salesforce", "adobe", "oracle", "sap", "ibm",
        "cisco", "intel", "amd", "qualcomm", "samsung", "intuit",
        "vmware", "servicenow", "shopify", "dropbox", "palantir",
        "postman", "browserstack", "chargebee", "freshworks", "zoho",
        "clevertap", "moengage", "webengage"
    },
}

TIER1_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(c) for c in COMPANY_TIERS[1]) + r')\b',
    re.IGNORECASE
)
TIER2_PATTERN = re.compile(
    r'\b(' + '|'.join(re.escape(c) for c in COMPANY_TIERS[2]) + r')\b',
    re.IGNORECASE
)

# ============================================================================
# TITLE PATTERNS
# ============================================================================

AI_TITLE_HIERARCHY = [
    (re.compile(r'\b(search\s*engineer|retrieval\s*engineer|ranking\s*engineer|'
                r'relevance\s*engineer|search\s*specialist)\b', re.IGNORECASE), 1.0, "Search"),
    (re.compile(r'\b(gen\s*ai\s*engineer|generative\s*ai\s*engineer|llm\s*engineer|'
                r'prompt\s*engineer)\b', re.IGNORECASE), 0.92, "GenAI"),
    (re.compile(r'\b(ai\s*engineer|artificial\s*intelligence\s*engineer|'
                r'ai/ml\s*engineer)\b', re.IGNORECASE), 0.88, "AI Engineer"),
    (re.compile(r'\b(ml\s*engineer|machine\s*learning\s*engineer|mle|'
                r'senior\s*mle)\b', re.IGNORECASE), 0.85, "ML Engineer"),
    (re.compile(r'\b(applied\s*scientist|research\s*scientist|research\s*engineer)\b',
                re.IGNORECASE), 0.82, "Research"),
    (re.compile(r'\b(nlp\s*engineer|nlp\s*scientist|computational\s*linguist)\b',
                re.IGNORECASE), 0.80, "NLP"),
    (re.compile(r'\b(ml\s*platform|ml\s*infrastructure|mlops\s*engineer|'
                r'platform\s*engineer.*ml)\b', re.IGNORECASE), 0.72, "ML Platform"),
    (re.compile(r'\b(data\s*scientist|senior\s*data\s*scientist|lead\s*data\s*scientist|'
                r'staff\s*data\s*scientist)\b', re.IGNORECASE), 0.55, "Data Science"),
    (re.compile(r'\b(software\s*engineer|senior\s*software|staff\s*software|'
                r'principal\s*engineer|sde|senior\s*sde|lead\s*sde)\b', re.IGNORECASE),
     0.35, "Software Eng"),
    (re.compile(r'\b(backend\s*engineer|senior\s*backend|staff\s*backend|'
                r'full\s*stack\s*engineer)\b', re.IGNORECASE), 0.25, "Backend"),
]

IRRELEVANT_TITLE_PATTERN = re.compile(
    r'\b(marketing|hr|human\s*resources|content\s*writer|operations|'
    r'sales|accountant|graphic\s*designer|customer\s*support|'
    r'mechanical|civil|finance|recruiter|talent\s*acquisition|'
    r'business\s*analyst|project\s*manager|scrum\s*master|'
    r'teacher|professor|lecturer|doctor|nurse|lawyer|chef|'
    r'ui\s*designer|ux\s*designer|product\s*manager|qa\s*engineer|'
    r'tester|devops\s*engineer|system\s*admin|network\s*engineer)\b',
    re.IGNORECASE
)

PROFICIENCY_WEIGHT = {
    "beginner": 0.30, "intermediate": 0.55, "advanced": 0.80, "expert": 1.00
}


def _normalize_skill_name(name: str) -> Optional[str]:
    name_lower = name.lower().strip()
    if name_lower in SKILL_TO_CANONICAL:
        return SKILL_TO_CANONICAL[name_lower]
    for alias, canonical in SKILL_TO_CANONICAL.items():
        if name_lower in alias or alias in name_lower:
            return canonical
    return None


def _get_company_tier(company_name: str) -> int:
    if not company_name:
        return 4
    if TIER1_PATTERN.search(company_name):
        return 1
    if TIER2_PATTERN.search(company_name):
        return 2
    if CONSULTING_PATTERNS.search(company_name):
        return 4
    return 3


def _get_title_info(title: str) -> Tuple[float, str]:
    if not title:
        return 0.10, "Unknown"
    if IRRELEVANT_TITLE_PATTERN.search(title.lower()):
        return 0.0, "Irrelevant"
    for pattern, score, category in AI_TITLE_HIERARCHY:
        if pattern.search(title.lower()):
            if any(w in title.lower() for w in ["senior", "lead", "staff", "principal", "head"]):
                score = min(score + 0.03, 1.0)
            return score, category
    return 0.12, "Other Technical"


def score_skills(candidate: Dict[str, Any]) -> float:
    skills = candidate.get("skills", [])
    if not skills:
        return 0.0
    assessment_scores = candidate.get("redrob_signals", {}).get("skill_assessment_scores", {})
    matched = {"A": [], "B": [], "C": []}
    seen = set()
    for skill in skills:
        name = skill.get("name", "")
        canonical = _normalize_skill_name(name)
        if not canonical or canonical in seen:
            continue
        seen.add(canonical)
        info = SKILL_ONTOLOGY[canonical]
        tier = info["tier"]
        prof = PROFICIENCY_WEIGHT.get(skill.get("proficiency", "beginner"), 0.30)
        dur = skill.get("duration_months", 0)
        end = skill.get("endorsements", 0)
        dur_mult = _fast_log_normalize(dur, 60) if dur > 0 else 0.3
        end_signal = _fast_log_normalize(end, 50)
        assess_bonus = 0.0
        for assessed, score_val in assessment_scores.items():
            if canonical.replace("_", " ") in assessed.lower():
                assess_bonus = (score_val / 100) * 0.10
                break
        recency = min(dur / 36, 1.0) if dur > 0 else 0.5
        skill_value = (
            prof * 0.35 + dur_mult * 0.20 + end_signal * 0.15 +
            assess_bonus + info["rarity"] * 0.10 + info["jd_relevance"] * 0.10
        ) * recency
        matched[tier].append(min(skill_value, 1.0))

    def aggregate(values: List[float], n: int) -> float:
        if not values:
            return 0.0
        sorted_vals = sorted(values, reverse=True)[:n]
        total = sum(v / (i + 1) for i, v in enumerate(sorted_vals))
        weight_sum = sum(1.0 / (i + 1) for i in range(len(sorted_vals)))
        return total / weight_sum if weight_sum > 0 else 0.0

    tier_a = aggregate(matched["A"], 5)
    tier_b = aggregate(matched["B"], 6)
    tier_c = aggregate(matched["C"], 4)
    diversity = 0.0
    if matched["A"] and matched["B"]:
        diversity += 0.04
    if len(matched["A"]) >= 2 and len(matched["B"]) >= 3:
        diversity += 0.04
    if matched["A"] and matched["B"] and matched["C"]:
        diversity += 0.02
    raw = 0.55 * tier_a + 0.35 * tier_b + 0.10 * tier_c + diversity
    return round(_fast_sigmoid(raw, 0.35, 6.0), 4)


def score_career(candidate: Dict[str, Any]) -> float:
    """Career scoring with company prestige, AI relevance, and JD-aligned penalties."""
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    years_exp = profile.get("years_of_experience", 0)
    current_title = profile.get("current_title", "")
    
    if not career:
        return 0.0
    
    total_months = sum(j.get("duration_months", 0) for j in career)
    if total_months == 0:
        total_months = 1
    
    title_score, title_category = _get_title_info(current_title)
    
    prestige_total = 0.0
    for job in career:
        tier = _get_company_tier(job.get("company", ""))
        duration = job.get("duration_months", 0)
        tier_mult = {1: 1.0, 2: 0.75, 3: 0.45, 4: 0.15}.get(tier, 0.2)
        prestige_total += tier_mult * duration
    
    avg_prestige = prestige_total / total_months
    best_tier = min((_get_company_tier(j.get("company", "")) for j in career), default=4)
    if best_tier == 4:
        avg_prestige *= 0.4
    elif best_tier == 3:
        avg_prestige *= 0.8
    
    ai_months = sum(
        j.get("duration_months", 0) for j in career
        if any(term in j.get("title", "").lower()
              for term in ["ml", "ai", "nlp", "search", "ranking", "retrieval",
                          "machine learning", "data scientist", "data science",
                          "applied scientist", "recommendation", "language model",
                          "embedding", "vector"])
    )
    ai_ratio = ai_months / total_months
    ai_score = _fast_sigmoid(ai_ratio, 0.4, 5.0)
    
    velocity = 0.0
    if len(career) >= 2 and years_exp > 0:
        titles = [j.get("title", "").lower() for j in career]
        levels = []
        for t in titles:
            if any(w in t for w in ["principal", "distinguished", "fellow", "director", "vp"]):
                levels.append(5)
            elif any(w in t for w in ["staff", "lead", "head", "manager", "architect"]):
                levels.append(4)
            elif any(w in t for w in ["senior", "sr.", "sr "]):
                levels.append(3)
            elif any(w in t for w in ["junior", "jr.", "associate", "intern", "trainee"]):
                levels.append(1)
            else:
                levels.append(2)
        if len(levels) >= 2:
            increases = sum(1 for i in range(1, len(levels)) if levels[i] > levels[i-1])
            velocity = min(increases / (len(levels) - 1), 1.0)
    
    product_months = sum(
        j.get("duration_months", 0) for j in career
        if _get_company_tier(j.get("company", "")) in {1, 2, 3}
    )
    product_ratio = product_months / total_months
    
    raw = (
        title_score * 0.20 + avg_prestige * 0.25 + ai_score * 0.25 +
        velocity * 0.15 + product_ratio * 0.15
    )
    
    if 4 <= years_exp <= 8:
        exp_bonus = 0.05
    elif 3 <= years_exp < 4 or 8 < years_exp <= 10:
        exp_bonus = 0.03
    elif years_exp > 10:
        exp_bonus = 0.01
    else:
        exp_bonus = 0.0
    
    # === JD-ALIGNED PENALTIES ===
    penalty = 1.0
    if best_tier == 4 and product_months < 6:
        penalty = 0.15
    elif product_ratio < 0.2:
        penalty = 0.30
    elif product_ratio < 0.4:
        penalty = 0.55
    if title_category == "Irrelevant":
        penalty *= 0.25
    if title_score < 0.3 and product_months < 12:
        penalty *= 0.70
    
    final = min(raw + exp_bonus, 1.0) * penalty
    return round(final, 4)


def score_availability(candidate: Dict[str, Any]) -> float:
    redrob = candidate.get("redrob_signals", {})
    today = date(2026, 7, 2)
    try:
        last_active = datetime.strptime(
            redrob.get("last_active_date", "2020-01-01"), "%Y-%m-%d"
        ).date()
        days_inactive = max((today - last_active).days, 0)
        recency = _fast_exp_decay(days_inactive)
    except:
        recency = 0.1
    open_signal = 1.0 if redrob.get("open_to_work_flag", False) else 0.1
    response = min(redrob.get("recruiter_response_rate", 0), 1.0)
    notice = _fast_notice_decay(redrob.get("notice_period_days", 90))
    interview = min(redrob.get("interview_completion_rate", 0), 1.0)
    combined = (
        (recency ** 0.30) * (open_signal ** 0.25) *
        ((response + 0.1) ** 0.20) * (notice ** 0.10) *
        ((interview + 0.1) ** 0.15)
    )
    return round(_fast_sigmoid(combined, 0.4, 5.0), 4)


def score_location(candidate: Dict[str, Any]) -> float:
    profile = candidate.get("profile", {})
    location = profile.get("location", "").lower()
    country = profile.get("country", "").lower()
    willing = candidate.get("redrob_signals", {}).get("willing_to_relocate", False)
    remote_ok = candidate.get("redrob_signals", {}).get("open_to_remote", False)
    tier1 = ["pune", "noida", "delhi", "new delhi", "gurugram", "gurgaon",
             "ghaziabad", "faridabad", "ncr"]
    tier2 = ["bangalore", "bengaluru", "hyderabad", "mumbai", "bombay",
             "navi mumbai", "thane"]
    tier3 = ["chennai", "kolkata", "ahmedabad", "jaipur", "chandigarh",
             "indore", "kochi", "coimbatore", "lucknow", "bhubaneswar",
             "visakhapatnam", "mysore", "nagpur", "surat"]
    for city in tier1:
        if city in location:
            return 1.0
    for city in tier2:
        if city in location:
            return 0.90 if willing else 0.80
    for city in tier3:
        if city in location:
            return 0.80 if willing else 0.65
    if "india" in country or "india" in location:
        base = 0.55
        if willing: base += 0.15
        if remote_ok: base += 0.10
        return min(base, 0.85)
    base = 0.25
    if willing: base += 0.20
    if remote_ok: base += 0.15
    return min(base, 0.60)


def compute_final_score(candidate: Dict[str, Any], honeypot_mult: float) -> Tuple[float, Dict[str, float]]:
    s_skills = score_skills(candidate)
    s_career = score_career(candidate)
    s_avail = score_availability(candidate)
    s_loc = score_location(candidate)
    if s_career < 0.15:
        effective_skills = s_skills * 0.35
    elif s_career < 0.25:
        effective_skills = s_skills * 0.55
    elif s_career < 0.35:
        effective_skills = s_skills * 0.75
    else:
        effective_skills = s_skills
    raw = 0.40 * effective_skills + 0.30 * s_career + 0.20 * s_avail + 0.10 * s_loc
    final = round(min(raw * honeypot_mult, 1.0), 6)
    return final, {"skills": s_skills, "career": s_career,
                   "availability": s_avail, "location": s_loc}