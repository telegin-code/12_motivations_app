# streamlit_app.py
import os
import datetime

import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from fpdf import FPDF

from scoring import QUESTIONS, FACTOR_NAMES, calculate_factors

FONT_PATH = "Roboto-Regular.ttf"  # файл шрифта в корне проекта

# Русские описания факторов для PDF
FACTOR_DESCRIPTIONS_RU = {
    1: "Для вас важна ощутимая связь между усилиями и вознаграждением. Высокий доход, премии и бонусы — значимый источник мотивации.",
    2: "Вы цените стабильность, предсказуемость и безопасные условия труда. Сильный стресс и нестабильность снижают вашу мотивацию.",
    3: "Вам комфортно, когда есть понятные правила, регламенты и структура. Неопределённость и хаос воспринимаются как демотиваторы.",
    4: "Для вас важны хорошие отношения в команде, доверие и поддержка коллег. Конфликты и токсичная среда сильно снижают мотивацию.",
    5: "Вам важно признание результатов, уважение и статус. Вы хотите, чтобы вклад был заметен и оценён.",
    6: "Вас мотивирует возможность применять и развивать свои способности на содержательных задачах, а не «просто быть занятым».",
    7: "Вы предпочитаете интересную, осмысленную работу, в которой есть интеллектуальный вызов, а не рутину ради процесса.",
    8: "Вас заряжают разнообразие задач, новые проекты и перемены. Монотонная, однообразная работа быстро снижает мотивацию.",
    9: "Для вас важна свобода в способах достижения результата. Избыточный контроль и микроменеджмент воспринимаются как давление.",
    10: "Вас мотивируют амбициозные цели, измеримый результат и ощущение прогресса. Вам важно видеть, чего вы достигли.",
    11: "Вам нравится придумывать новые решения, улучшать процессы и подходить к задачам творчески, а не работать «по инструкции».",
    12: "Для вас важно чувствовать, что работа приносит реальную пользу людям и обществу, а не сводится только к формальному результату.",
}


def classify_level(score: int) -> str:
    """0–34 низкий, 35–69 средний, 70+ высокий уровень фактора."""
    if score >= 70:
        return "высокий"
    elif score >= 35:
        return "средний"
    return "низкий"


def build_pdf_report(name: str, factor_scores: dict) -> bytes:
    """
    Формирует PDF с мотивационным профилем участника на русском языке
    с использованием шрифта Roboto (поддержка кириллицы).
    """
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Подключаем шрифт Roboto как основной
    pdf.add_font("Roboto", "", FONT_PATH, uni=True)
    pdf.add_font("Roboto", "B", FONT_PATH, uni=True)

    pdf.add_page()

    # Заголовок
    pdf.set_font("Roboto", "B", 16)
    pdf.set_text_color(40, 40, 40)
    pdf.cell(0, 10, "Мотивационный профиль (12 факторов)", ln=True)

    pdf.set_font("Roboto", "", 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 7, f"Участник: {name}", ln=True)
    pdf.ln(3)

    pdf.set_font("Roboto", "", 10)
    pdf.multi_cell(
        0,
        5,
        "Чем выше значение фактора, тем больше он влияет на вашу мотивацию. "
        "Уровни интерпретации: 0–34 — низкий, 35–69 — средний, 70 и более — высокий.",
    )
    pdf.ln(4)

    # Таблица факторов
    pdf.set_font("Roboto", "B", 11)
    pdf.set_fill_color(230, 230, 230)
    pdf.set_text_color(20, 20, 20)

    pdf.cell(100, 8, "Фактор", border=1, fill=True)
    pdf.cell(25, 8, "Баллы", border=1, fill=True, align="C")
    pdf.cell(35, 8, "Уровень", border=1, fill=True, align="C")
    pdf.ln(8)

    pdf.set_font("Roboto", "", 10)
    pdf.set_text_color(40, 40, 40)

    # факторы по убыванию значимости
    for fid in sorted(factor_scores.keys(), key=lambda x: -factor_scores[x]):
        score = factor_scores[fid]
        level = classify_level(score)
        fname = FACTOR_NAMES.get(fid, f"Фактор {fid}")

        pdf.cell(100, 7, fname, border=1)
        pdf.cell(25, 7, str(score), border=1, align="C")
        pdf.cell(35, 7, level, border=1, align="C")
        pdf.ln(7)

    pdf.ln(4)

    # Интерпретации
    pdf.set_font("Roboto", "B", 12)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(0, 8, "Интерпретация профиля:", ln=True)
    pdf.ln(2)

    for fid in sorted(factor_scores.keys(), key=lambda x: -factor_scores[x]):
        score = factor_scores[fid]
        level = classify_level(score)
        fname = FACTOR_NAMES.get(fid, f"Фактор {fid}")
        desc = FACTOR_DESCRIPTIONS_RU.get(fid, "")

        pdf.set_font("Roboto", "B", 11)
        pdf.set_text_color(40, 40, 80)
        pdf.multi_cell(0, 6, f"{fname} — {score} баллов ({level} уровень)")

        if desc:
            pdf.set_font("Roboto", "", 10)
            pdf.set_text_color(40, 40, 40)
            pdf.multi_cell(0, 5, desc)
        pdf.ln(2)

    pdf_bytes = pdf.output(dest="S").encode("latin1")
    return pdf_bytes

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
