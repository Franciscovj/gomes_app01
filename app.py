import streamlit as st
import pandas as pd
import plotly.express as px

def get_ranking_data(df, search_query=""):
    df0 = df[
        [
            "Liga",
            "Minuto",
            "Hora",
            "TimeA",
            "TimeB",
            "TimeA_Gols",
            "TimeB_Gols",
            "VencedorFT_Casa",
            "VencedorFT_Visitante",
            "TimeGols_Casa5mais",
            "TimeGols_Visitante5mais",
        ]
    ].copy()

    # Conversões
    df0["TimeA_Gols"] = pd.to_numeric(df0["TimeA_Gols"], errors="coerce").fillna(0).astype(int)
    df0["TimeB_Gols"] = pd.to_numeric(df0["TimeB_Gols"], errors="coerce").fillna(0).astype(int)
    df0["Minuto"] = pd.to_numeric(df0["Minuto"], errors="coerce").fillna(0).astype(int)
    df0["Hora"] = pd.to_numeric(df0["Hora"], errors="coerce").fillna(0).astype(int)
    df0["Total_Gols"] = df0["TimeA_Gols"] + df0["TimeB_Gols"]
    df0["confronto"] = df0["TimeA"] + " x " + df0["TimeB"]

    # Filtro de pesquisa por Hora
    if search_query:
        df0 = df0[df0["Hora"].astype(str).str.contains(search_query, case=False, na=False)]

    # Ranking por Hora
    ranking_por_hora = (
        df0.groupby("Hora")["Total_Gols"]
        .sum()
        .reset_index()
        .sort_values("Total_Gols", ascending=False)
    )
    ranking_por_hora["Rank"] = (
        ranking_por_hora["Total_Gols"].rank(method="min", ascending=False).astype(int)
    )

    # Ranking de Confrontos: Soma e Média
    confrontos_agg = (
        df0.groupby("confronto")["Total_Gols"]
        .agg(Total_Gols_Soma="sum", Jogos="count")
        .reset_index()
    )
    confrontos_agg["Media_Gols"] = (confrontos_agg["Total_Gols_Soma"] / confrontos_agg["Jogos"]).round(2)
    confrontos_agg = confrontos_agg.sort_values("Total_Gols_Soma", ascending=False)
    confrontos_agg["Rank_Soma"] = (
        confrontos_agg["Total_Gols_Soma"].rank(method="min", ascending=False).astype(int)
    )
    confrontos_agg["Rank_Media"] = (
        confrontos_agg["Media_Gols"].rank(method="min", ascending=False).astype(int)
    )

    # Ranking por Minuto
    ranking_minuto = (
        df0.groupby("Minuto")["Total_Gols"]
        .sum()
        .reset_index()
        .sort_values("Total_Gols", ascending=False)
    )

    # Odds: soma, jogos e média de gols por valor único
    odds_cols = [
        "VencedorFT_Casa",
        "VencedorFT_Visitante",
        "TimeGols_Casa5mais",
        "TimeGols_Visitante5mais",
    ]
    odds_stats = {}
    for col in odds_cols:
        stats = (
            df0.groupby(col)["Total_Gols"]
            .agg(Soma_Gols="sum", Jogos="count")
            .reset_index()
        )
        stats["Media_Gols"] = (stats["Soma_Gols"] / stats["Jogos"]).round(2)
        stats = stats.sort_values("Media_Gols", ascending=False)
        odds_stats[col] = stats

    # Estatísticas por TimeA e TimeB
    timeA_stats = (
        df0.groupby(["Minuto", "TimeA"]).agg(
            Total_Gols=("TimeA_Gols", "sum"), Jogos=("TimeA_Gols", "count")
        ).reset_index()
    )
    timeA_stats["Media_Gols_Minuto"] = (timeA_stats["Total_Gols"] / timeA_stats["Jogos"]).round(2)
    timeA_stats = timeA_stats.sort_values("Total_Gols", ascending=False)

    timeB_stats = (
        df0.groupby(["Minuto", "TimeB"]).agg(
            Total_Gols=("TimeB_Gols", "sum"), Jogos=("TimeB_Gols", "count")
        ).reset_index()
    )
    timeB_stats["Media_Gols_Minuto"] = (timeB_stats["Total_Gols"] / timeB_stats["Jogos"]).round(2)
    timeB_stats = timeB_stats.sort_values("Total_Gols", ascending=False)

    return (
        ranking_por_hora,
        confrontos_agg,
        ranking_minuto,
        timeA_stats,
        timeB_stats,
        odds_stats,
    )


def main():
    st.set_page_config(
        page_title="Dashboard de Gols", layout="wide", initial_sidebar_state="expanded"
    )

    st.sidebar.header("📁 Dados e Filtros")
    uploaded_file = st.sidebar.file_uploader("Envie seu CSV:", type=["csv"])
    search_text = st.sidebar.text_input("🔎 Pesquisar por Hora:", "")
    st.sidebar.markdown("---")

    if not uploaded_file:
        st.warning("📌 Por favor, envie um arquivo CSV para visualizar o dashboard.")
        return

    df = pd.read_csv(uploaded_file)
    for col in ["TimeA_Gols", "TimeB_Gols", "Minuto", "Hora"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    df["Total_Gols"] = df["TimeA_Gols"] + df["TimeB_Gols"]
    df['Over35'] = df['Total_Gols'].apply(lambda x: 1 if x > 3 else 0)
    df['Over45_HT'] = df['Total_Gols'].apply(lambda x: 1 if x > 4 else 0)
    df['Over55_HT'] = df['Total_Gols'].apply(lambda x: 1 if x > 5 else 0)

    ligas = st.sidebar.multiselect(
        "Ligas", options=sorted(df["Liga"].unique()), default=sorted(df["Liga"].unique())
    )

    todos_times = sorted(set(df["TimeA"].unique()) | set(df["TimeB"].unique()))
    selecionar_todos_times = st.sidebar.checkbox("Selecionar todos os times", value=False)

    if selecionar_todos_times:
        equipes_selecionadas = st.sidebar.multiselect(
            "Times (TimeA/TimeB)", options=todos_times, default=todos_times
        )
    else:
        equipes_selecionadas = st.sidebar.multiselect(
            "Times (TimeA/TimeB)", options=todos_times, default=[]
        )

    hora_range = st.sidebar.slider(
        "Horário (Hora)", int(df["Hora"].min()), int(df["Hora"].max()),
        (int(df["Hora"].min()), int(df["Hora"].max()))
    )

    minuto_range = st.sidebar.slider(
        "Minuto do Jogo", int(df["Minuto"].min()), int(df["Minuto"].max()),
        (int(df["Minuto"].min()), int(df["Minuto"].max()))
    )

    min_gols = st.sidebar.slider(
        "Gols Mínimos no Lance", int(df["Total_Gols"].min()), int(df["Total_Gols"].max()), int(df["Total_Gols"].min())
    )

    df_filtered = df[
        df["Liga"].isin(ligas)
        & ((df["TimeA"].isin(equipes_selecionadas)) | (df["TimeB"].isin(equipes_selecionadas)))
        & df["Hora"].between(hora_range[0], hora_range[1])
        & df["Minuto"].between(minuto_range[0], minuto_range[1])
        & (df["Total_Gols"] >= min_gols)
    ].copy()

    (
        ranking_por_hora,
        confrontos_agg,
        ranking_minuto,
        timeA_stats,
        timeB_stats,
        odds_stats,
    ) = get_ranking_data(df_filtered, search_text)

    st.title("📊 Dashboard de Gols por Hora e Minuto")

    # Métricas principais (com inclusão das % de Over/Under)
    if not ranking_por_hora.empty:
        top_hour = ranking_por_hora.iloc[0]
        c1, c2, c3 = st.columns(3)
        c1.metric("Horário com mais gols", f"{top_hour['Hora']}")
        c2.metric("Total de gols neste horário", f"{top_hour['Total_Gols']}")
        c3.metric("Posição no ranking", f"{top_hour['Rank']}")
        st.markdown("---")
        # cálculo das porcentagens
        c4, c5, c6 = st.columns(3)
        pct_over35    = df_filtered["Over35"].mean()    * 100
        pct_over45_ht = df_filtered["Over45_HT"].mean() * 100
        pct_under55_ht= df_filtered["Over55_HT"].mean()* 100
        c4.metric("% Over 3.5 Gols", f"{pct_over35:.2f}%")
        c5.metric("% Over 4.5 Gols", f"{pct_over45_ht:.2f}%")
        c6.metric("% Over 5.5 Gols", f"{pct_under55_ht:.2f}%")

    # Ranking por Hora
    st.markdown('<hr style="border: 1px solid blue;">', unsafe_allow_html=True)
    st.subheader("⏰Ranking por Hora")
    st.dataframe(
        ranking_por_hora[["Hora", "Total_Gols", "Rank"]].reset_index(drop=True)
        .style.format({"Total_Gols": "{:,.0f}", "Rank": "{:d}"}), use_container_width=True,
    )
    fig_hora = px.bar(ranking_por_hora, x="Hora", y="Total_Gols",
                      labels={"Hora": "Hora", "Total_Gols": "Total de Gols"},
                      title="Gols por Hora", template="plotly_white")
    st.plotly_chart(fig_hora, use_container_width=True)

    # Ranking de Confrontos
    st.markdown('<hr style="border: 1px solid green;">', unsafe_allow_html=True)
    st.subheader("✔️Ranking de Confrontos com Mais Gols")
    st.dataframe(
        confrontos_agg[["confronto", "Total_Gols_Soma", "Media_Gols", "Rank_Soma", "Rank_Media"]]
        .rename(columns={
            "confronto": "Confronto",
            "Total_Gols_Soma": "Total de Gols",
            "Media_Gols": "Média de Gols",
            "Rank_Soma": "Rank (Soma)",
            "Rank_Media": "Rank (Média)"
        })
        .reset_index(drop=True), use_container_width=True
    )
    fig_confrontos = px.bar(confrontos_agg, x="confronto", y="Total_Gols_Soma",
                            labels={"confronto": "Confronto", "Total_Gols_Soma": "Total de Gols"},
                            title="Total de Gols por Confronto", template="plotly_white")
    st.plotly_chart(fig_confrontos, use_container_width=True)

    # Odds vs Média de Gols
    st.markdown('<hr style="border: 1px solid teal;">', unsafe_allow_html=True)
    st.subheader("🎲 Odds vs Médio de Gols")
    for col, stats in odds_stats.items():
        st.markdown(f"**{col}**")
        st.dataframe(
            stats.rename(columns={col: "Valor Odds", "Soma_Gols": "Total de Gols",
                                   "Jogos": "Nº Jogos", "Media_Gols": "Média de Gols"}),
            use_container_width=True,
        )


    # Ranking por Minuto
    st.markdown('<hr style="border: 1px solid red;">', unsafe_allow_html=True)
    st.subheader("⌚Minutos com Mais Gols")
    st.dataframe(ranking_minuto, use_container_width=True)

    # Times que mais marcam por Minuto
    st.markdown('<hr style="border: 1px solid purple;">', unsafe_allow_html=True)
    st.subheader("⚽ Times que Mais Marcam por Minuto (TimeA)")
    st.dataframe(
        timeA_stats.rename(columns={"TimeA": "Time", "Total_Gols": "Gols",
                                     "Media_Gols_Minuto": "Média por Minuto"}),
        use_container_width=True,
    )
    fig_timeA = px.bar(timeA_stats, x="TimeA", y="Total_Gols",
                       labels={"TimeA": "Time", "Total_Gols": "Total de Gols"},
                       title="Gols do TimeA por Minuto", template="plotly_white")
    st.plotly_chart(fig_timeA, use_container_width=True)

    # Times que mais marcam por Minuto
    st.markdown('<hr style="border: 1px solid purple;">', unsafe_allow_html=True)
    st.subheader("⚽ Times que Mais Marcam por Minuto (TimeB)")
    st.dataframe(
        timeB_stats.rename(columns={"TimeB": "Time", "Total_Gols": "Gols",
                                     "Media_Gols_Minuto": "Média por Minuto"}),
        use_container_width=True,
    )
    fig_timeB = px.bar(timeB_stats, x="TimeB", y="Total_Gols",
                       labels={"TimeB": "Time", "Total_Gols": "Total de Gols"},
                       title="Gols do TimeB por Minuto", template="plotly_white")
    st.plotly_chart(fig_timeB, use_container_width=True)

if __name__ == "__main__":
    main()
