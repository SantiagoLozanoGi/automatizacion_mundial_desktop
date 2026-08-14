from __future__ import annotations

from typing import Iterable

from app.workflow_contract import WorkflowDefinition


class WorkflowRegistry:
    def __init__(self, definitions: Iterable[WorkflowDefinition] = ()) -> None:
        self._definitions: dict[str, WorkflowDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: WorkflowDefinition) -> None:
        if definition.id in self._definitions:
            raise ValueError(f"ID de workflow duplicado: {definition.id}")
        self._definitions[definition.id] = definition

    def get(self, workflow_id: str) -> WorkflowDefinition:
        return self._definitions[workflow_id]

    def enabled(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(definition for definition in self._definitions.values() if definition.enabled)

    def all(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(self._definitions.values())


from workflows.certificados_icbf.metadata import workflow_definition as certificados_icbf


workflow_registry = WorkflowRegistry([certificados_icbf])
WORKFLOW_DEFINITIONS = workflow_registry.all()
