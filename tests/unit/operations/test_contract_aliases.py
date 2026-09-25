"""Application service compatibility imports use operations contracts."""

from film_pipeline.app.services import errors as legacy_errors
from film_pipeline.app.services import models as legacy_models
from film_pipeline.operations import errors, models


def test_operator_contract_aliases_keep_identity() -> None:
    assert legacy_errors.ServiceError is errors.ServiceError
    assert legacy_errors.BackendOperationError is errors.BackendOperationError
    assert legacy_models.ProjectCreateRequest is models.ProjectCreateRequest
    assert legacy_models.DashboardSummary is models.DashboardSummary
