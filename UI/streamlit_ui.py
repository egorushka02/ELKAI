# streamlit_app.py
import streamlit as st
import requests
import pandas as pd
import json

st.set_page_config(page_title="ELK AI Agent", page_icon="🎄", layout="wide")

API_URL = st.sidebar.text_input("FastAPI base URL", value="http://localhost:8000")
st.sidebar.markdown("---")

# «Табы» через radio на sidebar
mode = st.sidebar.radio(
    "Выберите режим",
    ["🪄 Сгенерировать KQL", "🔍 Выполнить KQL", "🧠 Deep Research"],
)

st.title("🎄 ELK AI Agent – Windows Logs")

# ---------- 1. Генерация ----------
if mode == "🪄 Сгенерировать KQL":
    st.header("Сгенерировать KQL")
    desc = st.text_area("Опишите, что найти (rus/eng):", height=80)
    if st.button("Сгенерировать"):
        if not desc.strip():
            st.warning("Введите описание")
        else:
            with st.spinner("LLM думает..."):
                resp = requests.post(f"{API_URL}/kql/generate", json={"description": desc})
                if resp.ok:
                    kql = resp.json()["kql"]
                    st.code(kql, language="sql")
                    st.session_state["kql"] = kql
                else:
                    st.error(resp.text)

# ---------- 2. Выполнение ----------
elif mode == "🔍 Выполнить KQL":
    st.header("Выполнить KQL")
    kql = st.text_area("KQL:", value=st.session_state.get("kql", ""), height=80)
    size = st.number_input("Кол-во документов", 1, 10_000, 100)
    if st.button("Выполнить"):
        if not kql.strip():
            st.warning("KQL пусто")
        else:
            with st.spinner("Elasticsearch..."):
                resp = requests.post(f"{API_URL}/kql/execute", json={"kql": kql, "size": size})
                if resp.ok:
                    data = resp.json()
                    st.success(f"Найдено: {data['total']}")
                    df = pd.json_normalize(data["hits"])
                    st.dataframe(df, use_container_width=True)

                    json_str = json.dumps(data["hits"], indent=2, ensure_ascii=False)
                    st.download_button("Скачать JSON", json_str, "hits.json", "application/json")
                else:
                    st.error(resp.text)

# ---------- 3. Deep Research ----------
elif mode == "🧠 Deep Research":
    st.header("Deep Research")
    goal = st.text_area("Цель исследования:", height=80)
    max_iter = st.slider("Шагов уточнения", 1, 10, 3)
    if st.button("Старт"):
        if not goal.strip():
            st.warning("Цель не задана")
        else:
            with st.spinner("Исследование..."):
                resp = requests.post(f"{API_URL}/research/deep", json={"description": goal, "max_iterations": max_iter})
                if resp.ok:
                    d = resp.json()
                    st.info(d["summary"])
                    with st.expander("Итоговый KQL"):
                        st.code(d["kql_used"], language="sql")
                    df = pd.json_normalize(d["sample_hits"])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.error(resp.text)