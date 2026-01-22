/**
 * Netlify Serverless Function for Legal Lens API
 * 
 * Handles:
 * - POST /api/search - Search with KG + LightRAG
 * - GET /api/statute/{code}/{section} - Statute mapping
 * - GET /api - Health check
 */

// ============================================================================
// KNOWLEDGE GRAPH DATA (Embedded for serverless)
// ============================================================================

const STATUTE_MAPPINGS = {
    "302": { bns: "103", desc: "Punishment for murder" },
    "304": { bns: "105", desc: "Culpable homicide not amounting to murder" },
    "304A": { bns: "106", desc: "Causing death by negligence" },
    "307": { bns: "109", desc: "Attempt to murder" },
    "376": { bns: "63", desc: "Rape" },
    "377": { bns: "None", desc: "Unnatural offences (decriminalized)" },
    "420": { bns: "316", desc: "Cheating" },
    "498A": { bns: "84", desc: "Cruelty by husband or relatives" },
    "499": { bns: "354", desc: "Defamation" },
    "506": { bns: "349", desc: "Criminal intimidation" },
    "299": { bns: "100", desc: "Culpable homicide" },
    "300": { bns: "101", desc: "Murder" },
};

const DOCUMENTS = [
    {
        doc_id: "jacob_mathew_2005",
        title: "Jacob Mathew vs State of Punjab (2005)",
        content: `This landmark case established the comprehensive law on medical negligence in India. 
The Supreme Court held that a medical professional can only be held liable for negligence if:
1. He did not possess the requisite skill which he professed to have
2. He did not exercise reasonable care in its exercise

Key guidelines for prosecuting medical professionals:
- Private complaints cannot be entertained unless a prima facie case of negligence exists
- Simple lack of care, error of judgment, or accident is not negligence
- The doctor must be shown to have acted with gross negligence or recklessness`,
        keywords: ["medical negligence", "doctor liability", "malpractice", "prosecution", "304A"],
        statutes: ["IPC 304A", "BNS 106"],
        year: 2005,
        court: "Supreme Court of India"
    },
    {
        doc_id: "puttaswamy_2017",
        title: "K.S. Puttaswamy vs Union of India (2017)",
        content: `The landmark Right to Privacy judgment. A nine-judge Constitution Bench unanimously held:

1. Right to privacy is a fundamental right intrinsic to Article 21 (right to life)
2. Privacy includes: bodily autonomy, personal identity, informational privacy, decisional privacy
3. Privacy can be restricted only under a three-fold test:
   - Legitimate state aim
   - Law that is fair, just, and reasonable
   - Proportionality

This judgment is foundational for data protection law in India.`,
        keywords: ["privacy", "fundamental right", "article 21", "data protection", "aadhaar"],
        statutes: ["Article 21", "Article 14", "Article 19"],
        year: 2017,
        court: "Supreme Court of India"
    },
    {
        doc_id: "navtej_johar_2018",
        title: "Navtej Singh Johar vs Union of India (2018)",
        content: `The Supreme Court decriminalized homosexuality by reading down Section 377 of the IPC.

Key holdings:
1. Consensual sexual conduct between adults of the same sex in private is NOT a crime
2. Section 377 is unconstitutional to the extent it criminalizes consensual homosexual acts
3. LGBTQ+ individuals have equal rights under Articles 14, 19, and 21
4. Constitutional morality must prevail over social morality`,
        keywords: ["section 377", "homosexuality", "LGBTQ", "decriminalization", "privacy", "equality"],
        statutes: ["IPC 377", "Article 14", "Article 21", "Article 19"],
        year: 2018,
        court: "Supreme Court of India"
    },
    {
        doc_id: "kesavananda_bharati_1973",
        title: "Kesavananda Bharati vs State of Kerala (1973)",
        content: `The most important constitutional law case in India, establishing the Basic Structure Doctrine.

Key holdings (7-6 majority):
1. Parliament has power to amend ANY part of the Constitution
2. BUT Parliament CANNOT destroy the Constitution's basic structure
3. Basic structure includes:
   - Fundamental rights
   - Secularism
   - Federalism
   - Separation of powers
   - Judicial review`,
        keywords: ["basic structure", "constitution", "amendment", "parliament power", "judicial review"],
        statutes: ["Article 368", "Article 13"],
        year: 1973,
        court: "Supreme Court of India"
    },
    {
        doc_id: "vishaka_1997",
        title: "Vishaka vs State of Rajasthan (1997)",
        content: `Landmark case that laid down Vishaka Guidelines for prevention of sexual harassment at workplace.

Key holdings:
1. Sexual harassment at workplace violates Articles 14, 19(1)(g), and 21
2. The court laid down binding guidelines known as 'Vishaka Guidelines'
3. These guidelines have the force of law until proper legislation is enacted
4. Employers must establish Internal Complaints Committees`,
        keywords: ["sexual harassment", "workplace", "vishaka guidelines", "women rights", "POSH"],
        statutes: ["Article 14", "Article 19", "Article 21", "POSH Act 2013"],
        year: 1997,
        court: "Supreme Court of India"
    }
];

const KG_CONCEPTS = {
    "medical_negligence": ["jacob_mathew_2005"],
    "privacy": ["puttaswamy_2017", "navtej_johar_2018"],
    "right_to_privacy": ["puttaswamy_2017"],
    "lgbtq_rights": ["navtej_johar_2018"],
    "basic_structure": ["kesavananda_bharati_1973"],
    "sexual_harassment": ["vishaka_1997"],
    "fundamental_rights": ["puttaswamy_2017", "kesavananda_bharati_1973"],
    "equality": ["navtej_johar_2018", "vishaka_1997"],
};

// ============================================================================
// SEARCH FUNCTIONS
// ============================================================================

function getStatuteMapping(section) {
    const mapping = STATUTE_MAPPINGS[section];
    if (mapping) {
        return {
            old_code: "IPC",
            old_section: section,
            new_code: "BNS",
            new_section: mapping.bns,
            title: mapping.desc
        };
    }
    return null;
}

function extractStatuteFromQuery(query) {
    const patterns = [
        /(?:IPC|ipc)\s*(?:section)?\s*(\d+[A-Za-z]?)/,
        /(?:section|Section)\s*(\d+[A-Za-z]?)/,
        /(\d+[A-Za-z]?)\s*(?:IPC|ipc)/,
    ];

    for (const pattern of patterns) {
        const match = query.match(pattern);
        if (match) {
            return match[1];
        }
    }
    return null;
}

function searchDocuments(query, topK = 5) {
    const queryLower = query.toLowerCase();
    const queryWords = queryLower.split(/\s+/).filter(w => w.length > 2);

    const scoredDocs = [];

    for (const doc of DOCUMENTS) {
        let score = 0;

        const title = (doc.title || "").toLowerCase();
        const content = (doc.content || "").toLowerCase();
        const keywords = (doc.keywords || []).map(k => k.toLowerCase());

        for (const word of queryWords) {
            if (title.includes(word)) {
                score += 0.4;
            }
            for (const kw of keywords) {
                if (kw.includes(word) || word.includes(kw)) {
                    score += 0.35;
                    break;
                }
            }
            const wordCount = (content.match(new RegExp(word, 'g')) || []).length;
            if (wordCount > 0) {
                score += Math.min(wordCount * 0.02, 0.15);
            }
        }

        score = Math.min(score, 1.0);

        if (score > 0) {
            scoredDocs.push({
                doc_id: doc.doc_id,
                title: doc.title,
                content: doc.content.substring(0, 500),
                score: Math.round(score * 1000) / 1000,
                year: doc.year,
                court: doc.court || "",
                statutes: doc.statutes || [],
                keywords: doc.keywords || []
            });
        }
    }

    scoredDocs.sort((a, b) => b.score - a.score);
    return scoredDocs.slice(0, topK);
}

function findConcepts(query) {
    const queryLower = query.toLowerCase();
    const found = [];

    for (const [conceptId, judgments] of Object.entries(KG_CONCEPTS)) {
        const conceptName = conceptId.replace(/_/g, " ");
        if (queryLower.includes(conceptName) || queryLower.split(/\s+/).some(w => conceptId.includes(w))) {
            found.push({ id: conceptId, name: conceptName.charAt(0).toUpperCase() + conceptName.slice(1) });
        }
    }

    return found.slice(0, 5);
}

async function callGroqLLM(query, context) {
    const groqKey = process.env.GROQ_API_KEY;
    if (!groqKey) {
        return null;
    }

    const systemPrompt = `You are a legal research assistant specializing in Indian law.
Provide accurate, concise summaries based on the documents provided.
Cite specific case names and years. Keep responses under 200 words.`;

    try {
        const response = await fetch("https://api.groq.com/openai/v1/chat/completions", {
            method: "POST",
            headers: {
                "Authorization": `Bearer ${groqKey}`,
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                model: "llama-3.1-8b-instant",
                messages: [
                    { role: "system", content: systemPrompt },
                    { role: "user", content: `Query: ${query}\n\nRelevant Documents:\n${context}` }
                ],
                max_tokens: 400,
                temperature: 0.3
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data.choices && data.choices[0]) {
                return data.choices[0].message.content;
            }
        }
    } catch (e) {
        console.error("Groq API error:", e);
    }

    return null;
}

// ============================================================================
// MAIN HANDLER
// ============================================================================

exports.handler = async (event, context) => {
    const headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Content-Type": "application/json"
    };

    // Handle CORS preflight
    if (event.httpMethod === "OPTIONS") {
        return { statusCode: 200, headers, body: "" };
    }

    const path = (event.path || "")
        .replace("/.netlify/functions/api", "")
        .replace("/api", "");
    const method = event.httpMethod || "GET";

    // Health check
    if (path === "" || path === "/") {
        return {
            statusCode: 200,
            headers,
            body: JSON.stringify({
                status: "ok",
                service: "Legal Lens API",
                version: "2.0-netlify",
                documents: DOCUMENTS.length
            })
        };
    }

    // Search endpoint
    if (path === "/search" && method === "POST") {
        try {
            const body = JSON.parse(event.body || "{}");
            const query = (body.query || "").trim();
            const topK = Math.min(body.top_k || 5, 10);

            if (!query) {
                return {
                    statusCode: 400,
                    headers,
                    body: JSON.stringify({ error: "Query required" })
                };
            }

            // Extract statute and get mapping
            const section = extractStatuteFromQuery(query);
            const statuteMapping = section ? getStatuteMapping(section) : null;

            // Search documents
            const results = searchDocuments(query, topK);

            // Find concepts
            const concepts = findConcepts(query);

            // Generate AI answer using Groq
            const contextStr = results.slice(0, 3)
                .map(r => `**${r.title}**\n${r.content}`)
                .join("\n\n");
            const lightragAnswer = await callGroqLLM(query, contextStr);

            return {
                statusCode: 200,
                headers,
                body: JSON.stringify({
                    query,
                    statute_mapping: statuteMapping,
                    related_statutes: [],
                    kg_concepts: concepts,
                    results,
                    total_results: results.length,
                    lightrag_answer: lightragAnswer
                })
            };

        } catch (e) {
            return {
                statusCode: 500,
                headers,
                body: JSON.stringify({ error: e.message })
            };
        }
    }

    // Statute mapping endpoint
    if (path.startsWith("/statute/")) {
        const parts = path.split("/");
        if (parts.length >= 3) {
            const section = parts[parts.length - 1];
            const mapping = getStatuteMapping(section);
            if (mapping) {
                return { statusCode: 200, headers, body: JSON.stringify(mapping) };
            }
            return {
                statusCode: 404,
                headers,
                body: JSON.stringify({ error: `No mapping for section ${section}` })
            };
        }
    }

    // Not found
    return {
        statusCode: 404,
        headers,
        body: JSON.stringify({ error: "Not found", path })
    };
};
