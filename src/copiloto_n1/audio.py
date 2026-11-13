from __future__ import annotations

import argparse
import platform
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

try:
    import sounddevice as sd
    import soundfile as sf
except ImportError:  # pragma: no cover - depende do ambiente do usuário.
    sd = None
    sf = None

try:
    import pyaudiowpatch as pyaudio
except ImportError:  # pragma: no cover - depende do ambiente do usuário.
    pyaudio = None

TARGET_SAMPLE_RATE = 16000
TARGET_CHANNELS = 1
TARGET_BITS = 16


def _install_hint(pacote: str) -> str:
    cmd = f'"{sys.executable}" -m pip install {pacote}'
    return (
        f"Dependência ausente: {pacote}. "
        f"Este ambiente usa o interpretador: {sys.executable}. "
        f"Comando exato: {cmd}"
    )


def _device_label(dispositivo: int | str | None) -> str:
    if dispositivo is None:
        return "dispositivo padrão"
    return f"dispositivo {dispositivo}"


def _device_hint() -> str:
    return (
        "Dica provável: verifique a permissão de microfone do Windows, confirme que o dispositivo existe "
        "e não está em uso por outra aplicação, e teste a entrada padrão do sistema."
    )


def _resolve_input_device(dispositivo: int | str | None = None) -> int | None:
    if dispositivo is None:
        try:
            default_device = getattr(sd, "default", None)
            if default_device is not None and getattr(default_device, "device", None):
                return int(default_device.device[0])
        except Exception:
            return None
        return None
    try:
        return int(dispositivo)
    except (TypeError, ValueError):
        return None


def _raise_capture_error(exc: Exception, dispositivo: int | str | None, sample_rate: int, etapa: str) -> None:
    mensagem = (
        f"Erro ao {etapa} no { _device_label(dispositivo) } (sample rate={sample_rate}): "
        f"{type(exc).__name__}: {exc}. {_device_hint()}"
    )
    raise RuntimeError(mensagem) from exc


def _to_float32_mono(audio: np.ndarray) -> np.ndarray:
    arr = np.asarray(audio, dtype=np.float32)
    if arr.ndim == 2:
        if arr.shape[1] == 1:
            arr = arr[:, 0]
        else:
            arr = np.mean(arr, axis=1)
    return arr.astype(np.float32, copy=False)


def reamostrar_audio(audio: np.ndarray, sample_rate_atual: int, target_sample_rate: int = TARGET_SAMPLE_RATE) -> np.ndarray:
    if audio.size == 0:
        return np.empty(0, dtype=np.float32)
    if sample_rate_atual <= 0:
        raise ValueError(f"sample_rate_atual deve ser positivo; recebido {sample_rate_atual!r}")
    if sample_rate_atual == target_sample_rate:
        return np.asarray(audio, dtype=np.float32)

    orig = np.asarray(audio, dtype=np.float32)
    n_amostras_alvo = max(1, int(len(orig) * target_sample_rate / sample_rate_atual))
    indice_original = np.linspace(0, len(orig) - 1, num=n_amostras_alvo, dtype=np.float32)
    indice_alvo = np.arange(n_amostras_alvo, dtype=np.float32) * (sample_rate_atual / target_sample_rate)
    resampled = np.interp(indice_alvo, indice_original, orig)
    return resampled.astype(np.float32, copy=False)


def audio_mudo(audio: np.ndarray | list[float], limite: float = 0.01) -> bool:
    arr = np.asarray(audio, dtype=np.float32)
    if arr.size == 0:
        return True
    pico = float(np.max(np.abs(arr)))
    return pico < float(limite)


def _selecionar_dispositivo_loopback(pa: object, dispositivo: int | str | None = None) -> int:
    try:
        if dispositivo is not None:
            info = pa.get_device_info_by_index(int(dispositivo))
            if info.get("isLoopbackDevice") is True or info.get("maxInputChannels"):
                return int(dispositivo)
            raise RuntimeError(f"O dispositivo {dispositivo} não é um dispositivo de loopback válido do WASAPI.")

        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("isLoopbackDevice") is True:
                return i
        raise RuntimeError("Nenhum dispositivo de loopback WASAPI foi encontrado. Confirme que o áudio do sistema está disponível no Windows.")
    except Exception as exc:  # pragma: no cover - depende do ambiente do usuário.
        raise RuntimeError(
            "Não foi possível localizar um dispositivo de loopback do Windows: "
            f"{type(exc).__name__}: {exc}"
        ) from exc


def gravar_loopback(segundos: float, dispositivo: int | str | None = None, caminho: str | Path = "cliente.wav") -> Path:
    if segundos <= 0:
        raise ValueError("segundos deve ser maior que zero.")
    if pyaudio is None:
        raise RuntimeError(_install_hint("PyAudioWPatch"))
    if platform.system() != "Windows":
        raise RuntimeError("A captura de áudio do sistema via loopback do Windows exige o sistema operacional Windows.")

    pa = pyaudio.PyAudio()
    path = Path(caminho)
    path.parent.mkdir(parents=True, exist_ok=True)
    index = _selecionar_dispositivo_loopback(pa, dispositivo)
    frames: list[np.ndarray] = []
    stream = None
    try:
        stream = pa.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=TARGET_SAMPLE_RATE,
            frames_per_buffer=4096,
            input=True,
            input_device_index=index,
            as_loopback=True,
        )
        for _ in range(int((TARGET_SAMPLE_RATE / 4096) * segundos) + 1):
            chunk = stream.read(4096, exception_on_overflow=False)
            frames.append(np.frombuffer(chunk, dtype=np.float32))
    except Exception as exc:
        raise RuntimeError(
            f"Erro ao capturar o áudio do sistema no dispositivo {index}: {type(exc).__name__}: {exc}. "
            "Dica provável: confirme que o Windows está usando um dispositivo de saída com áudio disponível e que o loopback WASAPI está habilitado."
        ) from exc
    finally:
        if stream is not None:
            stream.stop_stream()
            stream.close()
        pa.terminate()

    if not frames:
        dados = np.empty(0, dtype=np.float32)
    else:
        dados = np.concatenate(frames).astype(np.float32, copy=False)
    dados = _to_float32_mono(dados)
    if dados.size and dados.shape[0] != 0:
        dados = reamostrar_audio(dados, TARGET_SAMPLE_RATE, TARGET_SAMPLE_RATE)
    sf.write(str(path), dados.astype(np.float32, copy=False), TARGET_SAMPLE_RATE, subtype="PCM_16")
    return path


def gravar_dupla(
    segundos: float,
    dispositivo_microfone: int | str | None = None,
    caminho_microfone: str | Path = "microfone.wav",
    caminho_loopback: str | Path = "cliente.wav",
) -> dict[str, Path]:
    with ThreadPoolExecutor(max_workers=2) as executor:
        futuro_microfone = executor.submit(gravar, segundos, dispositivo_microfone, caminho_microfone)
        futuro_cliente = executor.submit(gravar_loopback, segundos, None, caminho_loopback)
    return {"microfone": futuro_microfone.result(), "cliente": futuro_cliente.result()}


def listar_dispositivos() -> list[dict[str, object]]:
    if sd is None:
        raise RuntimeError(_install_hint("sounddevice"))
    try:
        dispositivos = sd.query_devices()
    except Exception as exc:  # pragma: no cover - depende do sistema do usuário.
        raise RuntimeError(f"Não foi possível listar dispositivos de áudio: {exc}") from exc

    saida: list[dict[str, object]] = []
    if isinstance(dispositivos, dict):
        dispositivos = [dispositivos]
    for idx, item in enumerate(dispositivos):
        if isinstance(item, dict):
            saida.append(
                {
                    "index": idx,
                    "name": item.get("name", f"Dispositivo {idx}"),
                    "input_channels": int(item.get("max_input_channels", 0) or 0),
                    "default_samplerate": float(item.get("default_samplerate", TARGET_SAMPLE_RATE) or TARGET_SAMPLE_RATE),
                }
            )
        else:
            saida.append({"index": idx, "name": str(item), "input_channels": 0, "default_samplerate": float(TARGET_SAMPLE_RATE)})
    return saida


class Gravador:
    def __init__(
        self,
        dispositivo: int | str | None = None,
        caminho: str | Path = "teste.wav",
        sample_rate: int = TARGET_SAMPLE_RATE,
        canais: int = TARGET_CHANNELS,
    ) -> None:
        self.dispositivo = _resolve_input_device(dispositivo) if dispositivo is None else int(dispositivo) if isinstance(dispositivo, int) else dispositivo
        self.caminho = Path(caminho)
        self.sample_rate = int(sample_rate)
        self.canais = int(canais)
        self._buffer: list[np.ndarray] = []
        self._stream = None
        self._sample_rate_uso = self.sample_rate
        self._canais_uso = self.canais
        self._ultimo_pico = 0.0
        self._ultimo_status: Exception | None = None

    def ultimo_pico(self) -> float:
        return float(self._ultimo_pico)

    def _callback(self, indata, frames, time_info, status):
        if status:
            self._ultimo_status = RuntimeError(f"Status de áudio: {status}")
            return
        chunk = _to_float32_mono(np.asarray(indata, dtype=np.float32))
        if chunk.size:
            self._ultimo_pico = max(self._ultimo_pico, float(np.max(np.abs(chunk))))
        self._buffer.append(chunk)

    def iniciar(self) -> None:
        if self._stream is not None:
            return

        if sd is None:
            raise RuntimeError(_install_hint("sounddevice"))
        if sf is None:
            raise RuntimeError(_install_hint("soundfile"))

        self._buffer.clear()
        self._ultimo_pico = 0.0
        self._ultimo_status = None
        device_index = _resolve_input_device(self.dispositivo)
        if device_index is not None:
            self.dispositivo = device_index

        taxas = []
        for taxa in (self.sample_rate, 44100, 48000, _default_device_rate(self.dispositivo)):
            if taxa > 0 and taxa not in taxas:
                taxas.append(taxa)

        ultimo_erro: Exception | None = None
        for taxa in taxas:
            try:
                canais = 1
                if self.canais == 1:
                    canais = 1
                self._stream = sd.InputStream(
                    device=self.dispositivo,
                    channels=canais,
                    samplerate=taxa,
                    dtype="float32",
                    callback=self._callback,
                )
                self._stream.start()
                self._sample_rate_uso = taxa
                self._canais_uso = canais
                return
            except Exception as exc:
                try:
                    if self._stream is not None:
                        self._stream.stop()
                        self._stream.close()
                except Exception:
                    pass
                self._stream = None
                ultimo_erro = exc
                continue

        if ultimo_erro is not None:
            _raise_capture_error(ultimo_erro, self.dispositivo, self.sample_rate, "capturar áudio")
        raise RuntimeError(f"Não foi possível iniciar a captura de áudio no { _device_label(self.dispositivo) }.")

    def parar(self) -> Path:
        if self._stream is None:
            return self.caminho

        try:
            self._stream.stop()
            self._stream.close()
        except Exception as exc:  # pragma: no cover - depende do ambiente do usuário.
            _raise_capture_error(exc, self.dispositivo, self._sample_rate_uso, "encerrar a captura")
        finally:
            self._stream = None

        if self._ultimo_status is not None:
            raise RuntimeError(str(self._ultimo_status))

        if not self._buffer:
            dados = np.empty(0, dtype=np.float32)
        else:
            dados = np.concatenate(self._buffer).astype(np.float32, copy=False)

        if self._sample_rate_uso != TARGET_SAMPLE_RATE:
            dados = reamostrar_audio(dados, self._sample_rate_uso, TARGET_SAMPLE_RATE)

        self.caminho.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(self.caminho), dados.astype(np.float32, copy=False), TARGET_SAMPLE_RATE, subtype="PCM_16")
        return self.caminho


def _default_device_rate(dispositivo: int | str | None) -> int:
    if sd is None:
        return TARGET_SAMPLE_RATE
    try:
        info = sd.query_devices(dispositivo, "input") if dispositivo is not None else sd.query_devices(kind="input")
    except Exception:
        return TARGET_SAMPLE_RATE

    if isinstance(info, dict):
        taxa = info.get("default_samplerate")
        if taxa:
            return int(float(taxa))
    if isinstance(info, (list, tuple)) and info:
        primeiro = info[0]
        if isinstance(primeiro, dict):
            taxa = primeiro.get("default_samplerate")
            if taxa:
                return int(float(taxa))
    return TARGET_SAMPLE_RATE


def gravar(segundos: float, dispositivo: int | str | None = None, caminho: str | Path = "teste.wav") -> Path:
    if segundos <= 0:
        raise ValueError("segundos deve ser maior que zero.")

    gravador = Gravador(dispositivo=dispositivo, caminho=caminho)
    gravador.iniciar()
    time.sleep(float(segundos))
    return gravador.parar()


def gravar_wav(caminho: str | Path = "teste.wav", segundos: float = 5.0, dispositivo: int | str | None = None) -> Path:
    return gravar(segundos=segundos, dispositivo=dispositivo, caminho=caminho)


def _cli_teste() -> int:
    caminho = Path("teste.wav")
    print(f"Gravando 5 segundos em {caminho} ...")
    try:
        caminho_salvo = gravar(5.0, caminho=caminho)
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    audio, sample_rate = sf.read(str(caminho_salvo), dtype="float32", always_2d=False)
    pico = float(np.max(np.abs(audio))) if audio.size else 0.0
    silencio = pico < 0.01
    duracao = len(audio) / float(sample_rate) if sample_rate else 0.0
    print(f"Arquivo: {caminho_salvo}")
    print(f"Duração: {duracao:.2f}s")
    print(f"Pico de volume: {pico:.6f}")
    print(f"Áudio mudo: {silencio}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Captura áudio do microfone e salva em WAV.")
    parser.add_argument("--listar", action="store_true", help="lista os dispositivos de entrada disponíveis")
    parser.add_argument("--teste", action="store_true", help="grava 5 segundos e salva teste.wav")
    parser.add_argument("--segundos", type=float, default=5.0, help="duração da gravação em segundos")
    parser.add_argument("--dispositivo", type=int, default=None, help="índice do dispositivo a capturar")
    parser.add_argument("--saida", type=str, default="teste.wav", help="arquivo WAV de saída")
    args = parser.parse_args()

    if args.listar:
        for item in listar_dispositivos():
            print(
                f"index={item['index']} | name={item['name']} | "
                f"input_channels={item['input_channels']} | default_samplerate={item['default_samplerate']}"
            )
        return 0

    if args.teste:
        return _cli_teste()

    caminho = gravar(args.segundos, dispositivo=args.dispositivo, caminho=args.saida)
    print(f"Arquivo salvo: {caminho}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
