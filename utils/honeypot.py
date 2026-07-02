"""
Honeypot detection module for TalentLens Ranker.
Identifies synthetic/fake candidate profiles using consistency checks.
All checks run in O(n) where n = number of candidate fields.
"""

from datetime import datetime, date
from typing import Dict, List, Any, Set
import re

# Pre-compiled patterns for speed
CONSULTING_PATTERNS = re.compile(
    r'\b(tcs|infosys|wipro|accenture|cognizant|capgemini|hcl|'
    r'tech\s*mahindra|mphasis|hexaware|lti|mindtree)\b',
    re.IGNORECASE
)

IRRELEVANT_TITLES_PATTERN = re.compile(
    r'\b(marketing|hr\s*manager|content\s*writer|operations\s*manager|'
    r'sales\s*executive|accountant|graphic\s*designer|customer\s*support|'
    r'mechanical\s*engineer|civil\s*engineer|business\s*analyst|'
    r'finance|accounting|recruitment|talent\s*acquisition)\b',
    re.IGNORECASE
)

# Suspicious company name patterns
SUSPICIOUS_COMPANY_PATTERNS = re.compile(
    r'(test|demo|fake|dummy|sample|xyz|abc\s*corp|unknown|'
    r'not\s*applicable|freelance\s*only|self\s*employed\s*only)',
    re.IGNORECASE
)

def _calculate_experience_gap(career_history: List[Dict], claimed_years: float) -> float:
    """Calculate gap between claimed and actual experience."""
    total_months = sum(j.get("duration_months", 0) for j in career_history)
    claimed_months = claimed_years * 12
    return total_months - claimed_months


def _check_skill_paradox(skills: List[Dict]) -> int:
    """
    Check for impossible skill combinations.
    Returns number of paradoxes found.
    """
    flags = 0
    
    for skill in skills:
        proficiency = skill.get("proficiency", "")
        duration = skill.get("duration_months", 0)
        endorsements = skill.get("endorsements", 0)
        
        # Expert with insufficient time (need at least 12 months for expert)
        if proficiency == "expert" and duration < 12:
            flags += 2
        # Advanced with very little time
        elif proficiency == "advanced" and duration < 6:
            flags += 1
        # Expert with no endorsements (very suspicious)
        if proficiency == "expert" and endorsements == 0:
            flags += 1
    
    return flags


def _check_endorsement_ratio(skills: List[Dict]) -> int:
    """Check if endorsement patterns are realistic."""
    flags = 0
    expert_count = sum(1 for s in skills if s.get("proficiency") == "expert")
    advanced_count = sum(1 for s in skills if s.get("proficiency") == "advanced")
    total_endorsements = sum(s.get("endorsements", 0) for s in skills)
    
    # Too many expert claims with too few endorsements
    if expert_count >= 3 and total_endorsements < 10:
        flags += 2
    # High-level skills but almost no endorsements
    if (expert_count + advanced_count) >= 5 and total_endorsements < 15:
        flags += 2
    # Many skills but zero endorsements total
    if len(skills) > 5 and total_endorsements == 0:
        flags += 1
    
    return flags


def _check_company_consistency(career_history: List[Dict]) -> int:
    """Check for suspicious company patterns."""
    flags = 0
    companies = [j.get("company", "") for j in career_history]
    
    # All companies are suspicious
    suspicious_count = sum(1 for c in companies if SUSPICIOUS_COMPANY_PATTERNS.search(c))
    if suspicious_count == len(companies) and len(companies) > 0:
        flags += 3
    
    # Too many short stints (< 3 months each)
    short_stints = sum(1 for j in career_history if j.get("duration_months", 0) < 3)
    if short_stints >= 4:
        flags += 2
    
    return flags


def _check_response_anomalies(redrob_signals: Dict) -> int:
    """Check for suspicious response patterns."""
    flags = 0
    completeness = redrob_signals.get("profile_completeness_score", 0)
    response_rate = redrob_signals.get("recruiter_response_rate", 0)
    interview_rate = redrob_signals.get("interview_completion_rate", 0)
    
    # Perfect profile but never responds
    if completeness >= 90 and response_rate == 0.0:
        flags += 1
    
    # High completeness but suspiciously low interview completion
    if completeness >= 85 and interview_rate < 0.1:
        flags += 1
    
    # Claims open to work but never responds
    if redrob_signals.get("open_to_work_flag") and response_rate == 0.0:
        flags += 1
    
    return flags


def get_honeypot_multiplier(candidate: Dict[str, Any]) -> float:
    """
    Calculate honeypot multiplier for a candidate.
    
    Args:
        candidate: Candidate profile dictionary
        
    Returns:
        float: 0.05 if likely honeypot, 1.0 otherwise
    """
    flags = 0
    
    # Extract data once
    skills = candidate.get("skills", [])
    career_history = candidate.get("career_history", [])
    redrob = candidate.get("redrob_signals", {})
    profile = candidate.get("profile", {})
    
    # Check 1: Skill proficiency paradoxes
    flags += _check_skill_paradox(skills)
    
    # Check 2: Endorsement ratio anomalies
    flags += _check_endorsement_ratio(skills)
    
    # Check 3: Career timeline mismatch
    claimed_years = profile.get("years_of_experience", 0)
    gap = _calculate_experience_gap(career_history, claimed_years)
    
    if gap > 24:  # Career shows 2+ years more than claimed
        flags += 2
    if claimed_years >= 5 and gap < -42:  # Claims 5+ years but has < 1.5 years actual
        flags += 3
    
    # Check 4: Company consistency
    flags += _check_company_consistency(career_history)
    
    # Check 5: Response anomalies
    flags += _check_response_anomalies(redrob)
    
    # Check 6: Title-career mismatch
    current_title = profile.get("current_title", "").lower()
    if IRRELEVANT_TITLES_PATTERN.search(current_title):
        # Check if they have ANY relevant AI experience
        ai_related = sum(1 for j in career_history 
                        if any(term in j.get("title", "").lower() 
                              for term in ["ml", "ai", "data scientist", "machine learning"]))
        if ai_related == 0 and claimed_years > 3:
            flags += 1
    
    # Threshold: if 2 or more flags, mark as honeypot
    return 0.05 if flags >= 2 else 1.0


def is_consulting_only(candidate: Dict[str, Any]) -> bool:
    """
    Check if candidate has only consulting experience.
    
    Args:
        candidate: Candidate profile dictionary
        
    Returns:
        bool: True if candidate has < 12 months non-consulting experience
    """
    career = candidate.get("career_history", [])
    non_consulting_months = sum(
        j.get("duration_months", 0) for j in career
        if not CONSULTING_PATTERNS.search(j.get("company", ""))
    )
    return non_consulting_months < 12