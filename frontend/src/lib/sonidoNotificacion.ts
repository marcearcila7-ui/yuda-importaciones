// Beep corto de dos tonos para avisar que llegó un mensaje nuevo al chat de
// cubicaje. Sintetizado con Web Audio API (sin archivo de audio que cargar).
// La preferencia de encendido/apagado se guarda en localStorage: es algo
// personal de quien usa el navegador, no de la cotización.

const CLAVE_SONIDO = 'yuda_sonido_cubicaje'

export function sonidoActivado(): boolean {
  try {
    const guardado = localStorage.getItem(CLAVE_SONIDO)
    return guardado === null ? true : guardado === '1'
  } catch {
    return true
  }
}

export function guardarSonidoActivado(activado: boolean): void {
  try {
    localStorage.setItem(CLAVE_SONIDO, activado ? '1' : '0')
  } catch {
    // localStorage bloqueado (privado/incógnito): la preferencia no persiste
    // entre recargas, pero no hay nada más que hacer al respecto acá.
  }
}

let contexto: AudioContext | null = null

export function reproducirSonidoNotificacion(): void {
  try {
    if (!contexto) {
      const AudioContextCtor = window.AudioContext || (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext
      contexto = new AudioContextCtor()
    }
    if (contexto.state === 'suspended') contexto.resume()
    const ahora = contexto.currentTime
    // Dos notas cortas ascendentes (tipo "ding-dong" de mensaje), no un solo
    // tono plano que se confunda con cualquier pitido del sistema.
    ;[
      { freq: 880, inicio: 0 },
      { freq: 1108.73, inicio: 0.11 },
    ].forEach(({ freq, inicio }) => {
      const osc = contexto!.createOscillator()
      const ganancia = contexto!.createGain()
      osc.type = 'sine'
      osc.frequency.value = freq
      ganancia.gain.setValueAtTime(0.0001, ahora + inicio)
      ganancia.gain.exponentialRampToValueAtTime(0.2, ahora + inicio + 0.02)
      ganancia.gain.exponentialRampToValueAtTime(0.0001, ahora + inicio + 0.18)
      osc.connect(ganancia)
      ganancia.connect(contexto!.destination)
      osc.start(ahora + inicio)
      osc.stop(ahora + inicio + 0.2)
    })
  } catch {
    // Sin soporte de Web Audio, o el navegador bloqueó el audio por falta de
    // interacción del usuario todavía: el mensaje igual llega, solo sin
    // sonido esta vez.
  }
}
