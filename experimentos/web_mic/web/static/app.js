const recordButton = document.getElementById('recordButton');
const copyButton = document.getElementById('copyButton');
const statusText = document.getElementById('statusText');
const transcript = document.getElementById('transcript');
const errorBox = document.getElementById('errorBox');

let stream = null;
let mediaRecorder = null;
let chunks = [];
let isRecording = false;

function setStatus(message, isError = false) {
  statusText.textContent = message;
  statusText.style.color = isError ? '#b91c1c' : '#1f2937';
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.add('visible');
  setStatus('Erro', true);
}

function clearError() {
  errorBox.textContent = '';
  errorBox.classList.remove('visible');
}

function getAudioExtension(blobType) {
  const type = String(blobType || '').toLowerCase();
  if (type.includes('ogg')) return 'ogg';
  if (type.includes('mp4')) return 'mp4';
  if (type.includes('webm')) return 'webm';
  return 'webm';
}

async function startRecording() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    showError('Seu navegador não suporta acesso ao microfone.');
    return;
  }

  try {
    clearError();
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    const mimeTypeOptions = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg'
    ];

    const supportedMimeType = mimeTypeOptions.find((type) => MediaRecorder.isTypeSupported(type)) || '';
    const recorderOptions = supportedMimeType ? { mimeType: supportedMimeType } : undefined;

    mediaRecorder = new MediaRecorder(stream, recorderOptions);
    chunks = [];

    mediaRecorder.ondataavailable = (event) => {
      if (event.data && event.data.size > 0) {
        chunks.push(event.data);
      }
    };

    mediaRecorder.onstop = async () => {
      const blob = new Blob(chunks, {
        type: mediaRecorder.mimeType || 'audio/webm'
      });

      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }

      recordButton.disabled = false;
      setStatus('Transcrevendo...');

      try {
        const formData = new FormData();
        const fileName = `gravacao_${new Date().toISOString().replace(/[:.]/g, '-')}.${blob.type.includes('ogg') ? 'ogg' : blob.type.includes('mp4') ? 'mp4' : 'webm'}`;
        formData.append('audio', blob, fileName);

        const response = await fetch('/transcrever', {
          method: 'POST',
          body: formData
        });

        const payload = await response.json().catch(() => ({}));

        if (!response.ok) {
          throw new Error(payload.erro || payload.detail || 'Erro na transcrição');
        }

        const texto = payload.texto || payload.aviso || '';
        transcript.value = texto;

        if (payload.aviso) {
          showError(payload.aviso);
        } else {
          clearError();
          setStatus('Pronto');
        }
      } catch (error) {
        console.error(error);
        showError(`Erro ao transcrever: ${error.message}`);
      } finally {
        isRecording = false;
        recordButton.disabled = false;
        recordButton.textContent = 'Gravar';
        mediaRecorder = null;
      }
    };

    mediaRecorder.start();
    isRecording = true;
    recordButton.textContent = 'Parar';
    setStatus('Gravando...');
  } catch (error) {
    console.error(error);
    showError(`Erro ao acessar o microfone: ${error.name}: ${error.message}`);
  }
}

function stopRecording() {
  if (!mediaRecorder) {
    return;
  }

  mediaRecorder.stop();
  recordButton.disabled = true;
  setStatus('Finalizando gravação...');
}

recordButton.addEventListener('click', () => {
  if (isRecording) {
    stopRecording();
    return;
  }

  startRecording();
});

copyButton.addEventListener('click', async () => {
  const text = transcript.value;
  if (!text.trim()) {
    showError('Não há texto para copiar.');
    return;
  }

  try {
    await navigator.clipboard.writeText(text);
    setStatus('Texto copiado');
  } catch (error) {
    console.error(error);
    showError(`Não foi possível copiar: ${error.message}`);
  }
});

if (!window.MediaRecorder) {
  showError('Este navegador não suporta gravação de áudio do microfone.');
  recordButton.disabled = true;
}
