from app.workflow_contract import WorkflowDefinition
from workflows.certificados_icbf.view import CertificadosIcbfView


workflow_definition = WorkflowDefinition(
    id="certificados_icbf",
    name="Certificados ICBF",
    description="Procesamiento y generación de certificados ICBF.",
    view_class=CertificadosIcbfView,
    version="1",
    enabled=True,
)
