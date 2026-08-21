import streamlit as st
import openai
import json

# Nastavení stránky
st.set_page_config(page_title="AutoCheck CZ", page_icon="🚗")

st.title("🚗 AutoCheck CZ")
st.subheader("Rychlá analýza ojetiny pomocí AI (zdarma přes Groq)")

# Sidebar pro API klíč
st.sidebar.markdown("### Jak získat klíč zdarma:")
st.sidebar.markdown("1. Jdi na [console.groq.com/keys](https://console.groq.com/keys)")
st.sidebar.markdown("2. Přihlas se (např. Google účtem)")
st.sidebar.markdown("3. Vygeneruj a vlož klíč níže:")

api_key = st.sidebar.text_input("Groq API Key", type="password")

# Formulář
with st.form("car_form"):
    col1, col2 = st.columns(2)
    model = col1.text_input("Značka a model", value="Škoda Octavia 1.5 TSI")
    year = col2.number_input("Rok výroby", min_value=1990, max_value=2026, value=2021)
    
    km = col1.number_input("Nájezd (km)", min_value=0, value=118000)
    price = col2.number_input("Cena (Kč)", min_value=0, value=399000)
    
    fuel = st.selectbox("Palivo", ["Benzín", "Nafta", "Hybrid", "Elektro"])
    gearbox = st.selectbox("Převodovka", ["Manuální", "Automatická"])
    
    submitted = st.form_submit_button("Analyzovat nabídku")

if submitted:
    if not api_key:
        st.error("Prosím, vlož v levém panelu svůj Groq API klíč.")
    else:
        with st.spinner('AI analyzuje data...'):
            # Inicializujeme klienta s Groq endpointem
            client = openai.OpenAI(
                base_url="https://api.groq.com/openai/v1",
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
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.3
                )
                
                result_text = response.choices[0].message.content.strip()
                # Ošetření, kdyby model přesto přidal markdown
                if result_text.startswith("```json"):
                    result_text = result_text[7:]
                if result_text.endswith("```"):
                    result_text = result_text[:-3]
                    
                data = json.loads(result_text.strip())
                
                # Zobrazení výsledků
                st.subheader(f"Výsledek: {data['verdict']}")
                
                st.metric("Odhadovaná férová cena", f"{data['fair_price_min']:,} - {data['fair_price_max']:,} Kč")
                st.write(f"**Poměr cena/nájezd:** {data['price_ratio_text']}")
                st.write(f"**Odhad servisu (2 roky):** {data['servicing_cost']}")
                
                st.write("### 🔍 Co zkontrolovat")
                for item in data['checklist']:
                    st.write(f"- {item}")
                    
            except Exception as e:
                st.error(f"Nastala chyba při zpracování: {e}")
