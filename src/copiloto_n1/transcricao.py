from __future__ import annotations

import argparse
import inspect
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import av
except ImportError:  # pragma: no cover - depende do ambiente do usuário.
    av = None
else:
    try:
        av.open("dummy.wav", mode="r", metadata_errors="ignore")
    except TypeError:
        _av_open_original = av.open

        def _av_open_compat(*args, **kwargs):
            kwargs.pop("metadata_errors", None)
            return _av_open_original(*args, **kwargs)

        av.open = _av_open_compat

try:
    from faster_whisper import WhisperModel
except ImportError:  # pragma: no cover - depende do ambiente do usuário.
    WhisperModel = None


@dataclass
class SegmentoTranscricao:
    inicio: float
    fim: float
    texto: str

    @property
    def text(self) -> str:
        return self.texto


@dataclass
class ResultadoTranscricao:
    texto: str
    segmentos: list[SegmentoTranscricao] = field(default_factory=list)

    @property
    def text(self) -> str:
        return self.texto


_CACHE_MODELOS: dict[tuple[str, str, str], object] = {}
_MODEL_CACHE_DIR = Path(__file__).resolve().parents[2] / "data" / "whisper_models"
_MODEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _install_hint(pacote: str) -> str:
    cmd = f'"{sys.executable}" -m pip install {pacote}'
    return (
        f"Dependência ausente: {pacote}. "
        f"Este ambiente usa o interpretador: {sys.executable}. "
        f"Comando exato: {cmd}"
    )


def _obter_modelo(modelo: str, device: str, compute_type: str):
    if WhisperModel is None:
        raise RuntimeError(_install_hint("faster-whisper"))

    chave = (modelo, device, compute_type)
    if chave not in _CACHE_MODELOS:
        print(
            f"Modelo faster-whisper '{modelo}' não encontrado localmente. "
            f"Baixando para '{_MODEL_CACHE_DIR}'..."
        )
        try:
            kwargs = {"device": device, "compute_type": compute_type}
            try:
                params = inspect.signature(WhisperModel).parameters
            except (TypeError, ValueError):
                params = {}
            if "download_root" in params:
                kwargs["download_root"] = str(_MODEL_CACHE_DIR)
            _CACHE_MODELOS[chave] = WhisperModel(modelo, **kwargs)
        except Exception as exc:  # pragma: no cover - depende do ambiente do usuário.
            raise RuntimeError(
                f"Não foi possível carregar o modelo faster-whisper '{modelo}' no device '{device}' com compute_type '{compute_type}': {type(exc).__name__}: {exc}"
            ) from exc
    return _CACHE_MODELOS[chave]


def transcrever(
    caminho_wav: str | Path,
    modelo: str = "small",
    idioma: str = "pt",
    device: str = "cpu",
    compute_type: str = "int8",
) -> ResultadoTranscricao:
    if WhisperModel is None:
        raise RuntimeError(_install_hint("faster-whisper"))

    path = Path(caminho_wav)
    if not path.exists():
        raise FileNotFoundError(f"Arquivo de áudio não encontrado: {path}")

    try:
        modelo_obj = _obter_modelo(modelo, device, compute_type)
        segmentos, _informacao = modelo_obj.transcribe(
            str(path),
            language=idioma,
            beam_size=5,
            vad_filter=True,
        )
    except FileNotFoundError:
        raise
    except Exception as exc:
        raise RuntimeError(
            f"Falha na transcrição do arquivo '{path}' com modelo '{modelo}' e idioma '{idioma}': {type(exc).__name__}: {exc}"
        ) from exc

    segmentos_norm = []
    textos = []
    for segmento in segmentos:
        texto = getattr(segmento, "text", "") or ""
        texto_limpo = texto.strip()
        if not texto_limpo:
            continue
        segmentos_norm.append(
            SegmentoTranscricao(
                inicio=float(getattr(segmento, "start", 0.0) or 0.0),
                fim=float(getattr(segmento, "end", 0.0) or 0.0),
                texto=texto_limpo,
            )
        )
        textos.append(texto_limpo)

    return ResultadoTranscricao(texto=" ".join(textos).strip(), segmentos=segmentos_norm)


def intercalar_segmentos(
    analista: list[SegmentoTranscricao | dict[str, object]],
    cliente: list[SegmentoTranscricao | dict[str, object]],
    rotulo_analista: str = "Analista",
    rotulo_cliente: str = "Cliente",
) -> list[dict[str, object]]:
    def _normalizar(segmento: SegmentoTranscricao | dict[str, object]) -> dict[str, object]:
        if isinstance(segmento, SegmentoTranscricao):
            return {
                "inicio": float(segmento.inicio),
                "fim": float(segmento.fim),
                "texto": segmento.texto,
            }
        return {
            "inicio": float(segmento.get("inicio", 0.0) or 0.0),
            "fim": float(segmento.get("fim", 0.0) or 0.0),
            "texto": str(segmento.get("texto", "") or "").strip(),
        }

    itens: list[dict[str, object]] = []
    for segmento in analista:
        item = _normalizar(segmento)
        texto = str(item["texto"]).strip()
        if not texto:
            continue
        itens.append({**item, "rotulo": rotulo_analista, "texto": texto})
    for segmento in cliente:
        item = _normalizar(segmento)
        texto = str(item["texto"]).strip()
        if not texto:
            continue
        itens.append({**item, "rotulo": rotulo_cliente, "texto": texto})

    itens.sort(key=lambda item: (float(item["inicio"]), float(item["fim"]), str(item["rotulo"])))
    return itens


def formatar_conversa_intercalada(
    analista: list[SegmentoTranscricao | dict[str, object]],
    cliente: list[SegmentoTranscricao | dict[str, object]],
    rotulo_analista: str = "Analista",
    rotulo_cliente: str = "Cliente",
) -> str:
    linhas: list[str] = []
    for item in intercalar_segmentos(analista, cliente, rotulo_analista, rotulo_cliente):
        texto = str(item["texto"]).strip()
        if not texto:
            continue
        linhas.append(f"{str(item['rotulo'])}: {texto}")
    return "\n".join(linhas)


def transcrever_arquivo(
    caminho: str | Path,
    model_size: str = "small",
    language: str = "pt",
    device: str = "cpu",
    compute_type: str = "int8",
) -> str:
    resultado = transcrever(
        caminho_wav=caminho,
        modelo=model_size,
        idioma=language,
        device=device,
        compute_type=compute_type,
    )
    return resultado.texto


def main() -> int:
    parser = argparse.ArgumentParser(description="Transcreve um arquivo WAV usando faster-whisper.")
    parser.add_argument("arquivo", type=str, help="caminho do arquivo WAV")
    parser.add_argument("--model", default="small", help="modelo faster-whisper (ex.: tiny, base, small)")
    parser.add_argument("--language", default="pt", help="idioma do áudio")
    parser.add_argument("--device", default="cpu", help="cpu ou cuda")
    parser.add_argument("--compute-type", default="int8", help="compute type do faster-whisper")
    args = parser.parse_args()

    inicio = time.perf_counter()
    try:
        resultado = transcrever(
            caminho_wav=args.arquivo,
            modelo=args.model,
            idioma=args.language,
            device=args.device,
            compute_type=args.compute_type,
        )
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    tempo = time.perf_counter() - inicio
    print(resultado.texto or "[Sem texto reconhecido]")
    print(f"Tempo de processamento: {tempo:.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
