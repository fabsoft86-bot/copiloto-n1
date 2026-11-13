from copiloto_n1.adaptadores.arquivo import AdaptadorArquivo
from copiloto_n1.adaptadores.base import AdaptadorHelpdesk
from copiloto_n1.adaptadores.factory import criar_adaptador
from copiloto_n1.adaptadores.glpi import AdaptadorGLPI
from copiloto_n1.adaptadores.jira import AdaptadorJira

__all__ = [
    "AdaptadorArquivo",
    "AdaptadorGLPI",
    "AdaptadorHelpdesk",
    "AdaptadorJira",
    "criar_adaptador",
]
