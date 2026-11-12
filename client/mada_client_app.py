"""The HTTP API of the DAQ client (docs/specs/2026-11-12.md)."""

import hmac
from typing import Optional

from fastapi import Depends, FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException

import mada_client_files as files
import mada_client_ops as ops
import mada_client_paths as paths
import mada_client_state as state
from mada_client_errors import ApiError

API = '/api/v1'
HTTP_CODES = {401: 'unauthorized', 403: 'forbidden_origin', 404: 'not_found'}


class StartRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run: Optional[str] = None
    file_num: Optional[int] = Field(None, ge=1)
    event_num: Optional[int] = Field(None, ge=1)
    sci: bool = False
    config_from: Optional[str] = None


def error_response(status, code, message):
    return JSONResponse(status_code=status, content={'error': {'code': code, 'message': message}})


def create_app(settings):
    app = FastAPI(title='MADA DAQ client', version='1')

    def check_origin(request: Request):
        host = request.client.host if request.client else None
        if host not in settings.allowed_servers:
            raise ApiError(403, 'forbidden_origin', f'{host} is not an allowed server')

    def check_auth(request: Request):
        check_origin(request)
        header = request.headers.get('authorization', '')
        token = header[7:] if header.lower().startswith('bearer ') else ''
        if not hmac.compare_digest(token.encode(), settings.token.encode()):
            raise ApiError(401, 'unauthorized', 'missing or invalid token')

    auth = [Depends(check_auth)]

    @app.exception_handler(ApiError)
    async def api_error(request, exc):
        return error_response(exc.status, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return error_response(422, 'invalid_request', '; '.join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()))

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return error_response(exc.status_code, HTTP_CODES.get(exc.status_code, 'internal'), str(exc.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(request, exc):
        return error_response(500, 'internal', f'{type(exc).__name__}: {exc}')

    @app.get(API + '/health', dependencies=[Depends(check_origin)])
    def health():
        return {'ok': True, 'api_version': 1}

    @app.get(API + '/status', dependencies=auth)
    def status():
        return state.build_status(settings)

    @app.get(API + '/progress', dependencies=auth)
    def progress():
        return state.build_progress()

    @app.post(API + '/daq/start', status_code=202, dependencies=auth)
    def daq_start(body: StartRequest, request: Request):
        phase = ops.start_daq(settings, body.model_dump(), request.client.host)
        return {'phase': phase}

    @app.post(API + '/daq/stop', status_code=202, dependencies=auth)
    def daq_stop(request: Request):
        return {'phase': ops.stop_daq(request.client.host)}

    @app.get(API + '/runs', dependencies=auth)
    def runs():
        return {'runs': files.list_runs(settings)}

    @app.get(API + '/runs/{run}/config', dependencies=auth)
    def run_config(run: str):
        return files.read_config(settings, run)

    @app.get(API + '/runs/{run}/periods/{period}/files', dependencies=auth)
    def period_files(run: str, period: int, after: int = -1, limit: int = Query(100, ge=1, le=1000)):
        return {'files': files.read_files(files.period_path(settings, run, period), after, limit)}

    @app.get(API + '/runs/{run}/periods/{period}/warnings', dependencies=auth)
    def period_warnings(run: str, period: int, after: float = 0.0, limit: int = Query(200, ge=1, le=2000)):
        return {'records': files.read_warnings(files.period_path(settings, run, period), after, limit)}

    @app.get(API + '/log', dependencies=auth)
    def log(offset: Optional[int] = Query(None, ge=0), max_bytes: int = Query(65536, ge=1, le=1048576)):
        return files.read_log(current_log_name(), offset, max_bytes)

    def current_log_name():
        _, pid, run_state = state.current_phase()
        if run_state and run_state.get('run') is not None and run_state.get('period') is not None:
            return f"{run_state['run']}_{int(run_state['period']):04d}.log"
        return files.newest_log()

    return app
