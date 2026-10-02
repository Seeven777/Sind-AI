from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import secrets
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from ctypes import wintypes
from http.server import BaseHTTPRequestHandler,HTTPServer
from pathlib import Path


SCOPES=(
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
)


class GoogleAuthError(RuntimeError):
    pass


class _DATA_BLOB(ctypes.Structure):
    _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_char))]


def _blob(data:bytes):
    buf=ctypes.create_string_buffer(data)
    return _DATA_BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_char))),buf


def _dpapi_protect(data:bytes)->bytes:
    if os.name!="nt":
        return data
    in_blob,buf=_blob(data)
    out_blob=_DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),None,None,None,None,0,ctypes.byref(out_blob)
    ):
        raise GoogleAuthError("DPAPI CryptProtectData falhou.")
    try:
        return ctypes.string_at(out_blob.pbData,out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _dpapi_unprotect(data:bytes)->bytes:
    if os.name!="nt":
        return data
    in_blob,buf=_blob(data)
    out_blob=_DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),None,None,None,None,0,ctypes.byref(out_blob)
    ):
        raise GoogleAuthError("DPAPI CryptUnprotectData falhou.")
    try:
        return ctypes.string_at(out_blob.pbData,out_blob.cbData)
    finally:
        ctypes.windll.kernel32.LocalFree(out_blob.pbData)


class GoogleTokenStore:
    def __init__(self,path:Path):
        self.path=Path(path)

    def exists(self):
        return self.path.is_file()

    def save(self,token:dict):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        raw=json.dumps(token,ensure_ascii=False).encode("utf-8")
        protected=_dpapi_protect(raw)
        self.path.write_bytes(protected)
        try: os.chmod(self.path,0o600)
        except OSError: pass

    def load(self):
        if not self.path.exists():
            return None
        try:
            raw=_dpapi_unprotect(self.path.read_bytes())
            return json.loads(raw.decode("utf-8"))
        except Exception as exc:
            raise GoogleAuthError(f"Token Google inválido: {exc}") from exc

    def delete(self):
        self.path.unlink(missing_ok=True)


class GoogleOAuthClient:
    AUTH_URL="https://accounts.google.com/o/oauth2/v2/auth"
    TOKEN_URL="https://oauth2.googleapis.com/token"

    def __init__(self,client_config_path:Path,token_store:GoogleTokenStore,scopes=SCOPES):
        self.client_config_path=Path(client_config_path)
        self.token_store=token_store
        self.scopes=tuple(scopes)

    def configured(self):
        return self.client_config_path.is_file()

    def _client(self):
        if not self.client_config_path.exists():
            raise GoogleAuthError(
                f"Credencial OAuth não encontrada: {self.client_config_path}"
            )
        raw=json.loads(self.client_config_path.read_text(encoding="utf-8"))
        cfg=raw.get("installed") or raw.get("web") or raw
        client_id=cfg.get("client_id")
        if not client_id:
            raise GoogleAuthError("google_client.json não contém client_id.")
        return {
            "client_id":client_id,
            "client_secret":cfg.get("client_secret",""),
        }

    def _post_form(self,url,payload):
        req=urllib.request.Request(
            url,
            data=urllib.parse.urlencode(payload).encode("utf-8"),
            headers={"Content-Type":"application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req,timeout=30) as response:
                return json.loads(response.read().decode("utf-8"))
        except Exception as exc:
            raise GoogleAuthError(f"OAuth Google falhou: {exc}") from exc

    def authenticate_interactive(self,open_browser=True,timeout=180):
        client=self._client()
        state=secrets.token_urlsafe(24)
        verifier=secrets.token_urlsafe(64)
        challenge=base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode("ascii")).digest()
        ).decode("ascii").rstrip("=")

        result={"code":None,"error":None}
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self_inner):
                parsed=urllib.parse.urlparse(self_inner.path)
                params=urllib.parse.parse_qs(parsed.query)
                if params.get("state",[""])[0]!=state:
                    result["error"]="state inválido"
                elif params.get("error"):
                    result["error"]=params["error"][0]
                else:
                    result["code"]=params.get("code",[None])[0]
                body=b"Jarvis recebeu a autorizacao. Pode fechar esta janela."
                self_inner.send_response(200)
                self_inner.send_header("Content-Type","text/plain; charset=utf-8")
                self_inner.send_header("Content-Length",str(len(body)))
                self_inner.end_headers()
                self_inner.wfile.write(body)
            def log_message(self_inner,*args):
                return

        server=HTTPServer(("127.0.0.1",0),Handler)
        port=server.server_address[1]
        redirect_uri=f"http://127.0.0.1:{port}/callback"
        params={
            "client_id":client["client_id"],
            "redirect_uri":redirect_uri,
            "response_type":"code",
            "scope":" ".join(self.scopes),
            "access_type":"offline",
            "include_granted_scopes":"true",
            "prompt":"consent",
            "state":state,
            "code_challenge":challenge,
            "code_challenge_method":"S256",
        }
        auth_url=self.AUTH_URL+"?"+urllib.parse.urlencode(params)
        thread=threading.Thread(target=server.handle_request,daemon=True)
        thread.start()
        if open_browser:
            webbrowser.open(auth_url)
        thread.join(timeout)
        server.server_close()
        if not result["code"]:
            raise GoogleAuthError(result["error"] or "Autorização Google expirou.")

        payload={
            "client_id":client["client_id"],
            "client_secret":client["client_secret"],
            "code":result["code"],
            "code_verifier":verifier,
            "grant_type":"authorization_code",
            "redirect_uri":redirect_uri,
        }
        token=self._post_form(self.TOKEN_URL,payload)
        token["obtained_at"]=int(time.time())
        self.token_store.save(token)
        return token

    def access_token(self):
        token=self.token_store.load()
        if not token:
            raise GoogleAuthError("Google ainda não foi autorizado.")
        expires_in=int(token.get("expires_in",3600))
        obtained=int(token.get("obtained_at",0))
        if token.get("access_token") and time.time()<obtained+expires_in-60:
            return token["access_token"]
        refresh=token.get("refresh_token")
        if not refresh:
            raise GoogleAuthError("Token Google expirado e sem refresh_token.")
        client=self._client()
        refreshed=self._post_form(self.TOKEN_URL,{
            "client_id":client["client_id"],
            "client_secret":client["client_secret"],
            "refresh_token":refresh,
            "grant_type":"refresh_token",
        })
        refreshed["refresh_token"]=refresh
        refreshed["obtained_at"]=int(time.time())
        self.token_store.save(refreshed)
        return refreshed["access_token"]

    def status(self):
        if not self.configured():
            return {"status":"unconfigured","client_config":str(self.client_config_path)}
        if not self.token_store.exists():
            return {"status":"authorization_required","client_config":str(self.client_config_path)}
        try:
            self.access_token()
            return {"status":"healthy","client_config":str(self.client_config_path)}
        except Exception as exc:
            return {"status":"error","error":str(exc),"client_config":str(self.client_config_path)}


def google_json_request(oauth:GoogleOAuthClient,url:str):
    token=oauth.access_token()
    req=urllib.request.Request(
        url,
        headers={
            "Authorization":f"Bearer {token}",
            "Accept":"application/json",
            "User-Agent":"JarvisNext/1.0",
        },
    )
    with urllib.request.urlopen(req,timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))
