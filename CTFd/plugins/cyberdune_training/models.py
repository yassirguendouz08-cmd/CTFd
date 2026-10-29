"""Training records are deliberately independent of CTFd challenges/submissions."""
from datetime import datetime

from CTFd.models import db


class TrainingChallenge(db.Model):
    __tablename__ = "cyberdune_training_challenges"
    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    difficulty = db.Column(db.String(20), nullable=False, default="Easy")
    kind = db.Column(db.String(20), nullable=False, default="challenge")
    description = db.Column(db.Text, nullable=False)
    hint = db.Column(db.Text, nullable=False, default="")
    value = db.Column(db.Integer, nullable=False, default=50)
    minutes = db.Column(db.Integer, nullable=False, default=15)
    active = db.Column(db.Boolean, nullable=False, default=True)
    recipe = db.Column(db.String(50), nullable=True)
    flag_hash = db.Column(db.String(64), nullable=True)
    resource_url = db.Column(db.String(2048), nullable=False, default="")
    source = db.Column(db.String(240), nullable=False, default="CyberDune")
    review_note = db.Column(db.Text, nullable=False, default="")
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TrainingSolve(db.Model):
    __tablename__ = "cyberdune_training_solves"
    __table_args__ = (db.UniqueConstraint("user_id", "challenge_id", name="uq_training_user_challenge"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey(TrainingChallenge.id, ondelete="CASCADE"), nullable=False, index=True)
    value = db.Column(db.Integer, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TrainingAttempt(db.Model):
    __tablename__ = "cyberdune_training_attempts"
    __table_args__ = (db.Index("ix_training_attempt_user_time", "user_id", "created"),)
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    challenge_id = db.Column(db.Integer, db.ForeignKey(TrainingChallenge.id, ondelete="CASCADE"), nullable=False)
    correct = db.Column(db.Boolean, nullable=False)
    created = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class TrainingAnswer(db.Model):
    """Multiple accepted, keyed flag hashes for imported exercises."""
    __tablename__ = "cyberdune_training_answers"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey(TrainingChallenge.id, ondelete="CASCADE"), nullable=False, index=True)
    flag_hash = db.Column(db.String(64), nullable=False)


class TrainingAttachment(db.Model):
    __tablename__ = "cyberdune_training_attachments"
    id = db.Column(db.Integer, primary_key=True)
    challenge_id = db.Column(db.Integer, db.ForeignKey(TrainingChallenge.id, ondelete="CASCADE"), nullable=False, index=True)
    name = db.Column(db.String(240), nullable=False)
    location = db.Column(db.String(512), nullable=False)
    sha256 = db.Column(db.String(64), nullable=False)
