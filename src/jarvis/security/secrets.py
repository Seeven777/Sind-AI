from __future__ import annotations

import ctypes
import json
import os
from ctypes import wintypes
from pathlib import Path


class SecretStoreError(RuntimeError):
    pass


class _DATA_BLOB(ctypes.Structure):
    _fields_=[("cbData",wintypes.DWORD),("pbData",ctypes.POINTER(ctypes.c_char))]


def _blob(data:bytes):
    buf=ctypes.create_string_buffer(data)
    return _DATA_BLOB(len(data),ctypes.cast(buf,ctypes.POINTER(ctypes.c_char))),buf


def _protect(data:bytes)->bytes:
    if os.name!='nt':
        return data
    in_blob,buf=_blob(data);out_blob=_DATA_BLOB()
    if not ctypes.windll.crypt32.CryptProtectData(
        ctypes.byref(in_blob),None,None,None,None,0,ctypes.byref(out_blob)
    ):
        raise SecretStoreError('DPAPI protect failed.')
    try:return ctypes.string_at(out_blob.pbData,out_blob.cbData)
    finally:ctypes.windll.kernel32.LocalFree(out_blob.pbData)


def _unprotect(data:bytes)->bytes:
    if os.name!='nt':
        return data
    in_blob,buf=_blob(data);out_blob=_DATA_BLOB()
    if not ctypes.windll.crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),None,None,None,None,0,ctypes.byref(out_blob)
    ):
        raise SecretStoreError('DPAPI unprotect failed.')
    try:return ctypes.string_at(out_blob.pbData,out_blob.cbData)
    finally:ctypes.windll.kernel32.LocalFree(out_blob.pbData)


class SecretStore:
    def __init__(self,root:Path):
        self.root=Path(root)
        self.root.mkdir(parents=True,exist_ok=True)

    def _path(self,key):
        safe=''.join(c for c in key if c.isalnum() or c in '._-')
        if not safe:raise ValueError('secret key inválida')
        return self.root/f'{safe}.bin'

    def set(self,key,value):
        raw=json.dumps({'value':str(value)}).encode('utf-8')
        path=self._path(key)
        path.write_bytes(_protect(raw))
        try:os.chmod(path,0o600)
        except OSError:pass

    def get(self,key,default=None):
        path=self._path(key)
        if not path.exists():return default
        try:
            raw=_unprotect(path.read_bytes())
            return json.loads(raw.decode('utf-8')).get('value',default)
        except Exception as exc:
            raise SecretStoreError(f'Falha ao ler secret {key}: {exc}') from exc

    def delete(self,key):
        self._path(key).unlink(missing_ok=True)

    def exists(self,key):
        return self._path(key).exists()
