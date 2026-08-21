import streamlit as st
import openai
import json

# Nastavení stránky
st.set_page_config(page_title="AutoCheck CZ", page_icon="🚗")

st.title("🚗 AutoCheck CZ")
st.subheader("Chytrá analýza ojetiny s podporou AI")

# Sidebar pro API klíč
st.sidebar.markdown("### Groq API Klíč (Zdarma)")
api_key = st.sidebar.text_input("Vlož svůj Groq API Key", type="password")

# --- SEKCE PRO NAČTENÍ Z TEXTU INZERÁTU ---
st.markdown("### 📋 Automatické vyplnění z inzerátu")
st.markdown("Zkopíruj text inzerátu (např. popis a parametry z bazoše nebo sauta) sem:")

ad_text_input = st.text_area("Text inzerátu", placeholder="Sem vlož zkopírovaný text inzerátu...")

if "form_model" not in st.session_state:
    st.session_state.form_model = "Škoda Octavia 1.5 TSI"
    st.session_state.form_year = 2021
    st.session_state.form_km = 118000
    st.session_state.form_price = 399000
    st.session_state.form_fuel = "Benzín"
    st.session_state.form_gearbox = "Manuální"

if st.button("✨ Načíst data z textu"):
    if not api_key:
        st.error("Pro chytré načtení nejprve vlož Groq API klíč v levém panelu.")
    elif not ad_text_input.strip():
        st.warning("Vlož nejdřív text inzerátu.")
    else:
        with st.spinner("AI čte inzerát..."):
            try:
                client = openai.OpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=api_key
                )
                parse_prompt = f"""
                Jsi parser inzerátů ojetých aut. Z následujícího textu inzerátu vytáhni údaje a vrať POUZE validní JSON (bez markdownu ```json):
                Text inzerátu: "{ad_text_input}"
                
                Struktura JSON:
                {{
                    "model": "přesná značka a model auta (např. Škoda Superb 2.0 TDI)",
                    "year": rok výroby jako celé číslo (např. 2020),
                    "km": nájezd v km jako celé číslo (např. 150000),
                    "price": cena v Kč jako celé číslo (např. 450000),
                    "fuel": "Benzín" nebo "Nafta" nebo "Hybrid" nebo "Elektro",
                    "gearbox": "Manuální" nebo "Automatická"
                }}
                """
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": parse_prompt}],
                    temperature=0.1
                )
                res_text = response.choices[0].message.content.strip()
                if res_text.startswith("```json"): res_text = res_text[7:]
                if res_text.endswith("```"): res_text = res_text[:-3]
                
                parsed_data = json.loads(res_text.strip())
                
                st.session_state.form_model = parsed_data.get("model", st.session_state.form_model)
                st.session_state.form_year = int(parsed_data.get("year", st.session_state.form_year))
                st.session_state.form_km = int(parsed_data.get("km", st.session_state.form_km))
                st.session_state.form_price = int(parsed_data.get("price", st.session_state.form_price))
                st.session_state.form_fuel = parsed_data.get("fuel", st.session_state.form_fuel)
                st.session_state.form_gearbox = parsed_data.get("gearbox", st.session_state.form_gearbox)
                
                st.success("Údaje z inzerátu úspěšně načteny do formuláře níže!")
            except Exception as e:
                st.error(f"Detail chyby při načítání: {e}")

st.markdown("---")

# --- HLAVNÍ FORMULÁŘ ---
with st.form("car_form"):
    st.markdown("### 🚗 Parametry vozidla (zkontroluj / uprav)")
    col1, col2 = st.columns(2)
    model = col1.text_input("Značka a model", value=st.session_state.form_model)
    year = col2.number_input("Rok výroby", min_value=1990, max_value=2026, value=st.session_state.form_year)
    
    km = col1.number_input("Nájezd (km)", min_value=0, value=st.session_state.form_km)
    price = col2.number_input("Cena (Kč)", min_value=0, value=st.session_state.form_price)
    
    fuel_options = ["Benzín", "Nafta", "Hybrid", "Elektro"]
    default_fuel_idx = fuel_options.index(st.session_state.form_fuel) if st.session_state.form_fuel in fuel_options else 0
    fuel = st.selectbox("Palivo", fuel_options, index=default_fuel_idx)
    
    gearbox_options = ["Manuální", "Automatická"]
    default_gear_idx = gearbox_options.index(st.session_state.form_gearbox) if st.session_state.form_gearbox in gearbox_options else 0
    gearbox = st.selectbox("Převodovka", gearbox_options, index=default_gear_idx)
    
    submitted = st.form_submit_button("🔍 Analyzovat nabídku")

if submitted:
    if not api_key:
        st.error("Prosím, vlož v levém panelu svůj Groq API klíč.")
    else:
        with st.spinner('AI analyzuje trh a staví verdikt...'):
            client = openai.OpenAI(
                base_url="[https://api.groq.com/openai/v1](https://api.groq.com/openai/v1)",
                api_key=api_key
            )
            
            prompt = f"""
            Jsi špičkový český automechanik a expert na trh ojetých vozů v ČR. 
            Analyzuj toto auto: Model: {model}, Rok: {year}, Nájezd: {km} km, Cena: {price} Kč, Palivo: {fuel}, Převodovka: {gearbox}.
            Vrať odpověď POUZE jako validní JSON objekt s těmito klíči (bez markdown formátování jako ```json):
            {{
                "verdict": "🟢 ZAJÍMAVÁ NABÍDKA" nebo "🟡 MÍRNĚ PŘEDRAŽENO" nebo "🔴 PŘEDRAŽENO / NEBRAT",
                "fair_price_min": odhadovaná minimální férová cena v Kč (číslo),
                "fair_price_max": odhadovaná maximální férová cena v Kč (číslo),
                "price_ratio_text": "krátký text o poměru ceny a nájezdu v češtině",
                "servicing_cost": "odhad servisu na 2 roky (např. 25 000 – 40 000 Kč)",
                "checklist": [
                    "položka kontroly 1",
                    "položka kontroly 2",
                    "položka kontroly 3",
                    "položka kontroly 4",
                    "položka kontroly 5"
                ]
            }}
            """
            
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                result_text = response.choices[0].message.content.strip()
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                    
                data = json.loads(result_text.strip())
                
                st.subheader(f"Výsledek: {data['verdict']}")
                st.metric("Odhadovaná férová cena", f"{data['fair_price_min']:,} - {data['fair_price_max']:,} Kč")
                st.write(f"**Poměr cena/nájezd:** {data['price_ratio_text']}")
                st.write(f"**Odhad servisu (2 roky):** {data['servicing_cost']}")
                
                st.write("### 🔍 Co zkontrolovat")
                for item in data['checklist']:
                    st.write(f"- {item}")
                    
            except Exception as e:
                st.error(f"Detail chyby při analýze: {e}")
