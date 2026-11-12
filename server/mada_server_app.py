#!/usr/bin/env python3

"""The FastAPI application: routes, auth wiring and the client/poller
lifecycle. See docs/specs/2026-11-12_3.md for what each page/endpoint is
for. create_app(config) is the single entry point; mada_server.py calls it
after loading config and initializing the DB."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from typing import Literal, Optional

from fastapi import Depends, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

import mada_server_auth as auth
import mada_server_config as cfg
import mada_server_controls as ctl
import mada_server_db as db
from mada_server_client import DaqClient, DaqClientError
from mada_server_poller import Poller
from mada_server_state import state

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, 'templates'))


class StartRequest(BaseModel):
    run: str
    file_num: Optional[int] = None
    event_num: Optional[int] = None
    sci: bool = False


class StopRequest(BaseModel):
    mode: Literal['soft', 'force']


def _client_error_response(error: DaqClientError):
    return JSONResponse({'error': {'code': error.code, 'message': error.message}},
                         status_code=error.status_code or 502)


def create_app(config):
    cookie_secure = config.get('cookie_secure', False)
    presets = config.get('presets', [])
    defaults = config['defaults']

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        token = cfg.read_client_token(config)
        client = DaqClient(config['client']['base_url'], token, timeout=cfg.client_timeout(config))
        poller = Poller(client, state)
        stop_event = asyncio.Event()
        poll_task = asyncio.create_task(poller.run(stop_event))
        app.state.client = client
        try:
            yield
        finally:
            stop_event.set()
            await poll_task
            await client.aclose()

    app = FastAPI(lifespan=lifespan)
    app.mount('/static', StaticFiles(directory=os.path.join(BASE_DIR, 'static')), name='static')
    # Signed-cookie session (no server-side store), modeled on
    # /home/msgc/repo/MPOD/web_backend/app/main.py.
    app.add_middleware(SessionMiddleware, secret_key=config['session_secret'],
                        same_site='lax', https_only=cookie_secure)

    def client_of(request: Request) -> DaqClient:
        return request.app.state.client

    # -- auth -----------------------------------------------------------------

    @app.get('/login', response_class=HTMLResponse)
    async def login_page(request: Request):
        if auth.current_user(request):
            return RedirectResponse('/', status_code=303)
        response = templates.TemplateResponse(request, 'login.html', {'error': None})
        auth.issue_csrf_cookie(response, cookie_secure)
        return response

    @app.post('/login')
    async def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
        logged_in = auth.verify_login(config.get('users', {}), username, password)
        if logged_in is None:
            response = templates.TemplateResponse(
                request, 'login.html', {'error': 'Invalid username or password'}, status_code=401)
            auth.issue_csrf_cookie(response, cookie_secure)
            return response
        auth.login(request, *logged_in)
        return RedirectResponse('/', status_code=303)

    @app.post('/logout')
    async def logout_submit(request: Request):
        auth.logout(request)
        return RedirectResponse('/login', status_code=303)

    # -- dashboard --------------------------------------------------------------

    @app.get('/', response_class=HTMLResponse)
    async def dashboard(request: Request, user=Depends(auth.require_page_user)):
        response = templates.TemplateResponse(request, 'dashboard.html', {
            'user': user,
            'state_json': json.dumps(state.snapshot(), ensure_ascii=False),
            'presets': presets,
            'defaults': defaults,
            'notifications': db.list_notifications(),
        })
        auth.issue_csrf_cookie(response, cookie_secure)
        return response

    @app.get('/api/state')
    async def api_state(request: Request, user=Depends(auth.require_user)):
        queue = state.subscribe()

        async def events():
            try:
                yield f'data: {json.dumps(state.snapshot())}\n\n'
                while True:
                    payload = await queue.get()
                    yield f'data: {json.dumps(payload)}\n\n'
            finally:
                state.unsubscribe(queue)

        return StreamingResponse(events(), media_type='text/event-stream')

    # -- start / stop -------------------------------------------------------------

    @app.post('/daq/start')
    async def daq_start(request: Request, body: StartRequest,
                         user=Depends(auth.require_operator), _csrf=Depends(auth.require_csrf)):
        client = client_of(request)
        params = body.model_dump_json()
        try:
            result = await client.daq_start(body.run, body.file_num, body.event_num, body.sci)
        except DaqClientError as e:
            db.record_operation(user['username'], 'start', params, e.status_code, e.code, e.message)
            return _client_error_response(e)
        db.record_operation(user['username'], 'start', params, 202)
        return JSONResponse(result, status_code=202)

    @app.post('/daq/stop')
    async def daq_stop(request: Request, body: StopRequest,
                        user=Depends(auth.require_operator), _csrf=Depends(auth.require_csrf)):
        """soft: stop after the current file is complete. force: stop now,
        but only while a file is being acquired (not during the ADALM
        control at the start and end of a file). The state is read fresh
        from daq-client here, not from the poller's cache, so the check
        doesn't act on a snapshot that is up to a couple of seconds old."""
        client = client_of(request)
        params = body.model_dump_json()
        try:
            status = await client.status()
            progress = await client.progress() if body.mode == 'force' else None
            refusal = ctl.soft_stop_refusal(status) if body.mode == 'soft' else ctl.force_stop_refusal(status, progress)
            if refusal:
                code, message = refusal
                db.record_operation(user['username'], 'stop', params, 409, code, message)
                return JSONResponse({'error': {'code': code, 'message': message}}, status_code=409)
            result = await (client.daq_stop_soft() if body.mode == 'soft' else client.daq_stop())
        except DaqClientError as e:
            db.record_operation(user['username'], 'stop', params, e.status_code, e.code, e.message)
            return _client_error_response(e)
        db.record_operation(user['username'], 'stop', params, 202)
        return JSONResponse(result, status_code=202)

    # -- runs / files / warnings / config (read-only browsing) --------------------

    @app.get('/runs', response_class=HTMLResponse)
    async def runs_page(request: Request, user=Depends(auth.require_page_user)):
        client = client_of(request)
        error = None
        runs = []
        try:
            runs = (await client.runs()).get('runs', [])
        except DaqClientError as e:
            error = e.message
        return templates.TemplateResponse(request, 'runs.html', {'user': user, 'runs': runs, 'error': error})

    @app.get('/runs/{run}/periods/{period}/files', response_class=HTMLResponse)
    async def files_page(request: Request, run: str, period: int, after: Optional[int] = None,
                          user=Depends(auth.require_page_user)):
        client = client_of(request)
        error = None
        files = []
        try:
            files = (await client.files(run, period, after=after, limit=1000)).get('files', [])
        except DaqClientError as e:
            error = e.message
        return templates.TemplateResponse(request, 'files.html', {
            'user': user, 'run': run, 'period': period, 'files': files, 'error': error})

    @app.get('/runs/{run}/periods/{period}/warnings', response_class=HTMLResponse)
    async def warnings_page(request: Request, run: str, period: int,
                             after: Optional[float] = None, level: Optional[str] = None,
                             source: Optional[str] = None, user=Depends(auth.require_page_user)):
        client = client_of(request)
        error = None
        records = []
        try:
            records = (await client.warnings(run, period, after=after, limit=2000)).get('records', [])
        except DaqClientError as e:
            error = e.message
        if level:
            records = [r for r in records if r.get('level') == level]
        if source:
            records = [r for r in records if r.get('source') == source]
        return templates.TemplateResponse(request, 'warnings.html', {
            'user': user, 'run': run, 'period': period, 'records': records, 'error': error,
            'level': level or '', 'source': source or ''})

    @app.get('/runs/{run}/config', response_class=HTMLResponse)
    async def run_config_page(request: Request, run: str, user=Depends(auth.require_page_user)):
        client = client_of(request)
        error = None
        run_config = {}
        try:
            run_config = await client.run_config(run)
        except DaqClientError as e:
            error = e.message
        return templates.TemplateResponse(request, 'config.html', {
            'user': user, 'run': run, 'error': error,
            'config_json': json.dumps(run_config, indent=2, ensure_ascii=False)})

    # -- log viewer ---------------------------------------------------------------

    @app.get('/log', response_class=HTMLResponse)
    async def log_page(request: Request, user=Depends(auth.require_page_user)):
        return templates.TemplateResponse(request, 'log.html', {'user': user})

    @app.get('/api/log')
    async def api_log(request: Request, offset: Optional[int] = None, max_bytes: Optional[int] = None,
                       user=Depends(auth.require_user)):
        client = client_of(request)
        try:
            return await client.log(offset=offset, max_bytes=max_bytes)
        except DaqClientError as e:
            return _client_error_response(e)

    # -- history / notifications ---------------------------------------------------

    @app.get('/history', response_class=HTMLResponse)
    async def history_page(request: Request, user=Depends(auth.require_page_user)):
        return templates.TemplateResponse(request, 'history.html', {
            'user': user,
            'operations': db.list_operations(),
            'notifications': db.list_notifications(include_acknowledged=True),
        })

    @app.post('/notifications/{notification_id}/ack')
    async def ack_notification(notification_id: int,
                                user=Depends(auth.require_operator), _csrf=Depends(auth.require_csrf)):
        db.acknowledge_notification(notification_id)
        return JSONResponse({'ok': True})

    return app
