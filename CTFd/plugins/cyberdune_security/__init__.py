"""Account abuse controls backed by shared atomic Redis counters."""
import hashlib
import math
import os
import threading
import time

from flask import Blueprint, current_app, jsonify, render_template, request, session

from CTFd.cache import cache
from CTFd.utils import get_config
from CTFd.utils.config import can_send_mail
from CTFd.utils.user import is_admin, is_verified

# Count and expiry are one operation: concurrent workers cannot lose increments.
COUNTER_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
return {count, redis.call('TTL', KEYS[1])}
"""
_local_lock = threading.Lock()

INSTANCE_PATH = '/api/v1/plugins/ctfd-chall-manager/instance'


def consume(bucket, identity, limit, interval):
    digest = hashlib.sha256(str(identity).encode()).hexdigest()
    key = f'cyberdune-security:v1:{bucket}:{digest}'
    backend = cache.cache
    client = getattr(backend, '_write_client', None)
    if client is not None:
        count, ttl = client.eval(COUNTER_SCRIPT, 1, key, interval)
        return max(1, int(ttl)) if count > limit else 0
    if current_app.config.get('TESTING'):
        # Only disposable test apps use local counters. Production must use Redis.
        with _local_lock:
            counters = current_app.extensions.setdefault('cyberdune_security_counters', {})
            now = time.monotonic()
            count, expiry = counters.get(key, (0, now + interval))
            if expiry <= now:
                count, expiry = 0, now + interval
            counters[key] = (count + 1, expiry)
            return max(1, math.ceil(expiry - now)) if count + 1 > limit else 0
    raise RuntimeError('Shared Redis rate limiter is unavailable')


def rules():
    endpoint, method = request.endpoint, request.method
    ip = request.remote_addr or 'unknown'
    identity = request.form.get('name', '').strip().casefold()
    email = request.form.get('email', '').strip().casefold()
    if method == 'POST':
        if endpoint == 'auth.register':
            result = [('register-ip-minute', ip, current_app.config['SECURITY_REGISTER_IP_MINUTE'], 60), ('register-ip-hour', ip, current_app.config['SECURITY_REGISTER_IP_HOUR'], 3600)]
            if email:
                result.append(('register-email', email, 3, 3600))
            return result
        if endpoint == 'auth.login':
            result = [('login-ip-minute', ip, current_app.config['SECURITY_LOGIN_IP_MINUTE'], 60), ('login-ip-window', ip, current_app.config['SECURITY_LOGIN_IP_WINDOW'], 900)]
            if identity:
                result.append(('login-account', identity, 20, 900))
            return result
        if endpoint == 'auth.confirm':
            return [('confirm-ip', ip, 100, 900), ('confirm-user-minute', session.get('id', ip), 1, 60), ('confirm-user-window', session.get('id', ip), 3, 900)]
        if endpoint == 'auth.reset_password':
            result = [('reset-ip', ip, 50, 900)]
            if email:
                result.append(('reset-email', email, 3, 3600))
            return result
        if endpoint in ('teams.join', 'teams.new'):
            return [('team-ip', ip, 100, 300)]
    if request.path.rstrip('/') == INSTANCE_PATH and method in ('GET', 'POST', 'PATCH', 'DELETE'):
        if session.get('id') is None:
            return [('instance-anonymous', ip, 30, 60)]
        if method == 'GET':
            return [('instance-read-user', session['id'], 120, 60)]
        return [('instance-change-user', session['id'], 12, 60), ('instance-change-ip', ip, 600, 60)]
    if request.path.endswith('/admin/zip/new') and method == 'POST':
        return [('zip-upload-user', session.get('id', ip), 5, 300)]
    return []


def error_response(message, status, retry_after=None):
    if request.path.startswith('/api/'):
        response = jsonify(success=False, message=message, errors={'rate_limit': message})
    else:
        response = current_app.make_response(render_template('security_notice.html', message=message))
    response.status_code = status
    if retry_after is not None:
        response.headers['Retry-After'] = str(retry_after)
    response.headers['Cache-Control'] = 'no-store'
    return response


def load(app):
    for name, default in {'SECURITY_REGISTER_IP_MINUTE':30, 'SECURITY_REGISTER_IP_HOUR':300, 'SECURITY_LOGIN_IP_MINUTE':100, 'SECURITY_LOGIN_IP_WINDOW':600}.items():
        app.config.setdefault(name, int(os.getenv(name, default)))
        if app.config[name] <= 0:
            raise ValueError(f'{name} must be a positive number')
    app.register_blueprint(Blueprint('cyberdune-security', __name__, template_folder='templates'))
    if get_config('cyberdune_https') or app.config.get('PUBLIC_ORIGIN', '').startswith('https://'):
        app.config['SESSION_COOKIE_SECURE'] = True
        app.config['SESSION_COOKIE_HTTPONLY'] = True
        app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    @app.before_request
    def protect_accounts():
        for bucket, identity, limit, interval in rules():
            try:
                retry = consume(bucket, identity, limit, interval)
            except Exception:
                app.logger.error('CyberDune shared rate limiter unavailable')
                return error_response('Please try again shortly. Account protection is temporarily unavailable.', 503, 30)
            if retry:
                return error_response(f'Too many attempts. Please try again in {retry} seconds.', 429, retry)
        if request.method == 'POST' and request.endpoint == 'auth.register' and get_config('verify_emails') and not can_send_mail():
            return error_response('Registration is temporarily unavailable while email verification is being configured.', 503, 60)
        # The manager API bypasses CTFd's core challenge decorators; guard it here.
        if request.path.rstrip('/') == INSTANCE_PATH and session.get('id') and get_config('verify_emails') and not is_admin() and not is_verified():
            return error_response('Verify your email before using challenge instances.', 403)

    @app.after_request
    def security_headers(response):
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        if get_config('cyberdune_https') or app.config.get('PUBLIC_ORIGIN', '').startswith('https://'):
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000')
        if request.endpoint in ('auth.login', 'auth.register', 'auth.confirm', 'auth.reset_password'):
            response.headers['Cache-Control'] = 'no-store'
        return response
