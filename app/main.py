from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import db
from .grades import cgpa, course_percentage, percentage_to_points
from .models import Assessment, Course, StudySession, Task, utcnow

bp = Blueprint("main", __name__)


def owned_or_404(model, obj_id):
    obj = db.session.get(model, obj_id)
    if obj is None:
        abort(404)
    owner_id = obj.course.user_id if model is Assessment else obj.user_id
    if owner_id != current_user.id:
        abort(404)
    return obj


def parse_date(value):
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def parse_float(value, default=None):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def user_courses():
    return Course.query.filter_by(user_id=current_user.id).order_by(Course.code).all()


def week_minutes():
    since = utcnow() - timedelta(days=7)
    total = (
        db.session.query(db.func.coalesce(db.func.sum(StudySession.minutes), 0))
        .filter(StudySession.user_id == current_user.id, StudySession.created_at >= since)
        .scalar()
    )
    return int(total)


@bp.route("/")
@login_required
def dashboard():
    today = date.today()
    courses = user_courses()
    pending = (
        Task.query.filter_by(user_id=current_user.id, done=False).order_by(Task.due_date).all()
    )
    rows = []
    for c in courses:
        pct = course_percentage(c.assessments)
        rows.append({"course": c, "pct": pct, "points": percentage_to_points(pct)})
    return render_template(
        "dashboard.html",
        rows=rows,
        cgpa=cgpa(courses),
        overdue=[t for t in pending if t.due_date < today],
        upcoming=[t for t in pending if t.due_date >= today][:5],
        done_count=Task.query.filter_by(user_id=current_user.id, done=True).count(),
        minutes=week_minutes(),
        today=today,
    )


# ---------- courses & grades ----------
@bp.route("/courses", methods=["GET", "POST"])
@login_required
def courses():
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        name = request.form.get("name", "").strip()
        credits = int(parse_float(request.form.get("credits"), 3))
        if not code or not name or not 1 <= credits <= 10:
            flash("Course code, name and credits (1-10) are required.", "danger")
        else:
            db.session.add(Course(user_id=current_user.id, code=code, name=name, credits=credits))
            db.session.commit()
            flash(f"Added {code}.", "success")
        return redirect(url_for("main.courses"))
    return render_template("courses.html", courses=user_courses())


@bp.route("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    course = owned_or_404(Course, course_id)
    pct = course_percentage(course.assessments)
    tasks = Task.query.filter_by(course_id=course.id).order_by(Task.due_date).all()
    return render_template(
        "course_detail.html", course=course, pct=pct, points=percentage_to_points(pct),
        tasks=tasks, weight_used=sum(a.weight for a in course.assessments),
    )


@bp.route("/courses/<int:course_id>/delete", methods=["POST"])
@login_required
def delete_course(course_id):
    db.session.delete(owned_or_404(Course, course_id))
    db.session.commit()
    flash("Course deleted.", "info")
    return redirect(url_for("main.courses"))


@bp.route("/courses/<int:course_id>/assessments", methods=["POST"])
@login_required
def add_assessment(course_id):
    course = owned_or_404(Course, course_id)
    title = request.form.get("title", "").strip()
    raw_score = request.form.get("score", "").strip()
    score = parse_float(raw_score) if raw_score else None
    max_score = parse_float(request.form.get("max_score"), 100)
    weight = parse_float(request.form.get("weight"), 0)
    valid = title and max_score > 0 and weight > 0 and (raw_score == "" or score is not None)
    if valid and score is not None and score > max_score:
        valid = False
    if not valid:
        flash("Check the assessment: title, score <= max, and weight > 0 are required.", "danger")
    else:
        db.session.add(Assessment(course_id=course.id, title=title, score=score,
                                  max_score=max_score, weight=weight))
        db.session.commit()
    return redirect(url_for("main.course_detail", course_id=course.id))


@bp.route("/assessments/<int:assessment_id>/delete", methods=["POST"])
@login_required
def delete_assessment(assessment_id):
    a = owned_or_404(Assessment, assessment_id)
    course_id = a.course_id
    db.session.delete(a)
    db.session.commit()
    return redirect(url_for("main.course_detail", course_id=course_id))


# ---------- tasks ----------
@bp.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        due = parse_date(request.form.get("due_date"))
        priority = request.form.get("priority", "medium")
        course_id = request.form.get("course_id", type=int)
        if course_id:
            owned_or_404(Course, course_id)
        if not title or due is None or priority not in ("low", "medium", "high"):
            flash("Title and a valid due date are required.", "danger")
        else:
            db.session.add(Task(user_id=current_user.id, course_id=course_id or None,
                                title=title, due_date=due, priority=priority))
            db.session.commit()
        return redirect(url_for("main.tasks"))

    flt = request.args.get("filter", "pending")
    query = Task.query.filter_by(user_id=current_user.id)
    if flt == "pending":
        query = query.filter_by(done=False)
    elif flt == "done":
        query = query.filter_by(done=True)
    return render_template("tasks.html", tasks=query.order_by(Task.due_date).all(),
                           courses=user_courses(), flt=flt, today=date.today())


@bp.route("/tasks/<int:task_id>/toggle", methods=["POST"])
@login_required
def toggle_task(task_id):
    task = owned_or_404(Task, task_id)
    task.done = not task.done
    db.session.commit()
    return redirect(request.referrer or url_for("main.tasks"))


@bp.route("/tasks/<int:task_id>/delete", methods=["POST"])
@login_required
def delete_task(task_id):
    db.session.delete(owned_or_404(Task, task_id))
    db.session.commit()
    return redirect(request.referrer or url_for("main.tasks"))


# ---------- study timer & API ----------
@bp.route("/timer")
@login_required
def timer():
    return render_template("timer.html", courses=user_courses())


@bp.route("/api/sessions", methods=["POST"])
@login_required
def log_session():
    data = request.get_json(silent=True) or {}
    minutes = data.get("minutes")
    course_id = data.get("course_id")
    if not isinstance(minutes, int) or not 1 <= minutes <= 600:
        return jsonify(error="minutes must be an integer between 1 and 600"), 400
    if course_id:
        owned_or_404(Course, int(course_id))
    db.session.add(StudySession(user_id=current_user.id, course_id=course_id or None,
                                minutes=minutes))
    db.session.commit()
    return jsonify(ok=True, week_minutes=week_minutes()), 201


@bp.route("/api/stats")
@login_required
def stats():
    courses = user_courses()
    return jsonify(
        cgpa=cgpa(courses),
        week_minutes=week_minutes(),
        pending_tasks=Task.query.filter_by(user_id=current_user.id, done=False).count(),
        courses=[{"code": c.code, "percentage": course_percentage(c.assessments)}
                 for c in courses],
    )
