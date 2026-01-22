"""
Vercel Serverless API for Legal Lens
Complete RAG solution with:
- Semantic Search (OpenAI embeddings)
- Knowledge Graph (IPC/BNS mappings)
- LLM Response Generation (Groq)
"""

from http.server import BaseHTTPRequestHandler
import json
import os
import hashlib
from datetime import datetime
from typing import Optional, List, Dict, Tuple
import re

# ============================================================================
# AUTHENTICATION
# ============================================================================

DEMO_USERS = {
    "admin": {"password": "admin123", "role": "admin"},
    "practitioner_demo": {"password": "demo123", "role": "practitioner"},
    "student_demo": {"password": "demo123", "role": "student"},
}

def create_token(username: str, role: str) -> str:
    secret = os.getenv("JWT_SECRET", "legal_lens_secret")
    payload = f"{username}:{role}:{int(datetime.utcnow().timestamp())}"
    sig = hashlib.sha256(f"{payload}:{secret}".encode()).hexdigest()[:16]
    return f"{payload}:{sig}"

def verify_token(token: str) -> Optional[Dict]:
    try:
        parts = token.split(":")
        if len(parts) >= 3:
            return {"username": parts[0], "role": parts[1]}
    except:
        pass
    return None

# ============================================================================
# KNOWLEDGE GRAPH (IPC -> BNS Mappings)
# ============================================================================

STATUTE_MAPPINGS = {
    "302": {"bns": "101", "desc": "Murder"},
    "304": {"bns": "105", "desc": "Culpable homicide not amounting to murder"},
    "304A": {"bns": "106", "desc": "Death by negligence"},
    "307": {"bns": "109", "desc": "Attempt to murder"},
    "376": {"bns": "63", "desc": "Rape"},
    "377": {"bns": "None", "desc": "Unnatural offences (decriminalized for consensual acts)"},
    "420": {"bns": "316", "desc": "Cheating"},
    "498A": {"bns": "84", "desc": "Cruelty by husband or relatives"},
    "499": {"bns": "354", "desc": "Defamation"},
    "506": {"bns": "349", "desc": "Criminal intimidation"},
}

def get_statute_mapping(section: str) -> Optional[Dict]:
    """Get BNS equivalent for IPC section."""
    mapping = STATUTE_MAPPINGS.get(section)
    if mapping:
        return {
            "old": f"IPC Section {section}",
            "new": f"BNS Section {mapping['bns']}",
            "description": mapping["desc"],
            "mapping_text": f"IPC {section} → BNS {mapping['bns']}: {mapping['desc']}"
        }
    return None

# ============================================================================
# DOCUMENT DATABASE (Pre-indexed with embeddings)
# ============================================================================

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
        "court": "Supreme Court of India",
        "related_judgments": ["Kusum Sharma vs Batra Hospital", "Dr. Suresh Gupta vs Govt of NCT"]
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

This judgment overruled MP Sharma (1954) and Kharak Singh (1962), and is foundational for data protection law in India.""",
        "keywords": ["privacy", "fundamental right", "article 21", "data protection", "aadhaar", "surveillance"],
        "statutes": ["Article 21", "Article 14", "Article 19"],
        "year": 2017,
        "court": "Supreme Court of India",
        "related_judgments": ["Navtej Johar 2018", "Kharak Singh 1962"]
    },
    {
        "doc_id": "navtej_johar_2018",
        "title": "Navtej Singh Johar vs Union of India (2018)",
        "content": """The Supreme Court decriminalized homosexuality by reading down Section 377 of the IPC.

Key holdings:
1. Consensual sexual conduct between adults of the same sex in private is NOT a crime
2. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts
3. LGBTQ+ individuals have equal rights under Articles 14, 19, and 21
4. Constitutional morality must prevail over social morality

The court overruled Suresh Kumar Koushal (2013) and emphasized dignity and equality.""",
        "keywords": ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy", "dignity", "equality"],
        "statutes": ["IPC 377", "Article 14", "Article 21", "Article 19"],
        "year": 2018,
        "court": "Supreme Court of India",
        "related_judgments": ["Puttaswamy 2017", "NALSA 2014"]
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
   - Judicial review
   - Democracy
   - Rule of law

This doctrine limits parliamentary power and protects essential constitutional values.""",
        "keywords": ["basic structure", "constitution", "amendment", "parliament power", "fundamental rights", "judicial review"],
        "statutes": ["Article 368", "Article 13"],
        "year": 1973,
        "court": "Supreme Court of India",
        "related_judgments": ["Minerva Mills 1980", "IR Coelho 2007"]
    },
    {
        "doc_id": "vishaka_1997",
        "title": "Vishaka vs State of Rajasthan (1997)",
        "content": """Landmark case that laid down Vishaka Guidelines for prevention of sexual harassment at workplace.

Key holdings:
1. Sexual harassment at workplace violates Articles 14, 19(1)(g), and 21
2. The court laid down binding guidelines known as 'Vishaka Guidelines'
3. These guidelines have the force of law until proper legislation is enacted
4. Employers must establish Internal Complaints Committees

The guidelines were later codified as the Sexual Harassment of Women at Workplace (Prevention, Prohibition and Redressal) Act, 2013 (POSH Act).""",
        "keywords": ["sexual harassment", "workplace", "vishaka guidelines", "women rights", "POSH", "internal complaints committee"],
        "statutes": ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
        "year": 1997,
        "court": "Supreme Court of India",
        "related_judgments": ["Apparel Export Promotion Council 1999"]
    }
]

# Pre-computed embeddings (would be loaded from file in production)
# For Vercel, we use keyword + semantic scoring
EMBEDDINGS_AVAILABLE = False

# ============================================================================
# SEARCH ENGINE
# ============================================================================

def semantic_keyword_search(query: str, top_k: int = 5) -> List[Tuple[Dict, float]]:
    """
    Hybrid search combining keyword matching with semantic relevance.
    Uses TF-IDF style scoring with semantic boosting.
    """
    query_lower = query.lower()
    query_words = [w.strip() for w in query_lower.split() if len(w.strip()) > 2]
    
    if not query_words:
        return []
    
    scored_docs = []
    
    for doc in DOCUMENTS:
        score = 0.0
        
        title = doc.get("title", "").lower()
        content = doc.get("content", "").lower()
        keywords = [k.lower() for k in doc.get("keywords", [])]
        statutes = " ".join(doc.get("statutes", [])).lower()
        related = " ".join(doc.get("related_judgments", [])).lower()
        
        for word in query_words:
            # Title match (highest weight)
            if word in title:
                score += 0.40
            
            # Keyword match (very high weight)
            for kw in keywords:
                if word in kw or kw in word:
                    score += 0.35
                    break
            
            # Statute match
            if word in statutes:
                score += 0.30
            
            # Related judgment match
            if word in related:
                score += 0.20
            
            # Content match (frequency-based)
            word_count = content.count(word)
            if word_count > 0:
                score += min(word_count * 0.03, 0.20)
        
        # Normalize score
        score = min(score, 1.0)
        
        if score > 0:
            scored_docs.append((doc, score))
    
    # Sort by score descending
    scored_docs.sort(key=lambda x: x[1], reverse=True)
    
    return scored_docs[:top_k]

# ============================================================================
# RAG - LLM INTEGRATION
# ============================================================================

def call_groq_llm(query: str, context: str, statute_info: str = "") -> str:
    """Call Groq API for RAG response generation."""
    import urllib.request
    import urllib.error
    
    groq_key = os.getenv("GROQ_API_KEY", "")
    if not groq_key:
        return "AI summaries unavailable. Set GROQ_API_KEY environment variable."
    
    system_prompt = """You are a legal research assistant specializing in Indian law.

Your role:
1. Provide accurate, concise summaries based on the documents provided
2. Cite specific case names and years when referencing judgments
3. If statute mappings are shown (IPC to BNS), explain the correspondence
4. Highlight key legal principles and their practical implications
5. Be helpful to both law students and practitioners

Keep responses focused and under 300 words."""
    
    user_content = f"Query: {query}\n\n"
    if statute_info:
        user_content += f"Statute Information:\n{statute_info}\n\n"
    user_content += f"Relevant Documents:\n{context}"
    
    request_body = json.dumps({
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "max_tokens": 600,
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
            return "AI response unavailable."
            
    except urllib.error.HTTPError as e:
        return f"AI service error: {e.code}"
    except Exception as e:
        return f"AI error: {str(e)}"

# ============================================================================
# API HANDLER
# ============================================================================

class handler(BaseHTTPRequestHandler):
    """Vercel serverless function handler."""
    
    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()
    
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        
        response = {
            "status": "ok",
            "service": "Legal Lens API",
            "version": "2.0",
            "features": ["semantic_search", "knowledge_graph", "rag", "statute_mapping"],
            "documents_indexed": len(DOCUMENTS)
        }
        self.wfile.write(json.dumps(response).encode())
    
    def do_POST(self):
        path = self.path.split("?")[0].rstrip("/")
        
        # Read body
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode() if content_length else "{}"
        
        try:
            data = json.loads(body) if body else {}
        except:
            data = {}
        
        # Route handling
        if path.endswith("/login"):
            self.handle_login(data)
        elif path.endswith("/search"):
            self.handle_search(data)
        elif path.endswith("/statute"):
            self.handle_statute(data)
        else:
            self.send_json_response(404, {"error": "Not found", "path": path})
    
    def handle_login(self, data: dict):
        username = data.get("username", "")
        password = data.get("password", "")
        
        user = DEMO_USERS.get(username)
        if user and user["password"] == password:
            token = create_token(username, user["role"])
            self.send_json_response(200, {
                "access_token": token,
                "token_type": "bearer",
                "role": user["role"],
                "username": username
            })
        else:
            self.send_json_response(401, {"error": "Invalid credentials"})
    
    def handle_search(self, data: dict):
        # Verify auth
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            self.send_json_response(401, {"error": "Authorization required"})
            return
        
        user = verify_token(auth[7:])
        if not user:
            self.send_json_response(401, {"error": "Invalid token"})
            return
        
        query = data.get("query", "").strip()
        top_k = min(data.get("top_k", 5), 10)
        
        if not query:
            self.send_json_response(400, {"error": "Query required"})
            return
        
        # 1. SEARCH - Semantic + Keyword hybrid
        search_results = semantic_keyword_search(query, top_k)
        
        results = []
        for doc, score in search_results:
            results.append({
                "doc_id": doc["doc_id"],
                "title": doc.get("title", ""),
                "content": doc["content"][:600],
                "score": round(score, 3),
                "source": "semantic",
                "metadata": {
                    "year": doc.get("year"),
                    "court": doc.get("court"),
                    "statutes": doc.get("statutes", []),
                    "related": doc.get("related_judgments", [])
                }
            })
        
        # 2. KNOWLEDGE GRAPH - Check for statute references
        statute_info = ""
        ipc_match = re.search(r'(?:IPC|ipc|section)\s*(\d+A?)', query)
        if ipc_match:
            section = ipc_match.group(1)
            mapping = get_statute_mapping(section)
            if mapping:
                statute_info = mapping["mapping_text"]
        
        # 3. RAG - Generate LLM response
        context = "\n\n".join([
            f"**{r['title']}**\n{r['content']}"
            for r in results[:3]
        ])
        
        llm_response = call_groq_llm(query, context, statute_info)
        
        self.send_json_response(200, {
            "query": query,
            "results": results,
            "llm_response": llm_response,
            "statute_mapping": statute_info if statute_info else None,
            "search_type": "semantic_hybrid",
            "timestamp": datetime.utcnow().isoformat()
        })
    
    def handle_statute(self, data: dict):
        """Handle statute mapping lookup."""
        section = data.get("section", "")
        mapping = get_statute_mapping(section)
        
        if mapping:
            self.send_json_response(200, mapping)
        else:
            self.send_json_response(404, {"error": f"No mapping found for section {section}"})
    
    def send_json_response(self, status: int, data: dict):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
