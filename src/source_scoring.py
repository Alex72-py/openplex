"""
OpenPlex Source Trust Engine.
Heuristics-based scoring for web sources based on domain authority,
primary source detection, and content quality.
"""

import re
from urllib.parse import urlparse

# Domain Authority Tiers
TRUST_TIERS = {
    "official": 100,      # documentation, project sites
    "government": 95,     # .gov, .mil
    "academic": 95,       # .edu, research papers
    "security": 90,       # advisories (cve.mitre, etc.)
    "news": 85,           # major news orgs
    "tech_pub": 75,       # technical publications (wired, arstechnica)
    "eng_blog": 65,       # company engineering blogs
    "blog": 50,           # independent blogs
    "forum": 35,          # stackoverflow, quora
    "reddit": 30,         # reddit
    "unknown": 20         # default
}

# Domain mapping for specific high-authority/common sites
DOMAIN_MAP = {
    "reuters.com": "news",
    "bbc.com": "news",
    "nytimes.com": "news",
    "apnews.com": "news",
    "wsj.com": "news",
    "bloomberg.com": "news",
    "theguardian.com": "news",
    
    "wired.com": "tech_pub",
    "arstechnica.com": "tech_pub",
    "theverge.com": "tech_pub",
    "techcrunch.com": "tech_pub",
    "zdnet.com": "tech_pub",
    "bleepingcomputer.com": "security",
    
    "stackoverflow.com": "forum",
    "quora.com": "forum",
    "reddit.com": "reddit",
    
    "github.com": "official",
    "gitlab.com": "official",
    "microsoft.com": "official",
    "apple.com": "official",
    "google.com": "official",
    "openai.com": "official",
    "anthropic.com": "official",
    "nvidia.com": "official"
}

def calculate_trust_score(url, title, snippet, content, query):
    """
    Calculate a trust score (0-100) based on domain authority,
    primary source detection, and content quality.
    """
    domain = urlparse(url).netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]

    # 1. Base Domain Authority
    score = TRUST_TIERS["unknown"]
    
    # Check official mapping
    if domain in DOMAIN_MAP:
        score = TRUST_TIERS[DOMAIN_MAP[domain]]
    elif domain.endswith((".gov", ".mil")):
        score = TRUST_TIERS["government"]
    elif domain.endswith(".edu"):
        score = TRUST_TIERS["academic"]
    elif any(d in domain for d in ["docs.", "developer.", "support."]):
        score = TRUST_TIERS["official"]
    elif "blog" in domain:
        score = TRUST_TIERS["blog"]

    # 2. Primary Source Boost (+20)
    # Detect if the domain is the origin of the claim (e.g., query has 'openai' and domain is 'openai.com')
    query_parts = set(re.findall(r'\w+', query.lower()))
    domain_parts = set(re.findall(r'\w+', domain))
    
    # Significant overlap between domain name and query indicates a potential primary source
    if len(query_parts & domain_parts) >= 1:
        # Avoid boosting generic top-level domains or common words
        common_words = {"com", "org", "net", "io", "edu", "gov", "blog", "docs"}
        specific_domain_parts = domain_parts - common_words
        if any(part in query_parts for part in specific_domain_parts):
            score += 20

    # 3. Content Quality Scoring
    content_lower = content.lower()
    
    # Boosts
    if re.search(r'\b(by|author|written by):?\s+[a-z]+', content_lower):
        score += 5  # Named author
    if re.search(r'\b(20\d{2})[-/]\d{2}[-/]\d{2}\b', content_lower) or "2024" in content_lower or "2025" in content_lower:
        score += 5  # Publication date (recent-ish)
    if "references" in content_lower or "citations" in content_lower or "sources" in content_lower:
        score += 5  # References section
    if len(re.findall(r'\[\d+\]', content_lower)) > 2:
        score += 5  # Outbound citations/references
    
    # Penalties
    clickbait_patterns = ["shocking", "you won't believe", "secrets revealed", "miracle", "exposed"]
    if any(p in title.lower() for p in clickbait_patterns):
        score -= 15
    if len(content) < 500:
        score -= 10  # Thin content
    if re.search(r'\b(buy now|order now|limited time offer)\b', content_lower):
        score -= 10  # Excessive commercial patterns

    # Final clamp
    return max(0, min(100, score))

def deduplicate_sources(sources):
    """
    Remove redundant sources that quote the same original information.
    Uses simple Jaccard similarity on word sets.
    """
    if not sources:
        return []

    unique_sources = []
    # Sort by trust score so we keep the most trusted version of the info
    sorted_sources = sorted(sources, key=lambda x: x.get("trust_score", 0), reverse=True)

    for source in sorted_sources:
        content = (source.get("content") or source.get("snippet", "")).lower()
        words = set(re.findall(r'\w{4,}', content))  # Only words 4+ chars
        
        is_duplicate = False
        for seen_source in unique_sources:
            seen_content = (seen_source.get("content") or seen_source.get("snippet", "")).lower()
            seen_words = set(re.findall(r'\w{4,}', seen_content))
            
            if not words or not seen_words:
                continue
                
            intersection = len(words & seen_words)
            union = len(words | seen_words)
            similarity = intersection / union
            
            if similarity > 0.7:  # High overlap threshold
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique_sources.append(source)
            
    return unique_sources
