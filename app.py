import streamlit as st
import requests
import json
import re
from urllib.parse import quote


# ============================================================
# AUTO CHECK CZ
# ============================================================

st.set_page_config(
    page_title="AutoCheck CZ",
    page_icon="🚗",
    layout="wide"
)


# ============================================================
# KONFIGURACE
# ============================================================

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MODEL = "openai/gpt-oss-20b"


# ============================================================
# CSS
# ============================================================

st.markdown("""
<style>

.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 0;
}

.subtitle {
    color: #8b95a7;
    font-size: 17px;
    margin-bottom: 25px;
}

.card {
    background: #161b26;
    border: 1px solid #252c39;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 15px;
}

.verdict {
    border-radius: 18px;
    padding: 25px;
    margin: 20px 0;
    border: 1px solid rgba(255,255,255,.1);
}

.green {
    background: linear-gradient(135deg,#0d3327,#10251f);
}

.yellow {
    background: linear-gradient(135deg,#3b3010,#29230f);
}

.red {
    background: linear-gradient(135deg,#3b1515,#291010);
}

.verdict-title {
    font-size: 32px;
    font-weight: 900;
}

.score {
    font-size: 46px;
    font-weight: 900;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# SESSION
# ============================================================

if "car" not in st.session_state:
    st.session_state.car = None

if "analysis" not in st.session_state:
    st.session_state.analysis = None

if "debug" not in st.session_state:
    st.session_state.debug = ""


# ============================================================
# API KEY
# ============================================================

def get_api_key():

    try:
        secret = st.secrets.get(
            "GROQ_API_KEY",
            ""
        )
    except Exception:
        secret = ""

    if secret:
        return secret.strip()

    return st.session_state.get(
        "manual_api_key",
        ""
    ).strip()


# ============================================================
# GROQ
# ============================================================

def groq_request(
    prompt,
    max_tokens=1500
):

    api_key = get_api_key()

    if not api_key:
        raise Exception(
            "Chybí Groq API klíč."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {

        "model": MODEL,

        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ],

        # GPT-OSS
        "reasoning_effort": "low",

        # Nepotřebujeme dlouhé přemýšlení
        "max_completion_tokens": max_tokens,

        "temperature": 0.2,

        # Garantovaný JSON
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "autocheck_result",
                "strict": True,
                "schema": {
                    "type": "object",

                    "properties": {

                        "car": {
                            "type": "object",
                            "properties": {

                                "brand": {
                                    "type": ["string", "null"]
                                },

                                "model": {
                                    "type": ["string", "null"]
                                },

                                "year": {
                                    "type": ["integer", "null"]
                                },

                                "mileage_km": {
                                    "type": ["integer", "null"]
                                },

                                "price_czk": {
                                    "type": ["integer", "null"]
                                },

                                "engine": {
                                    "type": ["string", "null"]
                                },

                                "power_kw": {
                                    "type": ["integer", "null"]
                                },

                                "fuel": {
                                    "type": ["string", "null"]
                                },

                                "gearbox": {
                                    "type": ["string", "null"]
                                },

                                "body": {
                                    "type": ["string", "null"]
                                },

                                "drive": {
                                    "type": ["string", "null"]
                                },

                                "equipment": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                },

                                "seller_claims": {
                                    "type": "array",
                                    "items": {
                                        "type": "string"
                                    }
                                }

                            },

                            "required": [
                                "brand",
                                "model",
                                "year",
                                "mileage_km",
                                "price_czk",
                                "engine",
                                "power_kw",
                                "fuel",
                                "gearbox",
                                "body",
                                "drive",
                                "equipment",
                                "seller_claims"
                            ],

                            "additionalProperties": False
                        },

                        "verdict": {
                            "type": "string",
                            "enum": [
                                "KUPUJ",
                                "VYJEDNÁVAT",
                                "RUCE PRYČ"
                            ]
                        },

                        "score": {
                            "type": "number"
                        },

                        "summary": {
                            "type": "string"
                        },

                        "fair_price_low": {
                            "type": "integer"
                        },

                        "fair_price_high": {
                            "type": "integer"
                        },

                        "recommended_max_price": {
                            "type": "integer"
                        },

                        "negotiation_price": {
                            "type": "integer"
                        },

                        "technical_score": {
                            "type": "number"
                        },

                        "price_score": {
                            "type": "number"
                        },

                        "risk_score": {
                            "type": "number"
                        },

                        "technical_summary": {
                            "type": "string"
                        },

                        "weaknesses": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {

                                    "title": {
                                        "type": "string"
                                    },

                                    "risk": {
                                        "type": "string"
                                    },

                                    "description": {
                                        "type": "string"
                                    },

                                    "check": {
                                        "type": "string"
                                    }

                                },

                                "required": [
                                    "title",
                                    "risk",
                                    "description",
                                    "check"
                                ],

                                "additionalProperties": False
                            }
                        },

                        "checklist": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        },

                        "service_low": {
                            "type": "integer"
                        },

                        "service_high": {
                            "type": "integer"
                        },

                        "negotiation_arguments": {
                            "type": "array",
                            "items": {
                                "type": "string"
                            }
                        }

                    },

                    "required": [
                        "car",
                        "verdict",
                        "score",
                        "summary",
                        "fair_price_low",
                        "fair_price_high",
                        "recommended_max_price",
                        "negotiation_price",
                        "technical_score",
                        "price_score",
                        "risk_score",
                        "technical_summary",
                        "weaknesses",
                        "checklist",
                        "service_low",
                        "service_high",
                        "negotiation_arguments"
                    ],

                    "additionalProperties": False
                }
            }
        }
    }

    response = requests.post(
        GROQ_URL,
        headers=headers,
        json=payload,
        timeout=90
    )

    # --------------------------------------------------------
    # RATE LIMIT
    # --------------------------------------------------------

    if response.status_code == 429:

        retry = response.headers.get(
            "retry-after",
            "neznámý"
        )

        remaining = response.headers.get(
            "x-ratelimit-remaining-tokens",
            "neznámý"
        )

        reset = response.headers.get(
            "x-ratelimit-reset-tokens",
            "neznámý"
        )

        raise Exception(
            "GROQ RATE LIMIT 429\n\n"
            f"Zbývající tokeny: {remaining}\n"
            f"Reset tokenového limitu: {reset}\n"
            f"Retry-After: {retry}\n\n"
            f"Groq odpověď:\n{response.text[:1500]}"
        )

    # --------------------------------------------------------
    # OSTATNÍ CHYBY
    # --------------------------------------------------------

    if response.status_code != 200:

        raise Exception(
            f"Groq API chyba {response.status_code}:\n\n"
            f"{response.text[:2000]}"
        )

    data = response.json()

    st.session_state.debug = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    content = (
        data["choices"][0]["message"]["content"]
    )

    if not content:
        raise Exception(
            "Groq vrátil prázdnou odpověď."
        )

    return json.loads(content)


# ============================================================
# TRŽNÍ VYHLEDÁVÁNÍ
# ============================================================

def search_market(
    brand,
    model,
    year,
    engine
):

    query = (
        f"{brand} {model} {year} "
        f"{engine or ''} cena ojeté auto"
    )

    url = (
        "https://html.duckduckgo.com/html/?q="
        + quote(query)
    )

    headers = {
        "User-Agent":
        "Mozilla/5.0"
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15
        )

        if response.status_code != 200:
            return []

        html = response.text

        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            html,
            re.DOTALL
        )

        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</',
            html,
            re.DOTALL
        )

        results = []

        for i, title in enumerate(
            titles[:8]
        ):

            title = re.sub(
                r"<[^>]+>",
                "",
                title
            ).strip()

            snippet = ""

            if i < len(snippets):

                snippet = re.sub(
                    r"<[^>]+>",
                    "",
                    snippets[i]
                ).strip()

            results.append(
                {
                    "title": title,
                    "snippet": snippet
                }
            )

        return results

    except Exception:
        return []


# ============================================================
# HLAVNÍ ANALÝZA – JEDEN REQUEST
# ============================================================

def analyze_car(
    ad_text,
    market_results
):

    market_text = "\n".join(
        [
            f"- {x['title']}: {x['snippet']}"
            for x in market_results
        ]
    )

    if not market_text:
        market_text = (
            "Tržní vyhledávání neposkytlo "
            "použitelné výsledky."
        )

    prompt = f"""
Jsi český expert na ojeté automobily.

Analyzuj tento automobilový inzerát.

DŮLEŽITÉ:

Pracuj pouze s informacemi,
které jsou skutečně v inzerátu
nebo v přiložených tržních výsledcích.

Nevymýšlej konkrétní skutečnosti.

Rozlišuj mezi:

1. skutečností uvedenou v inzerátu
2. typickým rizikem dané motorizace
3. věcí, kterou je nutné ověřit

Cena musí být hodnocena realisticky.

Pokud nemáš dostatek tržních dat,
buď konzervativní.

---

TEXT INZERÁTU:

{ad_text}

---

TRŽNÍ VÝSLEDKY:

{market_text}

---

Vytvoř kompletní nákupní posudek.

Buď stručný, ale konkrétní.

U technických rizik uváděj
především věci relevantní pro
konkrétní motor, převodovku,
rok a nájezd.

U ceny:

- odhadni férové rozpětí
- doporuč maximální cenu
- doporuč cenu, na kterou začít vyjednávat

U verdiktu:

KUPUJ =
auto vypadá jako dobrá koupě

VYJEDNÁVAT =
auto může být dobré, ale cena/rizika
vyžadují vyjednávání

RUCE PRYČ =
výrazné riziko nebo nevýhodná koupě

Nespoléhej slepě na tvrzení prodejce.
