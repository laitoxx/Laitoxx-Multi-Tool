# ruff: noqa: F405
from .username_window_base import *  # noqa: F403


class _CorrelationWorker(QThread):
    completed = pyqtSignal(object, object)
    failed = pyqtSignal(str)

    def __init__(self, results, username, downloader, cached_paths):
        super().__init__()
        self.results = list(results)
        self.username = username
        self.downloader = downloader
        self.cached_paths = dict(cached_paths)

    def run(self):
        try:
            profiles = []
            for result in self.results:
                path = self.cached_paths.get(result.site_name)
                if not path and result.avatar_url:
                    path = self.downloader.download(result.avatar_url, self.username, result.site_name)
                avatar_hash = ""
                if path and os.path.exists(path):
                    self.cached_paths[result.site_name] = path
                    avatar_hash = avatar_fingerprint(path)["dhash"]
                profiles.append(
                    AccountProfile(
                        username=self.username,
                        platform=result.site_name,
                        avatar_hash=avatar_hash,
                        links=(result.profile_url or result.url,),
                    )
                )
            self.completed.emit(correlate_many(profiles), self.cached_paths)
        except Exception as exc:
            self.failed.emit(str(exc))
