from app.models import ClinicSettings
from app.repositories.base import Repository


class ClinicSettingsRepository(Repository[ClinicSettings]):
    model = ClinicSettings

    # The single settings row is created lazily, so a fresh database works too
    def current(self) -> ClinicSettings:
        settings = self.get(1)
        if settings is None:
            settings = self.add(ClinicSettings(id=1))
        return settings
