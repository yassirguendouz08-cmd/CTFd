"""A practice area with per-user progress and an independent solved-count board."""
import hashlib
import hmac
import io
import math
import uuid
from datetime import datetime, timedelta
from functools import wraps
from urllib.parse import urlsplit

import click
from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_file, session, url_for
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError, OperationalError

from CTFd.models import Users, db
from CTFd.plugins import register_admin_plugin_menu_bar, register_user_page_menu_bar
from CTFd.utils import get_config, set_config
from CTFd.utils.decorators import admins_only
from CTFd.utils.config.pages import build_markdown
from CTFd.utils.user import get_current_user, get_locale

from .catalog import CATEGORIES, artifact, lab_data, starter_rows
from .advanced import advanced_rows
from .pico import rows as pico_rows
from .challenge_text import localize_challenge as localize_training_challenge
from .models import TrainingAnswer, TrainingAttachment, TrainingAttempt, TrainingChallenge, TrainingSolve

training = Blueprint("cyberdune_training", __name__, template_folder="templates", static_folder="assets", static_url_path="/plugins/cyberdune_training/assets")
DIFFICULTIES = ("Easy", "Medium", "Hard")


def tr(text):
    from .translations import MESSAGES
    language = str(get_locale()).split("_")[0].split("-")[0]
    return MESSAGES.get(language, {}).get(text, text)


def digest(value):
    key = current_app.secret_key
    if isinstance(key, str):
        key = key.encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def exercise_flag(challenge, user_id):
    return "CYBERDUNE{" + challenge.slug.replace("-", "_") + "_" + digest(f"training:v1:{challenge.id}:{user_id}")[:16] + "}"


def training_user():
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            user = get_current_user()
            if user is None or user.banned:
                if request.is_json:
                    return jsonify(success=False, message=tr("Log in to continue.")), 403
                return redirect(url_for("auth.login", next=request.full_path))
            if get_config("verify_emails") and not user.verified and user.type != "admin":
                if request.is_json:
                    return jsonify(success=False, message=tr("Verify your email before using the Academy.")), 403
                return redirect(url_for("auth.confirm"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


@training.before_request
def protect_training_forms():
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        # Core permits Authorization headers to skip CSRF. These session-based
        # training forms always require the actual session nonce, regardless.
        expected = session.get("nonce")
        supplied = request.headers.get("CSRF-Token") if request.is_json else request.form.get("nonce")
        if not isinstance(expected, str) or not isinstance(supplied, str) or not hmac.compare_digest(expected, supplied):
            abort(403)


@training.after_request
def private_training_responses(response):
    if request.endpoint != "cyberdune_training.static":
        response.headers["Cache-Control"] = "private, no-store"
        response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


def challenge_or_404(slug):
    return TrainingChallenge.query.filter_by(slug=slug, active=True).first_or_404()


def solved_ids(user_id):
    if user_id is None:
        return set()
    return {row[0] for row in db.session.query(TrainingSolve.challenge_id).filter_by(user_id=user_id)}


def ranked_users():
    totals = db.session.query(
        Users.id.label("user_id"), Users.name.label("name"),
        func.count(TrainingSolve.id).label("solved"),
    ).join(TrainingSolve, TrainingSolve.user_id == Users.id).join(
        TrainingChallenge, TrainingChallenge.id == TrainingSolve.challenge_id,
    ).filter(TrainingChallenge.active.is_(True), Users.banned.is_(False), Users.hidden.is_(False), Users.type == "user").group_by(Users.id, Users.name).subquery()
    # Academy ranks users only by the number of flags they captured.
    ranked = db.session.query(totals, func.rank().over(order_by=totals.c.solved.desc()).label("place")).subquery()
    return ranked


def user_summary(user):
    total = TrainingChallenge.query.filter_by(active=True).count()
    result = {"solved": 0, "total": total, "rank": None, "percent": 0}
    if user:
        count = db.session.query(func.count(TrainingSolve.id)).join(
            TrainingChallenge, TrainingChallenge.id == TrainingSolve.challenge_id,
        ).filter(TrainingSolve.user_id == user.id, TrainingChallenge.active.is_(True)).scalar() or 0
        ranking = ranked_users()
        row = db.session.query(ranking).filter(ranking.c.user_id == user.id).first()
        result.update(solved=count, rank=row.place if row else None, percent=round(count * 100 / total) if total else 0)
    return result


@training.route("/training")
@training.route("/academy")
def catalog():
    user = get_current_user()
    complete = solved_ids(user.id if user else None)
    filters = {key: request.args.get(key, "").strip()[:120] for key in ("q", "category", "difficulty", "kind", "progress")}
    query = TrainingChallenge.query.filter_by(active=True)
    if filters["q"]:
        query = query.filter(TrainingChallenge.name.contains(filters["q"], autoescape=True) | TrainingChallenge.description.contains(filters["q"], autoescape=True))
    for key in ("category", "difficulty", "kind"):
        if filters[key]:
            query = query.filter(getattr(TrainingChallenge, key) == filters[key])
    if filters["progress"] == "solved":
        query = query.filter(TrainingChallenge.id.in_(complete))
    elif filters["progress"] == "unsolved":
        query = query.filter(~TrainingChallenge.id.in_(complete))
    page = max(1, min(request.args.get("page", 1, type=int), 100000))
    count = query.count()
    items = query.order_by(TrainingChallenge.id).offset((page - 1) * 24).limit(24).all()
    categories = [row[0] for row in db.session.query(TrainingChallenge.category).filter_by(active=True).distinct().order_by(TrainingChallenge.category)]
    solve_counts = dict(db.session.query(
        TrainingSolve.challenge_id, func.count(TrainingSolve.id),
    ).join(TrainingChallenge, TrainingChallenge.id == TrainingSolve.challenge_id).filter(
        TrainingChallenge.active.is_(True),
    ).group_by(TrainingSolve.challenge_id).all())
    items = [localize_training_challenge(item) for item in items]
    return render_template("training/catalog.html", title="Academy | CyberDune", items=items, categories=categories,
                           difficulties=DIFFICULTIES, complete=complete, filters=filters, summary=user_summary(user),
                           page=page, pages=max(1, math.ceil(count / 24)), count=count, user=user, solve_counts=solve_counts)


@training.route("/training/scoreboard")
@training.route("/academy/scoreboard")
def scoreboard():
    page = max(1, min(request.args.get("page", 1, type=int), 100000))
    ranking = ranked_users()
    query = db.session.query(ranking)
    columns = ranking.c
    total = query.count()
    rows = query.order_by(columns.solved.desc(), columns.name, columns.user_id).offset((page - 1) * 50).limit(50).all()
    return render_template("training/scoreboard.html", title="Academy leaderboard | CyberDune", rows=rows, page=page,
                           pages=max(1, math.ceil(total / 50)), summary=user_summary(get_current_user()), user=get_current_user())


@training.route("/training/challenges/<slug>")
@training.route("/academy/challenges/<slug>")
@training_user()
def detail(slug):
    challenge = challenge_or_404(slug)
    challenge_view = localize_training_challenge(challenge)
    template = "training/detail_modal.html" if request.args.get("modal") == "1" else "training/detail.html"
    return render_template(template, title=challenge_view.name + " | Academy", challenge=challenge_view,
                           description=build_markdown(challenge_view.description, sanitize=True), solved=challenge.id in solved_ids(get_current_user().id),
                           summary=user_summary(get_current_user()), attachments=TrainingAttachment.query.filter_by(challenge_id=challenge.id).all())


@training.route("/training/challenges/<slug>/artifact")
@training.route("/academy/challenges/<slug>/artifact")
@training_user()
def download(slug):
    challenge = challenge_or_404(slug)
    if not challenge.recipe or challenge.kind != "challenge":
        abort(404)
    name, data = artifact(challenge.recipe, exercise_flag(challenge, get_current_user().id))
    return send_file(io.BytesIO(data), mimetype="application/octet-stream", as_attachment=True, download_name=name, max_age=0)


@training.route("/training/challenges/<slug>/files/<int:attachment_id>")
@training.route("/academy/challenges/<slug>/files/<int:attachment_id>")
@training_user()
def attachment(slug, attachment_id):
    from CTFd.utils.uploads import get_uploader
    challenge = challenge_or_404(slug)
    item = TrainingAttachment.query.filter_by(id=attachment_id, challenge_id=challenge.id).first_or_404()
    response = get_uploader().download(item.location)
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@training.route("/training/challenges/<slug>/lab")
@training.route("/academy/challenges/<slug>/lab")
@training_user()
def lab(slug):
    challenge = challenge_or_404(slug)
    if not challenge.recipe or challenge.kind != "lab":
        abort(404)
    payload = lab_data(challenge.recipe, exercise_flag(challenge, get_current_user().id))
    response = current_app.make_response(render_template("training/lab.html", challenge=localize_training_challenge(challenge), payload=payload))
    # Even a directly opened lab has an opaque origin and cannot fetch app APIs.
    response.headers["Content-Security-Policy"] = "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; img-src data:; form-action 'none'; base-uri 'none'; frame-ancestors 'self'; sandbox allow-scripts"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@training.route("/training/challenges/<slug>/sql", methods=["POST"])
@training.route("/academy/challenges/<slug>/sql", methods=["POST"])
@training_user()
def sql_login(slug):
    from .pico import check_sql_login
    challenge = challenge_or_404(slug)
    if challenge.recipe != "pico-sql-1":
        abort(404)
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or any(not isinstance(data.get(key), str) or len(data[key]) > 128 for key in ("username", "password")):
        return jsonify(success=False, message="Use two text fields of at most 128 characters."), 400
    passed = check_sql_login(data["username"], data["password"])
    return jsonify(success=passed, message=exercise_flag(challenge, get_current_user().id) if passed else "Fictional login failed.")


@training.route("/training/challenges/<slug>/submit", methods=["POST"])
@training.route("/academy/challenges/<slug>/submit", methods=["POST"])
@training_user()
def submit(slug):
    challenge = challenge_or_404(slug)
    user = get_current_user()
    payload = request.get_json(silent=True) if request.is_json else request.form
    flag = payload.get("flag") if isinstance(payload, dict) or hasattr(payload, "get") else None
    if not isinstance(flag, str) or not 1 <= len(flag.strip()) <= 256:
        return jsonify(success=False, message=tr("Enter a flag of at most 256 characters.")), 400
    if TrainingSolve.query.filter_by(user_id=user.id, challenge_id=challenge.id).first():
        return submission_result(challenge, "already_solved", tr("You already solved this exercise."))
    attempts = TrainingAttempt.query.filter(TrainingAttempt.user_id == user.id, TrainingAttempt.created >= datetime.utcnow() - timedelta(minutes=1)).count()
    if attempts >= 30:
        response = jsonify(success=False, message=tr("Too many attempts. Wait a minute and try again."))
        response.status_code = 429; response.headers["Retry-After"] = "60"
        return response
    supplied = flag.strip()
    correct = hmac.compare_digest(supplied.encode(), exercise_flag(challenge, user.id).encode()) if challenge.recipe else hmac.compare_digest(digest("training:static:" + supplied), challenge.flag_hash or "")
    if not challenge.recipe and not correct:
        candidate = digest("training:static:" + supplied)
        correct = any(hmac.compare_digest(candidate, row.flag_hash) for row in TrainingAnswer.query.filter_by(challenge_id=challenge.id))
    db.session.add(TrainingAttempt(user_id=user.id, challenge_id=challenge.id, correct=correct))
    if correct:
        db.session.add(TrainingSolve(user_id=user.id, challenge_id=challenge.id, value=challenge.value))
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if TrainingSolve.query.filter_by(user_id=user.id, challenge_id=challenge.id).first():
            return submission_result(challenge, "already_solved", tr("You already solved this exercise."))
        raise
    return submission_result(challenge, "correct" if correct else "incorrect", tr("Correct flag. Academy progress saved!") if correct else tr("That flag is not correct. Try again."))


def submission_result(challenge, status, message):
    if request.is_json:
        return jsonify(success=True, status=status, message=message, summary=user_summary(get_current_user()))
    flash(message, "success" if status != "incorrect" else "danger")
    return redirect(url_for("cyberdune_training.detail", slug=challenge.slug))


def safe_resource_url(value):
    if not value:
        return ""
    try:
        parsed = urlsplit(value)
        if len(value) > 2048 or parsed.scheme not in ("https", "http") or not parsed.hostname or parsed.username or parsed.password or any(ord(c) < 32 for c in value):
            raise ValueError
    except ValueError:
        raise ValueError("Use a complete HTTP or HTTPS resource URL.") from None
    return value


@training.route("/admin/training", methods=["GET", "POST"])
@training.route("/admin/training/<int:challenge_id>", methods=["GET", "POST"])
@admins_only
def admin(challenge_id=None):
    item = TrainingChallenge.query.get_or_404(challenge_id) if challenge_id else None
    error = None
    if request.method == "POST":
        try:
            if request.form.get("action") == "toggle" and item:
                item.active = not item.active
            else:
                values = {key: request.form.get(key, "").strip() for key in ("name", "category", "difficulty", "kind", "description", "hint", "resource_url")}
                if not 1 <= len(values["name"]) <= 120 or not 1 <= len(values["category"]) <= 50 or not 1 <= len(values["description"]) <= 20000 or len(values["hint"]) > 4000:
                    raise ValueError("Provide a title, category and instructions within the allowed lengths.")
                if values["difficulty"] not in DIFFICULTIES or values["kind"] not in ("challenge", "lab"):
                    raise ValueError("Choose a valid difficulty and exercise type.")
                values["resource_url"] = safe_resource_url(values["resource_url"])
                if item and item.recipe and values["kind"] != item.kind:
                    raise ValueError("The type of a built-in exercise cannot be changed.")
                if values["kind"] == "lab" and not (item and item.recipe) and not values["resource_url"]:
                    raise ValueError("Custom labs need a resource URL to a separately hosted lab.")
                # Points appear on cards; leaderboard ranking remains based on flags captured.
                value = int(request.form.get("value", item.value if item else 50))
                minutes = int(request.form.get("minutes", 15))
                if not 0 <= value <= 10000 or not 1 <= minutes <= 600:
                    raise ValueError("Points must be 0–10000 and duration 1–600 minutes.")
                flag = request.form.get("flag", "").strip()
                if len(flag) > 256 or (not (item and (item.recipe or item.flag_hash)) and not flag):
                    raise ValueError("A new exercise needs a flag of at most 256 characters.")
                if item is None:
                    item = TrainingChallenge(slug="exercise-" + uuid.uuid4().hex[:16]); db.session.add(item)
                for key, val in values.items():
                    setattr(item, key, val)
                item.value = value; item.minutes = minutes
                item.active = request.form.get("active") == "1"
                if flag and not item.recipe:
                    item.flag_hash = digest("training:static:" + flag)
                    TrainingAnswer.query.filter_by(challenge_id=item.id).delete()
            db.session.commit()
            return redirect(url_for("cyberdune_training.admin", challenge_id=item.id))
        except (ValueError, TypeError) as exc:
            db.session.rollback(); error = str(exc)
    items = TrainingChallenge.query.order_by(TrainingChallenge.id).all()
    return render_template("training/admin.html", items=items, item=item, categories=CATEGORIES, difficulties=DIFFICULTIES, error=error), 400 if error else 200


def seed_starters():
    if get_config("cyberdune_training:starter_catalog_v1"):
        return
    existing = {row[0] for row in db.session.query(TrainingChallenge.slug)}
    try:
        for row in starter_rows():
            if row["slug"] not in existing:
                db.session.add(TrainingChallenge(**row))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
    set_config("cyberdune_training:starter_catalog_v1", True)


def simplify_seeded_titles():
    """Update only the original generated labels; keep admin-edited content intact."""
    old_source = "picoCTF official examples · Tim Becker / ForAllSecure · MIT · adapted by CyberDune"
    labels = {
        "pico-ecb-1": ("picoCTF sample: ECB 1", "ECB Challenge"),
        "pico-sql-1": ("picoCTF sample: SQL Injection 1", "SQL Login"),
    }
    changed = False
    for slug, (old_name, new_name) in labels.items():
        challenge = TrainingChallenge.query.filter_by(slug=slug).first()
        if challenge and challenge.name == old_name:
            challenge.name = new_name
            changed = True
        if challenge and challenge.source == old_source:
            challenge.source = "Licensed learning example · author and license credits are included with the exercise files"
            changed = True
    if changed:
        db.session.commit()


def load(app):
    tables = [TrainingChallenge.__table__, TrainingSolve.__table__, TrainingAttempt.__table__, TrainingAnswer.__table__, TrainingAttachment.__table__]
    try:
        db.metadata.create_all(bind=db.engine, tables=tables, checkfirst=True)
    except OperationalError as error:
        # Concurrent worker startup may have created the same table first.
        if "already exists" not in str(error).lower():
            raise
        db.metadata.create_all(bind=db.engine, tables=tables, checkfirst=True)
    # CTFd configuration reads may already hold a MariaDB repeatable-read
    # snapshot from before these tables existed. End it before querying them.
    db.session.commit()
    seed_starters()
    if not get_config("cyberdune_training:advanced_catalog_v1"):
        existing = {row[0] for row in db.session.query(TrainingChallenge.slug)}
        try:
            for row in list(advanced_rows()) + list(pico_rows()):
                if row["slug"] not in existing:
                    db.session.add(TrainingChallenge(**row))
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
        set_config("cyberdune_training:advanced_catalog_v1", True)
    simplify_seeded_titles()
    app.register_blueprint(training)
    app.jinja_env.globals["training_copy"] = tr
    register_user_page_menu_bar("Academy", "/academy")
    register_admin_plugin_menu_bar("Academy", "/admin/training")

    def limit_training_body():
        if (request.endpoint or "").startswith("cyberdune_training.") and request.method == "POST":
            request.max_content_length = 32768 if request.path.startswith(request.script_root + "/admin/") else 4096
    app.before_request_funcs.setdefault(None, []).insert(0, limit_training_body)

    @app.cli.group("training")
    def training_cli():
        """Maintain independent training content and telemetry."""

    @training_cli.command("import-bootcamp")
    @click.argument("archive", type=click.Path(exists=True, dir_okay=False))
    def import_bootcamp_command(archive):
        from .bootcamp import import_bootcamp
        report = import_bootcamp(archive)
        click.echo(f"Bootcamp: {report['imported']} imported; {report['published']} published; {report['pending']} awaiting lab/content restoration. No user data imported.")

    @training_cli.command("prune-attempts")
    @click.option("--days", default=30, type=click.IntRange(1, 3650))
    def prune_attempts(days):
        count = TrainingAttempt.query.filter(TrainingAttempt.created < datetime.utcnow() - timedelta(days=days)).delete()
        db.session.commit()
        click.echo(f"Pruned {count} old attempts; solves and progress were retained.")
