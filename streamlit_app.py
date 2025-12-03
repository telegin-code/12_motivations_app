# streamlit_app.py
import os
import datetime

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from scoring import QUESTIONS, FACTOR_NAMES, calculate_factors

RESULTS_FILE = "results.csv"


def load_results():
    if os.path.exists(RESULTS_FILE):
        return pd.read_csv(RESULTS_FILE)
    else:
        return pd.DataFrame(
            columns=["timestamp", "name"] + list(FACTOR_NAMES.values())
        )


def save_result(name, factor_scores):
    df = load_results()
    row = {
        "timestamp": datetime.datetime.now().isoformat(timespec="seconds"),
        "name": name,
    }
    for fid, score in factor_scores.items():
        row[FACTOR_NAMES[fid]] = score
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(RESULTS_FILE, index=False)


def show_radar_chart(factor_scores, title="Мотивационный профиль"):
    labels = [FACTOR_NAMES[fid] for fid in sorted(factor_scores.keys())]
    values = [factor_scores[fid] for fid in sorted(factor_scores.keys())]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=labels + [labels[0]],
        fill="toself",
        name="Профиль",
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True)
        ),
        showlegend=False,
        title=title,
        margin=dict(l=40, r=40, t=60, b=40),
    )
    st.plotly_chart(fig, use_container_width=True)


def show_bar_chart(factor_scores, title="12 факторов мотивации"):
    labels = [FACTOR_NAMES[fid] for fid in sorted(factor_scores.keys())]
    values = [factor_scores[fid] for fid in sorted(factor_scores.keys())]
    fig = go.Figure(
        data=[go.Bar(x=labels, y=values)]
    )
    fig.update_layout(
        title=title,
        xaxis_tickangle=-45,
        margin=dict(l=40, r=40, t=60, b=120),
    )
    st.plotly_chart(fig, use_container_width=True)


def app():
    st.set_page_config(
        page_title="Мотивационный профиль (12 факторов)",
        layout="wide"
    )
    st.title("Мотивационный опросник: 12 факторов мотивационного профиля")

    st.markdown(
        """
        Этот опросник позволяет определить ваш индивидуальный мотивационный профиль
        по 12 факторам (модель Ричи–Мартина).  

        В каждом вопросе распределите **11 баллов** между четырьмя вариантами ответа.
        Можно использовать любую комбинацию (например, 11-0-0-0, 5-4-2-0 и т.д.),  
        но **сумма по вопросу всегда должна быть равна 11**.
        """
    )

    tab1, tab2, tab3 = st.tabs(
        ["📝 Пройти тест", "📊 Мой результат (эта сессия)", "📈 Групповой дашборд"]
    )

    # ---------- TAB 1: ПРОЙТИ ТЕСТ ----------
    with tab1:
        st.header("Шаг 1. Заполните опросник")
        name = st.text_input("Ваше имя (для индивидуального отчёта):", "")

        if "answers" not in st.session_state:
            st.session_state["answers"] = {}

        form = st.form("questionnaire")
        form.write("Для каждого вопроса распределите 11 баллов между вариантами a, b, c, d.")

        for q in QUESTIONS:
            form.markdown(f"**{q['num']}. {q['text']}**")
            cols = form.columns(4)
            for i, opt in enumerate(["a", "b", "c", "d"]):
                label = f"{opt}) {q['options'][opt]}"
                key = f"q{q['num']}_{opt}"
                # значение по умолчанию — из session_state, если уже есть
                default_val = st.session_state["answers"].get((q["num"], opt), 0)
                val = cols[i].number_input(
                    label,
                    min_value=0,
                    max_value=11,
                    step=1,
                    key=key,
                    value=default_val,
                )
                st.session_state["answers"][(q["num"], opt)] = val

            form.markdown("---")

        submitted = form.form_submit_button("Отправить ответы и рассчитать профиль")

        if submitted:
            # Валидация сумм по вопросам
            errors = []
            for q in QUESTIONS:
                s = 0
                for opt in ["a", "b", "c", "d"]:
                    s += st.session_state["answers"].get((q["num"], opt), 0)
                if s != 11:
                    errors.append(f"Вопрос {q['num']}: сумма баллов = {s}, должна быть 11")

            if not name.strip():
                st.error("Пожалуйста, введите имя.")
            elif errors:
                st.error("Найдены ошибки в распределении баллов:")
                for e in errors:
                    st.write("• " + e)
                st.info("Исправьте суммы и нажмите кнопку ещё раз.")
            else:
                factor_scores = calculate_factors(st.session_state["answers"])
                st.session_state["factor_scores"] = factor_scores
                st.success("Ответы сохранены, мотивационный профиль рассчитан.")
                # Сохранение результата в CSV
                save_result(name.strip(), factor_scores)
                st.info("Ваш результат также учтён в групповом дашборде.")
                st.write("Ниже — ваш профиль мотивации.")
                show_radar_chart(factor_scores, title=f"Профиль {name}")
                show_bar_chart(factor_scores, title="12 факторов мотивации")

    # ---------- TAB 2: МОЙ РЕЗУЛЬТАТ ----------
    with tab2:
        st.header("Ваш результат в текущей сессии")
        if "factor_scores" not in st.session_state:
            st.info("Сначала заполните опросник на вкладке «Пройти тест».")
        else:
            factor_scores = st.session_state["factor_scores"]
            name_for_pdf = st.session_state.get("participant_name", "Участник")

            show_radar_chart(factor_scores, title="Ваш мотивационный профиль")
            show_bar_chart(factor_scores, title="Ваши значения по 12 факторам")

            st.subheader("Таблица факторов")
            df_ind = pd.DataFrame(
                {
                    "Фактор": [
                        FACTOR_NAMES[fid] for fid in sorted(factor_scores.keys())
                    ],
                    "Баллы": [
                        factor_scores[fid] for fid in sorted(factor_scores.keys())
                    ],
                }
            )
            st.dataframe(df_ind, use_container_width=True)

            st.subheader("Скачать индивидуальный PDF-отчёт")
            pdf_bytes = build_pdf_report(name_for_pdf, factor_scores)
            safe_name = name_for_pdf.replace(" ", "_")
            st.download_button(
                label="📄 Скачать PDF-отчёт",
                data=pdf_bytes,
                file_name=f"motivation_profile_{safe_name}.pdf",
                mime="application/pdf",
            )

    # ---------- TAB 3: ГРУППОВОЙ ДАШБОРД ----------
    with tab3:
        st.header("Групповой дашборд")
        df = load_results()
        if df.empty:
            st.info("Пока нет данных. Результаты появятся после первых прохождений теста.")
        else:
            st.write(f"Всего результатов: **{len(df)}**")
            st.dataframe(df, use_container_width=True)

            # Средние значения по факторам
            factor_cols = list(FACTOR_NAMES.values())
            mean_scores = df[factor_cols].mean().to_dict()
            st.subheader("Средние значения по факторам (группа)")
            mean_factor_scores = {
                fid: mean_scores[FACTOR_NAMES[fid]] for fid in FACTOR_NAMES.keys()
            }
            show_bar_chart(
                mean_factor_scores,
                title="Средние значения факторов (группа)"
            )

            st.markdown(
                "_При желании сюда можно добавить фильтры по факультетам, уровням N-2/N-3 и др., "
                "если в results.csv будут соответствующие столбцы._"
            )


if __name__ == "__main__":
    app()
