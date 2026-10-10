
import os
import requests
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Football Stats",
    page_icon="⚽",
    layout="wide"
)

LEAGUES = {
    "Premier League": "PL",
    "La Liga": "PD",
    "Liga Portugal Betclic": "PPL",
    "Bundesliga": "BL1",
    "Ligue 1": "FL1",
}

BASE_URL = "https://api.football-data.org/v4"


def get_token():
    try:
        token = st.secrets.get("FOOTBALL_DATA_TOKEN", "")
    except Exception:
        token = ""
    return token or os.getenv("FOOTBALL_DATA_TOKEN", "")


@st.cache_data(ttl=900)
def api_request(endpoint, token, params=None):
    response = requests.get(
        f"{BASE_URL}/{endpoint}",
        headers={"X-Auth-Token": token},
        params=params,
        timeout=20,
    )
    response.raise_for_status()
    return response.json()


def get_standings(token, code):
    data = api_request(f"competitions/{code}/standings", token)
    tables = data.get("standings", [])
    table = next(
        (t for t in tables if t.get("type") == "TOTAL"),
        tables[0] if tables else None,
    )

    if not table:
        return pd.DataFrame()

    rows = []
    for item in table.get("table", []):
        team = item.get("team", {})
        rows.append({
            "Posição": item.get("position"),
            "Equipa": team.get("name"),
            "Jogos": item.get("playedGames"),
            "Vitórias": item.get("won"),
            "Empates": item.get("draw"),
            "Derrotas": item.get("lost"),
            "Golos marcados": item.get("goalsFor"),
            "Golos sofridos": item.get("goalsAgainst"),
            "Diferença": item.get("goalDifference"),
            "Pontos": item.get("points"),
        })

    return pd.DataFrame(rows)


def get_matches(token, code):
    data = api_request(
        f"competitions/{code}/matches",
        token,
        {"status": "FINISHED", "limit": 100},
    )

    rows = []
    for match in data.get("matches", []):
        home = match.get("homeTeam") or {}
        away = match.get("awayTeam") or {}
        score = match.get("score", {}).get("fullTime", {})

        rows.append({
            "Data": match.get("utcDate", "")[:10],
            "Equipa da casa": home.get("name"),
            "Golos casa": score.get("home"),
            "Golos fora": score.get("away"),
            "Equipa visitante": away.get("name"),
        })

    return pd.DataFrame(rows)


def main():
    st.title("⚽ Football Stats")
    st.write(
        "Explora classificações, resultados e estatísticas "
        "das principais ligas europeias."
    )

    with st.sidebar:
        st.header("Configurações")
        league = st.selectbox("Escolhe a liga", list(LEAGUES.keys()))

    token = get_token()

    if not token:
        st.error(
            "Falta configurar a chave da API. "
            "Adiciona FOOTBALL_DATA_TOKEN nos Secrets do Streamlit."
        )
        st.stop()

    code = LEAGUES[league]
    st.subheader(f"🏆 {league}")

    tab1, tab2, tab3 = st.tabs([
        "Classificação",
        "Resultados",
        "Comparação",
    ])

    with tab1:
        try:
            with st.spinner("A carregar classificação..."):
                standings = get_standings(token, code)

            if standings.empty:
                st.info("Não há classificação disponível.")
            else:
                st.dataframe(
                    standings,
                    use_container_width=True,
                    hide_index=True,
                )
                st.bar_chart(standings.set_index("Equipa")["Pontos"])

                st.download_button(
                    "Descarregar classificação CSV",
                    standings.to_csv(index=False).encode("utf-8-sig"),
                    f"{code}_classificacao.csv",
                    "text/csv",
                )

        except requests.HTTPError as error:
            st.error(
                f"Erro da API: HTTP {error.response.status_code}. "
                "Confirma a chave e as permissões do teu plano."
            )
        except requests.RequestException as error:
            st.error(f"Erro de ligação: {error}")

    with tab2:
        try:
            with st.spinner("A carregar resultados..."):
                matches = get_matches(token, code)

            if matches.empty:
                st.info("Não foram encontrados resultados.")
            else:
                st.dataframe(
                    matches.sort_values("Data", ascending=False),
                    use_container_width=True,
                    hide_index=True,
                )
        except requests.HTTPError as error:
            st.error(f"Erro da API: HTTP {error.response.status_code}.")
        except requests.RequestException as error:
            st.error(f"Erro de ligação: {error}")

    with tab3:
        try:
            standings = get_standings(token, code)
            teams = standings["Equipa"].dropna().tolist()

            if len(teams) >= 2:
                col1, col2 = st.columns(2)

                team1 = col1.selectbox(
                    "Primeira equipa", teams, key="team1"
                )
                team2 = col2.selectbox(
                    "Segunda equipa", teams, index=1, key="team2"
                )

                selected = standings[
                    standings["Equipa"].isin([team1, team2])
                ].set_index("Equipa")

                st.dataframe(
                    selected,
                    use_container_width=True,
                )
            else:
                st.info("Não há equipas suficientes para comparar.")

        except (requests.RequestException, KeyError) as error:
            st.error(f"Não foi possível comparar: {error}")


if __name__ == "__main__":
    main()
