import base64
import json
from datetime import date, datetime, time, timedelta

import pandas as pd
import streamlit as st
from github import Github
from github import GithubException


# ============================================================
# Login
# ============================================================

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password = st.text_input("Passwort", type="password")

    if st.button("Anmelden"):
        stored_hash = st.secrets["PASSWORD_HASH"]

        if bcrypt.checkpw(
            password.encode(),
            stored_hash.encode()
        ):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Falsches Passwort")

    st.stop()


# ============================================================
# KONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Semesterplaner",
    page_icon="📚",
    layout="wide",
)


# ============================================================
# GITHUB / DATENSPEICHER
# ============================================================

def get_github_config():
    """Liest die GitHub-Konfiguration aus Streamlit Secrets."""

    token = st.secrets["GITHUB"]["TOKEN"]
    repo_name = st.secrets["GITHUB"]["REPO"]
    file_path = st.secrets["GITHUB"].get("FILE", "data/semester.json")
    branch = st.secrets["GITHUB"].get("BRANCH", "main")

    return token, repo_name, file_path, branch


def get_github_repo():
    token, repo_name, _, _ = get_github_config()

    github = Github(token)
    return github.get_repo(repo_name)


def default_data():
    """Erzeugt eine leere Datenstruktur."""

    return {
        "semester": {
            "name": "Mein Semester",
            "start": date.today().isoformat(),
            "end": (date.today() + timedelta(days=180)).isoformat(),
        },
        "subjects": [],
        "exams": [],
        "tasks": [],
        "blocked_times": [],
        "study_sessions": [],
    }


def load_data():
    """Lädt die JSON-Datei aus dem privaten GitHub-Repository."""

    try:
        repo = get_github_repo()
        _, _, file_path, branch = get_github_config()

        file = repo.get_contents(file_path, ref=branch)

        content = base64.b64decode(file.content).decode("utf-8")
        data = json.loads(content)

        return data, file.sha

    except GithubException as e:
        # Datei existiert noch nicht
        if e.status == 404:
            return default_data(), None

        st.error(f"Fehler beim Laden von GitHub: {e}")
        return default_data(), None

    except Exception as e:
        st.error(f"Fehler beim Laden der Daten: {e}")
        return default_data(), None


def save_data(data, file_sha=None):
    """Speichert die JSON-Datei im privaten GitHub-Repository."""

    try:
        repo = get_github_repo()
        _, _, file_path, branch = get_github_config()

        content = json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        )

        if file_sha:
            repo.update_file(
                path=file_path,
                message="Semesterplan aktualisiert",
                content=content,
                sha=file_sha,
                branch=branch,
            )
        else:
            repo.create_file(
                path=file_path,
                message="Semesterplan erstellt",
                content=content,
                branch=branch,
            )

        return True

    except Exception as e:
        st.error(f"Fehler beim Speichern auf GitHub: {e}")
        return False


# ============================================================
# HILFSFUNKTIONEN
# ============================================================

def generate_id():
    return datetime.now().strftime("%Y%m%d%H%M%S%f")


def format_date(value):
    try:
        return datetime.fromisoformat(value).strftime("%d.%m.%Y")
    except Exception:
        return value


def get_subject_name(data, subject_id):
    for subject in data["subjects"]:
        if subject["id"] == subject_id:
            return subject["name"]

    return "Unbekannt"


def save_current_data():
    """Speichert den aktuellen Stand und lädt danach die neue SHA."""

    if save_data(st.session_state.data, st.session_state.file_sha):
        _, new_sha = load_data()
        st.session_state.file_sha = new_sha
        st.session_state.saved = True


def add_days(start_date, days):
    return start_date + timedelta(days=days)


# ============================================================
# DATEN LADEN
# ============================================================

if "data" not in st.session_state:
    data, file_sha = load_data()

    st.session_state.data = data
    st.session_state.file_sha = file_sha
    st.session_state.saved = False


data = st.session_state.data


# ============================================================
# HEADER
# ============================================================

st.title("📚 Semesterplaner")

st.caption(
    "Plane Prüfungen, Aufgaben, Lernzeiten und Zeiten, in denen du nicht arbeiten möchtest."
)

if st.session_state.saved:
    st.success("Änderungen wurden auf GitHub gespeichert.")
    st.session_state.saved = False


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    st.header("⚙️ Semester")

    semester_name = st.text_input(
        "Semestername",
        value=data["semester"].get("name", ""),
    )

    semester_start = st.date_input(
        "Semesterbeginn",
        value=date.fromisoformat(
            data["semester"].get("start", date.today().isoformat())
        ),
    )

    semester_end = st.date_input(
        "Semesterende",
        value=date.fromisoformat(
            data["semester"].get("end", (date.today() + timedelta(days=180)).isoformat())
        ),
    )

    if st.button("Semester speichern", use_container_width=True):
        data["semester"]["name"] = semester_name
        data["semester"]["start"] = semester_start.isoformat()
        data["semester"]["end"] = semester_end.isoformat()

        save_current_data()

    st.divider()

    if st.button("🔄 Daten neu laden", use_container_width=True):
        data, file_sha = load_data()
        st.session_state.data = data
        st.session_state.file_sha = file_sha
        st.rerun()

    st.caption("Die Daten werden in deinem privaten GitHub-Repository gespeichert.")


# ============================================================
# TABS
# ============================================================

tab_dashboard, tab_plan, tab_exams, tab_tasks, tab_blocked, tab_subjects = st.tabs(
    [
        "📊 Übersicht",
        "🗓️ Planung",
        "📝 Prüfungen",
        "✅ Aufgaben",
        "🚫 Nicht verfügbar",
        "📚 Fächer",
    ]
)


# ============================================================
# ÜBERSICHT
# ============================================================

with tab_dashboard:

    st.header("Semesterübersicht")

    semester_start = date.fromisoformat(data["semester"]["start"])
    semester_end = date.fromisoformat(data["semester"]["end"])

    today = date.today()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Fächer",
            len(data["subjects"]),
        )

    with col2:
        st.metric(
            "Prüfungen",
            len(data["exams"]),
        )

    with col3:
        open_tasks = sum(
            1 for task in data["tasks"]
            if task.get("status") != "Erledigt"
        )

        st.metric(
            "Offene Aufgaben",
            open_tasks,
        )

    with col4:
        remaining_days = max(
            0,
            (semester_end - today).days,
        )

        st.metric(
            "Tage verbleibend",
            remaining_days,
        )

    st.divider()

    # --------------------------------------------------------
    # NÄCHSTE PRÜFUNGEN
    # --------------------------------------------------------

    st.subheader("📝 Nächste Prüfungen")

    upcoming_exams = []

    for exam in data["exams"]:
        try:
            exam_date = date.fromisoformat(exam["date"])

            if exam_date >= today:
                upcoming_exams.append(exam)

        except Exception:
            pass

    upcoming_exams.sort(key=lambda x: x["date"])

    if upcoming_exams:

        rows = []

        for exam in upcoming_exams[:5]:
            rows.append(
                {
                    "Datum": format_date(exam["date"]),
                    "Fach": get_subject_name(data, exam["subject_id"]),
                    "Prüfung": exam["name"],
                    "Lernaufwand": f'{exam.get("study_hours", 0)} h',
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.info("Keine kommenden Prüfungen eingetragen.")

    # --------------------------------------------------------
    # OFFENE AUFGABEN
    # --------------------------------------------------------

    st.subheader("✅ Offene Aufgaben")

    open_tasks_list = [
        task
        for task in data["tasks"]
        if task.get("status") != "Erledigt"
    ]

    open_tasks_list.sort(
        key=lambda x: x.get("due_date", "9999-12-31")
    )

    if open_tasks_list:

        rows = []

        for task in open_tasks_list[:10]:
            rows.append(
                {
                    "Deadline": format_date(task["due_date"]),
                    "Fach": get_subject_name(data, task["subject_id"]),
                    "Aufgabe": task["name"],
                    "Priorität": task.get("priority", "Normal"),
                    "Aufwand": f'{task.get("estimated_hours", 0)} h',
                    "Status": task.get("status", "Offen"),
                }
            )

        st.dataframe(
            pd.DataFrame(rows),
            use_container_width=True,
            hide_index=True,
        )

    else:
        st.success("🎉 Keine offenen Aufgaben!")


# ============================================================
# PLANUNG
# ============================================================

with tab_plan:

    st.header("🗓️ Wochenplanung")

    selected_date = st.date_input(
        "Woche auswählen",
        value=today,
        key="planning_date",
    )

    monday = selected_date - timedelta(
        days=selected_date.weekday()
    )

    sunday = monday + timedelta(days=6)

    st.write(
        f"**{monday.strftime('%d.%m.%Y')} – {sunday.strftime('%d.%m.%Y')}**"
    )

    st.divider()

    # --------------------------------------------------------
    # Lernzeit hinzufügen
    # --------------------------------------------------------

    st.subheader("➕ Lernzeit einplanen")

    with st.form("add_study_session"):

        col1, col2 = st.columns(2)

        with col1:
            study_date = st.date_input(
                "Datum",
                value=selected_date,
            )

            start_time = st.time_input(
                "Start",
                value=time(16, 0),
            )

        with col2:

            end_time = st.time_input(
                "Ende",
                value=time(17, 0),
            )

            subject_options = {
                subject["name"]: subject["id"]
                for subject in data["subjects"]
            }

            if subject_options:
                selected_subject_name = st.selectbox(
                    "Fach",
                    list(subject_options.keys()),
                )
            else:
                selected_subject_name = None

        session_description = st.text_input(
            "Was möchtest du machen?",
            placeholder="z. B. Kapitel 3 lernen",
        )

        submitted = st.form_submit_button(
            "Lernzeit hinzufügen",
            use_container_width=True,
        )

        if submitted:

            if not subject_options:
                st.error("Bitte zuerst mindestens ein Fach anlegen.")

            elif end_time <= start_time:
                st.error("Die Endzeit muss nach der Startzeit liegen.")

            elif not session_description.strip():
                st.error("Bitte eine Beschreibung eingeben.")

            else:

                session = {
                    "id": generate_id(),
                    "date": study_date.isoformat(),
                    "start": start_time.strftime("%H:%M"),
                    "end": end_time.strftime("%H:%M"),
                    "subject_id": subject_options[selected_subject_name],
                    "description": session_description,
                }

                data["study_sessions"].append(session)

                save_current_data()

                st.rerun()

    st.divider()

    # --------------------------------------------------------
    # Wochenansicht
    # --------------------------------------------------------

    st.subheader("Diese Woche")

    for day_offset in range(7):

        current_day = monday + timedelta(days=day_offset)

        day_sessions = [
            session
            for session in data["study_sessions"]
            if session["date"] == current_day.isoformat()
        ]

        day_blocked = [
            blocked
            for blocked in data["blocked_times"]
            if blocked["date"] == current_day.isoformat()
        ]

        with st.expander(
            f"{current_day.strftime('%A, %d.%m.%Y')}",
            expanded=current_day == selected_date,
        ):

            if day_blocked:

                st.warning(
                    "🚫 Nicht verfügbar: "
                    + ", ".join(
                        blocked["description"]
                        for blocked in day_blocked
                    )
                )

            if day_sessions:

                for session in sorted(
                    day_sessions,
                    key=lambda x: x["start"],
                ):

                    col1, col2, col3 = st.columns(
                        [1, 4, 1]
                    )

                    with col1:
                        st.write(
                            f"**{session['start']}–{session['end']}**"
                        )

                    with col2:
                        st.write(
                            f"**{get_subject_name(data, session['subject_id'])}**"
                        )
                        st.caption(session["description"])

                    with col3:

                        if st.button(
                            "🗑️",
                            key=f"delete_session_{session['id']}",
                        ):

                            data["study_sessions"] = [
                                s
                                for s in data["study_sessions"]
                                if s["id"] != session["id"]
                            ]

                            save_current_data()
                            st.rerun()

            elif not day_blocked:

                st.caption("Keine Lernzeit geplant.")


# ============================================================
# PRÜFUNGEN
# ============================================================

with tab_exams:

    st.header("📝 Prüfungen")

    subject_options = {
        subject["name"]: subject["id"]
        for subject in data["subjects"]
    }

    if not subject_options:

        st.info("Lege zuerst ein Fach an.")

    else:

        with st.form("add_exam"):

            exam_name = st.text_input(
                "Prüfung",
                placeholder="z. B. Mathematik Klausur",
            )

            col1, col2 = st.columns(2)

            with col1:

                exam_subject_name = st.selectbox(
                    "Fach",
                    list(subject_options.keys()),
                )

                exam_date = st.date_input(
                    "Datum",
                    value=today,
                )

            with col2:

                exam_time = st.time_input(
                    "Uhrzeit",
                    value=time(9, 0),
                )

                exam_duration = st.number_input(
                    "Dauer (Minuten)",
                    min_value=15,
                    max_value=600,
                    value=90,
                    step=15,
                )

            study_hours = st.number_input(
                "Geschätzter Lernaufwand (Stunden)",
                min_value=0.0,
                max_value=500.0,
                value=10.0,
                step=0.5,
            )

            exam_weight = st.number_input(
                "Gewichtung",
                min_value=0.0,
                max_value=100.0,
                value=100.0,
                step=5.0,
            )

            notes = st.text_area(
                "Notizen",
                placeholder="Themen, Hinweise usw.",
            )

            submitted = st.form_submit_button(
                "Prüfung hinzufügen",
                use_container_width=True,
            )

            if submitted:

                if not exam_name.strip():
                    st.error("Bitte einen Namen eingeben.")

                else:

                    exam = {
                        "id": generate_id(),
                        "name": exam_name,
                        "subject_id": subject_options[
                            exam_subject_name
                        ],
                        "date": exam_date.isoformat(),
                        "time": exam_time.strftime("%H:%M"),
                        "duration_minutes": exam_duration,
                        "study_hours": study_hours,
                        "weight": exam_weight,
                        "notes": notes,
                    }

                    data["exams"].append(exam)

                    save_current_data()

                    st.rerun()

        st.divider()

        # Liste

        for exam in sorted(
            data["exams"],
            key=lambda x: x["date"],
        ):

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [1, 5, 1]
                )

                with col1:

                    st.markdown(
                        f"### {format_date(exam['date'])}"
                    )

                with col2:

                    st.markdown(
                        f"**{exam['name']}**"
                    )

                    st.caption(
                        f"{get_subject_name(data, exam['subject_id'])} · "
                        f"{exam['time']} · "
                        f"{exam['duration_minutes']} min · "
                        f"{exam['study_hours']} h Lernaufwand"
                    )

                    if exam.get("notes"):
                        st.write(exam["notes"])

                with col3:

                    if st.button(
                        "🗑️",
                        key=f"delete_exam_{exam['id']}",
                    ):

                        data["exams"] = [
                            e
                            for e in data["exams"]
                            if e["id"] != exam["id"]
                        ]

                        save_current_data()
                        st.rerun()


# ============================================================
# AUFGABEN
# ============================================================

with tab_tasks:

    st.header("✅ Aufgaben")

    subject_options = {
        subject["name"]: subject["id"]
        for subject in data["subjects"]
    }

    if not subject_options:

        st.info("Lege zuerst ein Fach an.")

    else:

        with st.form("add_task"):

            task_name = st.text_input(
                "Aufgabe",
                placeholder="z. B. Übungsblatt 4 lösen",
            )

            col1, col2 = st.columns(2)

            with col1:

                task_subject_name = st.selectbox(
                    "Fach",
                    list(subject_options.keys()),
                )

                due_date = st.date_input(
                    "Deadline",
                    value=today,
                )

            with col2:

                estimated_hours = st.number_input(
                    "Geschätzter Aufwand (Stunden)",
                    min_value=0.0,
                    max_value=100.0,
                    value=1.0,
                    step=0.5,
                )

                priority = st.selectbox(
                    "Priorität",
                    [
                        "Niedrig",
                        "Normal",
                        "Hoch",
                        "Sehr hoch",
                    ],
                )

            description = st.text_area(
                "Notizen",
            )

            submitted = st.form_submit_button(
                "Aufgabe hinzufügen",
                use_container_width=True,
            )

            if submitted:

                if not task_name.strip():
                    st.error("Bitte eine Aufgabe eingeben.")

                else:

                    task = {
                        "id": generate_id(),
                        "name": task_name,
                        "subject_id": subject_options[
                            task_subject_name
                        ],
                        "due_date": due_date.isoformat(),
                        "estimated_hours": estimated_hours,
                        "priority": priority,
                        "status": "Offen",
                        "description": description,
                    }

                    data["tasks"].append(task)

                    save_current_data()

                    st.rerun()

        st.divider()

        # Aufgaben anzeigen

        for task in sorted(
            data["tasks"],
            key=lambda x: x["due_date"],
        ):

            with st.container(border=True):

                col1, col2, col3 = st.columns(
                    [1, 5, 2]
                )

                with col1:

                    if task.get("status") == "Erledigt":
                        st.write("✅")
                    else:
                        st.write("⬜")

                with col2:

                    st.markdown(
                        f"**{task['name']}**"
                    )

                    st.caption(
                        f"{get_subject_name(data, task['subject_id'])} · "
                        f"Deadline: {format_date(task['due_date'])} · "
                        f"{task['estimated_hours']} h · "
                        f"{task['priority']}"
                    )

                    if task.get("description"):
                        st.caption(task["description"])

                with col3:

                    new_status = st.selectbox(
                        "Status",
                        [
                            "Offen",
                            "In Arbeit",
                            "Erledigt",
                        ],
                        index=[
                            "Offen",
                            "In Arbeit",
                            "Erledigt",
                        ].index(
                            task.get("status", "Offen")
                        ),
                        key=f"status_{task['id']}",
                        label_visibility="collapsed",
                    )

                    if new_status != task.get("status"):
                        task["status"] = new_status
                        save_current_data()
                        st.rerun()

                    if st.button(
                        "🗑️ Löschen",
                        key=f"delete_task_{task['id']}",
                    ):

                        data["tasks"] = [
                            t
                            for t in data["tasks"]
                            if t["id"] != task["id"]
                        ]

                        save_current_data()
                        st.rerun()


# ============================================================
# NICHT VERFÜGBAR
# ============================================================

with tab_blocked:

    st.header("🚫 Zeiten, in denen du nicht arbeiten willst")

    st.write(
        "Diese Zeiten werden bei der späteren automatischen "
        "Planung als blockiert behandelt."
    )

    with st.form("add_blocked"):

        blocked_date = st.date_input(
            "Datum",
            value=today,
        )

        col1, col2 = st.columns(2)

        with col1:

            blocked_start = st.time_input(
                "Von",
                value=time(18, 0),
            )

        with col2:

            blocked_end = st.time_input(
                "Bis",
                value=time(22, 0),
            )

        blocked_description = st.text_input(
            "Grund",
            placeholder="z. B. Sport / Freizeit / Arbeit",
        )

        submitted = st.form_submit_button(
            "Zeit blockieren",
            use_container_width=True,
        )

        if submitted:

            if blocked_end <= blocked_start:
                st.error("Die Endzeit muss nach der Startzeit liegen.")

            else:

                blocked = {
                    "id": generate_id(),
                    "date": blocked_date.isoformat(),
                    "start": blocked_start.strftime("%H:%M"),
                    "end": blocked_end.strftime("%H:%M"),
                    "description": blocked_description,
                }

                data["blocked_times"].append(blocked)

                save_current_data()

                st.rerun()

    st.divider()

    for blocked in sorted(
        data["blocked_times"],
        key=lambda x: (x["date"], x["start"]),
    ):

        with st.container(border=True):

            col1, col2, col3 = st.columns(
                [2, 5, 1]
            )

            with col1:

                st.write(
                    f"**{format_date(blocked['date'])}**"
                )

            with col2:

                st.write(
                    f"{blocked['start']} – {blocked['end']}  \n"
                    f"{blocked.get('description', '')}"
                )

            with col3:

                if st.button(
                    "🗑️",
                    key=f"delete_blocked_{blocked['id']}",
                ):

                    data["blocked_times"] = [
                        b
                        for b in data["blocked_times"]
                        if b["id"] != blocked["id"]
                    ]

                    save_current_data()
                    st.rerun()


# ============================================================
# FÄCHER
# ============================================================

with tab_subjects:

    st.header("📚 Fächer")

    with st.form("add_subject"):

        subject_name = st.text_input(
            "Fach",
            placeholder="z. B. Mathematik",
        )

        color = st.color_picker(
            "Farbe",
            "#4CAF50",
        )

        submitted = st.form_submit_button(
            "Fach hinzufügen",
            use_container_width=True,
        )

        if submitted:

            if not subject_name.strip():
                st.error("Bitte einen Namen eingeben.")

            elif any(
                s["name"].lower() == subject_name.lower()
                for s in data["subjects"]
            ):
                st.error("Dieses Fach existiert bereits.")

            else:

                subject = {
                    "id": generate_id(),
                    "name": subject_name,
                    "color": color,
                }

                data["subjects"].append(subject)

                save_current_data()

                st.rerun()

    st.divider()

    for subject in data["subjects"]:

        with st.container(border=True):

            col1, col2, col3 = st.columns(
                [1, 6, 1]
            )

            with col1:

                st.markdown(
                    f"<div style='background:{subject['color']};"
                    f"width:25px;height:25px;border-radius:50%;'></div>",
                    unsafe_allow_html=True,
                )

            with col2:

                st.write(
                    f"**{subject['name']}**"
                )

            with col3:

                if st.button(
                    "🗑️",
                    key=f"delete_subject_{subject['id']}",
                ):

                    subject_id = subject["id"]

                    # Fach löschen
                    data["subjects"] = [
                        s
                        for s in data["subjects"]
                        if s["id"] != subject_id
                    ]

                    # Zugehörige Aufgaben/Prüfungen/Lernzeiten löschen
                    data["tasks"] = [
                        t
                        for t in data["tasks"]
                        if t["subject_id"] != subject_id
                    ]

                    data["exams"] = [
                        e
                        for e in data["exams"]
                        if e["subject_id"] != subject_id
                    ]

                    data["study_sessions"] = [
                        s
                        for s in data["study_sessions"]
                        if s["subject_id"] != subject_id
                    ]

                    save_current_data()
                    st.rerun()
