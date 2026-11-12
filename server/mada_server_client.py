#!/usr/bin/env python3

"""HTTP client for the daq-client API (docs/specs/2026-11-12.md). One
instance, shared by the poller and the request handlers, so every call to
the DAQ PC goes through the same timeout/auth/error handling (spec
2026-11-12_3.md section 7: "クライアントへの呼び出しは、1つのクライアント
クラスに集約する")."""

import httpx


class DaqClientError(Exception):
    """A call to daq-client failed. `code` is the contract's error code
    (docs/specs/2026-11-12.md section 2) or 'unreachable' when the client
    could not be reached at all (connection refused, timeout, bad JSON)."""

    def __init__(self, code, message, status_code=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class DaqClient:
    def __init__(self, base_url, token, timeout=5.0):
        self._base_url = base_url.rstrip('/') + '/api/v1'
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={'Authorization': f'Bearer {token}'})

    async def aclose(self):
        await self._client.aclose()

    async def _request(self, method, path, **kwargs):
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.TimeoutException:
            raise DaqClientError('unreachable', 'timed out contacting daq-client')
        except httpx.RequestError as e:
            raise DaqClientError('unreachable', f'could not contact daq-client: {e}')

        if response.status_code >= 400:
            try:
                body = response.json()
                error = body.get('error', {})
                code, message = error.get('code', 'unknown'), error.get('message', response.text)
            except ValueError:
                code, message = 'unknown', response.text
            raise DaqClientError(code, message, status_code=response.status_code)

        try:
            return response.json()
        except ValueError:
            raise DaqClientError('unreachable', 'daq-client returned a non-JSON body')

    async def health(self):
        return await self._request('GET', '/health')

    async def status(self):
        return await self._request('GET', '/status')

    async def progress(self):
        return await self._request('GET', '/progress')

    async def runs(self):
        return await self._request('GET', '/runs')

    async def run_config(self, run):
        return await self._request('GET', f'/runs/{run}/config')

    async def files(self, run, period, after=None, limit=None):
        params = {}
        if after is not None:
            params['after'] = after
        if limit is not None:
            params['limit'] = limit
        return await self._request('GET', f'/runs/{run}/periods/{period}/files', params=params)

    async def warnings(self, run, period, after=None, limit=None):
        params = {}
        if after is not None:
            params['after'] = after
        if limit is not None:
            params['limit'] = limit
        return await self._request('GET', f'/runs/{run}/periods/{period}/warnings', params=params)

    async def log(self, offset=None, max_bytes=None):
        params = {}
        if offset is not None:
            params['offset'] = offset
        if max_bytes is not None:
            params['max_bytes'] = max_bytes
        return await self._request('GET', '/log', params=params)

    async def daq_start(self, run, file_num=None, event_num=None, sci=False, config_from=None):
        body = {'run': run, 'sci': sci}
        if file_num is not None:
            body['file_num'] = file_num
        if event_num is not None:
            body['event_num'] = event_num
        if config_from is not None:
            body['config_from'] = config_from
        return await self._request('POST', '/daq/start', json=body)

    async def daq_stop(self):
        return await self._request('POST', '/daq/stop')
