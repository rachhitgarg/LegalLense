"""
Netlify Serverless Function for Legal Lens API

Handles:
- POST /api/search - Search with KG + LightRAG
- GET /api/statute/{code}/{section} - Statute mapping
- GET /api - Health check
"""

import json
import os
import re
from datetime import datetime

# ============================================================================
# KNOWLEDGE GRAPH DATA (Embedded for serverless)
# ============================================================================

STATUTE_MAPPINGS = {
    "302": {"bns": "103", "desc": "Punishment for murder"},
    "304": {"bns": "105", "desc": "Culpable homicide not amounting to murder"},
    "304A": {"bns": "106", "desc": "Causing death by negligence"},
    "307": {"bns": "109", "desc": "Attempt to murder"},
    "376": {"bns": "63", "desc": "Rape"},
    "377": {"bns": "None", "desc": "Unnatural offences (decriminalized)"},
    "420": {"bns": "316", "desc": "Cheating"},
    "498A": {"bns": "84", "desc": "Cruelty by husband or relatives"},
    "499": {"bns": "354", "desc": "Defamation"},
    "506": {"bns": "349", "desc": "Criminal intimidation"},
    "299": {"bns": "100", "desc": "Culpable homicide"},
    "300": {"bns": "101", "desc": "Murder"},
}

# Judgment documents (embedded)
DOCUMENTS = [
    {
        "doc_id": "jacob_mathew_2005",
        "title": "Jacob Mathew vs State of Punjab (2005)",
        "content": """This landmark case established the comprehensive law on medical negligence in India. 
The Supreme Court held that a medical professional can only be held liable for negligence if:
1. He did not possess the requisite skill which he professed to have
2. He did not exercise reasonable care in its exercise

Key guidelines for prosecuting medical professionals:
- Private complaints cannot be entertained unless a prima facie case of negligence exists
- Simple lack of care, error of judgment, or accident is not negligence
- The doctor must be shown to have acted with gross negligence or recklessness""",
        "keywords": ["medical negligence", "doctor liability", "malpractice", "prosecution", "304A"],
        "statutes": ["IPC 304A", "BNS 106"],
        "year": 2005,
        "court": "Supreme Court of India"
    },
    {
        "doc_id": "puttaswamy_2017",
        "title": "K.S. Puttaswamy vs Union of India (2017)",
        "content": """The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held:

1. Right to privacy is a fundamental right intrinsic to Article 21 (right to life)
2. Privacy includes: bodily autonomy, personal identity, informational privacy, decisional privacy
3. Privacy can be restricted only under a three-fold test:
   - Legitimate state aim
   - Law that is fair, just, and reasonable
   - Proportionality

This judgment is foundational for data protection law in India.""",
        "keywords": ["privacy", "fundamental right", "article 21", "data protection", "aadhaar"],
        "statutes": ["Article 21", "Article 14", "Article 19"],
        "year": 2017,
        "court": "Supreme Court of India"
    },
    {
        "doc_id": "navtej_johar_2018",
        "title": "Navtej Singh Johar vs Union of India (2018)",
        "content": """The Supreme Court decriminalized homosexuality by reading down Section 377 of the IPC.

Key holdings:
1. Consensual sexual conduct between adults of the same sex in private is NOT a crime
2. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts
3. LGBTQ+ individuals have equal rights under Articles 14, 19, and 21
4. Constitutional morality must prevail over social morality""",
        "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy", "equality"],
        "statutes": ["IPC 377", "Article 14", "Article 21", "Article 19"],
        "year": 2018,
        "court": "Supreme Court of India"
    },
    {
        "doc_id": "kesavananda_bharati_1973",
        "title": "Kesavananda Bharati vs State of Kerala (1973)",
        "content": """The most important constitutional law case in India, establishing the Basic Structure Doctrine.

Key holdings (7-6 majority):
1. Parliament has power to amend ANY part of the Constitution
2. BUT Parliament CANNOT destroy the Constitution's basic structure
3. Basic structure includes:
   - Fundamental rights
   - Secularism
   - Federalism
   - Separation of powers
   - Judicial review""",
        "keywords": ["basic structure", "constitution", "amendment", "parliament power", "judicial review"],
        "statutes": ["Article 368", "Article 13"],
        "year": 1973,
        "court": "Supreme Court of India"
    },
    {
        "doc_id": "vishaka_1997",
        "title": "Vishaka vs State of Rajasthan (1997)",
        "content": """Landmark case that laid down Vishaka Guidelines for prevention of sexual harassment at workplace.

Key holdings:
1. Sexual harassment at workplace violates Articles 14, 19(1)(g), and 21
2. The court laid down binding guidelines known as 'Vishaka Guidelines'
3. These guidelines have the force of law until proper legislation is enacted
4. Employers must establish Internal Complaints Committees""",
        "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women rights", "POSH"],
        "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
        "year": 1997,
        "court": "Supreme Court of India"
    }
]

# KG Concepts linked to judgments
KG_CONCEPTS = {
    "medical_negligence": ["jacob_mathew_2005"],
    "privacy": ["puttaswamy_2017", "navtej_johar_2018"],
    "right_to_privacy": ["puttaswamy_2017"],
    "lgbtq_rights": ["navtej_johar_2018"],
    "basic_structure": ["kesavananda_bharati_1973"],
    "sexual_harassment": ["vishaka_1997"],
    "fundamental_rights": ["puttaswamy_2017", "kesavananda_bharati_1973"],
    "equality": ["navtej_johar_2018", "vishaka_1997"],
}


# ============================================================================
# SEARCH FUNCTIONS
# ============================================================================

def get_statute_mapping(section: str):
    """Get BNS mapping for IPC section."""
    mapping = STATUTE_MAPPINGS.get(section)
    if mapping:
        return {
            "old_code": "IPC",
            "old_section": section,
            "new_code": "BNS",
            "new_section": mapping["bns"],
            "title": mapping["desc"]
        }
    return None


def extract_statute_from_query(query: str):
    """Extract statute reference from query."""
    patterns = [
        r'(?:IPC|ipc)\s*(?:section)?\s*(\d+[A-Za-z]?)',
        r'(?:section|Section)\s*(\d+[A-Za-z]?)',
        r'(\d+[A-Za-z]?)\s*(?:IPC|ipc)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query)
        if match:
            return match.group(1)
    return None


def search_documents(query: str, top_k: int = 5):
    """Search documents with keyword matching."""
    query_lower = query.lower()
    query_words = [w.strip() for w in query_lower.split() if len(w.strip()) > 2]
    
    scored_docs = []
    
    for doc in DOCUMENTS:
        score = 0.0
        
        title = doc.get("title", "").lower()
        content = doc.get("content", "").lower()
        keywords = [k.lower() for k in doc.get("keywords", [])]
        
        for word in query_words:
            if word in title:
                score += 0.4
            for kw in keywords:
                if word in kw or kw in word:
                    score += 0.35
                    break
            word_count = content.count(word)
            if word_count > 0:
                score += min(word_count * 0.02, 0.15)
        
        score = min(score, 1.0)
        
        if score > 0:
            scored_docs.append({
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "content": doc["content"][:500],
                "score": round(score, 3),
                "year": doc.get("year"),
                "court": doc.get("court", ""),
                "statutes": doc.get("statutes", []),
                "keywords": doc.get("keywords", [])
            })
    
    scored_docs.sort(key=lambda x: x["score"], reverse=True)
    return scored_docs[:top_k]


def find_concepts(query: str):
    """Find relevant KG concepts from query."""
    query_lower = query.lower()
    found = []
    
    for concept_id, judgments in KG_CONCEPTS.items():
        concept_name = concept_id.replace("_", " ")
        if concept_name in query_lower or any(w in concept_id for w in query_lower.split()):
            found.append({"id": concept_id, "name": concept_name.title()})
    
    return found[:5]


def call_groq_llm(query: str, context: str):
    """Call Groq API for RAG response."""
    import urllib.request
    import urllib.error
    
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return None
    
    system_prompt = """You are a legal research assistant specializing in Indian law.
Provide accurate, concise summaries based on the documents provided.
Cite specific case names and years. Keep responses under 200 words."""
    
    user_content = f"Query: {query}\n\nRelevant Documents:\n{context}"
    
    request_body = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": 400,
        "temperature": 0.3
    }).encode()
    
    try:
        req = urllib.request.Request(
            "https://api.groq.com/openai/v1/chat/completions",
            data=request_body,
            headers={
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
            if "choices" in data:
                return data["choices"][0]["message"]["content"]
    except:
        pass
    
    return None


# ============================================================================
# MAIN HANDLER
# ============================================================================

def handler(event, context):
    """Netlify function handler."""
    
    # Handle CORS preflight
    if event.get("httpMethod") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS"
            },
            "body": ""
        }
    
    path = event.get("path", "").replace("/.netlify/functions/api", "").replace("/api", "")
    method = event.get("httpMethod", "GET")
    
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Content-Type": "application/json"
    }
    
    # Health check
    if path == "" or path == "/":
        return {
            "statusCode": 200,
            "headers": headers,
            "body": json.dumps({
                "status": "ok",
                "service": "Legal Lens API",
                "version": "2.0-netlify",
                "documents": len(DOCUMENTS)
            })
        }
    
    # Search endpoint
    if path == "/search" and method == "POST":
        try:
            body = json.loads(event.get("body", "{}"))
            query = body.get("query", "").strip()
            top_k = min(body.get("top_k", 5), 10)
            
            if not query:
                return {
                    "statusCode": 400,
                    "headers": headers,
                    "body": json.dumps({"error": "Query required"})
                }
            
            # Extract statute and get mapping
            section = extract_statute_from_query(query)
            statute_mapping = get_statute_mapping(section) if section else None
            
            # Search documents
            results = search_documents(query, top_k)
            
            # Find concepts
            concepts = find_concepts(query)
            
            # Generate AI answer using Groq
            context = "\n\n".join([
                f"**{r['title']}**\n{r['content']}" 
                for r in results[:3]
            ])
            lightrag_answer = call_groq_llm(query, context)
            
            return {
                "statusCode": 200,
                "headers": headers,
                "body": json.dumps({
                    "query": query,
                    "statute_mapping": statute_mapping,
                    "related_statutes": [],
                    "kg_concepts": concepts,
                    "results": results,
                    "total_results": len(results),
                    "lightrag_answer": lightrag_answer
                })
            }
            
        except Exception as e:
            return {
                "statusCode": 500,
                "headers": headers,
                "body": json.dumps({"error": str(e)})
            }
    
    # Statute mapping endpoint
    if path.startswith("/statute/"):
        parts = path.split("/")
        if len(parts) >= 3:
            section = parts[-1]
            mapping = get_statute_mapping(section)
            if mapping:
                return {
                    "statusCode": 200,
                    "headers": headers,
                    "body": json.dumps(mapping)
                }
            return {
                "statusCode": 404,
                "headers": headers,
                "body": json.dumps({"error": f"No mapping for section {section}"})
            }
    
    # Not found
    return {
        "statusCode": 404,
        "headers": headers,
        "body": json.dumps({"error": "Not found", "path": path})
    }
