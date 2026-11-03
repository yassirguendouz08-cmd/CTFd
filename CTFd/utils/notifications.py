"""Helpers for durable, in-app broadcast notifications."""


def publish_broadcast_notification(title, content):
    """Save a notification for all accounts and publish it to connected clients."""
    from flask import current_app

    from CTFd.models import Notifications, db
    from CTFd.schemas.notifications import NotificationSchema

    notification = Notifications(title=title, content=content, user_id=None, team_id=None)
    try:
        db.session.add(notification)
        db.session.commit()

        response = NotificationSchema().dump(notification)
        data = response.data
        data["type"] = "alert"
        data["sound"] = False
        current_app.events_manager.publish(data=data, type="notification")
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Unable to publish a CyberDune content notification")
        return None

    return notification
