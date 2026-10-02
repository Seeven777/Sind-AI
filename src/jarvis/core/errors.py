class JarvisError(Exception):
    """Base exception for expected Jarvis failures."""

class ConfigError(JarvisError):
    pass

class StorageError(JarvisError):
    pass

class MigrationError(StorageError):
    pass

class StateTransitionError(JarvisError):
    pass

class RecoveryError(JarvisError):
    pass

class LockError(JarvisError):
    pass

class LifecycleError(JarvisError):
    pass
