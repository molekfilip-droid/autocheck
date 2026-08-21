import streamlit as st
import json
import requests
import re

st.set_page_config(page_title="AutoCheck CZ", page_icon="🚗", layout="wide")

st.title("🚗 AutoCheck CZ – Expertní analýza ojetiny")
st.subheader("Hloubkový technický posudek, skrytá rizika a nákupní verdikt")

default_key = st.secrets.get("GROQ_API_KEY", "")

st.sidebar.markdown("### Nastavení")
api_key = st.sidebar.text_input("Groq API Key", value=default_key, type="password").strip()

st.markdown("### 📋 Automatické vyplnění z inzerátu")
ad_text_input = st.text_area("Zkopíruj text inzerátu (popis, výbavu, parametry)...", placeholder="Sem vlož inzerát z Bazoše, Sauta apod...")

if "form_model" not in st.session_state:
    st.session_state.form_model = ""
    st.session_state.form_year = 2020
    st.session_state.form_km = 0
    st.session_state.form_price = 0
    st.session_state.form_fuel = "Benzín"
    st.session_state.form_gearbox = "Manuální"
    st.session_state.parsed_equipment = "Zatím neuloženo – vlož inzerát a klikni na tlačítko výše."

def call_groq(prompt_text, max_tokens=3000):
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {
        "model": "openai/gpt-oss-20b",
        "messages": [{"role": "user", "content": prompt_text}],
        "temperature": 0.2,
        "max_tokens": max_tokens
    }
    response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=45)
    if response.status_code != 200:
        raise Exception(f"API Error {response.status_code}: {response.text}")
    return response.json()["choices"][0]["message"]["content"].strip()

if st.button("✨ Načíst data z textu inzerátu"):
    if not api_key:
        st.error("Chybí Groq API klíč v secrets nebo v sidebaru.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI podrobně analyzuje inzerát a vytahuje kompletní výbavu..."):
            try:
                clean_ad = ad_text_input.replace('"', "'").replace('\n', ' ').replace('\r', ' ')
                
                # VYLEPŠENÝ PARSOVACÍ PROMPT PRO MAXIMÁLNÍ DETAIL VÝBAVY
                p_text = f"""Jsi špičkový analytik automobilových inzerátů. Tvým úkolem je vytáhnout z textu inzerátu absolutně všechny detaily. 
Nesmíš vynechat žádnou zmínku o výbavě, paketech, kolech, asistentech, typu interiéru nebo technických datech.

Text inzerátu: "{clean_ad}"

Vrať POUZE validní JSON ve formátu (žádný markdown, žádný text okolo):
{{
    "model": "přesná značka, model a případně motorizace",
    "year": 2020,
    "km": 0,
    "price": 0,
    "fuel": "Benzín",
    "gearbox": "Manuální",
    "equipment_summary": "Extrémně detailní a vyčerpávající seznam výbavy rozepsaný do kategorií (např. Bezpečnost a asistenti, Komfort a interiéry, Exteriér a světla, Infotainment, Kola/podvozek atd.) tak, jak to zaznělo v inzerátu, nic nevynechej!"
}}"""
                
                res = call_groq(p_text, 2500)
                
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'\s*```$', '', res)
                
                match = re.search(r'\{.*\}', res, re.DOTALL)
                if match:
                    res = match.group(0)
                
                data = json.loads(res.strip())
                st.session_state.form_model = str(data.get("model", ""))
                st.session_state.form_year = int(data.get("year", 2020))
                st.session_state.form_km = int(data.get("km", 0))
                st.session_state.form_price = int(data.get("price", 0))
                
                f_val = str(data.get("fuel", "Benzín"))
                st.session_state.form_fuel = f_val if f_val in ["Benzín", "Nafta", "Hybrid", "Elektro"] else "Benzín"
                
                g_val = str(data.get("gearbox", "Manuální"))
                st.session_state.form_gearbox = g_val if g_val in ["Manuální", "Automatická"] else "Manuální"
                
                st.session_state.parsed_equipment = str(data.get("equipment_summary", "Bez popisu výbavy."))
                st.success("Kompletní data a detailní výbava úspěšně načteny!")
            except Exception as e:
                st.error(f"Chyba při parsování: {e}. Zkus text inzerátu vložit znovu nebo upravit.")

st.markdown("---")

with st.expander("🔍 Zkontrolovat načtenou výbavu (Detailní přehled)", expanded=True):
    st.info(st.session_state.parsed_equipment)

with st.form("car_form"):
    st.markdown("### 🚗 Parametry vozidla")
    c1, c2 = st.columns(2)
    model = c1.text_input("Značka a model", value=st.session_state.form_model)
    year = c2.number_input("Rok výroby", min_value=1990, max_value=2026, value=st.session_state.form_year)
    km = c1.number_input("Nájezd (km)", min_value=0, value=st.session_state.form_km, step=1000)
    price = c2.number_input("Cena (Kč)", min_value=0, value=st.session_state.form_price, step=10000)
    
    f_opts = ["Benzín", "Nafta", "Hybrid", "Elektro"]
    f_idx = f_opts.index(st.session_state.form_fuel) if st.session_state.form_fuel in f_opts else 0
    fuel = st.selectbox("Palivo", f_opts, index=f_idx)
    
    g_opts = ["Manuální", "Automatická"]
    g_idx = g_opts.index(st.session_state.form_gearbox) if st.session_state.form_gearbox in g_opts else 0
    gearbox = st.selectbox("Převodovka", g_opts, index=g_idx)
    
    submitted = st.form_submit_button("🚀 Spustit hloubkovou expertní analýzu")

if submitted:
    if not api_key:
        st.error("Chybí Groq API klíč.")
    elif not model.strip():
        st.warning("Zadej značku a model vozidla.")
    else:
        with st.spinner("Špičkový mechanik prověřuje reálný stav trhu, skryté vady, servisní historii a reálnou hodnotu..."):
            try:
                clean_full_ad = ad_text_input.replace('"', "'").replace('\n', ' ') if ad_text_input else "Neuveden"
                
                main_prompt = f"""Jsi špičkový český automobilový expert, nezávislý soudní znalec pro motorová vozidla a majitel vyhlášeného autoservisu s 25 lety praxe. Tvojí úlohou je provést nekompromisně objektivní, technicky hloubkový a reálný audit ojetého vozu pro český trh. Zapomeň na obecné fráze, jdi po tvrdých technických faktech.

Parametry hodnoceného vozu:
- Model: {model}
- Rok výroby: {year}
- Nájezd: {km} km
- Požadovaná cena: {price} Kč
- Palivo: {fuel}
- Převodovka: {gearbox}
- Celý text inzerátu / výbava: {clean_full_ad}

Instrukce pro analýzu:
1. Zhodnot reálnou tržní hodnotu (fair price rozmezí v Kč) v ČR s ohledem na aktuální stav trhu, motorizaci a výbavu. Je inzerovaná cena předražená, férová, nebo je to výhodná koupě?
2. Proveď tvrdý technický rozbor konkrétního motoru a převodovky pro tento model a ročník (zmiň specifické slabiny, rozvody, turbo, vstřiky, DPF/GPF, mechatroniku automatu apod.).
3. Vyjmenuj 3 až 4 konkrétní typické chronické bolístky (skrytá rizika) tohoto konkrétního modelu a motoru.
4. Odhadni reálné náklady na servis v příštích 2 letech (včetně konkrétních položek a orientačních částek v Kč, např. výměna olejů, brzdy, podvozek, očekávané investice).
5. Sestav specifický inspekční checklist – čeho si u tohoto auta 100% všimnout při osobní prohlídce a na zvedáku.
6. Dej jasné nákupní doporučení a tipy pro vyjednávání o ceně.

Celá odpověď musí být 100% v češtině. Vrať POUZE validní JSON bez jakéhokoliv markdownu či komentářů (začni rovnou znakem {{ a skonči }}):
{{
    "verdict": "🟢 KUPUJ / VÝBORNÁ NABÍDKA nebo 🟡 ZVÁŽIT / JEDNAT O CENU nebo 🔴 RUCE PRYČ / RIZIKOVÉ",
    "verdict_summary": "1-2 věty ostrého a trefného shrnutí",
    "fair_price_min": 100000,
    "fair_price_max": 150000,
    "price_evaluation": "Detailní rozbor ceny vzhledem k reálnému stavu trhu, nájezdu a výbavě",
    "engine_gearbox_analysis": "Odborný technický rozbor konkrétní motorizace a převodovky včetně jejich specifik",
    "common_failures": ["Konkrétní bolístka 1 s popisem rizika", "Konkrétní bolístka 2 s popisem rizika", "Konkrétní bolístka 3 s popisem rizika"],
    "servicing_cost_2years": "Reálný finanční odhad nutného servisu na 2 roky s výčtem prací/dílů a částkou v Kč",
    "inspection_checklist": ["Specifická kontrola 1 pro tento vůz", "Specifická kontrola 2", "Specifická kontrola 3", "Specifická kontrola 4"],
    "recommendation": "Závěrečný verdikt a konkrétní taktika pro vyjednávání o slevě"
}}"""

                res = call_groq(main_prompt, 4000)
                res = re.sub(r'^```json\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'^```\s*', '', res, flags=re.IGNORECASE)
                res = re.sub(r'\s*```$', '', res)
                
                data = json.loads(res.strip())
                
                st.markdown("---")
                st.header(f"Výsledek auditu: {data['verdict']}")
                st.info(data['verdict_summary'])
                
                ca, cb = st.columns(2)
                with ca:
                    st.metric("Odhadovaná férová cena", f"{data['fair_price_min']:,} - {data['fair_price_max']:,} Kč".replace(",", " "))
                with cb:
                    st.markdown("**🔧 Odhadovaný servis na 2 roky:**")
                    st.success(data['servicing_cost_2years'])
                
                st.markdown("### 💰 Tržní hodnocení ceny")
                st.write(data['price_evaluation'])
                
                st.markdown("### ⚙️ Technický stav: Motor a převodovka")
                st.write(data['engine_gearbox_analysis'])
                
                st.markdown("### ⚠️ Typické slabiny a rizika")
                for f in data.get('common_failures', []):
                    st.error(f"• {f}")
                    
                st.markdown("### 🔍 Inspekční checklist")
                for chk in data.get('inspection_checklist', []):
                    st.warning(f"✓ {chk}")
                    
                st.markdown("### 🏁 Závěrečný verdikt a doporučení")
                st.success(data['recommendation'])
                
            except Exception as e:
                st.error(f"Chyba při generování analýzy: {e}")
