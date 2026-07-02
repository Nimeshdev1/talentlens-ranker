"""
Winning reasoning generation module.
Generates human-readable, factual, and varied explanations for rankings.
"""

from datetime import datetime, date
from typing import Dict, List, Tuple, Any
from utils.honeypot import CONSULTING_PATTERNS
from utils.scorer import (
    SKILL_ONTOLOGY, SKILL_TO_CANONICAL, _get_company_tier, _get_title_info
)

TODAY = date(2026, 7, 2)


def _get_best_skills(candidate: Dict[str, Any], n: int = 3) -> List[Tuple[str, str, int]]:
    """Extract top N most relevant skills."""
    skills = candidate.get("skills", [])
    scored = []
    
    for skill in skills:
        name = skill.get("name", "")
        name_lower = name.lower().strip()
        
        # Find canonical match
        canonical = None
        if name_lower in SKILL_TO_CANONICAL:
            canonical = SKILL_TO_CANONICAL[name_lower]
        else:
            for alias, can in SKILL_TO_CANONICAL.items():
                if name_lower in alias or alias in name_lower:
                    canonical = can
                    break
        
        if not canonical:
            continue
        
        info = SKILL_ONTOLOGY[canonical]
        tier_mult = {"A": 3.0, "B": 2.0, "C": 1.0}.get(info["tier"], 0)
        rarity = info["rarity"]
        prof_mult = {"expert": 1.0, "advanced": 0.8, "intermediate": 0.5, "beginner": 0.3}.get(
            skill.get("proficiency", ""), 0.3
        )
        duration = skill.get("duration_months", 0)
        
        relevance = tier_mult * rarity + prof_mult * min(duration / 12, 1.0)
        scored.append((name, skill.get("proficiency", ""), duration, relevance))
    
    scored.sort(key=lambda x: x[3], reverse=True)
    return [(s[0], s[1], s[2]) for s in scored[:n]]


def _get_ai_experience_years(career: List[Dict]) -> float:
    """Calculate total years of AI/ML experience."""
    ai_months = sum(
        j.get("duration_months", 0) for j in career
        if any(term in j.get("title", "").lower()
              for term in ["ml", "ai", "nlp", "search", "ranking", "retrieval",
                          "machine learning", "data scientist", "data science",
                          "applied scientist", "recommendation", "language model",
                          "embedding", "vector"])
    )
    return round(ai_months / 12, 1)


def _get_notable_company(career: List[Dict]) -> str:
    """Find the highest-tier company in career history."""
    best_tier = 5
    best_company = ""
    for job in career:
        company = job.get("company", "")
        tier = _get_company_tier(company)
        if tier < best_tier:
            best_tier = tier
            best_company = company
    return best_company


def _count_product_companies(career: List[Dict]) -> int:
    """Count distinct product companies."""
    companies = set()
    for job in career:
        company = job.get("company", "").lower()
        tier = _get_company_tier(company)
        if tier in {1, 2, 3}:
            companies.add(company)
    return len(companies)


def generate_reasoning(candidate: Dict[str, Any], rank: int,
                      score: float, dim_scores: Dict[str, float]) -> str:
    """
    Generate varied, factual reasoning based on actual candidate data.
    """
    profile = candidate.get("profile", {})
    redrob = candidate.get("redrob_signals", {})
    career = candidate.get("career_history", [])
    
    # Extract key data
    title = profile.get("current_title", "Professional")
    years = profile.get("years_of_experience", 0)
    current_company = profile.get("current_company", "")
    response_rate = redrob.get("recruiter_response_rate", 0)
    notice_days = redrob.get("notice_period_days", 90)
    open_to_work = redrob.get("open_to_work_flag", False)
    
    # Title info
    title_score, title_category = _get_title_info(title)
    
    # Days inactive
    try:
        last_active = datetime.strptime(
            redrob.get("last_active_date", "2020-01-01"), "%Y-%m-%d"
        ).date()
        days_inactive = (TODAY - last_active).days
    except:
        days_inactive = 999
    
    # Skills
    top_skills = _get_best_skills(candidate, 3)
    skills_phrase = ", ".join(f"{s[0]} ({s[1]})" for s in top_skills[:2]) if top_skills else "general skills"
    
    # Career
    ai_years = _get_ai_experience_years(career)
    notable_company = _get_notable_company(career)
    product_count = _count_product_companies(career)
    
    # Determine career background type
    consulting_months = sum(
        j.get("duration_months", 0) for j in career
        if _get_company_tier(j.get("company", "")) == 4
    )
    total_months = sum(j.get("duration_months", 0) for j in career)
    is_consulting_heavy = total_months > 0 and consulting_months / total_months > 0.6
    
    # Activity description
    if days_inactive <= 1:
        activity = "active today"
    elif days_inactive <= 3:
        activity = "active this week"
    elif days_inactive <= 7:
        activity = f"active {days_inactive}d ago"
    elif days_inactive <= 14:
        activity = "active recently"
    elif days_inactive <= 30:
        activity = f"active {days_inactive}d ago"
    elif days_inactive <= 60:
        activity = "moderately active"
    elif days_inactive <= 90:
        activity = "less active recently"
    else:
        activity = f"inactive {days_inactive}d"
    
    # Notice period description
    if notice_days <= 7:
        notice_str = "immediate joiner"
    elif notice_days <= 15:
        notice_str = f"{notice_days}d notice"
    elif notice_days <= 30:
        notice_str = f"{notice_days}d notice"
    elif notice_days <= 60:
        notice_str = f"{notice_days}d notice"
    else:
        notice_str = f"{notice_days}d notice period"
    
    # Response rate description
    if response_rate >= 0.7:
        response_str = f"high response rate ({response_rate:.0%})"
    elif response_rate >= 0.4:
        response_str = f"moderate response rate ({response_rate:.0%})"
    elif response_rate > 0:
        response_str = f"low response rate ({response_rate:.0%})"
    else:
        response_str = "no response history"
    
    # --- Generate varied reasoning by rank tier ---
    
    if rank <= 10:
        # Elite candidates - highlight exceptional qualities
        strengths = []
        
        if dim_scores["skills"] >= 0.7:
            strengths.append(f"exceptional retrieval/AI skills ({skills_phrase})")
        elif dim_scores["skills"] >= 0.5:
            strengths.append(f"strong technical skills ({skills_phrase})")
        
        if notable_company and _get_company_tier(notable_company) <= 2:
            strengths.append(f"proven at {notable_company}")
        elif product_count >= 2:
            strengths.append(f"{product_count} product companies")
        
        if ai_years >= 3:
            strengths.append(f"{ai_years}yr AI/ML experience")
        
        if open_to_work:
            strengths.append("actively looking")
        
        strength_str = "; ".join(strengths[:3]) if strengths else "excellent overall profile"
        
        context = (f"#{rank}: {title} with {years:.0f}yr total experience. "
                  f"{strength_str}. {response_str}, {activity}, {notice_str}.")
    
    elif rank <= 30:
        # Strong candidates - good fit with minor gaps
        if dim_scores["skills"] >= 0.4:
            skill_desc = f"relevant skills in {skills_phrase}"
        else:
            skill_desc = f"skills include {skills_phrase}"
        
        if is_consulting_heavy:
            bg_desc = "consulting background"
        elif product_count >= 1:
            bg_desc = f"product experience ({notable_company})" if notable_company else "product background"
        else:
            bg_desc = f"{years:.0f}yr experience"
        
        gap = ""
        if dim_scores["skills"] < 0.3:
            gap = " but lacks depth in retrieval/embeddings"
        elif dim_scores["career"] < 0.3:
            gap = " but career less aligned with AI/Search roles"
        
        context = (f"#{rank}: {title}, {bg_desc}{gap}. "
                  f"{skill_desc}. {response_str}, {activity}.")
    
    elif rank <= 60:
        # Mid-tier - decent but not outstanding
        if dim_scores["skills"] < 0.3:
            primary_issue = "limited retrieval/search specialization"
        elif dim_scores["career"] < 0.3:
            primary_issue = "career not focused on AI/ML roles"
        elif dim_scores["availability"] < 0.3:
            primary_issue = "low availability signals"
        else:
            primary_issue = "moderate overall match"
        
        context = (f"#{rank}: {title}, {years:.0f}yr; {primary_issue}. "
                  f"Skills: {skills_phrase}. {response_str}, {activity}.")
    
    else:
        # Lower tier - explain why they didn't rank higher
        issues = []
        if dim_scores["skills"] < 0.2:
            issues.append("minimal retrieval/AI skills")
        if is_consulting_heavy:
            issues.append("consulting-only background")
        if dim_scores["career"] < 0.2:
            issues.append("career mismatch for AI/Search role")
        if days_inactive > 90:
            issues.append(f"inactive {days_inactive}d")
        if not open_to_work:
            issues.append("not actively looking")
        
        main_issue = issues[0] if issues else "lower priority match"
        
        context = (f"#{rank}: {title}, {years:.0f}yr; {main_issue}. "
                  f"Skills include {skills_phrase}. {activity}, {response_str}.")
    
    return context