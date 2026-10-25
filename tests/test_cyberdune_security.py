"""Behavioral checks for spam protection; no real emails or users created."""
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from flask import Flask
from jinja2 import DictLoader
from CTFd.plugins import cyberdune_security as security

class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SECRET_KEY='disposable-security-tests')
        self.app.config.update(SECURITY_REGISTER_IP_MINUTE=3, SECURITY_REGISTER_IP_HOUR=10)
        self.app.jinja_loader = DictLoader({'security_notice.html': '{{ message }}'})
        self.settings = {'verify_emails': False, 'cyberdune_https': True}
        self.patches = [patch.object(security, 'get_config', side_effect=lambda name: self.settings.get(name)), patch.object(security, 'cache', SimpleNamespace(cache=SimpleNamespace())), patch.object(security, 'is_admin', return_value=False), patch.object(security, 'is_verified', return_value=False), patch.object(security, 'can_send_mail', return_value=False)]
        for p in self.patches: p.start()
        for name in ('register', 'login', 'confirm', 'reset_password'):
            self.app.add_url_rule('/' + name, endpoint='auth.' + name, view_func=lambda: 'allowed', methods=['GET','POST'])
        self.app.add_url_rule(security.INSTANCE_PATH, endpoint='instance', view_func=lambda: 'allowed', methods=['GET','POST','PATCH','DELETE'])
        with self.app.app_context(): security.load(self.app)
        self.client = self.app.test_client()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()

    def test_registration_limits_and_get_still_works(self):
        for _ in range(3): self.assertEqual(self.client.post('/register').status_code, 200)
        response = self.client.post('/register')
        self.assertEqual(response.status_code, 429)
        self.assertGreater(int(response.headers['Retry-After']), 0)
        self.assertEqual(self.client.get('/register').status_code, 200)

    def test_forwarded_ip_cannot_bypass_limits(self):
        for n in range(4): response = self.client.post('/register', headers={'X-Forwarded-For': f'192.0.2.{n}'})
        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.client.post('/register', environ_overrides={'REMOTE_ADDR':'192.0.2.99'}).status_code, 200)

    def test_login_account_limit_across_ips(self):
        for n in range(20):
            self.assertEqual(self.client.post('/login', data={'name':'Alice'}, environ_overrides={'REMOTE_ADDR':f'192.0.2.{n}'}).status_code, 200)
        self.assertEqual(self.client.post('/login', data={'name':'  ALICE  '}, environ_overrides={'REMOTE_ADDR':'192.0.2.250'}).status_code, 429)

    def test_shared_network_allows_distinct_attendees_without_removing_account_limits(self):
        self.app.config.update(SECURITY_REGISTER_IP_MINUTE=30, SECURITY_REGISTER_IP_HOUR=300)
        for n in range(20):
            self.assertEqual(self.client.post('/register', data={'email':f'attendee{n}@example.test'}).status_code, 200)
            self.assertEqual(self.client.post('/login', data={'name':f'attendee{n}'}).status_code, 200)

    def test_reset_email_limit_across_ips(self):
        for n in range(3): self.assertEqual(self.client.post('/reset_password', data={'email':'a@example.test'}, environ_overrides={'REMOTE_ADDR':f'192.0.2.{n}'}).status_code, 200)
        self.assertEqual(self.client.post('/reset_password', data={'email':'A@example.test'}, environ_overrides={'REMOTE_ADDR':'192.0.2.250'}).status_code, 429)

    def test_confirmation_cooldown(self):
        with self.client.session_transaction() as sess: sess['id'] = 77
        self.assertEqual(self.client.post('/confirm').status_code, 200)
        self.assertEqual(self.client.post('/confirm').status_code, 429)

    def test_verified_requirement_covers_manager_api(self):
        self.settings['verify_emails'] = True
        with self.client.session_transaction() as sess: sess['id'] = 77
        for method in ('get','post','patch','delete'):
            self.assertEqual(getattr(self.client, method)(security.INSTANCE_PATH).status_code, 403)
        with patch.object(security, 'is_verified', return_value=True): self.assertEqual(self.client.post(security.INSTANCE_PATH).status_code, 200)
        with patch.object(security, 'is_admin', return_value=True): self.assertEqual(self.client.get(security.INSTANCE_PATH).status_code, 200)

    def test_instance_mutation_limit_preserves_polling(self):
        with self.client.session_transaction() as sess: sess['id'] = 77
        for _ in range(12): self.assertEqual(self.client.post(security.INSTANCE_PATH).status_code, 200)
        self.assertEqual(self.client.post(security.INSTANCE_PATH).status_code, 429)
        self.assertEqual(self.client.get(security.INSTANCE_PATH).status_code, 200)

    def test_mail_unavailable_blocks_required_registration(self):
        self.settings['verify_emails'] = True
        self.assertEqual(self.client.post('/register').status_code, 503)
        with patch.object(security, 'can_send_mail', return_value=True): self.assertEqual(self.client.post('/register').status_code, 200)

    def test_security_headers_and_cookies(self):
        response = self.client.get('/login')
        for key in ('X-Content-Type-Options','X-Frame-Options','Referrer-Policy','Strict-Transport-Security'):
            self.assertIn(key, response.headers)
        self.assertEqual(response.headers['Cache-Control'],'no-store')
        self.assertTrue(self.app.config['SESSION_COOKIE_SECURE'])
        self.assertEqual(self.app.config['SESSION_COOKIE_SAMESITE'],'Lax')

    def test_redis_outage_fails_closed(self):
        with patch.object(security, 'consume', side_effect=ConnectionError):
            response = self.client.post('/login')
            self.assertEqual(response.status_code,503)
        self.assertEqual(self.client.get('/login').status_code,200)

    def test_counter_concurrency(self):
        def consume_one(_):
            with self.app.app_context(): return security.consume('isolated', 'same-owner', 7, 60)
        with ThreadPoolExecutor(max_workers=16) as pool: outcomes=list(pool.map(consume_one,range(60)))
        self.assertEqual(outcomes.count(0),7)
        with self.app.app_context(): self.assertEqual(security.consume('isolated','other-owner',7,60),0)



class SMTPTransportTests(unittest.TestCase):
    def test_starttls_uses_plain_connection_then_verified_tls(self):
        from CTFd.utils.email.providers.smtp import get_smtp
        with patch('smtplib.SMTP') as plain, patch('smtplib.SMTP_SSL') as encrypted:
            get_smtp('mail.example.test',587,SSL=False,TLS=True,auth=True,username='test',password='test')
            plain.assert_called_once_with('mail.example.test',587,timeout=3)
            encrypted.assert_not_called()
            ctx=plain.return_value.starttls.call_args.kwargs['context']
            self.assertTrue(ctx.check_hostname)
            plain.return_value.login.assert_called_once_with('test','test')

    def test_ssl_checks_server_certificate(self):
        from CTFd.utils.email.providers.smtp import get_smtp
        with patch('smtplib.SMTP_SSL') as encrypted:
            get_smtp('mail.example.test',465,SSL=True)
            self.assertTrue(encrypted.call_args.kwargs['context'].check_hostname)

class VerificationIntegrationTests(unittest.TestCase):
    def setUp(self):
        from CTFd.config import TestingConfig
        from tests.helpers import create_ctfd
        from CTFd.utils import set_config
        class Config(TestingConfig):
            SQLALCHEMY_DATABASE_URI='sqlite://'
            SERVER_NAME=None
        self.app=create_ctfd(config=Config,ctf_theme='core-theme',enable_plugins=True)
        with self.app.app_context():
            set_config('verify_emails',True)
            set_config('mail_server','smtp.example.test')
            set_config('mail_port',587)

        self.client=self.app.test_client()
        self.send=patch('CTFd.utils.email.sendmail',return_value=(True,'test-only'))
        self.mail_mock=self.send.start()

    def tearDown(self):
        from CTFd.cache import cache
        from CTFd.models import db
        self.send.stop()
        with self.app.app_context():
            cache.clear()
            db.session.remove()
            db.engine.dispose()

    def register(self):
        self.client.get('/register')
        with self.client.session_transaction() as sess: nonce=sess['nonce']
        return self.client.post('/register?next=/challenges',data={'name':'verify-test','email':'verify@example.test','password':'long-test-password','nonce':nonce})

    def test_signup_sends_confirmation_even_with_next_parameter(self):
        response=self.register()
        self.assertEqual(response.status_code,302)
        self.assertIn('/confirm',response.location)
        self.assertEqual(self.mail_mock.call_count,1)
        self.assertIn('/confirm/',self.mail_mock.call_args.kwargs['text'])
        self.assertEqual(self.client.get(security.INSTANCE_PATH+'?challengeId=1').status_code,403)

    def test_failed_signup_delivery_is_honest_and_resendable(self):
        with patch('CTFd.utils.email.sendmail',return_value=(False,'test-error')):
            response=self.register()
        self.assertEqual(response.status_code,503)
        self.assertIn(b'could not be sent',response.data)
        with self.client.session_transaction() as sess: nonce=sess['nonce']
        response=self.client.post('/confirm',data={'nonce':nonce})
        self.assertEqual(response.status_code,200)
        self.assertIn(b'Confirmation email sent',response.data)

    def test_confirmation_token_is_single_use(self):
        from CTFd.models import Users
        from CTFd.utils.security.email import generate_email_confirm_token
        self.register()
        with self.app.app_context(): token=generate_email_confirm_token('verify@example.test')
        response=self.client.get('/confirm/'+token)
        self.assertEqual(response.status_code,302)
        with self.app.app_context(): self.assertTrue(Users.query.filter_by(name='verify-test').one().verified)
        response=self.client.get('/confirm/'+token)
        self.assertIn(b'invalid',response.data)

    def test_failed_resend_never_reports_success(self):
        self.register()
        with self.client.session_transaction() as sess: nonce=sess['nonce']
        with patch('CTFd.utils.email.sendmail',return_value=(False,'test-error')):
            response=self.client.post('/confirm',data={'nonce':nonce})
        self.assertEqual(response.status_code,503)
        self.assertIn(b'could not send',response.data)
        self.assertNotIn(b'Confirmation email sent',response.data)

if __name__ == '__main__': unittest.main()
