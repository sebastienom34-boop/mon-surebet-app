import streamlit as st
import requests
import pandas as pd

# --- CONFIGURATION ---
# Assure-toi que dans tes secrets Streamlit tu as bien "api_key" (ou adapte le nom)
API_KEY = st.secrets["api_key"]

st.set_page_config(page_title="Scanner Multi-Sports Total", layout="wide", page_icon="🚀")

st.title("🎯 Scanner de Surebets : Toutes Ligues Confondues")
st.markdown("Ce scanner analyse l'intégralité des matchs disponibles pour chaque sport (ATP, WTA, NBA, NHL, Euroleague, etc.)")

st.sidebar.header("⚙️ Paramètres")
mise_totale_cible = st.sidebar.number_input("Budget total (€)", value=100)
arrondi = st.sidebar.selectbox("Arrondir les mises à :", [1, 2, 5, 10], index=2) 

# Liste des 3 bookmakers ARJEL
BOOKIES_CIBLES = ['winamax', 'unibet_fr', 'betclic_fr']

# --- MODIFICATION ICI : CLÉS RACINES LARGES ---
# Ces clés permettent de scanner TOUT le sport sans restriction de ligue
SPORTS_KEYS = [
    'tennis', 
    'basketball', 
    'icehockey', 
    'mma', 
    'volleyball',
    'table_tennis'
]

if st.button('🚀 Lancer le Scan Global (Toutes Ligues)'):
    with st.spinner('Analyse globale en cours...'):
        results = []
        
        for sport in SPORTS_KEYS:
            # On utilise l'URL avec la clé racine du sport
            url = f'https://api.the-odds-api.com/v4/sports/{sport}/odds/?apiKey={API_KEY}&regions=eu&markets=h2h'
            
            try:
                response = requests.get(url, timeout=15)
                if response.status_code != 200: 
                    continue
                
                data = response.json()

                for match in data:
                    cotes = {}
                    for b in match.get('bookmakers', []):
                        if b['key'] in BOOKIES_CIBLES:
                            # Sécurité : on vérifie que le marché h2h existe
                            if not b.get('markets'): continue
                            
                            market = b['markets'][0]
                            outcomes = market['outcomes']
                            
                            # Uniquement sports à 2 issues (Vainqueur 1 ou 2)
                            if len(outcomes) == 2:
                                cotes[b['title']] = {o['name']: o['price'] for o in outcomes}

                    noms_bk = list(cotes.keys())
                    if len(noms_bk) >= 2:
                        for i in range(len(noms_bk)):
                            for j in range(i + 1, len(noms_bk)):
                                bk1, bk2 = noms_bk[i], noms_bk[j]
                                eqs = list(cotes[bk1].keys())
                                if len(eqs) < 2: continue
                                
                                # Test des deux sens du pari
                                combos = [
                                    (cotes[bk1][eqs[0]], cotes[bk2][eqs[1]], eqs[0], eqs[1], bk1, bk2),
                                    (cotes[bk1][eqs[1]], cotes[bk2][eqs[0]], eqs[1], eqs[0], bk1, bk2)
                                ]

                                for v1, v2, n1, n2, b1, b2 in combos:
                                    rendement = (1/v1) + (1/v2)
                                    
                                    if rendement < -5.00: # On a un Surebet
                                        m1_raw = (1/v1 / rendement) * mise_totale_cible
                                        m1 = max(arrondi, round(m1_raw / arrondi) * arrondi)
                                        m2_raw = (m1 * v1) / v2
                                        m2 = max(arrondi, round(m2_raw / arrondi) * arrondi)
                                        
                                        total = m1 + m2
                                        gain = min((m1 * v1) - total, (m2 * v2) - total)
                                        perc = (gain / total) * 100

                                        if gain > -0.5: # On tolère un léger arrondi négatif
                                            title = match['sport_title']
                                            # Emoji dynamique
                                            emoji = "🎾" if "Tennis" in title else "🏀" if "Basket" in title else "🏒" if "Hockey" in title else "🥊" if "MMA" in title else "🏐" if "Volley" in title else "🏓"
                                            
                                            results.append({
                                                'Sport': f"{emoji} {title}",
                                                'Match': f"{eqs[0]} vs {eqs[1]}",
                                                'Profit %': f"{round(perc, 2)}%",
                                                'Pari 1': f"{int(m1)}€ sur {b1} ({n1} @{v1})",
                                                'Pari 2': f"{int(m2)}€ sur {b2} ({n2} @{v2})",
                                                'Gain Net': f"{round(gain, 2)}€",
                                                'Total': f"{int(total)}€"
                                            })
            except Exception as e:
                st.error(f"Erreur sur le sport {sport}: {e}")
                continue

        if results:
            st.success(f"✅ {len(results)} opportunités trouvées !")
            df = pd.DataFrame(results).sort_values(by='Profit %', ascending=False)
            st.table(df)
        else:
            st.info("Aucun surebet détecté. Les bookmakers sont bien alignés pour l'instant.")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Conseil :** Avec les clés globales, le scan est plus long mais trouve beaucoup plus de matchs 'exotiques' souvent très rentables.")
